import json
from typing import Any, Optional

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.combat.state import get_combat, restore_combat_state, snapshot_combat_state
from app.db.models import Character, Event, Player, Session, Skill
from app.web.constants import COMBAT_LOG_HISTORY_KEY, COMBAT_STATE_KEY, MAX_COMBAT_LOG_LINES
from app.web.session_state import (
    _ensure_settings,
    settings_get,
    _get_ready_map,
    _get_init_map,
    _get_last_seen_map,
    _get_pc_positions,
    _get_phase,
    _initiative_fixed,
)

from app.web.session_lock import get_session_lock
from app.web.ws_manager import manager


def _get_combat_log_history(sess: Session) -> dict:
    st = _ensure_settings(sess)
    raw = st.get(COMBAT_LOG_HISTORY_KEY)
    if not isinstance(raw, dict):
        return {"open": True, "lines": [], "status": None}

    lines_raw = raw.get("lines")
    lines: list[dict[str, Any]] = []
    status: Optional[str] = raw.get("status") if isinstance(raw.get("status"), str) else None
    if isinstance(lines_raw, list):
        for item in lines_raw:
            if isinstance(item, str):
                lines.append({"text": item, "muted": False})
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            line: dict[str, Any] = {"text": text, "muted": bool(item.get("muted"))}
            kind = item.get("kind")
            if isinstance(kind, str):
                if kind == "status":
                    status = text
                    line["kind"] = "status"
                else:
                    line["kind"] = kind
            lines.append(line)

    if len(lines) > MAX_COMBAT_LOG_LINES:
        lines = lines[-MAX_COMBAT_LOG_LINES:]
    return {"open": bool(raw.get("open", True)), "lines": lines, "status": status}


def _persist_combat_log_patch(sess: Session, patch: dict[str, Any]) -> None:
    if not isinstance(patch, dict):
        return

    history = _get_combat_log_history(sess)

    if patch.get("reset") is True:
        history["lines"] = []
        history["status"] = None

    open_value = patch.get("open")
    if isinstance(open_value, bool):
        history["open"] = open_value

    status_text = patch.get("status")
    if isinstance(status_text, str):
        history["status"] = status_text

    patch_lines = patch.get("lines")
    if isinstance(patch_lines, list):
        for item in patch_lines:
            if isinstance(item, str):
                history["lines"].append({"text": item, "muted": False})
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            line: dict[str, Any] = {"text": text, "muted": bool(item.get("muted"))}
            kind = item.get("kind")
            if isinstance(kind, str):
                if kind == "status":
                    history["status"] = text
                    line["kind"] = "status"
                else:
                    line["kind"] = kind
            history["lines"].append(line)

    lines = history.get("lines")
    if isinstance(lines, list) and len(lines) > MAX_COMBAT_LOG_LINES:
        history["lines"] = lines[-MAX_COMBAT_LOG_LINES:]

    st = _ensure_settings(sess)
    st[COMBAT_LOG_HISTORY_KEY] = history
    try:
        flag_modified(sess, "settings")
    except AttributeError:
        pass


def _combat_log_snapshot_patch(sess: Session) -> Optional[dict[str, Any]]:
    st = _ensure_settings(sess)
    history = st.get(COMBAT_LOG_HISTORY_KEY)
    if not isinstance(history, dict):
        return None
    lines = history.get("lines")
    if not isinstance(lines, list):
        return None
    status = history.get("status")
    if not lines and not isinstance(status, str):
        return None
    patch: dict[str, Any] = {"reset": True, "open": bool(history.get("open", True)), "lines": lines}
    if isinstance(status, str):
        patch["status"] = status
    return patch


def _persist_combat_state(sess: Session, session_id: str) -> bool:
    snapshot = snapshot_combat_state(session_id)
    st = _ensure_settings(sess)

    if snapshot is None:
        if COMBAT_STATE_KEY in st:
            st.pop(COMBAT_STATE_KEY, None)
            try:
                flag_modified(sess, "settings")
            except AttributeError:
                pass
            return True
        return False

    if st.get(COMBAT_STATE_KEY) != snapshot:
        st[COMBAT_STATE_KEY] = snapshot
        try:
            flag_modified(sess, "settings")
        except AttributeError:
            pass
        return True
    return False


def _maybe_restore_combat_state(sess: Session, session_id: str) -> None:
    if get_combat(session_id) is not None:
        return

    payload = settings_get(sess, COMBAT_STATE_KEY, None)
    if not isinstance(payload, dict):
        return
    restore_combat_state(session_id, payload)


