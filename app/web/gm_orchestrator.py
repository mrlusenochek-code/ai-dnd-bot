import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gm import generate_from_prompt, generate_lore
from app.combat.apply_machine import apply_combat_machine_commands
from app.combat.state import current_turn_label, get_combat
from app.combat.sync_pcs import sync_pcs_from_chars
from app.core.log_context import request_id_var, session_id_var
from app.db.connection import AsyncSessionLocal
from app.db.models import Character, Event, Player, Session
from app.gm import narration, service as gm_service
from app.web.combat_bridge import _maybe_apply_opening_combat_action
from app.web.db_helpers import get_session, list_session_players
from app.web.gameplay_helpers import (
    GM_DRAFT_NUM_PREDICT,
    GM_FINAL_NUM_PREDICT,
    GM_OLLAMA_TIMEOUT_SECONDS,
    _looks_like_refusal,
    _player_uid,
    add_system_event,
)
from app.web.machine_extract import _extract_machine_commands, _trim_for_log
from app.web.session_lock import get_session_lock
from app.web.session_state import _ensure_settings, _get_phase, _initialize_pc_positions, _set_phase, settings_get, settings_set
from app.web.state_builder import _broadcast_state_unlocked, broadcast_state
from app.web.utils import _clamp, as_int

logger = logging.getLogger("app.web.server")
GM_CONTEXT_EVENTS = max(1, int(os.getenv("GM_CONTEXT_EVENTS", "20")))


def _new_request_id() -> str:
    return uuid.uuid4().hex


