import json
import logging
import time
from typing import Any, Optional

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.combat.log_ui import normalize_combat_log_ui_patch
from app.combat.state import current_turn_label, get_combat, restore_combat_state, snapshot_combat_state
from app.db.connection import AsyncSessionLocal
from app.db.models import Character, Event, Player, Session, Skill
from app.web.db_helpers import get_session, list_session_players
from app.web.constants import COMBAT_LOG_HISTORY_KEY, COMBAT_STATE_KEY, MAX_COMBAT_LOG_LINES
from app.web.gameplay_helpers import _char_to_payload, _get_kicked
from app.web.utils import as_int
from app.web.ws_access import _load_actor_context, _player_uid
from app.web.ws_progression import _level_progress_payload, _skills_payload_for_character
from app.web.ws_rewards import _apply_defeat_effects_once, _grant_combat_rewards_once, _grant_defeat_outcome_once
from app.web.ws_turns import (
    TURN_TIMEOUT_SECONDS,
    _get_free_round,
    _get_round_actions,
    _is_free_turns,
    _ready_active_players,
    utcnow,
)
from app.web.session_state import (
    _ensure_settings,
    _group_available_resolutions_summary,
    settings_get,
    _group_camp_summary,
    _group_last_travel_resolution_summary,
    _group_movement_mode,
    _group_movement_intent_summary,
    _group_travel_state_summary,
    _group_travel_summary,
    _group_travel_activity_summary,
    _group_wait_summary,
    _get_group_states,
    _get_ready_map,
    _get_init_map,
    _get_last_seen_map,
    _get_map_positions,
    _get_pc_positions,
    _get_player_group_id,
    _get_phase,
    _initiative_fixed,
)

from app.web.session_lock import get_session_lock
from app.web.perf_log import log_perf
from app.web.ws_manager import manager