async def build_state(db: AsyncSession, sess: Session) -> dict:
    import app.web.server as deps

    all_sps = await deps.list_session_players(db, sess, active_only=False)
    kicked = deps._get_kicked(sess)
    all_sps = [sp for sp in all_sps if str(sp.player_id) not in kicked]
    active_sps = [sp for sp in all_sps if sp.is_active is not False]
    player_ids = [sp.player_id for sp in all_sps]

    players_by_id: dict = {}
    if player_ids:
        q = await db.execute(select(Player).where(Player.id.in_(player_ids)))
        players_by_id = {p.id: p for p in q.scalars().all()}
    chars_by_player_id: dict = {}
    skills_by_character_id: dict = {}
    if player_ids:
        q_chars = await db.execute(
            select(Character).where(
                Character.session_id == sess.id,
                Character.player_id.in_(player_ids),
            )
        )
        chars = q_chars.scalars().all()
        for ch in chars:
            chars_by_player_id[ch.player_id] = ch
        char_ids = [ch.id for ch in chars]
        if char_ids:
            q_skills = await db.execute(select(Skill).where(Skill.character_id.in_(char_ids)))
            for skill in q_skills.scalars().all():
                skills_by_character_id.setdefault(skill.character_id, []).append(skill)

    q2 = await db.execute(
        select(Event)
        .where(Event.session_id == sess.id)
        .order_by(Event.created_at.desc())
        .limit(250)
    )

    events_desc = q2.scalars().all()
    events = list(reversed(events_desc))

    remaining = None
    if sess.turn_started_at and not sess.is_paused and sess.current_player_id:
        elapsed = (deps.utcnow() - sess.turn_started_at).total_seconds()
        remaining = max(0, int(deps.TURN_TIMEOUT_SECONDS - elapsed))

    cur_order = None
    for sp in active_sps:
        if sp.player_id == sess.current_player_id:
            cur_order = sp.join_order
            break

    current_uid = None
    if sess.current_player_id:
        current_uid = deps._player_uid(players_by_id.get(sess.current_player_id))

    ready_map = _get_ready_map(sess)
    init_map = _get_init_map(sess)
    last_seen_map = _get_last_seen_map(sess)

    all_ready = True
    if active_sps:
        for sp in active_sps:
            if not bool(ready_map.get(str(sp.player_id), False)):
                all_ready = False
                break
    else:
        all_ready = False

    can_begin = all_ready and not bool(sess.current_player_id) and not bool(sess.is_active)
    free_turns = deps._is_free_turns(sess)
    phase = _get_phase(sess)
    round_actions = deps._get_round_actions(sess)
    round_participants = deps._ready_active_players(sess, active_sps) if free_turns else active_sps
    actions_total = len(round_participants)
    actions_done = sum(1 for sp in round_participants if str(sp.player_id) in round_actions)
    positions = _get_pc_positions(sess)
    players_payload = []
    for sp in all_sps:
        pl = players_by_id.get(sp.player_id)
        char = chars_by_player_id.get(sp.player_id)
        char_payload = deps._char_to_payload(char)
        if char and char_payload is not None:
            char_payload["level_progress"] = deps._level_progress_payload(char)
            char_payload["skills"] = deps._skills_payload_for_character(char, skills_by_character_id.get(char.id, []))
        players_payload.append(
            {
                "id": str(sp.player_id),
                "uid": deps._player_uid(pl),
                "name": (pl.display_name if pl else str(sp.player_id)),
                "order": int(sp.join_order or 0),
                "is_admin": bool(sp.is_admin),
                "is_current": (sp.is_active is not False) and sp.player_id == sess.current_player_id,
                "is_active": sp.is_active is not False,
                "is_ready": bool(ready_map.get(str(sp.player_id), False)) if sp.is_active is not False else False,
                "initiative": init_map.get(str(sp.player_id)) if sp.is_active is not False else None,
                "last_seen": last_seen_map.get(str(sp.player_id)),
                "char": char_payload,
                "has_character": char is not None,
                "zone": positions.get(str(sp.player_id), "стартовая локация"),
            }
        )

    pc_positions: dict[str, str] = {}
    for sp in all_sps:
        pl = players_by_id.get(sp.player_id)
        uid = deps._player_uid(pl)
        key = str(uid) if uid is not None else str(sp.player_id)
        zone = positions.get(str(sp.player_id), "стартовая локация")
        pc_positions[key] = zone

    return {
        "type": "state",
        "session": {
            "id": str(sess.id),
            "title": sess.title,
            "is_active": bool(sess.is_active),
            "requires_character": True,
            "is_paused": bool(sess.is_paused),
            "turn_index": int(sess.turn_index or 0),
            "current_order": (int(cur_order) if cur_order is not None else None),
            "current_uid": current_uid,
            "remaining_seconds": remaining,
            "all_ready": bool(all_ready),
            "can_begin": bool(can_begin),
            "initiative_fixed": _initiative_fixed(sess),
            "round": (deps.as_int(settings_get(sess, "round", 0), 0) or 1) if _initiative_fixed(sess) else None,
        },
        "players": players_payload,
        "events": [
            {
                "turn": int(e.turn_index or 0),
                "text": e.message_text,
                "ts": e.created_at.isoformat(),
            }
            for e in events
        ],
        "game": {
            "free_turns": free_turns,
            "phase": phase,
            "free_round": deps._get_free_round(sess) if free_turns else None,
            "actions_done": actions_done,
            "actions_total": actions_total,
            "pc_positions": pc_positions,
        },
    }