async def run_two_pass(
    db: AsyncSession,
    sess: Session,
    session_id: str,
    *,
    draft_prompt: str,
    default_actor_uid: Optional[int],
    previous_gm_text: str = "",
) -> tuple[str, dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    import app.web.server as server_mod

    settings = server_mod._ensure_settings(sess)
    location_fallback = server_mod.narration.build_location_block(settings, session_id)
    combat_state = server_mod.get_combat(session_id)
    combat_active = bool(combat_state and combat_state.active)
    return await gm_service.run_two_pass(
        db,
        sess,
        session_id=session_id,
        draft_prompt=draft_prompt,
        default_actor_uid=default_actor_uid,
        previous_gm_text=previous_gm_text,
        location_fallback=location_fallback,
        timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
        draft_num_predict=GM_DRAFT_NUM_PREDICT,
        final_num_predict=GM_FINAL_NUM_PREDICT,
        combat_active=combat_active,
        load_actor_context=server_mod._load_actor_context,
        compute_check_mod=server_mod._compute_check_mod,
        roll_check=server_mod._roll_check,
        build_check_result=server_mod._build_check_result,
        character_xp_gain_from_check=server_mod._character_xp_gain_from_check,
        level_from_xp_total=server_mod._level_from_xp_total,
        skill_xp_gain=server_mod._skill_xp_gain,
        xp_to_next_skill_rank=server_mod._xp_to_next_skill_rank,
        clamp_fn=_clamp,
        as_int_fn=as_int,
        get_phase_fn=_get_phase,
        trim_for_log_fn=_trim_for_log,
        looks_like_combat_drift_fn=server_mod._looks_like_combat_drift,
        llm_generate=server_mod.generate_from_prompt,
        logger=logger,
    )


async def run_turn_gm(session_id: str, expected_action_id: str) -> None:
    from app.web.server import (
        _apply_inventory_machine_commands,
        _apply_zone_set_machine_commands,
        _build_actor_list_for_prompt,
        _build_positions_block_for_prompt,
        _build_turn_draft_prompt,
        _clear_current_action_id,
        _detect_chat_combat_action,
        _emit_check_results_if_enabled,
        _find_latest_gm_text,
        _get_current_action_id,
        _is_free_turns,
        _load_actor_context,
        advance_turn,
        utcnow,
    )

    tok_rid = request_id_var.set(_new_request_id())
    tok_sid = session_id_var.set(session_id)
    try:
        lock = get_session_lock(session_id)
        async with lock:
            async with AsyncSessionLocal() as db:
                sess = await get_session(db, session_id)
                if not sess:
                    return
                if _is_free_turns(sess):
                    return
                if _get_phase(sess) != "gm_pending":
                    return
                if _get_current_action_id(sess) != expected_action_id:
                    return

                q_events = await db.execute(
                    select(Event)
                    .where(Event.session_id == sess.id)
                    .order_by(Event.created_at.desc())
                    .limit(GM_CONTEXT_EVENTS)
                )
                events_desc = q_events.scalars().all()
                opening_combat_action: Optional[str] = None
                opening_player_uid: Optional[int] = None
                opening_player_id: Optional[uuid.UUID] = sess.current_player_id if isinstance(sess.current_player_id, uuid.UUID) else None
                for ev in events_desc:
                    payload_raw = ev.result_json if isinstance(ev.result_json, dict) else {}
                    if str(payload_raw.get("type") or "").strip().lower() != "player_action":
                        continue
                    raw_text = str(payload_raw.get("raw_text") or "").strip()
                    detected = _detect_chat_combat_action(raw_text)
                    if detected is None:
                        continue
                    opening_combat_action = detected
                    actor_uid_raw = payload_raw.get("actor_uid")
                    if actor_uid_raw is not None:
                        try:
                            opening_player_uid = int(actor_uid_raw)
                        except Exception:
                            pass
                    actor_player_id_raw = str(payload_raw.get("actor_player_id") or "").strip()
                    if actor_player_id_raw:
                        try:
                            opening_player_id = uuid.UUID(actor_player_id_raw)
                        except Exception:
                            pass
                    break
                context_events: list[str] = []
                for ev in reversed(events_desc):
                    payload_raw = ev.result_json if isinstance(ev.result_json, dict) else {}
                    msg = str(ev.message_text or "").strip()
                    if str(payload_raw.get("type") or "").strip().lower() == "player_action":
                        raw_text = payload_raw.get("raw_text")
                        if isinstance(raw_text, str) and raw_text.strip():
                            msg = raw_text.strip()
                    if not msg:
                        continue
                    if msg.startswith("[SYSTEM] 📜 История:"):
                        continue
                    if _looks_like_refusal(msg):
                        continue
                    context_events.append(msg)
                if not context_events:
                    context_events = ["(контекст пуст)"]
                previous_gm_text = _find_latest_gm_text(context_events)

                story = settings_get(sess, "story", {}) or {}
                if not isinstance(story, dict):
                    story = {}
                story_title = str(story.get("story_title") or "").strip() or str(sess.title or "Campaign").strip() or "Campaign"

                uid_map, chars_by_uid, _skill_mods_by_char = await _load_actor_context(db, sess)
                actors_block = _build_actor_list_for_prompt(uid_map, chars_by_uid)
                positions_block = _build_positions_block_for_prompt(sess, uid_map, chars_by_uid)
                cur_uid: Optional[int] = None
                if sess.current_player_id:
                    q_cur_player = await db.execute(select(Player).where(Player.id == sess.current_player_id))
                    cur_player = q_cur_player.scalar_one_or_none()
                    cur_uid = _player_uid(cur_player)
                if opening_player_uid is None:
                    opening_player_uid = cur_uid
                draft_prompt = _build_turn_draft_prompt(
                    session_title=story_title,
                    context_events=context_events,
                    actor_uid=cur_uid,
                    actors_block=actors_block,
                    positions_block=positions_block,
                )
                gm_text, _draft_meta, _final_meta, _checks, _check_results = await run_two_pass(
                    db,
                    sess,
                    session_id=session_id,
                    draft_prompt=draft_prompt,
                    default_actor_uid=cur_uid,
                    previous_gm_text=previous_gm_text,
                )

                await db.refresh(sess)
                if _get_current_action_id(sess) != expected_action_id:
                    logger.info("gm final dropped due to action mismatch", extra={"action": {"expected_action_id": expected_action_id}})
                    return

                gm_text = gm_text.strip()
                before_state = get_combat(session_id)
                before_active = bool(before_state and before_state.active)
                combat_log_ui_patch = apply_combat_machine_commands(session_id, gm_text)
                sync_pcs_from_chars(session_id, chars_by_uid)
                after_state = get_combat(session_id)
                after_active = bool(after_state and after_state.active)
                if (not before_active) and after_active and opening_player_id is not None:
                    combat_log_ui_patch = _maybe_apply_opening_combat_action(
                        session_id=session_id,
                        combat_action=opening_combat_action,
                        player_uid=opening_player_uid,
                        player_id=opening_player_id,
                        combat_patch=combat_log_ui_patch,
                    )
                if combat_log_ui_patch is not None:
                    combat_state = get_combat(session_id)
                    if combat_state is not None and combat_state.active:
                        if combat_log_ui_patch.get("reset") is True:
                            combat_state.round_no = 1
                            combat_state.turn_index = 0
                        combat_log_ui_patch["status"] = (
                            f"⚔ Бой • Раунд {combat_state.round_no} • Ход: {current_turn_label(combat_state)}"
                        )
                gm_text_visible, inv_commands, zone_set_commands = _extract_machine_commands(gm_text)
                await _apply_inventory_machine_commands(db, sess, inv_commands)
                await _apply_zone_set_machine_commands(db, sess, zone_set_commands)
                gm_text_visible = gm_text_visible.strip()
                if gm_text_visible and not _looks_like_refusal(gm_text_visible):
                    await add_system_event(
                        db,
                        sess,
                        f"🧙 GM: {gm_text_visible}",
                        result_json={
                            "type": "gm_reply",
                            "checks": _checks,
                            "check_results": _check_results,
                            "inv_commands": inv_commands,
                            "zone_set_commands": zone_set_commands,
                        },
                    )
                elif not inv_commands and not zone_set_commands:
                    await add_system_event(db, sess, "🧙 GM: (модель отказала. Переформулируй действие проще, без жести и откровенных деталей.)")
                await _emit_check_results_if_enabled(db, sess, _check_results)

                nxt = await advance_turn(db, sess)
                if nxt:
                    sess.current_player_id = nxt.player_id
                    sess.turn_started_at = utcnow()
                    combat_active = bool(get_combat(session_id) and get_combat(session_id).active)
                    if not combat_active:
                        await add_system_event(db, sess, f"Следующий ход: игрок #{nxt.join_order}.")
                _set_phase(sess, "turns")
                _clear_current_action_id(sess)
                await db.commit()

        await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_log_ui_patch)
    except Exception:
        logger.exception("auto gm reply task failed")
    finally:
        request_id_var.reset(tok_rid)
        session_id_var.reset(tok_sid)


