import asyncio
import json
import os
import random
import re
from datetime import datetime, timedelta
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.connection import AsyncSessionLocal
from app.db.models import Session, Player, SessionPlayer, Event

TURN_TIMEOUT_SECONDS = int(os.getenv("TURN_TIMEOUT_SECONDS", "300"))
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Warsaw")


def utcnow() -> datetime:
    return datetime.utcnow()


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
        for ws in room:
            try:
                await ws.send_text(json.dumps(data, ensure_ascii=False))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)


manager = ConnectionManager()
app = FastAPI()


async def get_or_create_player_web(db: AsyncSession, uid: int, display_name: str, *, update_if_exists: bool = True) -> Player:
    """
    uid — это наш "web user id".
    Храним в Player.telegram_user_id, чтобы не менять твою БД-схему.
    """
    q = await db.execute(select(Player).where(Player.telegram_user_id == uid))
    player = q.scalar_one_or_none()
    if player:
        # обновим имя, если реально передали новое (не пустое)
        if update_if_exists and display_name and display_name.strip() and player.display_name != display_name.strip():
            player.display_name = display_name.strip()
            await db.commit()
        return player

    name = (display_name or "").strip() or f"Player {uid}"
    player = Player(
        telegram_user_id=uid,
        username=None,
        display_name=name,
    )
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return player


async def get_session(db: AsyncSession, session_id: str) -> Session | None:
    try:
        sid = uuid.UUID(session_id)
    except Exception:
        return None

    q = await db.execute(select(Session).where(Session.id == sid))
    return q.scalar_one_or_none()


