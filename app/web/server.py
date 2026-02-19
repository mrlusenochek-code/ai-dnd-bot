import asyncio
import json
import logging
import os
import random
import re
from datetime import datetime, timedelta
import uuid
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.logging import configure_logging
from app.core.log_context import request_id_var, session_id_var, uid_var, ws_conn_id_var, client_id_var
from app.db.connection import AsyncSessionLocal
from app.db.models import Session, Player, SessionPlayer, Event


TURN_TIMEOUT_SECONDS = int(os.getenv("TURN_TIMEOUT_SECONDS", "300"))
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Warsaw")
logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.utcnow()


# -------------------------
# WebSocket connection manager
# -------------------------
class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.rooms.setdefault(session_id, set()).add(ws)

    def disconnect(self, session_id: str, ws: WebSocket) -> None:
        room = self.rooms.get(session_id)
        if not room:
            return
        room.discard(ws)
        if not room:
            self.rooms.pop(session_id, None)

    async def broadcast_json(self, session_id: str, data: dict) -> None:
        room = list(self.rooms.get(session_id, set()))
        dead: list[WebSocket] = []
        payload = json.dumps(data, ensure_ascii=False)
        for ws in room:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)


manager = ConnectionManager()
app = FastAPI()
def _new_request_id() -> str:
    return uuid.uuid4().hex


@app.middleware("http")
async def _log_context_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or _new_request_id()
    tok_rid = request_id_var.set(rid)

    tok_sid = None
    tok_uid = None
    tok_cid = None
    try:
        sid = None
        cid = request.headers.get("x-client-id")
        if cid:
            tok_cid = client_id_var.set(str(cid))

        # session_id из URL вида /s/<uuid>
        m = re.search(r"/s/([0-9a-fA-F-]{36})", request.url.path)
        if m:
            sid = m.group(1)

        # session_id/uid из JSON тела (например /api/join)
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.json()
            except Exception:
                body = None

            if isinstance(body, dict):
                if not sid and body.get("session_id"):
                    sid = str(body.get("session_id"))
                if body.get("uid") is not None:
                    try:
                        tok_uid = uid_var.set(int(body.get("uid")))
                    except Exception:
                        pass

        if sid:
            tok_sid = session_id_var.set(str(sid))

        response = await call_next(request)
        logger.info("http request", extra={"http": {"method": request.method, "path": request.url.path, "status": response.status_code}})
        response.headers.setdefault("X-Request-ID", rid)
        return response

    finally:
        request_id_var.reset(tok_rid)
        if tok_sid is not None:
            session_id_var.reset(tok_sid)
        if tok_uid is not None:
            uid_var.reset(tok_uid)
        if tok_cid is not None:
            client_id_var.reset(tok_cid)

# -------------------------
# Settings helpers (Session.settings is JSON)
# -------------------------
def _ensure_settings(sess: Session) -> dict:
    if not sess.settings or not isinstance(sess.settings, dict):
        sess.settings = {}
    return sess.settings


def settings_get(sess: Session, key: str, default: Any) -> Any:
    st = _ensure_settings(sess)
    return st.get(key, default)


def settings_set(sess: Session, key: str, value: Any) -> None:
    st = _ensure_settings(sess)
    st[key] = value
    flag_modified(sess, "settings")


def as_int(s: Any, default: int = 0) -> int:
    try:
        return int(s)
    except Exception:
        return default


# -------------------------
# -------------------------
# Templates (Jinja2)
# -------------------------
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# -------------------------
# DB helpers
# -------------------------
async def get_or_create_player_web(db: AsyncSession, uid: int, display_name: str) -> Player:
    """
    uid — это наш "web user id". Храним в Player.web_user_id.
    """
    q = await db.execute(select(Player).where(Player.web_user_id == uid))
    player = q.scalar_one_or_none()
    if player:
        if display_name and display_name.strip() and player.display_name != display_name.strip():
            player.display_name = display_name.strip()
            await db.commit()
        return player

    name = (display_name or "").strip() or f"Player {uid}"
    player = Player(
        web_user_id=uid,
        username=None,
        display_name=name,
    )
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return player


async def get_session(db: AsyncSession, session_id: str) -> Optional[Session]:
    try:
        sid = uuid.UUID(session_id)
    except Exception:
        return None
    q = await db.execute(select(Session).where(Session.id == sid))
    return q.scalar_one_or_none()


async def list_session_players(db: AsyncSession, sess: Session, active_only: bool = True) -> list[SessionPlayer]:
    conds = [SessionPlayer.session_id == sess.id]
    if active_only:
        # is_active could be NULL for legacy records -> treat as active
        conds.append(or_(SessionPlayer.is_active == True, SessionPlayer.is_active.is_(None)))
    q = await db.execute(
        select(SessionPlayer)
        .where(*conds)
        .order_by(SessionPlayer.join_order.asc())
    )
    return q.scalars().all()