async def run_lore_generation(session_id: str) -> None:
    from app.web.server import (
        _clear_current_action_id,
        _clear_paused_remaining,
        _find_latest_gm_text,
        _get_free_round,
        _get_round_actions,
        _infer_initial_zone,
        _is_free_turns,
        _set_phase,
        _should_use_round_mode,
    )

    tok_rid = request_id_var.set(_new_request_id())
    tok_sid = session_id_var.set(session_id)
    try:
        logger.info("lore generation started")
        async with AsyncSessionLocal() as db:
            sess = await get_session(db, session_id)
            if not sess:
                return

            story = settings_get(sess, "story", {}) or {}
            if not (isinstance(story, dict) and story.get("story_configured") is True):
                return

            lore_text = str(settings_get(sess, "lore_text", "") or "").strip()
            lore_posted = bool(settings_get(sess, "lore_posted", False))

            if not lore_text and not bool(settings_get(sess, "lore_generated", False)):
                story_setting = str(story.get("story_setting") or "").strip()
                story_title = str(story.get("story_title") or "").strip() or str(sess.title or "Campaign").strip() or "Campaign"
                lore_resp = await generate_lore(
                    session_title=story_title,
                    setting_text=story_setting,
                    timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
                )
                logger.info(
                    "lore generation call",
                    extra={
                        "action": {
                            "llm_finish_reason": lore_resp.get("finish_reason"),
                            "llm_usage": lore_resp.get("usage"),
                        }
                    },
                )
                lore_text = str(lore_resp.get("text") or "")
                lore_text = lore_text.strip()
                if not lore_text:
                    _set_phase(sess, "lore_pending")
                    _clear_current_action_id(sess)
                    sess.current_player_id = None
                    sess.turn_started_at = None
                    await db.commit()
                    await add_system_event(db, sess, "Лор не сгенерирован: модель отказала. Измени сеттинг или нажми Сгенерировать лор.")
                    await broadcast_state(session_id)
                    return
                if _looks_like_refusal(lore_text):
                    _set_phase(sess, "lore_pending")
                    _clear_current_action_id(sess)
                    sess.current_player_id = None
                    sess.turn_started_at = None
                    await db.commit()
                    await add_system_event(db, sess, "Лор не сгенерирован: модель отказала. Измени сеттинг или нажми Сгенерировать лор.")
                    await broadcast_state(session_id)
                    return

                settings_set(sess, "lore_text", lore_text)
                settings_set(sess, "lore_generated", True)
                settings_set(sess, "lore_generated_at", datetime.now(timezone.utc).isoformat())
                settings_set(sess, "lore_posted", False)
                lore_posted = False

            if lore_text and not lore_posted:
                await add_system_event(db, sess, f"📜 История:\n{lore_text}")
                settings_set(sess, "lore_posted", True)

            sps = await list_session_players(db, sess, active_only=True)
            q_recent_events = await db.execute(
                select(Event)
                .where(Event.session_id == sess.id)
                .order_by(Event.created_at.desc())
                .limit(20)
            )
            recent_events = [e.message_text for e in reversed(q_recent_events.scalars().all()) if e.message_text]
            initial_zone = _infer_initial_zone(lore_text, _find_latest_gm_text(recent_events))
            _initialize_pc_positions(sess, [sp.player_id for sp in sps], initial_zone)
            free_turns = _should_use_round_mode(sess, sps)
            settings_set(sess, "free_turns", free_turns)
            if free_turns:
                _set_phase(sess, "collecting_actions")
                _clear_current_action_id(sess)
                settings_set(sess, "free_round", 1)
                settings_set(sess, "round_actions", {})
                sess.current_player_id = None
                sess.turn_started_at = None
                _clear_paused_remaining(sess)
                await db.commit()
                await add_system_event(db, sess, f"Раунд {_get_free_round(sess)}: каждый отправьте ОДНО сообщение с действием.")
            else:
                _set_phase(sess, "turns")
                _clear_current_action_id(sess)
                first = sps[0] if sps else None
                sess.current_player_id = first.player_id if first else None
                sess.turn_started_at = utcnow() if first else None
                _clear_paused_remaining(sess)
                await db.commit()
                if first:
                    await add_system_event(db, sess, f"Игра началась. Ход игрока #{first.join_order}.")
            await db.commit()

        logger.info("lore generation finished")
        await broadcast_state(session_id)
    except Exception:
        logger.exception("auto lore task failed")
    finally:
        request_id_var.reset(tok_rid)
        session_id_var.reset(tok_sid)