logger = logging.getLogger(__name__)


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
    session_id = str(sess.id)
    all_sps = await list_session_players(db, sess, active_only=False)
    kicked = _get_kicked(sess)
    all_sps = [sp for sp in all_sps if str(sp.player_id) not in kicked]
    active_sps = [sp for sp in all_sps if sp.is_active is not False]
    player_ids = [sp.player_id for sp in all_sps]

    players_by_id: dict = {}
    if player_ids:
        q = await db.execute(select(Player).where(Player.id.in_(player_ids)))
        players_by_id = {p.id: p for p in q.scalars().all()}
    players_by_id_str = {str(pid): player for pid, player in players_by_id.items()}
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
        elapsed = (utcnow() - sess.turn_started_at).total_seconds()
        remaining = max(0, int(TURN_TIMEOUT_SECONDS - elapsed))

    cur_order = None
    for sp in active_sps:
        if sp.player_id == sess.current_player_id:
            cur_order = sp.join_order
            break

    current_uid = None
    if sess.current_player_id:
        current_uid = _player_uid(players_by_id.get(sess.current_player_id))

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
    free_turns = _is_free_turns(sess)
    phase = _get_phase(sess)
    round_actions = _get_round_actions(sess)
    round_participants = _ready_active_players(sess, active_sps) if free_turns else active_sps
    actions_total = len(round_participants)
    actions_done = sum(1 for sp in round_participants if str(sp.player_id) in round_actions)
    group_states = _get_group_states(sess, [sp.player_id for sp in active_sps])
    positions = _get_pc_positions(sess)
    structured_positions = _get_map_positions(sess)
    combat_snapshot = snapshot_combat_state(session_id)
    players_payload = []
    for sp in all_sps:
        pl = players_by_id.get(sp.player_id)
        char = chars_by_player_id.get(sp.player_id)
        char_payload = _char_to_payload(char)
        if char and char_payload is not None:
            char_payload["level_progress"] = _level_progress_payload(char)
            char_payload["skills"] = _skills_payload_for_character(char, skills_by_character_id.get(char.id, []))
        group_id = _get_player_group_id(sess, sp.player_id, [sp.player_id for sp in active_sps])
        group = group_states.get(group_id) if group_id else None
        players_payload.append(
            {
                "id": str(sp.player_id),
                "uid": _player_uid(pl),
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
                "group_id": group_id,
                "group_area_label": (group.get("area_label") if isinstance(group, dict) else None),
                "group_map_position": (dict(group["current_map_position"]) if isinstance(group, dict) else None),
                "zone": positions.get(str(sp.player_id), "стартовая локация"),
                "map_position": structured_positions.get(str(sp.player_id)),
            }
        )

    pc_positions: dict[str, str] = {}
    map_positions: dict[str, dict[str, Any]] = {}
    for sp in all_sps:
        pl = players_by_id.get(sp.player_id)
        uid = _player_uid(pl)
        key = str(uid) if uid is not None else str(sp.player_id)
        zone = positions.get(str(sp.player_id), "стартовая локация")
        pc_positions[key] = zone

        structured = structured_positions.get(str(sp.player_id))
        if isinstance(structured, dict):
            map_positions[key] = dict(structured)

    groups_payload: dict[str, dict[str, Any]] = {}
    for group_id, group in group_states.items():
        member_uids: list[int] = []
        for member_id in group.get("player_ids", []):
            player_obj = players_by_id_str.get(str(member_id))
            member_uid = _player_uid(player_obj)
            if member_uid is not None:
                member_uids.append(member_uid)
        groups_payload[group_id] = {
            "group_id": group_id,
            "player_ids": list(group.get("player_ids", [])),
            "member_ids": list(group.get("player_ids", [])),
            "member_uids": member_uids,
            "current_map_position": dict(group["current_map_position"]),
            "area_label": group.get("area_label"),
            "status": group.get("status"),
            "movement_mode": _group_movement_mode(group),
            "travel_activity": _group_travel_activity_summary(group),
            "travel_activity_summary": _group_travel_activity_summary(group),
            "wait_summary": _group_wait_summary(group),
            "camp_summary": _group_camp_summary(group),
            "movement_intent_summary": _group_movement_intent_summary(group),
            "travel_state": _group_travel_state_summary(group),
            "travel_summary": _group_travel_summary(group),
            "pause_reason": (group.get("travel_state") or {}).get("pause_reason") if isinstance(group.get("travel_state"), dict) else None,
            "pause_details": dict((group.get("travel_state") or {}).get("pause_details") or {}) if isinstance((group.get("travel_state") or {}).get("pause_details"), dict) else None,
            "available_resolutions": _group_available_resolutions_summary(group),
            "last_resolution_summary": _group_last_travel_resolution_summary(group),
        }

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
            "current_group_id": (_get_player_group_id(sess, sess.current_player_id, [sp.player_id for sp in active_sps]) if sess.current_player_id else None),
            "initiative_fixed": _initiative_fixed(sess),
            "round": (as_int(settings_get(sess, "round", 0), 0) or 1) if _initiative_fixed(sess) else None,
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
            "free_round": _get_free_round(sess) if free_turns else None,
            "actions_done": actions_done,
            "actions_total": actions_total,
            "groups": groups_payload,
            "pc_positions": pc_positions,
            "map_positions": map_positions,
        },
        "combat": combat_snapshot if isinstance(combat_snapshot, dict) else None,
    }


async def _apply_combat_patch_handoff(
    db: AsyncSession,
    sess: Session,
    session_id: str,
    combat_log_ui_patch: Optional[dict[str, Any]],
) -> tuple[Optional[dict[str, Any]], bool]:
    if combat_log_ui_patch is None:
        return None, False

    history_raw = _ensure_settings(sess).get(COMBAT_LOG_HISTORY_KEY)
    prev_history = history_raw if isinstance(history_raw, dict) else None
    cs = get_combat(session_id)
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
            _uid_map, chars_by_uid, _skill_mods_by_char = await _load_actor_context(db, sess)
            character = chars_by_uid.get(actor_uid)
            actor_context = {"uid": actor_uid}
            if character is not None:
                actor_context["character"] = character

    combat_log_ui_patch = normalize_combat_log_ui_patch(
        combat_log_ui_patch,
        prev_history=prev_history,
        combat_state=cs,
        actor_context=actor_context,
    )
    _persist_combat_log_patch(sess, combat_log_ui_patch)
    return combat_log_ui_patch, True