async def is_admin(db: AsyncSession, sess: Session, player: Player) -> bool:
    q = await db.execute(
        select(SessionPlayer).where(
            SessionPlayer.session_id == sess.id,
            SessionPlayer.player_id == player.id,
        )
    )
    sp = q.scalar_one_or_none()
    return bool(sp and sp.is_admin)


async def add_event(db: AsyncSession, sess: Session, text: str, actor_player_id: Optional[uuid.UUID] = None) -> None:
    ev = Event(
        session_id=sess.id,
        turn_index=sess.turn_index or 0,
        actor_player_id=actor_player_id,
        actor_character_id=None,
        message_text=text,
        parsed_json=None,
        result_json=None,
    )
    db.add(ev)
    await db.commit()


async def add_system_event(db: AsyncSession, sess: Session, text: str) -> None:
    await add_event(db, sess, f"[SYSTEM] {text}", actor_player_id=None)


def _get_ready_map(sess: Session) -> dict[str, bool]:
    return settings_get(sess, "ready", {}) or {}


def _set_ready(sess: Session, player_id: uuid.UUID, value: bool) -> None:
    m = dict(_get_ready_map(sess))
    m[str(player_id)] = bool(value)
    settings_set(sess, "ready", m)


def _get_kicked(sess: Session) -> set[str]:
    raw = settings_get(sess, "kicked", []) or []
    out: set[str] = set()
    for x in raw:
        if x is None:
            continue
        out.add(str(x))
    return out


def _set_kicked(sess: Session, kicked: set[str]) -> None:
    settings_set(sess, "kicked", sorted(list(kicked)))


def _get_init_map(sess: Session) -> dict[str, int]:
    raw = settings_get(sess, "initiative", {}) or {}
    out: dict[str, int] = {}
    for k, v in raw.items():
        out[str(k)] = as_int(v, 0)
    return out


def _set_init_value(sess: Session, player_id: uuid.UUID, value: int) -> None:
    m = dict(_get_init_map(sess))
    m[str(player_id)] = int(value)
    settings_set(sess, "initiative", m)


def _clear_initiative(sess: Session) -> None:
    settings_set(sess, "initiative", {})
    settings_set(sess, "initiative_fixed", False)
    settings_set(sess, "initiative_order", [])
    settings_set(sess, "round", 0)


def _initiative_fixed(sess: Session) -> bool:
    return bool(settings_get(sess, "initiative_fixed", False))


def _get_initiative_order(sess: Session) -> list[uuid.UUID]:
    raw = settings_get(sess, "initiative_order", []) or []
    out: list[uuid.UUID] = []
    for x in raw:
        try:
            if isinstance(x, uuid.UUID):
                out.append(x)
            else:
                out.append(uuid.UUID(str(x)))
        except Exception:
            continue
    return out


def _set_initiative_order(sess: Session, order: list[uuid.UUID]) -> None:
    settings_set(sess, "initiative_order", [str(x) for x in order])


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

    # filter only active players
    sps = await list_session_players(db, sess, active_only=True)
    active_ids = {sp.player_id for sp in sps}
    order_active = [pid for pid in order if pid in active_ids]
    if not order_active:
        return await _advance_turn_join_order(db, sess)    # find next in order
    wrapped = False
    if sess.current_player_id in order_active:
        i = order_active.index(sess.current_player_id)
        nxt_index = (i + 1) % len(order_active)
        wrapped = (nxt_index == 0 and len(order_active) > 0)
        nxt_id = order_active[nxt_index]
    else:
        nxt_id = order_active[0]

    # round counter: increment when we wrap to the first in initiative order
    if wrapped:
        cur_round = as_int(settings_get(sess, "round", 1), 1)
        settings_set(sess, "round", cur_round + 1)

    # find SessionPlayer for next
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


