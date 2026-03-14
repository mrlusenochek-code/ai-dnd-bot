import os
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Session, SessionPlayer
from app.web.db_helpers import list_session_players
from app.web.session_state import (
    _clear_player_map_position,
    _get_init_map,
    _get_initiative_order,
    _get_last_seen_map,
    _get_ready_map,
    _initiative_fixed,
    settings_get,
    settings_set,
)
from app.web.utils import as_int


TURN_TIMEOUT_SECONDS = int(os.getenv("TURN_TIMEOUT_SECONDS", "300"))


def utcnow() -> datetime:
    return datetime.utcnow()


def _set_kicked(sess: Session, kicked: set[str]) -> None:
    settings_set(sess, "kicked", sorted(list(kicked)))


def _remove_player_from_session_settings(sess: Session, player_id: uuid.UUID) -> None:
    pid = str(player_id)

    ready_map = dict(_get_ready_map(sess))
    if pid in ready_map:
        ready_map.pop(pid, None)
        settings_set(sess, "ready", ready_map)

    init_map = dict(_get_init_map(sess))
    if pid in init_map:
        init_map.pop(pid, None)
        settings_set(sess, "initiative", init_map)

    last_seen_map = dict(_get_last_seen_map(sess))
    if pid in last_seen_map:
        last_seen_map.pop(pid, None)
        settings_set(sess, "last_seen", last_seen_map)

    round_actions = _get_round_actions(sess)
    if pid in round_actions:
        round_actions.pop(pid, None)
        settings_set(sess, "round_actions", round_actions)

    _clear_player_map_position(sess, player_id)


def _clear_initiative(sess: Session) -> None:
    settings_set(sess, "initiative", {})
    settings_set(sess, "initiative_fixed", False)
    settings_set(sess, "initiative_order", [])
    settings_set(sess, "round", 0)


def _set_paused_remaining(sess: Session, remaining: int) -> None:
    settings_set(sess, "paused_remaining_seconds", int(remaining))


def _get_paused_remaining(sess: Session) -> Optional[int]:
    v = settings_get(sess, "paused_remaining_seconds", None)
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _clear_paused_remaining(sess: Session) -> None:
    if sess.settings and isinstance(sess.settings, dict) and "paused_remaining_seconds" in sess.settings:
        sess.settings.pop("paused_remaining_seconds", None)
        flag_modified(sess, "settings")


def _new_action_id() -> str:
    return uuid.uuid4().hex


def _set_current_action_id(sess: Session, action_id: str) -> None:
    settings_set(sess, "current_action_id", str(action_id).strip())


def _clear_current_action_id(sess: Session) -> None:
    if sess.settings and isinstance(sess.settings, dict) and "current_action_id" in sess.settings:
        sess.settings.pop("current_action_id", None)
        flag_modified(sess, "settings")


def _is_free_turns(sess: Session) -> bool:
    return bool(settings_get(sess, "free_turns", False))


def _ready_active_players(sess: Session, sps_active: list[SessionPlayer]) -> list[SessionPlayer]:
    ready_map = _get_ready_map(sess)
    return [sp for sp in sps_active if bool(ready_map.get(str(sp.player_id), False))]


def _get_round_actions(sess: Session) -> dict[str, str]:
    raw = settings_get(sess, "round_actions", {}) or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        pid = str(k or "").strip()
        if not pid:
            continue
        txt = str(v or "").strip()
        if not txt:
            continue
        out[pid] = txt
    return out


def _get_free_round(sess: Session) -> int:
    return max(1, as_int(settings_get(sess, "free_round", 1), 1))


async def _compute_remaining(sess: Session) -> Optional[int]:
    if not sess.turn_started_at or not sess.current_player_id:
        return None
    elapsed = (utcnow() - sess.turn_started_at).total_seconds()
    return max(0, int(TURN_TIMEOUT_SECONDS - elapsed))


async def _advance_turn_join_order(db: AsyncSession, sess: Session) -> Optional[SessionPlayer]:
    sps = await list_session_players(db, sess, active_only=True)
    if not sps:
        return None

    idx = 0
    for i, sp in enumerate(sps):
        if sp.player_id == sess.current_player_id:
            idx = i
            break

    nxt = sps[(idx + 1) % len(sps)]
    sess.current_player_id = nxt.player_id
    sess.turn_index = (sess.turn_index or 0) + 1
    sess.turn_started_at = utcnow()
    _clear_paused_remaining(sess)
    await db.commit()
    return nxt


async def _advance_turn_initiative(db: AsyncSession, sess: Session) -> Optional[SessionPlayer]:
    order = _get_initiative_order(sess)
    if not order:
        return await _advance_turn_join_order(db, sess)

    sps = await list_session_players(db, sess, active_only=True)
    active_ids = {sp.player_id for sp in sps}
    order_active = [pid for pid in order if pid in active_ids]
    if not order_active:
        return await _advance_turn_join_order(db, sess)

    wrapped = False
    if sess.current_player_id in order_active:
        i = order_active.index(sess.current_player_id)
        nxt_index = (i + 1) % len(order_active)
        wrapped = nxt_index == 0 and len(order_active) > 0
        nxt_id = order_active[nxt_index]
    else:
        nxt_id = order_active[0]

    if wrapped:
        cur_round = as_int(settings_get(sess, "round", 1), 1)
        settings_set(sess, "round", cur_round + 1)

    nxt_sp = None
    for sp in sps:
        if sp.player_id == nxt_id:
            nxt_sp = sp
            break
    if not nxt_sp:
        return await _advance_turn_join_order(db, sess)

    sess.current_player_id = nxt_sp.player_id
    sess.turn_index = (sess.turn_index or 0) + 1
    sess.turn_started_at = utcnow()
    _clear_paused_remaining(sess)
    await db.commit()
    return nxt_sp


async def advance_turn(db: AsyncSession, sess: Session) -> Optional[SessionPlayer]:
    if _initiative_fixed(sess):
        return await _advance_turn_initiative(db, sess)
    return await _advance_turn_join_order(db, sess)


async def set_turn_to_order(db: AsyncSession, sess: Session, join_order: int) -> Optional[SessionPlayer]:
    sps = await list_session_players(db, sess, active_only=True)
    target = None
    for sp in sps:
        if int(sp.join_order or 0) == int(join_order):
            target = sp
            break
    if not target:
        return None
    sess.current_player_id = target.player_id
    sess.turn_index = (sess.turn_index or 0) + 1
    sess.turn_started_at = utcnow()
    _clear_paused_remaining(sess)
    await db.commit()
    return target
