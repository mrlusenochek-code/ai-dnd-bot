import json
from typing import Any, Optional

from fastapi import WebSocket

from app.web.session_lock import get_session_lock
from app.web.ws_manager import manager


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
            history_raw = deps._ensure_settings(sess).get(deps.COMBAT_LOG_HISTORY_KEY)
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
            deps._persist_combat_log_patch(sess, combat_log_ui_patch)
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

        changed = deps._persist_combat_state(sess, session_id) or changed
        if changed:
            await db.commit()
        state = await deps.build_state(db, sess)
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
        deps._maybe_restore_combat_state(sess, session_id)
        state = await deps.build_state(db, sess)
        if combat_log_ui_patch is None:
            snapshot = deps._combat_log_snapshot_patch(sess)
            if snapshot:
                cs = deps.get_combat(session_id)
                if cs is not None and cs.active and snapshot.get("open", True):
                    snapshot = dict(snapshot)  # safety copy
                    snapshot["status"] = f"⚔ Бой • Раунд {cs.round_no} • Ход: {deps.current_turn_label(cs)}"
                state["combat_log_ui_patch"] = snapshot
        else:
            state["combat_log_ui_patch"] = combat_log_ui_patch
    await ws.send_text(json.dumps(state, ensure_ascii=False))