# -------------------------
# State building / broadcasting
# -------------------------
async def build_state(db: AsyncSession, sess: Session) -> dict:
    sps = await list_session_players(db, sess, active_only=True)
    player_ids = [sp.player_id for sp in sps]

    players_by_id: dict = {}
    if player_ids:
        q = await db.execute(select(Player).where(Player.id.in_(player_ids)))
        players_by_id = {p.id: p for p in q.scalars().all()}

    # ---------------------------------------
    q2 = await db.execute(
        select(Event)
        .where(Event.session_id == sess.id)
        .order_by(Event.created_at.asc())
        .limit(250)
    )

    events = q2.scalars().all()

    remaining = None
    if sess.turn_started_at and not sess.is_paused and sess.current_player_id:
        elapsed = (utcnow() - sess.turn_started_at).total_seconds()
        remaining = max(0, int(TURN_TIMEOUT_SECONDS - elapsed))



    cur_order = None
    for sp in sps:
        if sp.player_id == sess.current_player_id:
            cur_order = sp.join_order
            break

    def _player_uid(pl: Optional[Player]) -> Optional[int]:
        if not pl:
            return None
        raw = pl.web_user_id if pl.web_user_id is not None else pl.telegram_user_id
        return int(raw) if raw is not None else None

    # UID текущего игрока (нужно для UI, независимо от паузы/таймера)
    current_uid = None
    if sess.current_player_id:
        current_uid = _player_uid(players_by_id.get(sess.current_player_id))

    ready_map = _get_ready_map(sess)
    init_map = _get_init_map(sess)

    all_ready = True
    if sps:
        for sp in sps:
            if not bool(ready_map.get(str(sp.player_id), False)):
                all_ready = False
                break
    else:
        all_ready = False

    can_begin = all_ready and not bool(sess.current_player_id)

    return {
        "type": "state",
        "session": {
            "id": str(sess.id),
            "title": sess.title,
            "is_active": bool(sess.is_active),
            "is_paused": bool(sess.is_paused),
            "turn_index": int(sess.turn_index or 0),
            "current_order": (int(cur_order) if cur_order is not None else None),
            "current_uid": current_uid,
            "remaining_seconds": remaining,
            "all_ready": bool(all_ready),
            "can_begin": bool(can_begin),
            "initiative_fixed": _initiative_fixed(sess),
            "round": (as_int(settings_get(sess, "round", 0), 0) or 1) if _initiative_fixed(sess) else None,
        },
        "players": [
            {
                "id": str(sp.player_id),
                "uid": _player_uid(players_by_id.get(sp.player_id)),
                "name": (players_by_id.get(sp.player_id).display_name if players_by_id.get(sp.player_id) else str(sp.player_id)),
                "order": int(sp.join_order or 0),
                "is_admin": bool(sp.is_admin),
                "is_current": sp.player_id == sess.current_player_id,
                "is_ready": bool(ready_map.get(str(sp.player_id), False)),
                "initiative": init_map.get(str(sp.player_id)),
            }
            for sp in sps
        ],
        "events": [
            {
                "turn": int(e.turn_index or 0),
                "text": e.message_text,
                "ts": e.created_at.isoformat(),
            }
            for e in events
        ],
    }


async def broadcast_state(session_id: str) -> None:
    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            return
        state = await build_state(db, sess)
    await manager.broadcast_json(session_id, state)


# -------------------------
# Routes
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/new")
async def api_new(payload: dict):
    title = (payload.get("title") or "Campaign").strip()
    uid = int(payload.get("uid"))
    name = (payload.get("name") or "Игрок").strip()

    async with AsyncSessionLocal() as db:
        player = await get_or_create_player_web(db, uid, name)

        room_id = random.randint(10_000_000_000, 99_999_999_999)
        sess = Session(
            telegram_chat_id=room_id,
            title=title,
            settings={"channel": "web"},
            world_seed=random.randint(1, 2_000_000_000),
            timezone=DEFAULT_TIMEZONE,
            is_active=False,
            is_paused=False,
            turn_index=0,
            current_player_id=None,
            turn_started_at=None,
        )
        db.add(sess)
        await db.commit()
        await db.refresh(sess)

        sp = SessionPlayer(
            session_id=sess.id,
            player_id=player.id,
            is_admin=True,
            join_order=1,
            is_active=True,
        )
        db.add(sp)
        await db.commit()

        # ready defaults
        _set_ready(sess, player.id, False)
        await db.commit()

        await add_system_event(db, sess, f"Создана игра «{title}». Админ: {player.display_name}.")

    return JSONResponse({"session_id": str(sess.id)})


@app.get("/s/{session_id}", response_class=HTMLResponse)
async def session_page(request: Request, session_id: str):
    return templates.TemplateResponse("session.html", {"request": request, "session_id": session_id})