async def _apply_combat_outcome_side_effects(
    db: AsyncSession,
    sess: Session,
    combat_log_ui_patch: Optional[dict[str, Any]],
) -> bool:
    if combat_log_ui_patch is None:
        return False

    changed = False
    rewards_granted = await _grant_combat_rewards_once(db, sess, combat_log_ui_patch)
    if rewards_granted:
        changed = True
    defeat_outcome_granted = await _grant_defeat_outcome_once(db, sess, combat_log_ui_patch)
    if defeat_outcome_granted:
        changed = True
    defeat_effects_applied = await _apply_defeat_effects_once(db, sess)
    if defeat_effects_applied:
        changed = True
    return changed


def _apply_combat_state_persistence(sess: Session, session_id: str, changed: bool) -> bool:
    return _persist_combat_state(sess, session_id) or changed


async def _broadcast_state_unlocked(
    session_id: str,
    combat_log_ui_patch: Optional[dict[str, Any]] = None,
) -> None:
    t_db0 = time.monotonic()
    commit_ms: float | None = None
    build_state_ms = 0.0
    ws_broadcast_ms = 0.0
    changed = False
    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            return
        combat_log_ui_patch, patch_changed = await _apply_combat_patch_handoff(
            db, sess, session_id, combat_log_ui_patch
        )
        changed = patch_changed or changed
        changed = await _apply_combat_outcome_side_effects(db, sess, combat_log_ui_patch) or changed

        changed = _apply_combat_state_persistence(sess, session_id, changed)
        if changed:
            t_commit0 = time.monotonic()
            await db.commit()
            commit_ms = (time.monotonic() - t_commit0) * 1000.0
        t_build0 = time.monotonic()
        state = await build_state(db, sess)
        build_state_ms = (time.monotonic() - t_build0) * 1000.0
        t_before_build = t_build0
    if combat_log_ui_patch is not None:
        state["combat_log_ui_patch"] = combat_log_ui_patch
    t_ws0 = time.monotonic()
    await manager.broadcast_json(session_id, state)
    ws_broadcast_ms = (time.monotonic() - t_ws0) * 1000.0

    db_total_ms = (t_before_build - t_db0) * 1000.0
    if commit_ms is not None:
        db_total_ms = max(0.0, db_total_ms - commit_ms)
    log_perf(
        logger,
        "broadcast_state_unlocked",
        db_total_ms + build_state_ms + ws_broadcast_ms + (commit_ms or 0.0),
        fields={
            "session_id": session_id,
            "db_ms": round(db_total_ms, 2),
            "build_state_ms": round(build_state_ms, 2),
            "ws_broadcast_ms": round(ws_broadcast_ms, 2),
            "commit_ms": round(commit_ms, 2) if commit_ms is not None else None,
            "changed": changed,
        },
    )


async def broadcast_state(
    session_id: str,
    combat_log_ui_patch: Optional[dict[str, Any]] = None,
) -> None:
    t0 = time.monotonic()
    lock = get_session_lock(session_id)
    async with lock:
        t1 = time.monotonic()
        await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_log_ui_patch)
        t2 = time.monotonic()
    wait_ms = (t1 - t0) * 1000.0
    inside_ms = (t2 - t1) * 1000.0
    total_ms = (t2 - t0) * 1000.0
    log_perf(
        logger,
        "broadcast_state",
        total_ms,
        fields={
            "session_id": session_id,
            "wait_ms": round(wait_ms, 2),
            "inside_ms": round(inside_ms, 2),
            "has_patch": combat_log_ui_patch is not None,
        },
    )


async def send_state_to_ws(
    session_id: str,
    ws: WebSocket,
    combat_log_ui_patch: Optional[dict[str, Any]] = None,
) -> None:
    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            return
        _maybe_restore_combat_state(sess, session_id)
        state = await build_state(db, sess)
        if combat_log_ui_patch is None:
            snapshot = _combat_log_snapshot_patch(sess)
            if snapshot:
                cs = get_combat(session_id)
                if cs is not None and cs.active and snapshot.get("open", True):
                    snapshot = dict(snapshot)  # safety copy
                    snapshot["status"] = f"⚔ Бой • Раунд {cs.round_no} • Ход: {current_turn_label(cs)}"
                state["combat_log_ui_patch"] = snapshot
        else:
            state["combat_log_ui_patch"] = combat_log_ui_patch
    await ws.send_text(json.dumps(state, ensure_ascii=False))