async def run_round_gm(session_id: str, expected_action_id: str) -> None:
    from app.web.server import (
        _apply_inventory_machine_commands,
        _apply_zone_set_machine_commands,
        _build_actor_list_for_prompt,
        _build_positions_block_for_prompt,
        _build_round_draft_prompt,
        _clear_current_action_id,
        _clear_paused_remaining,
        _detect_chat_combat_action,
        _emit_check_results_if_enabled,
        _find_latest_gm_text,
        _get_current_action_id,
        _get_free_round,
        _get_round_actions,
        _is_free_turns,
        _load_actor_context,
        _should_use_round_mode,
        utcnow,
    )

    tok_rid = request_id_var.set(_new_request_id())
    tok_sid = session_id_var.set(session_id)
    try:
        lock = get_session_lock(session_id)
        async with lock:
            async with AsyncSessionLocal() as db:
                sess = await get_session(db, session_id)
                if not sess:
                    return
                if not _is_free_turns(sess) or _get_phase(sess) != "gm_pending":
                    return
                if _get_current_action_id(sess) != expected_action_id:
                    return

                story = settings_get(sess, "story", {}) or {}
                if not isinstance(story, dict):
                    story = {}
                difficulty = str(story.get("difficulty") or "medium").strip().lower()
                gm_notes = str(story.get("gm_notes") or "").strip()
                lore_text = str(settings_get(sess, "lore_text", "") or "").strip()

                round_actions = _get_round_actions(sess)
                if not round_actions:
                    _set_phase(sess, "collecting_actions")
                    _clear_current_action_id(sess)
                    await db.commit()
                    await _broadcast_state_unlocked(session_id)
                    return

                sps = await list_session_players(db, sess, active_only=True)
                players_by_id: dict[uuid.UUID, Player] = {}
                if sps:
                    q_players = await db.execute(select(Player).where(Player.id.in_([sp.player_id for sp in sps])))
                    players_by_id = {p.id: p for p in q_players.scalars().all()}

                player_actions: list[str] = []
                chars_by_player_id: dict[uuid.UUID, Character] = {}
                opening_combat_action: Optional[str] = None
                opening_player_uid: Optional[int] = None
                opening_player_id: Optional[uuid.UUID] = None
                if sps:
                    q_chars = await db.execute(
                        select(Character).where(
                            Character.session_id == sess.id,
                            Character.player_id.in_([sp.player_id for sp in sps]),
                        )
                    )
                    chars_by_player_id = {c.player_id: c for c in q_chars.scalars().all()}
                for sp in sps:
                    action_text = str(round_actions.get(str(sp.player_id), "") or "").strip()
                    if not action_text:
                        continue
                    pl = players_by_id.get(sp.player_id)
                    ch = chars_by_player_id.get(sp.player_id)
                    pname = (
                        str(ch.name).strip()
                        if ch and str(ch.name or "").strip()
                        else (pl.display_name if pl else f"Игрок #{sp.join_order}")
                    )
                    player_actions.append(f"{pname} (#{sp.join_order}): {action_text}")
                    if opening_combat_action is None:
                        detected = _detect_chat_combat_action(action_text)
                        if detected is not None:
                            opening_combat_action = detected
                            opening_player_uid = _player_uid(pl)
                            opening_player_id = sp.player_id

                q_events = await db.execute(
                    select(Event)
                    .where(Event.session_id == sess.id)
                    .order_by(Event.created_at.desc())
                    .limit(40)
                )
                events_desc = q_events.scalars().all()
                recent_events = [e.message_text for e in reversed(events_desc) if e.message_text]
                previous_gm_text = _find_latest_gm_text(recent_events)

                story_title = str(story.get("story_title") or "").strip() or str(sess.title or "Campaign").strip() or "Campaign"
                uid_map, chars_by_uid, _skill_mods_by_char = await _load_actor_context(db, sess)
                actors_block = _build_actor_list_for_prompt(uid_map, chars_by_uid)
                positions_block = _build_positions_block_for_prompt(sess, uid_map, chars_by_uid)
                draft_prompt = _build_round_draft_prompt(
                    session_title=story_title,
                    lore_text=lore_text,
                    recent_events=recent_events,
                    player_actions=player_actions,
                    master_notes=gm_notes,
                    difficulty=difficulty,
                    actors_block=actors_block,
                    positions_block=positions_block,
                )
                gm_text, _draft_meta, _final_meta, _checks, _check_results = await run_two_pass(
                    db,
                    sess,
                    session_id=session_id,
                    draft_prompt=draft_prompt,
                    default_actor_uid=None,
                    previous_gm_text=previous_gm_text,
                )

                await db.refresh(sess)
                if _get_current_action_id(sess) != expected_action_id:
                    logger.info("round final dropped due to action mismatch", extra={"action": {"expected_action_id": expected_action_id}})
                    return

                gm_text = gm_text.strip()
                before_state = get_combat(session_id)
                before_active = bool(before_state and before_state.active)
                combat_log_ui_patch = apply_combat_machine_commands(session_id, gm_text)
                sync_pcs_from_chars(session_id, chars_by_uid)
                after_state = get_combat(session_id)
                after_active = bool(after_state and after_state.active)
                if (not before_active) and after_active and opening_player_id is not None:
                    combat_log_ui_patch = _maybe_apply_opening_combat_action(
                        session_id=session_id,
                        combat_action=opening_combat_action,
                        player_uid=opening_player_uid,
                        player_id=opening_player_id,
                        combat_patch=combat_log_ui_patch,
                    )
                if combat_log_ui_patch is not None:
                    combat_state = get_combat(session_id)
                    if combat_state is not None and combat_state.active:
                        if combat_log_ui_patch.get("reset") is True:
                            combat_state.round_no = 1
                            combat_state.turn_index = 0
                        combat_log_ui_patch["status"] = (
                            f"⚔ Бой • Раунд {combat_state.round_no} • Ход: {current_turn_label(combat_state)}"
                        )
                gm_text_visible, inv_commands, zone_set_commands = _extract_machine_commands(gm_text)
                await _apply_inventory_machine_commands(db, sess, inv_commands)
                await _apply_zone_set_machine_commands(db, sess, zone_set_commands)
                gm_text_visible = gm_text_visible.strip()
                if gm_text_visible:
                    await add_system_event(
                        db,
                        sess,
                        f"🧙 Мастер: {gm_text_visible}",
                        result_json={
                            "type": "gm_reply",
                            "checks": _checks,
                            "check_results": _check_results,
                            "inv_commands": inv_commands,
                            "zone_set_commands": zone_set_commands,
                        },
                    )
                await _emit_check_results_if_enabled(db, sess, _check_results)

                sps_active = await list_session_players(db, sess, active_only=True)
                if _should_use_round_mode(sess, sps_active):
                    next_round = _get_free_round(sess) + 1
                    settings_set(sess, "free_turns", True)
                    settings_set(sess, "round_actions", {})
                    _set_phase(sess, "collecting_actions")
                    settings_set(sess, "free_round", next_round)
                    _clear_current_action_id(sess)
                    sess.current_player_id = None
                    sess.turn_started_at = None
                    _clear_paused_remaining(sess)
                    await db.commit()
                    await add_system_event(db, sess, f"Раунд {next_round}: каждый отправьте ОДНО сообщение с действием.")
                    await db.commit()
                else:
                    settings_set(sess, "free_turns", False)
                    settings_set(sess, "round_actions", {})
                    _set_phase(sess, "turns")
                    _clear_current_action_id(sess)
                    first = sps_active[0] if sps_active else None
                    sess.current_player_id = first.player_id if first else None
                    sess.turn_started_at = utcnow() if first else None
                    _clear_paused_remaining(sess)
                    await db.commit()
                    if first:
                        combat_active = bool(get_combat(session_id) and get_combat(session_id).active)
                        if not combat_active:
                            await add_system_event(db, sess, f"Следующий ход: игрок #{first.join_order}.")
                    await db.commit()

        await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_log_ui_patch)
    except Exception:
        logger.exception("auto round task failed")
        try:
            async with AsyncSessionLocal() as db:
                sess = await get_session(db, session_id)
                if sess and _is_free_turns(sess):
                    _set_phase(sess, "collecting_actions")
                    _clear_current_action_id(sess)
                    await db.commit()
            await broadcast_state(session_id)
        except Exception:
            logger.exception("auto round recovery failed")
    finally:
        request_id_var.reset(tok_rid)
        session_id_var.reset(tok_sid)