@app.post("/api/join")
async def api_join(payload: dict):
    session_id = payload.get("session_id")
    uid = int(payload.get("uid"))
    name = (payload.get("name") or "Игрок").strip()

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_or_create_player_web(db, uid, name)

        kicked = _get_kicked(sess)
        if str(player.id) in kicked:
            raise HTTPException(status_code=403, detail="You were kicked from this session")

        q = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q.scalar_one_or_none()
        if sp:
            # reactivate if they had left
            if sp.is_active is False:
                sp.is_active = True
                await db.commit()
                _set_ready(sess, player.id, False)
                await db.commit()
                await add_system_event(db, sess, f"Игрок вернулся: {player.display_name} (#{sp.join_order}).")
                await broadcast_state(session_id)
            return JSONResponse({"ok": True})

        q2 = await db.execute(select(SessionPlayer.join_order).where(SessionPlayer.session_id == sess.id))
        orders = [r[0] for r in q2.all()] or [0]
        join_order = max(orders) + 1

        sp = SessionPlayer(
            session_id=sess.id,
            player_id=player.id,
            is_admin=False,
            join_order=join_order,
            is_active=True,
        )
        db.add(sp)
        await db.commit()

        _set_ready(sess, player.id, False)
        await db.commit()

        await add_system_event(db, sess, f"Игрок присоединился: {player.display_name} (#{join_order}).")

    await broadcast_state(session_id)
    return JSONResponse({"ok": True})