async def list_session_players(db: AsyncSession, sess: Session) -> list[SessionPlayer]:
    # Иногда is_active может быть NULL (особенно на старых записях) — считаем это "активен".
    q = await db.execute(
        select(SessionPlayer)
        .where(
            SessionPlayer.session_id == sess.id,
            or_(SessionPlayer.is_active == True, SessionPlayer.is_active.is_(None)),
        )
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


async def add_system_event(db: AsyncSession, sess: Session, text: str) -> None:
    ev = Event(
        session_id=sess.id,
        turn_index=sess.turn_index or 0,
        actor_player_id=None,
        actor_character_id=None,
        message_text=f"[SYSTEM] {text}",
        parsed_json=None,
        result_json=None,
    )
    db.add(ev)
    await db.commit()

# --- Dice роллы (DnD) -------------------------------------------------------

_DICE_ALLOWED = re.compile(r"^[0-9dD+\-\s]+$")
_DICE_TERM = re.compile(r"^([0-9]*)d([0-9]+)$", re.IGNORECASE)

def _extract_dice_command(text: str) -> tuple[str | None, str] | None:
    """
    Понимает варианты:
      - roll 1d20+3 / /roll 1d20+3
      - adv 1d20+3 / /adv 1d20+3
      - dis 1d20+3 / /dis 1d20+3
      - просто 1d20+3
    Возвращает (mode, expr) где mode: None | 'adv' | 'dis'
    """
    t = (text or "").strip()
    if not t:
        return None

    low = t.lower()
    mode: str | None = None

    def _strip_prefix(prefix: str) -> str:
        return t[len(prefix):].strip()

    if low.startswith("/adv"):
        mode = "adv"
        expr = _strip_prefix("/adv")
    elif low.startswith("adv"):
        mode = "adv"
        expr = _strip_prefix("adv")
    elif low.startswith("/dis"):
        mode = "dis"
        expr = _strip_prefix("/dis")
    elif low.startswith("dis"):
        mode = "dis"
        expr = _strip_prefix("dis")
    elif low.startswith("/roll"):
        expr = _strip_prefix("/roll")
    elif low.startswith("roll"):
        expr = _strip_prefix("roll")
    else:
        expr = t

    expr = (expr or "").strip()
    if not expr:
        return None
    if not _DICE_ALLOWED.fullmatch(expr):
        return None

    compact = expr.replace(" ", "").lower()
    if "d" not in compact:
        return None
    return mode, compact

def _roll_dice_expr(expr: str) -> tuple[int, str]:
    """Возвращает (total, details). Пример details: '2d6(3,5)+3'"""
    s = (expr or "").replace(" ", "").lower()
    if not s or "d" not in s:
        raise ValueError("Неверное выражение для броска.")

    # токены вида +term / -term
    tokens: list[tuple[int, str]] = []
    for part in re.finditer(r"([+-]?)([^+-]+)", s):
        sign_raw = part.group(1)
        term = part.group(2)
        sign = -1 if sign_raw == "-" else 1
        if not term:
            continue
        tokens.append((sign, term))

    if not tokens:
        raise ValueError("Неверное выражение для броска.")

    total = 0
    pieces: list[str] = []
    for sign, term in tokens:
        # константа
        if "d" not in term:
            try:
                val = int(term)
            except Exception:
                raise ValueError(f"Неверный модификатор: {term}")
            total += sign * val
            pieces.append(("+%d" % val) if sign > 0 else ("-%d" % val))
            continue

        m = _DICE_TERM.match(term)
        if not m:
            raise ValueError(f"Неверный куб: {term}")
        n_str, sides_str = m.group(1), m.group(2)
        n = int(n_str) if n_str else 1
        sides = int(sides_str)

        # ограничения, чтобы никто не повесил сервер
        if n < 1 or n > 100:
            raise ValueError("Количество кубов должно быть 1..100")
        if sides < 2 or sides > 1000:
            raise ValueError("Грани куба должны быть 2..1000")

        rolls = [random.randint(1, sides) for _ in range(n)]
        subtotal = sum(rolls)
        total += sign * subtotal

        part_txt = f"{n}d{sides}(" + ",".join(map(str, rolls)) + ")"
        pieces.append(("+" + part_txt) if sign > 0 else ("-" + part_txt))

    details = "".join(pieces)
    if details.startswith("+"):
        details = details[1:]
    return total, details

def _roll_adv_dis(expr: str, mode: str) -> tuple[int, str]:
    """
    Advantage/Disadvantage: кидаем выражение 2 раза, берём лучшее/хужее.
    Возвращает (chosen_total, details).
    """
    t1, d1 = _roll_dice_expr(expr)
    t2, d2 = _roll_dice_expr(expr)

    if mode == "adv":
        chosen = t1 if t1 >= t2 else t2
        mark = "✅ берём большее"
    else:
        chosen = t1 if t1 <= t2 else t2
        mark = "✅ берём меньшее"

    details = f"A: {d1} = {t1}; B: {d2} = {t2}; {mark}"
    return chosen, details

# --------------------------------------------------------------------------



def _get_ready_map(sess: Session) -> dict[str, bool]:
    settings = dict(sess.settings or {})
    ready = settings.get("ready") or {}
    # keys as str(player_id)
    if not isinstance(ready, dict):
        ready = {}
    # normalize to bool
    norm: dict[str, bool] = {}
    for k, v in ready.items():
        try:
            norm[str(k)] = bool(v)
        except Exception:
            pass
    return norm


def _set_ready(sess: Session, player_id: int, value: bool) -> None:
    settings = dict(sess.settings or {})
    ready = settings.get("ready") or {}
    if not isinstance(ready, dict):
        ready = {}
    ready[str(player_id)] = bool(value)
    settings["ready"] = ready
    sess.settings = settings
    flag_modified(sess, "settings")


def _all_players_ready(sess: Session, sps: list[SessionPlayer]) -> bool:
    ready = _get_ready_map(sess)
    for sp in sps:
        if not ready.get(str(sp.player_id), False):
            return False
    return True



def _clear_ready(sess: Session, player_id: int) -> None:
    settings = dict(sess.settings or {})
    ready = settings.get("ready") or {}
    if not isinstance(ready, dict):
        ready = {}
    ready.pop(str(player_id), None)
    settings["ready"] = ready
    sess.settings = settings
    flag_modified(sess, "settings")


def _get_banned_set(sess: Session) -> set[str]:
    settings = dict(sess.settings or {})
    banned = settings.get("banned") or []
    if isinstance(banned, dict):
        # allow {"123": true}
        return {str(k) for k, v in banned.items() if v}
    if isinstance(banned, list):
        return {str(x) for x in banned}
    return set()


def _is_banned(sess: Session, player_id: int) -> bool:
    return str(player_id) in _get_banned_set(sess)


def _ban_player(sess: Session, player_id: int) -> None:
    settings = dict(sess.settings or {})
    banned_set = _get_banned_set(sess)
    banned_set.add(str(player_id))
    settings["banned"] = sorted(banned_set)
    sess.settings = settings
    flag_modified(sess, "settings")


# --- Initiative ------------------------------------------------------------

def _get_initiative_map(sess: Session) -> dict[str, int]:
    settings = dict(sess.settings or {})
    init = settings.get("initiative") or {}
    if not isinstance(init, dict):
        init = {}
    norm: dict[str, int] = {}
    for k, v in init.items():
        try:
            norm[str(k)] = int(v)
        except Exception:
            continue
    return norm


def _set_initiative(sess: Session, player_id: int, value: int) -> None:
    settings = dict(sess.settings or {})
    init = settings.get("initiative") or {}
    if not isinstance(init, dict):
        init = {}
    init[str(player_id)] = int(value)
    settings["initiative"] = init
    sess.settings = settings
    flag_modified(sess, "settings")


def _clear_initiative(sess: Session) -> None:
    settings = dict(sess.settings or {})
    settings.pop("initiative", None)
    settings.pop("initiative_order", None)
    settings.pop("initiative_locked", None)
    sess.settings = settings
    flag_modified(sess, "settings")


def _get_initiative_order(sess: Session) -> list[str]:
    settings = dict(sess.settings or {})
    order = settings.get("initiative_order") or []
    if not isinstance(order, list):
        order = []
    return [str(x) for x in order]


def _set_initiative_order(sess: Session, order_player_ids: list[int], locked: bool = True) -> None:
    settings = dict(sess.settings or {})
    settings["initiative_order"] = [str(x) for x in order_player_ids]
    settings["initiative_locked"] = bool(locked)
    sess.settings = settings
    flag_modified(sess, "settings")


def _is_initiative_locked(sess: Session) -> bool:
    settings = sess.settings if isinstance(sess.settings, dict) else {}
    return bool(settings.get("initiative_locked")) and bool(settings.get("initiative_order"))


def _active_initiative_order(sess: Session, sps: list[SessionPlayer]) -> list[str]:
    active = {str(sp.player_id) for sp in sps}
    return [pid for pid in _get_initiative_order(sess) if pid in active]

# --------------------------------------------------------------------------


async def _advance_turn_if_needed_after_removal(
    db: AsyncSession, sess: Session, removed_order: int | None
) -> SessionPlayer | None:
    # If game not started, nothing to advance.
    if not sess.current_player_id:
        return None

    sps = await list_session_players(db, sess)
    if not sps:
        sess.current_player_id = None
        sess.is_active = False
        sess.is_paused = False
        sess.turn_started_at = None
        # cleanup pause tail
        settings = dict(sess.settings or {})
        settings.pop("paused_remaining", None)
        sess.settings = settings
        flag_modified(sess, "settings")
        await db.commit()
        return None

    active_ids = {sp.player_id for sp in sps}
    # If current player still active, nothing to do.
    if sess.current_player_id in active_ids:
        return None

    pick: SessionPlayer | None = None

    # If initiative is locked, try to pick "next in initiative order" after the removed current.
    if _is_initiative_locked(sess):
        full_order = _get_initiative_order(sess)
        active_set = {str(sp.player_id) for sp in sps}
        cur_id = str(sess.current_player_id) if sess.current_player_id is not None else None

        if cur_id and cur_id in full_order and full_order:
            idx = full_order.index(cur_id)
            for step in range(1, len(full_order) + 1):
                cand = full_order[(idx + step) % len(full_order)]
                if cand in active_set:
                    pick = next((sp for sp in sps if str(sp.player_id) == cand), None)
                    break

        if not pick:
            active_order = _active_initiative_order(sess, sps)
            if active_order:
                pick = next((sp for sp in sps if str(sp.player_id) == active_order[0]), None)

    # Fallback: by join_order after removed_order.
    if not pick and removed_order is not None:
        for sp in sps:
            if int(sp.join_order or 0) > int(removed_order):
                pick = sp
                break

    if not pick:
        pick = sps[0]

    sess.current_player_id = pick.player_id
    sess.turn_index = (sess.turn_index or 0) + 1

    if sess.is_paused:
        settings = dict(sess.settings or {})
        settings["paused_remaining"] = TURN_TIMEOUT_SECONDS
        sess.settings = settings
        flag_modified(sess, "settings")
        sess.turn_started_at = None
    else:
        sess.turn_started_at = utcnow()

    await db.commit()
    return pick


async def next_player(db: AsyncSession, sess: Session) -> SessionPlayer | None:
    sps = await list_session_players(db, sess)
    if not sps:
        return None

    nxt: SessionPlayer | None = None

    # If initiative is locked, use initiative order.
    if _is_initiative_locked(sess):
        order_ids = _active_initiative_order(sess, sps)
        if order_ids:
            cur_id = str(sess.current_player_id) if sess.current_player_id is not None else None
            if cur_id in order_ids:
                idx = order_ids.index(cur_id)
                next_id = order_ids[(idx + 1) % len(order_ids)]
            else:
                next_id = order_ids[0]
            nxt = next((sp for sp in sps if str(sp.player_id) == next_id), None)

    # Fallback: join order
    if not nxt:
        idx = 0
        for i, sp in enumerate(sps):
            if sp.player_id == sess.current_player_id:
                idx = i
                break
        nxt = sps[(idx + 1) % len(sps)]

    sess.current_player_id = nxt.player_id
    sess.turn_index = (sess.turn_index or 0) + 1
    sess.turn_started_at = utcnow()

    # если пауза была раньше — сбрасываем сохранённый остаток времени
    settings = dict(sess.settings or {})
    settings.pop("paused_remaining", None)
    sess.settings = settings
    flag_modified(sess, "settings")

    await db.commit()
    return nxt


async def build_state(db: AsyncSession, sess: Session) -> dict:
    sps = await list_session_players(db, sess)
    player_ids = [sp.player_id for sp in sps]

    players: dict = {}
    if player_ids:
        q = await db.execute(select(Player).where(Player.id.in_(player_ids)))
        players = {p.id: p for p in q.scalars().all()}

    q2 = await db.execute(
        select(Event)
        .where(Event.session_id == sess.id)
        .order_by(Event.created_at.asc())
        .limit(200)
    )
    events = q2.scalars().all()

    remaining = None
    if sess.current_player_id:
        if sess.is_paused:
            pr = (sess.settings or {}).get("paused_remaining") if isinstance(sess.settings, dict) else None
            if pr is not None:
                try:
                    remaining = max(0, int(pr))
                except Exception:
                    remaining = None
        elif sess.turn_started_at:
            elapsed = (utcnow() - sess.turn_started_at).total_seconds()
            remaining = max(0, int(TURN_TIMEOUT_SECONDS - elapsed))

    cur_order = None
    for sp in sps:
        if sp.player_id == sess.current_player_id:
            cur_order = sp.join_order
            break

    ready_map = _get_ready_map(sess)
    all_ready = _all_players_ready(sess, sps) if sps else False

    return {
        "type": "state",
        "session": {
            "id": str(sess.id),  # UUID -> str
            "title": sess.title,
            "is_active": bool(sess.is_active),
            "is_paused": bool(sess.is_paused),
            "turn_index": int(sess.turn_index or 0),
            "current_order": cur_order,
            "remaining_seconds": remaining,
            "all_ready": bool(all_ready),
        },
        "players": [
            {
                "id": str(sp.player_id),  # на всякий случай тоже в str
                "name": (players.get(sp.player_id).display_name if players.get(sp.player_id) else str(sp.player_id)),
                "order": int(sp.join_order or 0),
                "is_admin": bool(sp.is_admin),
                "is_current": sp.player_id == sess.current_player_id,
                "is_ready": bool(ready_map.get(str(sp.player_id), False)),
                "uid": int(players.get(sp.player_id).telegram_user_id) if players.get(sp.player_id) and players.get(sp.player_id).telegram_user_id is not None else None,
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


@app.get("/", response_class=HTMLResponse)
async def index():
    html = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <title>AI-DnD Web</title>
  <style>
    body{font-family:Arial, sans-serif; max-width:900px; margin:24px auto; padding:0 12px;}
    input,button{padding:10px; font-size:16px;}
    .row{display:flex; gap:12px; flex-wrap:wrap; align-items:center;}
    .card{border:1px solid #333; border-radius:10px; padding:14px; margin-top:16px;}
    .muted{opacity:.75}
  </style>
</head>
<body>
  <h1>AI-DnD Web (v0.1)</h1>
  <div class="card">
    <h3>Создать игру</h3>
    <div class="row">
      <input id="new_title" placeholder="Название кампании" style="flex:1; min-width:240px"/>
      <button onclick="createGame()">Создать</button>
    </div>
    <p class="muted">После создания ты попадёшь в комнату и станешь админом.</p>
  </div>

  <div class="card">
    <h3>Войти в игру по ID</h3>
    <div class="row">
      <input id="join_id" placeholder="Session ID (UUID)" style="flex:1; min-width:240px"/>
      <button onclick="goJoin()">Перейти</button>
    </div>
  </div>

<script>
function getUID(){
  let uid = localStorage.getItem("uid");
  if(!uid){
    uid = String(Math.floor(1000000000 + Math.random()*9000000000));
    localStorage.setItem("uid", uid);
  }
  return Number(uid);
}
function getName(){
  let name = localStorage.getItem("name");
  if(!name){
    name = prompt("Имя игрока (как тебя показывать):", "Игрок");
    if(!name) name = "Игрок";
    localStorage.setItem("name", name);
  }
  return name;
}
async function createGame(){
  const title = document.getElementById("new_title").value || "Campaign";
  const uid = getUID();
  const name = getName();

  const r = await fetch("/api/new", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({title, uid, name})
  });
  const data = await r.json();
  if(!r.ok){ alert(data.detail || "Ошибка"); return; }
  location.href = "/s/" + data.session_id;
}
function goJoin(){
  const id = (document.getElementById("join_id").value || "").trim();
  if(!id){ alert("Введи Session ID"); return; }
  location.href = "/s/" + id;
}
</script>
</body>
</html>
"""
    return HTMLResponse(html)


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
            settings={"channel": "web", "ready": {}},
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

        _set_ready(sess, player.id, False)
        await db.commit()

        await add_system_event(db, sess, f"Создана игра «{title}». Админ: {player.display_name}.")

    return JSONResponse({"session_id": str(sess.id)})


@app.get("/s/{session_id}", response_class=HTMLResponse)
async def session_page(session_id: str):
    html = f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <title>Session {session_id}</title>
  <style>
    body{{font-family:Arial, sans-serif; margin:0;}}
    .wrap{{display:grid; grid-template-columns: 1fr 280px; gap:0; height:100vh;}}
    .main{{padding:16px; overflow:auto;}}
    .side{{border-left:1px solid #333; padding:16px; overflow:auto;}}
    .log{{border:1px solid #333; border-radius:10px; padding:12px; height:60vh; overflow:auto; background:#0f0f0f; color:#eaeaea;}}
    .row{{display:flex; gap:10px; margin-top:12px;}}
    input{{flex:1; padding:10px; font-size:16px;}}
    button{{padding:10px; font-size:14px;}}
    .player{{padding:8px 10px; border:1px solid #333; border-radius:10px; margin-top:8px;}}
    .cur{{border-color:#6cff6c;}}
    .muted{{opacity:.75}}
  </style>
</head>
<body>
<div class="wrap">
  <div class="main">
    <h2 id="title">Session {session_id}</h2>
    <div class="muted">Session ID: <code>{session_id}</code></div>

    <div class="log" id="log"></div>

    <div class="row">
      <input id="msg" placeholder="Напиши действие обычным текстом (без /)"/>
      <button onclick="sendMsg()">Отправить</button>
    </div>

    <div class="row">
      <button id="btn_start" onclick="wsAction('begin')">Start (admin)</button>
      <button onclick="wsAction('pause')">Pause (admin)</button>
      <button onclick="wsAction('resume')">Resume (admin)</button>
      <button onclick="wsAction('skip')">Skip (admin)</button>
      <button id="ready_btn" onclick="wsAction('ready')">Ready</button>
      <button onclick="wsAction('status')">Status</button>
    </div>

    <div class="muted" style="margin-top:10px;">
      Если не отвечает на текст: проверь, что ты нажал Start и сейчас твой ход.
    </div>
  </div>

  <div class="side">
    <h3>Игроки</h3>
    <div id="players"></div>
    <h3 style="margin-top:18px;">Таймер</h3>
    <div id="timer" class="player">—</div>
  </div>
</div>

<script>
const SESSION_ID = "{session_id}";
let ws = null;
let timerInt = null;
let timerRemain = null;
let timerSyncedAt = 0;

function stopLocalTimer(){{
  if(timerInt){{ clearInterval(timerInt); timerInt = null; }}
  timerRemain = null;
  timerSyncedAt = 0;
}}

function startLocalTimer(rem){{
  stopLocalTimer();
  timerRemain = Number(rem);
  timerSyncedAt = Date.now();

  timerInt = setInterval(() => {{
    const passed = Math.floor((Date.now() - timerSyncedAt) / 1000);
    const left = Math.max(0, timerRemain - passed);
    const t = document.getElementById("timer");
    t.textContent = "Осталось: " + left + " сек";
  }}, 250);
}}

function getUID(){{
  let uid = localStorage.getItem("uid");
  if(!uid){{
    uid = String(Math.floor(1000000000 + Math.random()*9000000000));
    localStorage.setItem("uid", uid);
  }}
  return Number(uid);
}}
function getName(){{
  let name = localStorage.getItem("name");
  if(!name){{
    name = prompt("Имя игрока (как тебя показывать):", "Игрок");
    if(!name) name = "Игрок";
    localStorage.setItem("name", name);
  }}
  return name;
}}

function escapeHtml(s){{
  return (s||"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
}}

function logLine(text){{
  const el = document.getElementById("log");
  el.innerHTML += "<div style='margin-bottom:6px; white-space:pre-wrap;'>" + escapeHtml(text) + "</div>";
  el.scrollTop = el.scrollHeight;
}}

async function joinIfNeeded(){{
  const uid = getUID();
  const name = getName();

  const r = await fetch("/api/join", {{
    method:"POST",
    headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{session_id: SESSION_ID, uid, name}})
  }});
  const data = await r.json();
  if(!r.ok){{ alert(data.detail || "Ошибка join"); throw new Error("join failed"); }}
}}

function connectWS(){{
  const uid = getUID();
  const proto = (location.protocol === "https:") ? "wss" : "ws";
  ws = new WebSocket(`${{proto}}://${{location.host}}/ws/${{SESSION_ID}}?uid=${{uid}}`);

  ws.onopen = () => {{
    logLine("[client] connected");
  }};
  ws.onmessage = (ev) => {{
    const data = JSON.parse(ev.data);
    if(data.type === "state"){{
      renderState(data);
    }} else if(data.type === "error"){{
      logLine("[error] " + data.message);
    }}
  }};
  ws.onclose = () => {{
    logLine("[client] disconnected, retry in 1s");
    setTimeout(connectWS, 1000);
  }};
}}

function renderState(st){{
  document.getElementById("title").textContent = st.session.title + " (turn " + (st.session.turn_index || 0) + ")";
  const p = document.getElementById("players");
  p.innerHTML = "";
  for(const pl of st.players){{
    const div = document.createElement("div");
    div.className = "player" + (pl.is_current ? " cur" : "");
    const mark = pl.is_ready ? " ✅" : " ⏳";
    div.textContent = `#${{pl.order}} ${{pl.name}}` + (pl.is_admin ? " [admin]" : "") + mark;
    p.appendChild(div);
  }}

  const myUid = getUID();
  const me = (st.players || []).find(pl => pl.uid === myUid);

  const rb = document.getElementById("ready_btn");
  if(rb){{
    rb.disabled = !me || !!st.session.is_active;
    rb.textContent = (me && me.is_ready) ? "Not Ready" : "Ready";
  }}

  const sb = document.getElementById("btn_start");
  if(sb){{
    const canStart = (me && me.is_admin && !!st.session.all_ready && !st.session.is_active);
    sb.disabled = !canStart;
  }}

  const el = document.getElementById("log");
  el.innerHTML = "";
  for(const e of st.events){{
    logLine(`[${{e.turn}}] ${{e.text}}`);
  }}


  const t = document.getElementById("timer");
  if(st.session.is_paused){{
    stopLocalTimer();
    t.textContent = "PAUSED";
  }} else if(st.session.remaining_seconds === null || st.session.remaining_seconds === undefined){{
    stopLocalTimer();
    t.textContent = "—";
  }} else {{
    startLocalTimer(st.session.remaining_seconds);
  }}
}}

function sendMsg(){{
  const inp = document.getElementById("msg");
  const text = (inp.value || "").trim();

  // если игрок меняет имя, синхронизируем localStorage, чтобы /api/join не перетёр новое имя
  const low = text.toLowerCase();
  if(low.startsWith("name ") || low.startsWith("/name ") || low === "/name"){{
    const nn = text.replace(/^\\/?name\\s+/i, "").trim();
    if(nn) localStorage.setItem("name", nn);
  }}
  if(!text) return;
  inp.value = "";
  if(!ws || ws.readyState !== 1){{
    logLine("[error] websocket not connected");
    return;
  }}
  ws.send(JSON.stringify({{action:"say", text}}));
}}

function wsAction(action){{
  if(!ws || ws.readyState !== 1){{
    logLine("[error] websocket not connected");
    return;
  }}
  ws.send(JSON.stringify({{action}}));
}}

joinIfNeeded().then(() => connectWS());
</script>
</body>
</html>
"""
    return HTMLResponse(html)


@app.post("/api/join")
async def api_join(payload: dict):
    session_id = payload.get("session_id")
    uid = int(payload.get("uid"))
    name = (payload.get("name") or "Игрок").strip()

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_or_create_player_web(db, uid, name, update_if_exists=False)

        q = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q.scalar_one_or_none()
        if sp:
            # если игрок был исключён (ban) — не пускаем обратно
            if _is_banned(sess, player.id):
                raise HTTPException(status_code=403, detail="You were kicked from this session")
            # если игрок ранее вышел — активируем обратно
            if sp.is_active is False:
                sp.is_active = True
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


@app.websocket("/ws/{session_id}")
async def ws_room(ws: WebSocket, session_id: str):
    uid_raw = ws.query_params.get("uid")
    if not uid_raw or not uid_raw.isdigit():
        await ws.accept()
        await ws.send_text(json.dumps({"type": "error", "message": "No uid"}, ensure_ascii=False))
        await ws.close()
        return

    uid = int(uid_raw)
    await manager.connect(session_id, ws)

    try:
        # первичное состояние
        await broadcast_state(session_id)

        while True:
            raw = await ws.receive_text()

            try:
                data = json.loads(raw)
            except Exception:
                data = {"action": "say", "text": raw}

            action = data.get("action")
            text = (data.get("text") or "").strip()

            async with AsyncSessionLocal() as db:
                sess = await get_session(db, session_id)
                if not sess:
                    await ws.send_text(json.dumps({"type": "error", "message": "Session not found"}, ensure_ascii=False))
                    continue

                # имя НЕ перетираем (оно задаётся в /api/join)
                player = await get_or_create_player_web(db, uid, "", update_if_exists=False)

                q = await db.execute(
                    select(SessionPlayer).where(
                        SessionPlayer.session_id == sess.id,
                        SessionPlayer.player_id == player.id,
                    )
                )
                sp = q.scalar_one_or_none()
                if not sp:
                    await ws.send_text(json.dumps({"type": "error", "message": "Not joined. Refresh page."}, ensure_ascii=False))
                    continue

                # если игрок был исключён/вышел — закрываем соединение
                if _is_banned(sess, player.id):
                    await ws.send_text(json.dumps({"type": "error", "message": "You were kicked from this session"}, ensure_ascii=False))
                    await ws.close()
                    manager.disconnect(session_id, ws)
                    return
                if sp.is_active is False:
                    await ws.send_text(json.dumps({"type": "error", "message": "You are not active in this session. Refresh to join again."}, ensure_ascii=False))
                    await ws.close()
                    manager.disconnect(session_id, ws)
                    return


                if action == "status":
                    pass

                elif action == "ready":
                    if sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Game already started"}, ensure_ascii=False))
                        continue
                    cur = _get_ready_map(sess).get(str(player.id), False)
                    new_val = not cur
                    _set_ready(sess, player.id, new_val)
                    await db.commit()
                    await add_system_event(db, sess, f"Готовность: игрок #{sp.join_order} — {'ГОТОВ' if new_val else 'не готов'}.")

                elif action == "begin":
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can start"}, ensure_ascii=False))
                        continue

                    if sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Already started"}, ensure_ascii=False))
                        continue

                    sps = await list_session_players(db, sess)
                    if not sps:
                        await ws.send_text(json.dumps({"type": "error", "message": "No players"}, ensure_ascii=False))
                        continue

                    if not _all_players_ready(sess, sps):
                        ready_map = _get_ready_map(sess)
                        missing = [sp.join_order for sp in sps if not ready_map.get(str(sp.player_id), False)]
                        miss_txt = ", ".join([f"#{o}" for o in missing if o is not None]) or "unknown"
                        await ws.send_text(json.dumps({"type": "error", "message": f"Not all players are ready: {miss_txt}"}, ensure_ascii=False))
                        continue

                    sess.is_active = True
                    sess.current_player_id = sps[0].player_id
                    sess.turn_index = 1
                    sess.turn_started_at = utcnow()
                    sess.is_paused = False
                    # очищаем возможный "хвост" паузы
                    settings = dict(sess.settings or {})
                    settings.pop("paused_remaining", None)
                    sess.settings = settings
                    flag_modified(sess, "settings")
                    await db.commit()

                    await add_system_event(db, sess, f"Игра началась. Ход игрока #{sps[0].join_order}.")

                elif action == "pause":
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can pause"}, ensure_ascii=False))
                        continue
                    # сохраняем остаток времени и "замораживаем" ход
                    remaining = None
                    if sess.turn_started_at and sess.current_player_id and not sess.is_paused:
                        elapsed = (utcnow() - sess.turn_started_at).total_seconds()
                        remaining = max(0, int(TURN_TIMEOUT_SECONDS - elapsed))

                    settings = dict(sess.settings or {})
                    if remaining is not None:
                        settings["paused_remaining"] = remaining
                    sess.settings = settings
                    flag_modified(sess, "settings")
                    sess.is_paused = True
                    sess.turn_started_at = None
                    await db.commit()
                    if remaining is not None:
                        await add_system_event(db, sess, f"Пауза. Осталось: {remaining} сек.")
                    else:
                        await add_system_event(db, sess, "Пауза.")

                elif action == "resume":
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can resume"}, ensure_ascii=False))
                        continue
                    settings = dict(sess.settings or {})
                    pr = settings.pop("paused_remaining", None)
                    sess.settings = settings
                    flag_modified(sess, "settings")
                    sess.is_paused = False
                    if sess.current_player_id:
                        if pr is None:
                            # если не знаем остаток — считаем, что просто перезапуск
                            sess.turn_started_at = utcnow()
                        else:
                            try:
                                pr_int = int(pr)
                                pr_int = max(0, min(pr_int, TURN_TIMEOUT_SECONDS))
                            except Exception:
                                pr_int = TURN_TIMEOUT_SECONDS
                            elapsed_before = TURN_TIMEOUT_SECONDS - pr_int
                            sess.turn_started_at = utcnow() - timedelta(seconds=elapsed_before)
                    else:
                        sess.turn_started_at = None

                    await db.commit()
                    if pr is None:
                        await add_system_event(db, sess, "Продолжили игру. Таймер перезапущен.")
                    else:
                        await add_system_event(db, sess, f"Продолжили игру. Осталось: {int(pr) if str(pr).isdigit() else '—'} сек.")

                elif action == "skip":
                    if not await is_admin(db, sess, player):
                        await ws.send_text(json.dumps({"type": "error", "message": "Only admin can skip"}, ensure_ascii=False))
                        continue
                    if not sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Not started"}, ensure_ascii=False))
                        continue
                    if sess.is_paused:
                        await ws.send_text(json.dumps({"type": "error", "message": "Paused. Resume first."}, ensure_ascii=False))
                        continue

                    nxt = await next_player(db, sess)
                    if not nxt:
                        await ws.send_text(json.dumps({"type": "error", "message": "No players"}, ensure_ascii=False))
                        continue
                    await add_system_event(db, sess, f"Ход пропущен. Следующий: #{nxt.join_order}.")

                elif action == "say":
                    if not text:
                        continue
                    low = text.lower().strip()
                
                    
                    # name: смена имени (не тратит ход)
                    if low.startswith("name ") or low.startswith("/name"):
                        new_name = re.sub(r"^/?name\s+", "", text, flags=re.IGNORECASE).strip()
                        if not new_name:
                            await ws.send_text(json.dumps({"type": "error", "message": "Usage: name <New Name>"}, ensure_ascii=False))
                            continue
                        if len(new_name) > 50:
                            await ws.send_text(json.dumps({"type": "error", "message": "Name too long (max 50)"}, ensure_ascii=False))
                            continue
                        player.display_name = new_name
                        await db.commit()
                        await add_system_event(db, sess, f"Игрок #{sp.join_order} сменил имя на: {new_name}")
                        await broadcast_state(session_id)
                        continue


                    # leave/quit: выйти из игры (не тратит ход)
                    if low in ("leave", "/leave", "quit", "/quit", "exit", "/exit"):
                        sp.is_active = False
                        _clear_ready(sess, player.id)
                        await db.commit()
                        await add_system_event(db, sess, f"Игрок #{sp.join_order} вышел из игры.")
                        # если вышел текущий игрок — передаём ход
                        nxt = await _advance_turn_if_needed_after_removal(db, sess, int(sp.join_order or 0))
                        if nxt:
                            await add_system_event(db, sess, f"Текущий игрок вышел. Следующий: #{nxt.join_order}.")
                        elif sess.current_player_id is None:
                            await add_system_event(db, sess, "Игра остановлена: нет активных игроков.")
                        await broadcast_state(session_id)
                        await ws.close()
                        manager.disconnect(session_id, ws)
                        return

                    # kick: исключить игрока по номеру (только админ). Пример: kick 2 или kick #2
                    if low.startswith("kick ") or low.startswith("/kick"):
                        if not await is_admin(db, sess, player):
                            await ws.send_text(json.dumps({"type": "error", "message": "Only admin can kick"}, ensure_ascii=False))
                            continue
                        arg = re.sub(r"^/?kick\s+", "", text, flags=re.IGNORECASE).strip()
                        mo = re.search(r"#?(\d+)", arg)
                        if not mo:
                            await ws.send_text(json.dumps({"type": "error", "message": "Usage: kick <player_number> (join order)"}, ensure_ascii=False))
                            continue
                        order = int(mo.group(1))
                        qk = await db.execute(
                            select(SessionPlayer).where(
                                SessionPlayer.session_id == sess.id,
                                SessionPlayer.join_order == order,
                            )
                        )
                        target_sp = qk.scalar_one_or_none()
                        if not target_sp or target_sp.is_active is False:
                            await ws.send_text(json.dumps({"type": "error", "message": "Player not found or already inactive"}, ensure_ascii=False))
                            continue
                        if target_sp.player_id == player.id:
                            await ws.send_text(json.dumps({"type": "error", "message": "You cannot kick yourself"}, ensure_ascii=False))
                            continue

                        # имя для лога
                        qn = await db.execute(select(Player).where(Player.id == target_sp.player_id))
                        tp = qn.scalar_one_or_none()
                        tname = tp.display_name if tp else str(target_sp.player_id)

                        target_sp.is_active = False
                        _clear_ready(sess, target_sp.player_id)
                        _ban_player(sess, target_sp.player_id)
                        await db.commit()

                        await add_system_event(db, sess, f"Админ исключил игрока #{order} ({tname}).")

                        # если исключили текущего — передаём ход
                        nxt = await _advance_turn_if_needed_after_removal(db, sess, int(target_sp.join_order or 0))
                        if nxt:
                            await add_system_event(db, sess, f"Текущий игрок исключён. Следующий: #{nxt.join_order}.")
                        elif sess.current_player_id is None:
                            await add_system_event(db, sess, "Игра остановлена: нет активных игроков.")

                        await broadcast_state(session_id)
                        continue


                    # turn/goto: передать ход конкретному игроку по номеру (только админ). Пример: turn 2 / goto #3
                    if low.startswith("turn ") or low.startswith("/turn") or low.startswith("goto ") or low.startswith("/goto"):
                        if not await is_admin(db, sess, player):
                            await ws.send_text(json.dumps({"type": "error", "message": "Only admin can change turn"}, ensure_ascii=False))
                            continue
                        if not sess.current_player_id:
                            await ws.send_text(json.dumps({"type": "error", "message": "Not started"}, ensure_ascii=False))
                            continue

                        arg = re.sub(r"^/?(turn|goto)\s+", "", text, flags=re.IGNORECASE).strip()
                        mo = re.search(r"#?(\d+)", arg)
                        if not mo:
                            await ws.send_text(json.dumps({"type": "error", "message": "Usage: turn <player_number> (join order)"}, ensure_ascii=False))
                            continue
                        order = int(mo.group(1))

                        qt = await db.execute(
                            select(SessionPlayer).where(
                                SessionPlayer.session_id == sess.id,
                                SessionPlayer.join_order == order,
                                or_(SessionPlayer.is_active == True, SessionPlayer.is_active.is_(None)),
                            )
                        )
                        target_sp = qt.scalar_one_or_none()
                        if not target_sp:
                            await ws.send_text(json.dumps({"type": "error", "message": "Player not found or inactive"}, ensure_ascii=False))
                            continue

                        sess.current_player_id = target_sp.player_id
                        sess.turn_index = (sess.turn_index or 0) + 1

                        if sess.is_paused:
                            # оставляем паузу, но ставим полное время новому игроку
                            settings = dict(sess.settings or {})
                            settings["paused_remaining"] = TURN_TIMEOUT_SECONDS
                            sess.settings = settings
                            flag_modified(sess, "settings")
                            sess.turn_started_at = None
                        else:
                            # полный таймер для нового хода
                            sess.turn_started_at = utcnow()

                        await db.commit()
                        await add_system_event(db, sess, f"Админ передал ход игроку #{order}.")
                        await broadcast_state(session_id)
                        continue


                    # init: инициатива (init / init set / init roll / init start / init clear)
                    if low == "init" or low == "/init" or low.startswith("init ") or low.startswith("/init "):
                        cmd = re.sub(r"^/?init\s*", "", text, flags=re.IGNORECASE).strip()

                        sps_all = await list_session_players(db, sess)
                        if not sps_all:
                            await add_system_event(db, sess, "Инициатива: нет игроков.")
                            await broadcast_state(session_id)
                            continue

                        order_map = {int(spx.join_order or 0): spx for spx in sps_all}
                        init_map = _get_initiative_map(sess)

                        pids = [spx.player_id for spx in sps_all]
                        qpl = await db.execute(select(Player).where(Player.id.in_(pids)))
                        pby = {p.id: p for p in qpl.scalars().all()}

                        locked = _is_initiative_locked(sess)

                        def _nm(spx: SessionPlayer) -> str:
                            p = pby.get(spx.player_id)
                            return p.display_name if p else str(spx.player_id)

                        if not cmd:
                            lines: list[str] = []
                            if locked:
                                order_ids = _active_initiative_order(sess, sps_all)
                                lines.append("Инициатива (зафиксирована):")
                                for pid in order_ids:
                                    spx = next((x for x in sps_all if str(x.player_id) == pid), None)
                                    if not spx:
                                        continue
                                    val = int(init_map.get(str(spx.player_id), 0))
                                    cur_mark = " ← ход" if spx.player_id == sess.current_player_id else ""
                                    lines.append(f"  #{int(spx.join_order or 0)} {_nm(spx)}: {val}{cur_mark}")
                            else:
                                lines.append("Инициатива (не зафиксирована):")
                                sorted_sps = sorted(
                                    sps_all,
                                    key=lambda x: (-int(init_map.get(str(x.player_id), 0)), int(x.join_order or 0)),
                                )
                                for spx in sorted_sps:
                                    val = int(init_map.get(str(spx.player_id), 0))
                                    cur_mark = " ← ход" if spx.player_id == sess.current_player_id else ""
                                    lines.append(f"  #{int(spx.join_order or 0)} {_nm(spx)}: {val}{cur_mark}")

                            await add_system_event(db, sess, "\n".join(lines))
                            await broadcast_state(session_id)
                            continue

                        parts = cmd.split()
                        sub = (parts[0] or "").lower()

                        # только админ может менять/фиксировать инициативу
                        if sub in ("set", "roll", "start", "clear"):
                            if not await is_admin(db, sess, player):
                                await ws.send_text(json.dumps({"type": "error", "message": "Only admin can manage initiative"}, ensure_ascii=False))
                                continue

                        if sub == "set":
                            if len(parts) < 3:
                                await ws.send_text(json.dumps({"type": "error", "message": "Usage: init set <player#> <value>"}, ensure_ascii=False))
                                continue
                            mo = re.search(r"#?(\d+)", parts[1])
                            if not mo:
                                await ws.send_text(json.dumps({"type": "error", "message": "Usage: init set <player#> <value>"}, ensure_ascii=False))
                                continue
                            order = int(mo.group(1))
                            try:
                                val = int(parts[2])
                            except Exception:
                                await ws.send_text(json.dumps({"type": "error", "message": "Initiative value must be a number"}, ensure_ascii=False))
                                continue
                            if val < -50 or val > 50:
                                await ws.send_text(json.dumps({"type": "error", "message": "Initiative value range: -50..50"}, ensure_ascii=False))
                                continue

                            tsp = order_map.get(order)
                            if not tsp:
                                await ws.send_text(json.dumps({"type": "error", "message": "Player not found"}, ensure_ascii=False))
                                continue

                            _set_initiative(sess, tsp.player_id, val)
                            await db.commit()
                            await add_system_event(db, sess, f"Инициатива: игрок #{order} ({_nm(tsp)}) = {val}.")
                            await broadcast_state(session_id)
                            continue

                        if sub == "roll":
                            settings = dict(sess.settings or {})
                            init = settings.get("initiative") or {}
                            if not isinstance(init, dict):
                                init = {}
                            lines = ["Инициатива: всем брошено 1d20:"]
                            for spx in sorted(sps_all, key=lambda x: int(x.join_order or 0)):
                                r = random.randint(1, 20)
                                init[str(spx.player_id)] = r
                                lines.append(f"  #{int(spx.join_order or 0)} {_nm(spx)}: {r}")
                            settings["initiative"] = init
                            sess.settings = settings
                            flag_modified(sess, "settings")
                            await db.commit()
                            await add_system_event(db, sess, "\n".join(lines))
                            await broadcast_state(session_id)
                            continue

                        if sub == "start":
                            if not sess.current_player_id:
                                await ws.send_text(json.dumps({"type": "error", "message": "Game not started. Press Start."}, ensure_ascii=False))
                                continue

                            # фиксируем порядок: инициатива ↓, при равенстве — по номеру игрока ↑
                            sorted_sps = sorted(
                                sps_all,
                                key=lambda x: (-int(init_map.get(str(x.player_id), 0)), int(x.join_order or 0)),
                            )
                            order_ids_int = [int(x.player_id) for x in sorted_sps]
                            _set_initiative_order(sess, order_ids_int, locked=True)

                            first = sorted_sps[0]
                            sess.current_player_id = first.player_id
                            sess.turn_index = (sess.turn_index or 0) + 1

                            if sess.is_paused:
                                settings = dict(sess.settings or {})
                                settings["paused_remaining"] = TURN_TIMEOUT_SECONDS
                                sess.settings = settings
                                flag_modified(sess, "settings")
                                sess.turn_started_at = None
                            else:
                                sess.turn_started_at = utcnow()

                            await db.commit()

                            lines = ["Инициатива зафиксирована. Порядок:"]
                            for spx in sorted_sps:
                                val = int(init_map.get(str(spx.player_id), 0))
                                lines.append(f"  #{int(spx.join_order or 0)} {_nm(spx)}: {val}")
                            await add_system_event(db, sess, "\n".join(lines))
                            await add_system_event(db, sess, f"Ход по инициативе: игрок #{int(first.join_order or 0)}.")
                            await broadcast_state(session_id)
                            continue

                        if sub == "clear":
                            _clear_initiative(sess)
                            await db.commit()
                            await add_system_event(db, sess, "Инициатива сброшена.")
                            await broadcast_state(session_id)
                            continue

                        await ws.send_text(json.dumps({"type": "error", "message": "Unknown init command. Use: init | init set | init roll | init start | init clear"}, ensure_ascii=False))
                        continue

# --- сообщения, которые НЕ тратят ход (OOC / GM / help) ---
                    # OOC: "ooc ..." или "//..."
                    ooc_msg = None
                    if low.startswith("//"):
                        ooc_msg = text[2:].strip()
                    elif low.startswith("ooc "):
                        ooc_msg = text[4:].strip()
                    elif low.startswith("ooc:"):
                        ooc_msg = text[4:].strip()
                    elif low.startswith("/ooc"):
                        ooc_msg = text[4:].strip()
                    if ooc_msg:
                        ev = Event(
                            session_id=sess.id,
                            turn_index=sess.turn_index or 0,
                            actor_player_id=player.id,
                            actor_character_id=None,
                            message_text=f"[OOC] {player.display_name} (#{sp.join_order}): {ooc_msg}",
                            parsed_json=None,
                            result_json=None,
                        )
                        db.add(ev)
                        await db.commit()
                        await broadcast_state(session_id)
                        continue
                
                    # GM: "gm ..." или "gm: ..." (только админ)
                    gm_msg = None
                    if low.startswith("gm "):
                        gm_msg = text[3:].strip()
                    elif low.startswith("gm:"):
                        gm_msg = text[3:].strip()
                    elif low.startswith("/gm"):
                        gm_msg = text[3:].strip()
                    if gm_msg:
                        if not await is_admin(db, sess, player):
                            await ws.send_text(json.dumps({"type": "error", "message": "Only admin can use GM messages"}, ensure_ascii=False))
                            continue
                        await add_system_event(db, sess, f"🧙 GM: {gm_msg}")
                        await broadcast_state(session_id)
                        continue
                
                    # help
                    if low in ("help", "/help"):
                        await add_system_event(db, sess, "Команды: roll/adv/dis <1d20+3> (на своём ходу, не тратит ход), pass/end (на своём ходу, тратит ход), ooc <текст> или //текст (не тратит ход), gm <текст> (только админ), name <Новое имя> (не тратит ход), leave/quit (выйти, можно вернуться), kick <№> (только админ), turn/goto <№> (только админ), init (показать), init set <№> <значение>, init roll, init start, init clear (только админ).")
                        await broadcast_state(session_id)
                        continue
                
                    # --- обычное действие игрока (тратит ход) ---
                    if not sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Game not started. Press Start."}, ensure_ascii=False))
                        continue
                    if sess.is_paused:
                        await ws.send_text(json.dumps({"type": "error", "message": "Paused."}, ensure_ascii=False))
                        continue
                    if player.id != sess.current_player_id:
                        await ws.send_text(json.dumps({"type": "error", "message": "Not your turn."}, ensure_ascii=False))
                        continue

                    # pass/end: пропустить ход (тратит ход)
                    if low in ("pass", "/pass", "end", "/end"):
                        ev = Event(
                            session_id=sess.id,
                            turn_index=sess.turn_index,
                            actor_player_id=player.id,
                            actor_character_id=None,
                            message_text=text,
                            parsed_json=None,
                            result_json=None,
                        )
                        db.add(ev)
                        await db.commit()

                        nxt = await next_player(db, sess)
                        if not nxt:
                            await ws.send_text(json.dumps({"type": "error", "message": "No players"}, ensure_ascii=False))
                            continue
                        await add_system_event(db, sess, f"Игрок #{sp.join_order} пропустил ход. Следующий: #{nxt.join_order}.")
                        await broadcast_state(session_id)
                        continue
                    # броски кубов: roll / adv / dis / просто 1d20+3
                    dice_cmd = _extract_dice_command(text)
                    if dice_cmd is not None:
                        mode, dice_expr = dice_cmd
                        try:
                            if mode in ("adv", "dis"):
                                total, details = _roll_adv_dis(dice_expr, mode)
                            else:
                                total, details = _roll_dice_expr(dice_expr)
                        except ValueError as e:
                            await ws.send_text(json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False))
                            continue
                
                        # пишем команду игрока как событие, чтобы было видно, что он бросал
                        ev = Event(
                            session_id=sess.id,
                            turn_index=sess.turn_index,
                            actor_player_id=player.id,
                            actor_character_id=None,
                            message_text=text,
                            parsed_json=None,
                            result_json=None,
                        )
                        db.add(ev)
                        await db.commit()
                
                        tag = f" ({mode})" if mode else ""
                        await add_system_event(db, sess, f"🎲 Игрок #{sp.join_order}{tag}: {dice_expr} → {details} = {total}")
                        await add_system_event(db, sess, "(ход не закончен)")
                
                        # ВАЖНО: бросок кубов не заканчивает ход.
                        await broadcast_state(session_id)
                        continue
                
                    ev = Event(
                        session_id=sess.id,
                        turn_index=sess.turn_index,
                        actor_player_id=player.id,
                        actor_character_id=None,
                        message_text=text,
                        parsed_json=None,
                        result_json=None,
                    )
                    db.add(ev)
                    await db.commit()
                
                    nxt = await next_player(db, sess)
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
                    elapsed = (now - sess.turn_started_at).total_seconds()
                    if elapsed < TURN_TIMEOUT_SECONDS:
                        continue

                    nxt = await next_player(db, sess)
                    if not nxt:
                        continue
                    await add_system_event(db, sess, f"⏰ Время вышло. Ход пропущен. Следующий: #{nxt.join_order}.")
                    await broadcast_state(str(sess.id))
        except Exception:
            pass

        await asyncio.sleep(1)


@app.on_event("startup")
async def on_startup():
    print("[OK] Web server starting...")
    asyncio.create_task(timer_watcher())