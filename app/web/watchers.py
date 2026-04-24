import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select

from app.core.log_context import request_id_var, session_id_var
from app.db.connection import AsyncSessionLocal
from app.db.models import Player, Session
from app.web.db_helpers import list_session_players
from app.web.gameplay_helpers import add_system_event
from app.web.session_lock import get_session_lock
from app.web.session_state import _get_last_seen_map, _touch_last_seen
from app.web.state_builder import _broadcast_state_unlocked
from app.web.ws_manager import manager
from app.web.ws_turns import TURN_TIMEOUT_SECONDS, _clear_paused_remaining, advance_turn, utcnow


logger = logging.getLogger(__name__)
INACTIVE_TIMEOUT_SECONDS = int(os.getenv("DND_INACTIVE_TIMEOUT_SECONDS", "0"))
INACTIVE_SCAN_PERIOD_SECONDS = int(os.getenv("DND_INACTIVE_SCAN_PERIOD_SECONDS", "5"))


def _new_request_id() -> str:
    return uuid.uuid4().hex


def _parse_iso(ts: Any) -> Optional[datetime]:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
    except Exception:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def timer_watcher():
    while True:
        try:
            if TURN_TIMEOUT_SECONDS <= 0:
                await asyncio.sleep(1)
                continue

            async with AsyncSessionLocal() as db:
                q = await db.execute(
                    select(Session).where(
                        Session.is_active == True,
                        Session.is_paused == False,
                        Session.current_player_id.is_not(None),
                        Session.turn_started_at.is_not(None),
                    )
                )
                sessions = q.scalars().all()

                now = utcnow()
                for sess in sessions:
                    tok_rid = request_id_var.set(_new_request_id())
                    tok_sid = session_id_var.set(str(sess.id))
                    try:
                        elapsed = (now - sess.turn_started_at).total_seconds()
                        if elapsed < TURN_TIMEOUT_SECONDS:
                            continue

                        session_id = str(sess.id)
                        lock = get_session_lock(session_id)
                        async with lock:
                            nxt = await advance_turn(db, sess)
                            if not nxt:
                                continue
                            await add_system_event(db, sess, f"⏰ Время вышло. Ход пропущен. Следующий: #{nxt.join_order}.")
                            await _broadcast_state_unlocked(session_id)
                    finally:
                        request_id_var.reset(tok_rid)
                        session_id_var.reset(tok_sid)

        except Exception:
            logger.exception("timer_watcher iteration failed")

        await asyncio.sleep(1)


async def inactive_watcher():
    while True:
        try:
            if INACTIVE_TIMEOUT_SECONDS <= 0:
                await asyncio.sleep(INACTIVE_SCAN_PERIOD_SECONDS)
                continue

            room_session_ids: list[uuid.UUID] = []
            for sid_raw in list(manager.rooms.keys()):
                try:
                    room_session_ids.append(uuid.UUID(str(sid_raw)))
                except Exception:
                    continue

            if room_session_ids:
                async with AsyncSessionLocal() as db:
                    q = await db.execute(select(Session).where(Session.id.in_(room_session_ids)))
                    sessions = q.scalars().all()
                    now = utcnow()

                    for sess in sessions:
                        tok_rid = request_id_var.set(_new_request_id())
                        tok_sid = session_id_var.set(str(sess.id))
                        try:
                            session_id = str(sess.id)
                            lock = get_session_lock(session_id)
                            async with lock:
                                changed = False
                                active_sps = await list_session_players(db, sess, active_only=True)
                                if not active_sps:
                                    continue

                                player_ids = [sp.player_id for sp in active_sps]
                                players_by_id: dict[uuid.UUID, Player] = {}
                                if player_ids:
                                    q_players = await db.execute(select(Player).where(Player.id.in_(player_ids)))
                                    players_by_id = {p.id: p for p in q_players.scalars().all()}

                                last_seen_map = _get_last_seen_map(sess)

                                for sp in active_sps:
                                    ts = _parse_iso(last_seen_map.get(str(sp.player_id)))
                                    if ts is None:
                                        _touch_last_seen(sess, sp.player_id)
                                        changed = True
                                        continue

                                    if (now - ts).total_seconds() <= INACTIVE_TIMEOUT_SECONDS:
                                        continue

                                    if sess.current_player_id == sp.player_id and bool(sess.is_active):
                                        await advance_turn(db, sess)

                                    sp.is_active = False
                                    changed = True

                                    pl = players_by_id.get(sp.player_id)
                                    name = pl.display_name if pl else f"#{sp.join_order}"
                                    await add_system_event(db, sess, f"Игрок {name} стал неактивен (timeout).")

                                if changed:
                                    active_left = await list_session_players(db, sess, active_only=True)
                                    if not active_left:
                                        sess.current_player_id = None
                                        sess.turn_started_at = None
                                        _clear_paused_remaining(sess)
                                    await db.commit()
                                    await _broadcast_state_unlocked(session_id)
                        finally:
                            request_id_var.reset(tok_rid)
                            session_id_var.reset(tok_sid)
        except Exception:
            logger.exception("inactive_watcher iteration failed")

        await asyncio.sleep(INACTIVE_SCAN_PERIOD_SECONDS)