# -------------------------
# Dice parsing
# -------------------------
DICE_RE = re.compile(r"^\s*(?:(roll|adv|dis)\s+)?(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def roll_dice(n: int, sides: int) -> list[int]:
    return [random.randint(1, sides) for _ in range(n)]


def parse_dice(text: str):
    m = DICE_RE.match(text)
    if not m:
        return None
    mode = (m.group(1) or "roll").lower()
    n = int(m.group(2))
    sides = int(m.group(3))
    mod_raw = (m.group(4) or "").replace(" ", "")
    mod = int(mod_raw) if mod_raw else 0
    # reasonable limits
    if n < 1 or n > 50 or sides < 2 or sides > 1000:
        return None
    return mode, n, sides, mod, (f"{n}d{sides}{mod_raw}" if mod_raw else f"{n}d{sides}")


# -------------------------
# WebSocket room
# -------------------------
@app.websocket("/ws/{session_id}")
async def ws_room(ws: WebSocket, session_id: str):
    uid_raw = ws.query_params.get("uid")
    if not uid_raw or not uid_raw.isdigit():
        await ws.accept()
        await ws.send_text(json.dumps({"type": "error", "message": "No uid", "fatal": True}, ensure_ascii=False))
        await ws.close()
        return

    uid = int(uid_raw)

    # log context for this WS connection (task-local)
    request_id_var.set(_new_request_id())
    session_id_var.set(session_id)
    uid_var.set(uid)
    ws_conn_id_var.set(uuid.uuid4().hex[:12])
    cid = ws.query_params.get("cid")
    if cid:
        client_id_var.set(str(cid))

    await manager.connect(session_id, ws)
    logger.info("ws connected")

    try:
        await broadcast_state(session_id)

        while True:
            # Ждём входящее сообщение. State приходит через broadcast_state() по событиям,
            # а таймер рисуется локально на фронте.
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                data = {"action": "say", "text": raw}

            action = (data.get("action") or "").strip().lower()
            text = (data.get("text") or "").strip()

            async with AsyncSessionLocal() as db:
                sess = await get_session(db, session_id)
                if not sess:
                    await ws.send_text(json.dumps({"type": "error", "message": "Session not found"}, ensure_ascii=False))
                    continue

                # don't overwrite name here; join sets it
                player = await get_or_create_player_web(db, uid, "")

                # kicked check (live)
                if str(player.id) in _get_kicked(sess):
                    await ws.send_text(json.dumps({"type": "error", "message": "You were kicked from this session", "fatal": True}, ensure_ascii=False))
                    await ws.close()
                    return

                q = await db.execute(
                    select(SessionPlayer).where(
                        SessionPlayer.session_id == sess.id,
                        SessionPlayer.player_id == player.id,
                    )
                )
                sp = q.scalar_one_or_none()
                if not sp or sp.is_active is False:
                    await ws.send_text(json.dumps({"type": "error", "message": "Not joined/active. Refresh page."}, ensure_ascii=False))
                    continue

                # ready/unready actions (do not require game started)
                if action in ("ready", "unready"):
                    _set_ready(sess, player.id, action == "ready")
                    await db.commit()
                    await add_system_event(db, sess, f"Готовность: игрок #{sp.join_order} — {'ГОТОВ' if action=='ready' else 'НЕ ГОТОВ'}.")
                    await broadcast_state(session_id)
                    continue

                # status: just broadcast
                if action == "status":
                    await broadcast_state(session_id)
                    continue

                # Admin-only control actions
                if action == "begin":
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can start"}, ensure_ascii=False))
                        continue
                    if sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Already started"}, ensure_ascii=False))
                        continue

                    sps = await list_session_players(db, sess, active_only=True)
                    if not sps:
                        await ws.send_text(json.dumps({"type": "error", "message": "No players"}, ensure_ascii=False))
                        continue

                    # all ready check
                    ready_map = _get_ready_map(sess)
                    if any(not bool(ready_map.get(str(x.player_id), False)) for x in sps):
                        await ws.send_text(json.dumps({"type": "error", "message": "Not all players are ready"}, ensure_ascii=False))
                        continue

                    sess.is_active = True
                    sess.current_player_id = sps[0].player_id
                    sess.turn_index = 1
                    sess.turn_started_at = utcnow()
                    sess.is_paused = False
                    _clear_paused_remaining(sess)
                    await db.commit()
                    await add_system_event(db, sess, f"Игра началась. Ход игрока #{sps[0].join_order}.")
                    await broadcast_state(session_id)
                    continue

                if action == "pause":
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can pause"}, ensure_ascii=False))
                        continue
                    if sess.is_paused:
                        await broadcast_state(session_id)
                        continue
                    rem = await _compute_remaining(sess)
                    if rem is not None:
                        _set_paused_remaining(sess, rem)
                    sess.is_paused = True
                    await db.commit()
                    await add_system_event(db, sess, f"Пауза. Осталось: {rem if rem is not None else '—'} сек.")
                    await broadcast_state(session_id)
                    continue

                if action == "resume":
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can resume"}, ensure_ascii=False))
                        continue
                    if not sess.is_paused:
                        await broadcast_state(session_id)
                        continue

                    # continue timer from stored remaining
                    stored = _get_paused_remaining(sess)
                    if stored is not None and sess.current_player_id:
                        stored = max(0, min(TURN_TIMEOUT_SECONDS, int(stored)))
                        elapsed = TURN_TIMEOUT_SECONDS - stored
                        sess.turn_started_at = utcnow() - timedelta(seconds=elapsed)
                    else:
                        # fallback: restart timer (or clear if no current player)
                        sess.turn_started_at = utcnow() if sess.current_player_id else None

                    sess.is_paused = False
                    _clear_paused_remaining(sess)
                    await db.commit()
                    await add_system_event(db, sess, "Продолжили игру.")
                    await broadcast_state(session_id)
                    continue

                if action == "skip":
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can skip"}, ensure_ascii=False))
                        continue
                    if not sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Not started"}, ensure_ascii=False))
                        continue
                    if sess.is_paused:
                        await ws.send_text(json.dumps({"type": "error", "message": "Paused. Resume first."}, ensure_ascii=False))
                        continue

                    nxt = await advance_turn(db, sess)
                    if not nxt:
                        await ws.send_text(json.dumps({"type": "error", "message": "No players"}, ensure_ascii=False))
                        continue
                    await add_system_event(db, sess, f"Ход пропущен. Следующий: #{nxt.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # chat / command parsing
                if action != "say":
                    await ws.send_text(json.dumps({"type": "error", "message": "Unknown action"}, ensure_ascii=False))
                    continue

                if not text:
                    continue

                # normalize leading slash for typed commands
                cmdline = text.lstrip()
                if cmdline.startswith("/"):
                    cmdline = cmdline[1:].lstrip()

                lower = cmdline.lower()

                # OOC (any time, no turn)
                if lower.startswith("ooc ") or cmdline.startswith("//"):
                    msg = cmdline[4:].strip() if lower.startswith("ooc ") else cmdline[2:].strip()
                    await add_event(db, sess, f"[OOC] {player.display_name} (#{sp.join_order}): {msg}")
                    await broadcast_state(session_id)
                    continue

                # GM (admin only, any time, no turn)
                if lower.startswith("gm ") or lower.startswith("gm:"):
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can GM"}, ensure_ascii=False))
                        continue
                    msg = cmdline[2:].lstrip(":").strip()
                    await add_system_event(db, sess, f"🧙 GM: {msg}")
                    await broadcast_state(session_id)
                    continue

                if lower == "help":
                    await add_system_event(
                        db,
                        sess,
                        "Команды: roll/adv/dis <1d20+3> (на своём ходу, не тратит ход), "
                        "pass|end (на своём ходу, заканчивает ход), "
                        "ooc <текст> или //текст (не тратит ход), "
                        "gm <текст> (только админ), "
                        "name <НовоеИмя> (не тратит ход), "
                        "leave (выйти), kick <#> (админ), turn <#> (админ), "
                        "init / init roll / init set <#> <val> / init start / init clear (админ)."
                    )
                    await broadcast_state(session_id)
                    continue

                # name change (any time)
                m_name = re.match(r"^name\s+(.+)$", lower, re.IGNORECASE)
                if m_name:
                    new_name = cmdline.split(" ", 1)[1].strip()
                    if new_name:
                        player.display_name = new_name
                        await db.commit()
                        await add_system_event(db, sess, f"Игрок #{sp.join_order} сменил имя на: {new_name}")
                        await broadcast_state(session_id)
                    continue

                # leave/quit (any time)
                if lower in ("leave", "quit"):
                    sp.is_active = False
                    await db.commit()
                    _set_ready(sess, player.id, False)
                    await db.commit()
                    await add_system_event(db, sess, f"Игрок вышел: {player.display_name} (#{sp.join_order}).")
                    # if it was their turn, advance turn
                    if sess.current_player_id == player.id and not sess.is_paused:
                        nxt = await advance_turn(db, sess)
                        if nxt:
                            await add_system_event(db, sess, f"Следующий ход: игрок #{nxt.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # admin: kick <#>
                if lower.startswith("kick "):
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can kick"}, ensure_ascii=False))
                        continue
                    arg = cmdline.split(" ", 1)[1].strip().lstrip("#")
                    target_order = as_int(arg, 0)
                    if target_order <= 0:
                        await ws.send_text(json.dumps({"type": "error", "message": "Usage: kick 2 or kick #2"}, ensure_ascii=False))
                        continue

                    # find target
                    sps_all = await list_session_players(db, sess, active_only=False)
                    target_sp = next((x for x in sps_all if int(x.join_order or 0) == target_order), None)
                    if not target_sp:
                        await ws.send_text(json.dumps({"type": "error", "message": "Player not found"}, ensure_ascii=False))
                        continue
                    if target_sp.player_id == player.id:
                        await ws.send_text(json.dumps({"type": "error", "message": "You can't kick yourself"}, ensure_ascii=False))
                        continue

                    # mark kicked
                    kicked = _get_kicked(sess)
                    kicked.add(str(target_sp.player_id))
                    _set_kicked(sess, kicked)

                    target_sp.is_active = False
                    await db.commit()
                    _set_ready(sess, target_sp.player_id, False)
                    await db.commit()

                    await add_system_event(db, sess, f"Игрок #{target_order} исключён (kick).")
                    # if kicked player had the turn, advance
                    if sess.current_player_id == target_sp.player_id and not sess.is_paused:
                        nxt = await advance_turn(db, sess)
                        if nxt:
                            await add_system_event(db, sess, f"Ход передан следующему: #{nxt.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # admin: turn/goto <#>
                if lower.startswith("turn ") or lower.startswith("goto "):
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can change turn"}, ensure_ascii=False))
                        continue
                    arg = cmdline.split(" ", 1)[1].strip().lstrip("#")
                    target_order = as_int(arg, 0)
                    if target_order <= 0:
                        await ws.send_text(json.dumps({"type": "error", "message": "Usage: turn 2 or goto #2"}, ensure_ascii=False))
                        continue
                    target = await set_turn_to_order(db, sess, target_order)
                    if not target:
                        await ws.send_text(json.dumps({"type": "error", "message": "Player not found/active"}, ensure_ascii=False))
                        continue
                    await add_system_event(db, sess, f"Админ передал ход игроку #{target.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # initiative commands (admin)
                if lower.startswith("init"):
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can manage initiative"}, ensure_ascii=False))
                        continue
                    parts = cmdline.split()
                    sub = parts[1].lower() if len(parts) > 1 else ""

                    sps_active = await list_session_players(db, sess, active_only=True)
                    init_map = _get_init_map(sess)
                    # prefetch display names to avoid awaits in formatter
                    pids_active = [spx.player_id for spx in sps_active]
                    names: dict[str, str] = {}
                    
                    # pids_active должен быть UUID (players.id). Всё прочее игнорируем, чтобы не сломать запрос.
                    uuid_ids: list[uuid.UUID] = []
                    for x in pids_active:
                        if isinstance(x, uuid.UUID):
                            uuid_ids.append(x)
                        else:
                            try:
                                uuid_ids.append(uuid.UUID(str(x)))
                            except Exception:
                                pass
                    uuid_ids = list(dict.fromkeys(uuid_ids))  # убираем дубли, сохраняя порядок

                    if uuid_ids:
                        qn = await db.execute(select(Player).where(Player.id.in_(uuid_ids)))
                        for p in qn.scalars().all():
                            names[str(p.id)] = p.display_name
                            if p.web_user_id is not None:
                                names[str(p.web_user_id)] = p.display_name
                    def _format_init(fixed: bool) -> str:
                        rows = []
                        header = ""
                        if fixed:
                            rnd = as_int(settings_get(sess, "round", 1), 1)
                            header = f"Раунд: {rnd}\n"
                        # order for display: if fixed, show initiative_order else by join_order
                        if fixed:
                            pids = _get_initiative_order(sess)
                            # keep only active
                            pids = [pid for pid in pids if pid in {spx.player_id for spx in sps_active}]
                            # append missing actives
                            for spx in sps_active:
                                if spx.player_id not in pids:
                                    pids.append(spx.player_id)
                            for pid in pids:
                                spx = next((x for x in sps_active if x.player_id == pid), None)
                                if not spx:
                                    continue
                                nm = names.get(str(pid), str(pid))
                                val = init_map.get(str(pid), 0)
                                cur = " ← ход" if sess.current_player_id == pid else ""
                                rows.append(f"  #{spx.join_order} {nm}: {val}{cur}")
                        else:
                            for spx in sps_active:
                                nm = names.get(str(spx.player_id), str(spx.player_id))
                                val = init_map.get(str(spx.player_id), 0)
                                cur = " ← ход" if sess.current_player_id == spx.player_id else ""
                                rows.append(f"  #{spx.join_order} {nm}: {val}{cur}")
                        return (header + "\n".join(rows)) if rows else (header + "  (нет игроков)")

                    if sub == "" or sub == "show":
                        fixed = _initiative_fixed(sess)
                        await add_system_event(
                            db,
                            sess,
                            f"Инициатива ({'зафиксирована' if fixed else 'не зафиксирована'}):\n{_format_init(fixed)}",
                        )
                        await broadcast_state(session_id)
                        continue

                    if sub == "roll":
                        for spx in sps_active:
                            val = random.randint(1, 20)
                            _set_init_value(sess, spx.player_id, val)
                        await db.commit()
                        init_map = _get_init_map(sess)
                        lines = []
                        for spx in sps_active:
                            nm = names.get(str(spx.player_id), str(spx.player_id))
                            lines.append(f"  #{spx.join_order} {nm}: {init_map.get(str(spx.player_id), 0)}")
                        await add_system_event(db, sess, "Инициатива: всем брошено 1d20:\n" + "\n".join(lines))
                        await broadcast_state(session_id)
                        continue

                    if sub == "set" and len(parts) >= 4:
                        target_order = as_int(parts[2].lstrip("#"), 0)
                        val = as_int(parts[3], 0)
                        target_sp = next((x for x in sps_active if int(x.join_order or 0) == target_order), None)
                        if not target_sp:
                            await ws.send_text(json.dumps({"type": "error", "message": "Player not found/active"}, ensure_ascii=False))
                            continue
                        _set_init_value(sess, target_sp.player_id, val)
                        await db.commit()
                        nm = names.get(str(target_sp.player_id), str(target_sp.player_id))
                        await add_system_event(db, sess, f"Инициатива: игрок #{target_order} ({nm}) = {val}.")
                        await broadcast_state(session_id)
                        continue

                    if sub == "start":
                        # fix order by initiative desc, then join_order asc
                        init_map = _get_init_map(sess)
                        scored = []
                        for spx in sps_active:
                            scored.append((init_map.get(str(spx.player_id), 0), int(spx.join_order or 0), spx.player_id))
                        scored.sort(key=lambda x: (-x[0], x[1]))
                        order = [pid for _, _, pid in scored]
                        _set_initiative_order(sess, order)
                        settings_set(sess, "initiative_fixed", True)
                        settings_set(sess, "round", 1)
                        await db.commit()

                        # move turn to first in initiative
                        first_pid = order[0] if order else None
                        if first_pid:
                            sess.is_active = True
                            sess.current_player_id = first_pid
                            sess.turn_started_at = utcnow()
                            sess.turn_index = (sess.turn_index or 0) + 1 if sess.turn_index else 1
                            _clear_paused_remaining(sess)
                            await db.commit()

                        # log
                        lines = []
                        for pid in order:
                            spx = next((x for x in sps_active if x.player_id == pid), None)
                            if not spx:
                                continue
                            nm = names.get(str(pid), str(pid))
                            lines.append(f"  #{spx.join_order} {nm}: {init_map.get(str(pid), 0)}")
                        await add_system_event(db, sess, "Инициатива зафиксирована. Порядок:\n" + "\n".join(lines))
                        if first_pid:
                            sp_first = next((x for x in sps_active if x.player_id == first_pid), None)
                            if sp_first:
                                await add_system_event(db, sess, f"Ход по инициативе: игрок #{sp_first.join_order}.")
                        await broadcast_state(session_id)
                        continue

                    if sub == "clear":
                        _clear_initiative(sess)
                        await db.commit()
                        await add_system_event(db, sess, "Инициатива сброшена.")
                        await broadcast_state(session_id)
                        continue

                    await ws.send_text(json.dumps({"type": "error", "message": "Unknown init command"}, ensure_ascii=False))
                    continue

                # DICE (must be started, not paused, your turn) — does NOT end turn
                dice = parse_dice(cmdline)
                if dice:
                    if not sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Game not started. Press Start."}, ensure_ascii=False))
                        continue
                    if sess.is_paused:
                        await ws.send_text(json.dumps({"type": "error", "message": "Paused."}, ensure_ascii=False))
                        continue
                    if player.id != sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Not your turn."}, ensure_ascii=False))
                        continue

                    mode, n, sides, mod, expr = dice
                    if mode == "roll":
                        rolls = roll_dice(n, sides)
                        total = sum(rolls) + mod
                        detail = ",".join(str(x) for x in rolls)
                        await add_system_event(db, sess, f"🎲 Игрок #{sp.join_order}: {expr} → {n}d{sides}({detail}){('+'+str(mod)) if mod>0 else (str(mod) if mod<0 else '')} = {total}")
                        await add_system_event(db, sess, "(ход не закончен)")
                        await broadcast_state(session_id)
                        continue

                    # adv/dis only meaningful for 1d20-ish but we allow any NdS as whole formula twice
                    rolls_a = roll_dice(n, sides)
                    rolls_b = roll_dice(n, sides)
                    tot_a = sum(rolls_a) + mod
                    tot_b = sum(rolls_b) + mod
                    chosen = max(tot_a, tot_b) if mode == "adv" else min(tot_a, tot_b)
                    da = ",".join(str(x) for x in rolls_a)
                    dbb = ",".join(str(x) for x in rolls_b)
                    tag = "adv" if mode == "adv" else "dis"
                    pick = "большее" if mode == "adv" else "меньшее"
                    await add_system_event(
                        db,
                        sess,
                        f"🎲 Игрок #{sp.join_order} ({tag}): {expr} → A: {n}d{sides}({da}){('+'+str(mod)) if mod>0 else (str(mod) if mod<0 else '')} = {tot_a}; "
                        f"B: {n}d{sides}({dbb}){('+'+str(mod)) if mod>0 else (str(mod) if mod<0 else '')} = {tot_b}; ✅ берём {pick} = {chosen}"
                    )
                    await add_system_event(db, sess, "(ход не закончен)")
                    await broadcast_state(session_id)
                    continue

                # PASS/END — ends turn
                if lower in ("pass", "end"):
                    if not sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Game not started. Press Start."}, ensure_ascii=False))
                        continue
                    if sess.is_paused:
                        await ws.send_text(json.dumps({"type": "error", "message": "Paused."}, ensure_ascii=False))
                        continue
                    if player.id != sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Not your turn."}, ensure_ascii=False))
                        continue
                    nxt = await advance_turn(db, sess)
                    if not nxt:
                        await ws.send_text(json.dumps({"type": "error", "message": "No players"}, ensure_ascii=False))
                        continue
                    await add_system_event(db, sess, f"Игрок #{sp.join_order} пропустил ход. Следующий: #{nxt.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # Normal SAY — ends turn
                if not sess.current_player_id:
                    await ws.send_text(json.dumps({"type": "error", "message": "Game not started. Press Start."}, ensure_ascii=False))
                    continue
                if sess.is_paused:
                    await ws.send_text(json.dumps({"type": "error", "message": "Paused."}, ensure_ascii=False))
                    continue
                if player.id != sess.current_player_id:
                    await ws.send_text(json.dumps({"type": "error", "message": "Not your turn."}, ensure_ascii=False))
                    continue

                # store message as player event (raw text)
                await add_event(db, sess, text, actor_player_id=player.id)

                nxt = await advance_turn(db, sess)
                if not nxt:
                    await ws.send_text(json.dumps({"type": "error", "message": "No players"}, ensure_ascii=False))
                    continue
                await add_system_event(db, sess, f"Следующий ход: игрок #{nxt.join_order}.")
                await broadcast_state(session_id)

    except WebSocketDisconnect:
        manager.disconnect(session_id, ws)
    except Exception:
        manager.disconnect(session_id, ws)
        raise


# -------------------------
# Timer watcher (autopass on timeout)
# -------------------------


async def timer_watcher():
    while True:
        try:
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

                        nxt = await advance_turn(db, sess)
                        if not nxt:
                            continue
                        await add_system_event(db, sess, f"⏰ Время вышло. Ход пропущен. Следующий: #{nxt.join_order}.")
                        await broadcast_state(str(sess.id))
                    finally:
                        request_id_var.reset(tok_rid)
                        session_id_var.reset(tok_sid)

        except Exception:
            logger.exception("timer_watcher iteration failed")

        await asyncio.sleep(1)


@app.on_event("startup")
async def on_startup():
    configure_logging()
    logger.info("Web server starting")
    asyncio.create_task(timer_watcher())