async def _broadcast_state_unlocked(
    session_id: str,
    combat_log_ui_patch: Optional[dict[str, Any]] = None,
) -> None:
    import app.web.server as deps

    async with deps.AsyncSessionLocal() as db:
        sess = await deps.get_session(db, session_id)
        if not sess:
            return
        changed = False
        if combat_log_ui_patch is not None:
            history_raw = _ensure_settings(sess).get(COMBAT_LOG_HISTORY_KEY)
            prev_history = history_raw if isinstance(history_raw, dict) else None
            cs = deps.get_combat(session_id)
            actor_context: dict[str, Any] | None = None
            if cs is not None and cs.active:
                actor_uid: Optional[int] = None
                order = getattr(cs, "order", [])
                turn_index = int(getattr(cs, "turn_index", 0) or 0)
                if isinstance(order, list) and 0 <= turn_index < len(order):
                    turn_key = order[turn_index]
                    if isinstance(turn_key, str) and turn_key.startswith("pc_"):
                        uid_part = turn_key[3:]
                        if uid_part.isdigit():
                            actor_uid = int(uid_part)

                if actor_uid is None:
                    combatants = getattr(cs, "combatants", {})
                    if isinstance(combatants, dict):
                        for key in combatants.keys():
                            if not isinstance(key, str) or not key.startswith("pc_"):
                                continue
                            uid_part = key[3:]
                            if uid_part.isdigit():
                                actor_uid = int(uid_part)
                                break

                if actor_uid is not None:
                    _uid_map, chars_by_uid, _skill_mods_by_char = await deps._load_actor_context(db, sess)
                    character = chars_by_uid.get(actor_uid)
                    actor_context = {"uid": actor_uid}
                    if character is not None:
                        actor_context["character"] = character

            combat_log_ui_patch = deps.normalize_combat_log_ui_patch(
                combat_log_ui_patch,
                prev_history=prev_history,
                combat_state=cs,
                actor_context=actor_context,
            )
            _persist_combat_log_patch(sess, combat_log_ui_patch)
            changed = True
            rewards_granted = await deps._grant_combat_rewards_once(db, sess, combat_log_ui_patch)
            if rewards_granted:
                changed = True
            defeat_outcome_granted = await deps._grant_defeat_outcome_once(db, sess, combat_log_ui_patch)
            if defeat_outcome_granted:
                changed = True
            defeat_effects_applied = await deps._apply_defeat_effects_once(db, sess)
            if defeat_effects_applied:
                changed = True

        changed = _persist_combat_state(sess, session_id) or changed
        if changed:
            await db.commit()
        state = await build_state(db, sess)
    if combat_log_ui_patch is not None:
        state["combat_log_ui_patch"] = combat_log_ui_patch
    await manager.broadcast_json(session_id, state)


async def broadcast_state(
    session_id: str,
    combat_log_ui_patch: Optional[dict[str, Any]] = None,
) -> None:
    lock = get_session_lock(session_id)
    async with lock:
        await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_log_ui_patch)


async def send_state_to_ws(
    session_id: str,
    ws: WebSocket,
    combat_log_ui_patch: Optional[dict[str, Any]] = None,
) -> None:
    import app.web.server as deps

    async with deps.AsyncSessionLocal() as db:
        sess = await deps.get_session(db, session_id)
        if not sess:
            return
        _maybe_restore_combat_state(sess, session_id)
        state = await build_state(db, sess)
        if combat_log_ui_patch is None:
            snapshot = _combat_log_snapshot_patch(sess)
            if snapshot:
                cs = deps.get_combat(session_id)
                if cs is not None and cs.active and snapshot.get("open", True):
                    snapshot = dict(snapshot)  # safety copy
                    snapshot["status"] = f"⚔ Бой • Раунд {cs.round_no} • Ход: {deps.current_turn_label(cs)}"
                state["combat_log_ui_patch"] = snapshot
        else:
            state["combat_log_ui_patch"] = combat_log_ui_patch
    await ws.send_text(json.dumps(state, ensure_ascii=False))
