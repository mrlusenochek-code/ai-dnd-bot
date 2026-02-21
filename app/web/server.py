import asyncio
import ast
import json
import logging
import os
import random
import re
from datetime import datetime, timedelta, timezone
import uuid
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.ai.gm import generate_from_prompt, generate_lore
from app.core.logging import configure_logging
from app.core.log_context import request_id_var, session_id_var, uid_var, ws_conn_id_var, client_id_var
from app.db.connection import AsyncSessionLocal
from app.db.models import Session, Player, SessionPlayer, Character, Skill, Event


TURN_TIMEOUT_SECONDS = int(os.getenv("TURN_TIMEOUT_SECONDS", "300"))
INACTIVE_TIMEOUT_SECONDS = int(os.getenv("DND_INACTIVE_TIMEOUT_SECONDS", "600"))
INACTIVE_SCAN_PERIOD_SECONDS = int(os.getenv("DND_INACTIVE_SCAN_PERIOD_SECONDS", "5"))
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Warsaw")
GM_CONTEXT_EVENTS = max(1, int(os.getenv("GM_CONTEXT_EVENTS", "20")))
GM_OLLAMA_TIMEOUT_SECONDS = max(1.0, float(os.getenv("GM_OLLAMA_TIMEOUT_SECONDS", "30")))
logger = logging.getLogger(__name__)
CHAR_STAT_KEYS = ("str", "dex", "con", "int", "wis", "cha")
CHAR_DEFAULT_STATS = {k: 50 for k in CHAR_STAT_KEYS}
CHECK_LINE_RE = re.compile(r"^\s*@@CHECK\s+(\{.*\})\s*$", re.IGNORECASE)
INV_MACHINE_LINE_RE = re.compile(r"^\s*@@(?P<cmd>INV_ADD|INV_REMOVE|INV_TRANSFER)\s*\((?P<args>.*)\)\s*$", re.IGNORECASE)
TEXTUAL_CHECK_RE = re.compile(
    r"(?:проверка|check)\s*[:\-]?\s*([a-zA-Zа-яА-Я_]+)[^\n]{0,40}?\bdc\s*[:=]?\s*(\d+)",
    re.IGNORECASE,
)
SKILL_TO_ABILITY: dict[str, str] = {
    "acrobatics": "dex",
    "animal_handling": "wis",
    "arcana": "int",
    "athletics": "str",
    "deception": "cha",
    "history": "int",
    "insight": "wis",
    "intimidation": "cha",
    "investigation": "int",
    "medicine": "wis",
    "nature": "int",
    "perception": "wis",
    "performance": "cha",
    "persuasion": "cha",
    "religion": "int",
    "sleight_of_hand": "dex",
    "stealth": "dex",
    "survival": "wis",
    "endurance": "con",
    "tracking": "wis",
    "trickery": "dex",
    "focus": "wis",
    "faith": "wis",
}
STAT_ALIASES = {
    "strength": "str",
    "dexterity": "dex",
    "constitution": "con",
    "intelligence": "int",
    "wisdom": "wis",
    "charisma": "cha",
    "сила": "str",
    "ловкость": "dex",
    "телосложение": "con",
    "интеллект": "int",
    "мудрость": "wis",
    "харизма": "cha",
}
CLASS_PRESETS: dict[str, dict[str, Any]] = {
    "fighter": {
        "display_name": "Fighter",
        "hp_max": 24,
        "sta_max": 12,
        "stats_shift": {"str": 15, "con": 10, "dex": 5, "int": -5, "wis": -5, "cha": 0},
        "starter_skills": {"athletics": 2, "endurance": 1},
    },
    "rogue": {
        "display_name": "Rogue",
        "hp_max": 18,
        "sta_max": 14,
        "stats_shift": {"str": 0, "con": 0, "dex": 15, "int": 5, "wis": 0, "cha": 5},
        "starter_skills": {"stealth": 2, "trickery": 1},
    },
    "ranger": {
        "display_name": "Ranger",
        "hp_max": 20,
        "sta_max": 13,
        "stats_shift": {"str": 5, "con": 5, "dex": 10, "int": 0, "wis": 10, "cha": -5},
        "starter_skills": {"survival": 2, "tracking": 1},
    },
    "mage": {
        "display_name": "Mage",
        "hp_max": 16,
        "sta_max": 12,
        "stats_shift": {"str": -10, "con": -5, "dex": 0, "int": 20, "wis": 10, "cha": 0},
        "starter_skills": {"arcana": 2, "focus": 1},
    },
    "cleric": {
        "display_name": "Cleric",
        "hp_max": 20,
        "sta_max": 11,
        "stats_shift": {"str": 0, "con": 5, "dex": 0, "int": 5, "wis": 15, "cha": 5},
        "starter_skills": {"faith": 2, "medicine": 1},
    },
    "bard": {
        "display_name": "Bard",
        "hp_max": 18,
        "sta_max": 13,
        "stats_shift": {"str": -5, "con": 0, "dex": 5, "int": 5, "wis": 0, "cha": 20},
        "starter_skills": {"performance": 2, "persuasion": 1},
    },
}
STORY_DIFFICULTY_VALUES = {"easy", "medium", "hard"}
STORY_HEALTH_SYSTEM_VALUES = {"none", "normal"}
STORY_DMG_SCALE_VALUES = {"reduced", "standard", "increased"}
STORY_AI_VERBOSITY_VALUES = {"auto", "restrained", "very_restrained"}
STATE_COMMAND_ALIASES = {"state", "inv", "инв", "inventory"}


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
_GM_SESSION_LOCKS: dict[str, asyncio.Lock] = {}


def _get_session_gm_lock(session_id: str) -> asyncio.Lock:
    lock = _GM_SESSION_LOCKS.get(session_id)
    if lock is None:
        lock = asyncio.Lock()
        _GM_SESSION_LOCKS[session_id] = lock
    return lock


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


def _looks_like_refusal(text: str) -> bool:
    t = str(text or "").strip().lower()
    if not t:
        return False

    # базовые маркеры "не могу"
    cannot = ("не могу" in t) or ("can't" in t) or ("cannot" in t) or ("can’t" in t)
    if not cannot:
        return False

    # жёсткие шаблоны отказов (почти всегда это именно отказ ассистента)
    hard = [
        "я не могу продолжить эту тему",
        "я не могу продолжать эту тему",
        "я не могу помочь с этим",
        "не могу помочь с этим",
        "я не могу предоставить",
        "не могу предоставить",
        "i can't help",
        "i cannot help",
        "i can't continue",
        "i cannot continue",
        "i can't comply",
        "i cannot comply",
    ]
    if any(x in t for x in hard):
        return True

    # мягкие маркеры отказа: извинения / предложение помочь "с другим" / ссылки на правила
    starts_apology = t.startswith(("извини", "простите", "прошу прощения", "sorry", "i'm sorry", "i am sorry"))
    offers_other = any(x in t for x in (
        "я могу помочь с другим",
        "могу помочь с другим",
        "могу помочь с чем-то другим",
        "i can help with something else",
        "something else",
    ))
    mentions_policy = any(x in t for x in (
        "политик", "правил", "policy", "guideline",
        "как модель", "как ии", "as an ai",
    ))

    if starts_apology or offers_other or mentions_policy:
        return True

    return False
    t = str(text or "").lower()
    if "я не могу" not in t and "i can't" not in t:
        return False
    return any(k in t for k in ["сексу", "насил", "эксплуатац", "sexual", "violence"])


def _story_is_configured(sess: Session) -> bool:
    raw = settings_get(sess, "story", {}) or {}
    return bool(isinstance(raw, dict) and raw.get("story_configured"))


def infer_zone_from_action(text: str, current_zone: str) -> str:
    t = str(text or "").strip().lower()
    if not t:
        return current_zone
    if any(k in t for k in ("таверн", "бар", "внутри", "остаюсь")):
        return "таверна"
    if any(k in t for k in ("улиц", "выйду", "выхожу", "на улиц")):
        return "улица у таверны"
    if any(k in t for k in ("центр", "площад")):
        return "центр города"
    if any(k in t for k in ("река", "берег")):
        return "берег реки"
    if "замок" in t:
        if any(k in t for k in ("в замк", "внутри замк", "захожу в зам", "войти в зам", "вхожу в зам")):
            return "замок"
        return "дорога к замку"
    return current_zone


def _infer_initial_zone(lore_text: str, last_gm_text: str) -> str:
    src = f"{lore_text}\n{last_gm_text}".lower()
    if "таверн" in src:
        return "таверна"
    return "стартовая локация (вместе)"


def _split_red_flags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        parts = [str(x).strip() for x in raw]
    else:
        txt = str(raw or "")
        parts = [x.strip() for x in re.split(r"[\n,]+", txt)]
    out: list[str] = []
    for item in parts:
        if item:
            out.append(item[:200])
    return out


def _normalize_story_config(sess: Session, raw: Any) -> dict[str, Any]:
    cfg = raw if isinstance(raw, dict) else {}
    difficulty = str(cfg.get("difficulty") or "medium").strip().lower()
    if difficulty not in STORY_DIFFICULTY_VALUES:
        difficulty = "medium"
    health_system = str(cfg.get("health_system") or "normal").strip().lower()
    if health_system not in STORY_HEALTH_SYSTEM_VALUES:
        health_system = "normal"
    dmg_scale = str(cfg.get("dmg_scale") or "standard").strip().lower()
    if dmg_scale not in STORY_DMG_SCALE_VALUES:
        dmg_scale = "standard"
    ai_verbosity = str(cfg.get("ai_verbosity") or "auto").strip().lower()
    if ai_verbosity not in STORY_AI_VERBOSITY_VALUES:
        ai_verbosity = "auto"

    story_title = str(cfg.get("story_title") or "").strip()
    if not story_title:
        story_title = str(sess.title or "Campaign").strip() or "Campaign"

    return {
        "story_title": story_title[:200],
        "story_setting": str(cfg.get("story_setting") or "").strip()[:2000],
        "free_turns": bool(cfg.get("free_turns")),
        "difficulty": difficulty,
        "health_system": health_system,
        "dmg_scale": dmg_scale,
        "journal_hint": str(cfg.get("journal_hint") or "").strip()[:1000],
        "red_flags": _split_red_flags(cfg.get("red_flags")),
        "ai_verbosity": ai_verbosity,
        "gm_notes": str(cfg.get("gm_notes") or "").strip()[:1000],
    }


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


async def get_player_by_uid(db: AsyncSession, uid: int) -> Optional[Player]:
    q = await db.execute(select(Player).where(Player.web_user_id == uid))
    return q.scalar_one_or_none()


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


def _clamp(n: int, low: int, high: int) -> int:
    return max(low, min(high, n))


def _normalized_stats(stats_raw: Any) -> dict[str, int]:
    out = dict(CHAR_DEFAULT_STATS)
    if isinstance(stats_raw, dict):
        for key in CHAR_STAT_KEYS:
            if key in stats_raw:
                out[key] = _clamp(as_int(stats_raw.get(key), 50), 0, 100)
    return out


def _player_uid(player: Optional[Player]) -> Optional[int]:
    if not player:
        return None
    raw = player.web_user_id if player.web_user_id is not None else player.telegram_user_id
    return int(raw) if raw is not None else None


def _ability_mod_from_stats(stats_raw: Any, stat_key: str) -> int:
    stats = _normalized_stats(stats_raw)
    val = stats.get(stat_key, 50)
    return _clamp(int((val - 50) / 10), -5, 5)


def _normalize_check_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "normal").strip().lower()
    if mode in {"adv", "advantage"}:
        return "advantage"
    if mode in {"dis", "disadvantage"}:
        return "disadvantage"
    return "normal"


def _normalize_check_name(raw_name: Any) -> str:
    name = str(raw_name or "").strip().lower()
    return STAT_ALIASES.get(name, name)


def _check_kind_for_name(raw_kind: Any, normalized_name: str) -> str:
    kind = str(raw_kind or "").strip().lower()
    if normalized_name in CHAR_STAT_KEYS:
        return "ability"
    if kind in {"skill", "ability", "stat"}:
        return kind
    return "skill"


def _extract_checks_from_draft(draft_text: str, default_actor_uid: Optional[int]) -> tuple[str, list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    text_lines: list[str] = []
    for line in (draft_text or "").splitlines():
        m = CHECK_LINE_RE.match(line)
        if not m:
            text_lines.append(line)
            continue
        raw_json = m.group(1)
        try:
            payload = json.loads(raw_json)
        except Exception:
            text_lines.append(line)
            continue
        if not isinstance(payload, dict):
            text_lines.append(line)
            continue
        if payload.get("actor_uid") is None and default_actor_uid is not None:
            payload["actor_uid"] = default_actor_uid
        checks.append(payload)
    text = "\n".join(text_lines).strip()
    has_human_check_request = bool(TEXTUAL_CHECK_RE.search(text))
    return text, checks, has_human_check_request


def _checks_from_human_text(draft_text: str, default_actor_uid: Optional[int]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in TEXTUAL_CHECK_RE.finditer(draft_text or ""):
        name = _normalize_check_name(m.group(1))
        dc = as_int(m.group(2), 0)
        if dc <= 0:
            continue
        out.append(
            {
                "actor_uid": default_actor_uid,
                "kind": _check_kind_for_name(None, name),
                "name": name,
                "dc": dc,
                "mode": "normal",
                "reason": "ранее запрошено текстом",
            }
        )
    return out


def _trim_for_log(text: str, limit: int = 700) -> str:
    txt = str(text or "").strip()
    if len(txt) <= limit:
        return txt
    return txt[:limit] + "... [truncated]"


def _strip_machine_lines(text: str) -> str:
    out: list[str] = []
    for line in (text or "").splitlines():
        if line.strip().startswith("@@CHECK"):
            continue
        if line.strip().startswith("@@CHECK_RESULT"):
            continue
        out.append(line)
    return "\n".join(out).strip()


def _character_meta_from_stats(stats_raw: Any) -> dict[str, str]:
    if not isinstance(stats_raw, dict):
        return {"gender": "", "race": "", "description": ""}
    raw_meta = stats_raw.get("_meta")
    if not isinstance(raw_meta, dict):
        return {"gender": "", "race": "", "description": ""}
    return {
        "gender": str(raw_meta.get("gender") or "").strip()[:40],
        "race": str(raw_meta.get("race") or "").strip()[:60],
        "description": str(raw_meta.get("description") or "").strip()[:1000],
    }


def _put_character_meta_into_stats(stats_raw: Any, *, gender: str, race: str, description: str) -> dict[str, Any]:
    stats = dict(stats_raw) if isinstance(stats_raw, dict) else {}
    stats["_meta"] = {
        "gender": str(gender or "").strip()[:40],
        "race": str(race or "").strip()[:60],
        "description": str(description or "").strip()[:1000],
    }
    return stats


def _slugify_inventory_id(raw: Any, fallback_name: str, index: int) -> str:
    src = str(raw or fallback_name or "").strip().lower()
    src = re.sub(r"[^a-z0-9]+", "-", src)
    src = src.strip("-")
    if src:
        return src[:40]
    return f"item-{max(1, index)}"


def _normalize_inventory_item(raw_item: Any, index: int) -> Optional[dict[str, Any]]:
    if isinstance(raw_item, str):
        name = raw_item.strip()
        qty = 1
        item_id_raw = ""
        tags_raw = None
        notes_raw = ""
    elif isinstance(raw_item, dict):
        name = str(raw_item.get("name") or "").strip()
        qty = _clamp(as_int(raw_item.get("qty"), 1), 1, 99)
        item_id_raw = str(raw_item.get("id") or "").strip()
        tags_raw = raw_item.get("tags")
        notes_raw = str(raw_item.get("notes") or "").strip()
    else:
        return None

    if not name:
        return None

    item: dict[str, Any] = {
        "id": _slugify_inventory_id(item_id_raw, name, index),
        "name": name[:80],
        "qty": _clamp(as_int(qty, 1), 1, 99),
    }

    if isinstance(tags_raw, list):
        tags: list[str] = []
        for tag in tags_raw:
            t = str(tag or "").strip()
            if t:
                tags.append(t[:30])
            if len(tags) >= 8:
                break
        if tags:
            item["tags"] = tags

    notes = str(notes_raw or "").strip()[:200]
    if notes:
        item["notes"] = notes

    return item


def _parse_inventory_text(raw_text: Any) -> list[dict[str, Any]]:
    text = str(raw_text or "")
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        ln = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(line or "").strip())
        if not ln:
            continue
        qty = 1
        name = ln
        m_tail = re.match(r"^(.*?)\s*[xх*]\s*(\d{1,2})\s*$", ln, flags=re.IGNORECASE)
        if m_tail:
            name = m_tail.group(1).strip()
            qty = _clamp(as_int(m_tail.group(2), 1), 1, 99)
        else:
            m_head = re.match(r"^(\d{1,2})\s*[xх*]?\s+(.+?)\s*$", ln, flags=re.IGNORECASE)
            if m_head:
                qty = _clamp(as_int(m_head.group(1), 1), 1, 99)
                name = m_head.group(2).strip()
        if name:
            items.append({"name": name, "qty": qty})
    return items


def _normalize_inventory_payload(inventory_raw: Any, inventory_text_raw: Any) -> list[dict[str, Any]]:
    source_items: list[Any]
    if isinstance(inventory_raw, list):
        source_items = inventory_raw
    elif str(inventory_text_raw or "").strip():
        source_items = _parse_inventory_text(inventory_text_raw)
    else:
        source_items = []

    out: list[dict[str, Any]] = []
    for idx, raw_item in enumerate(source_items, start=1):
        normalized = _normalize_inventory_item(raw_item, idx)
        if normalized:
            out.append(normalized)
        if len(out) >= 60:
            break
    return out


def _character_inventory_from_stats(stats_raw: Any) -> list[dict[str, Any]]:
    if not isinstance(stats_raw, dict):
        return []
    raw = stats_raw.get("_inv")
    return raw if isinstance(raw, list) else []


def _put_character_inventory_into_stats(stats_raw: Any, inventory: list[dict[str, Any]]) -> dict[str, Any]:
    stats = dict(stats_raw) if isinstance(stats_raw, dict) else {}
    stats["_inv"] = list(inventory) if isinstance(inventory, list) else []
    return stats


def _split_machine_args(args_raw: str) -> list[str]:
    parts: list[str] = []
    cur: list[str] = []
    in_quote: Optional[str] = None
    depth = 0
    esc = False
    for ch in str(args_raw or ""):
        if esc:
            cur.append(ch)
            esc = False
            continue
        if ch == "\\":
            cur.append(ch)
            esc = True
            continue
        if in_quote:
            cur.append(ch)
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ("'", '"'):
            cur.append(ch)
            in_quote = ch
            continue
        if ch in ("[", "{", "("):
            depth += 1
            cur.append(ch)
            continue
        if ch in ("]", "}", ")"):
            depth = max(0, depth - 1)
            cur.append(ch)
            continue
        if ch == "," and depth == 0:
            token = "".join(cur).strip()
            if token:
                parts.append(token)
            cur = []
            continue
        cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_machine_value(raw: str) -> Any:
    src = str(raw or "").strip()
    if not src:
        return ""
    if re.fullmatch(r"[+-]?\d+", src):
        return as_int(src, 0)
    if src[0] in ("'", '"', "[", "{", "("):
        try:
            return ast.literal_eval(src)
        except Exception:
            pass
    return src


def _parse_inventory_machine_line(line: str) -> Optional[dict[str, Any]]:
    m = INV_MACHINE_LINE_RE.match(str(line or ""))
    if not m:
        return None
    cmd = str(m.group("cmd") or "").strip().upper()
    args_raw = str(m.group("args") or "")
    fields: dict[str, Any] = {}
    for token in _split_machine_args(args_raw):
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        k = str(key or "").strip().lower()
        if not k:
            continue
        fields[k] = _parse_machine_value(value)

    if cmd == "INV_ADD":
        uid = as_int(fields.get("uid"), 0)
        name = str(fields.get("name") or "").strip()
        if uid <= 0 or not name:
            return None
        tags: Optional[list[str]] = None
        tags_raw = fields.get("tags")
        if isinstance(tags_raw, (list, tuple)):
            tag_vals: list[str] = []
            for tag in tags_raw:
                t = str(tag or "").strip()
                if not t:
                    continue
                tag_vals.append(t[:30])
                if len(tag_vals) >= 8:
                    break
            if tag_vals:
                tags = tag_vals
        notes = str(fields.get("notes") or "").strip()[:200]
        return {
            "op": "add",
            "uid": uid,
            "name": name[:80],
            "qty": _clamp(as_int(fields.get("qty"), 1), 1, 99),
            "tags": tags,
            "notes": notes or None,
        }
    if cmd == "INV_REMOVE":
        uid = as_int(fields.get("uid"), 0)
        name = str(fields.get("name") or "").strip()
        if uid <= 0 or not name:
            return None
        return {
            "op": "remove",
            "uid": uid,
            "name": name[:80],
            "qty": _clamp(as_int(fields.get("qty"), 1), 1, 99),
        }
    if cmd == "INV_TRANSFER":
        from_uid = as_int(fields.get("from_uid"), 0)
        to_uid = as_int(fields.get("to_uid"), 0)
        name = str(fields.get("name") or "").strip()
        if from_uid <= 0 or to_uid <= 0 or not name:
            return None
        return {
            "op": "transfer",
            "from_uid": from_uid,
            "to_uid": to_uid,
            "name": name[:80],
            "qty": _clamp(as_int(fields.get("qty"), 1), 1, 99),
        }
    return None


def _extract_inventory_machine_commands(text: str) -> tuple[str, list[dict[str, Any]]]:
    out_lines: list[str] = []
    commands: list[dict[str, Any]] = []
    for line in str(text or "").splitlines():
        if not str(line).lstrip().startswith("@@INV_"):
            out_lines.append(line)
            continue
        parsed = _parse_inventory_machine_line(line)
        if parsed:
            commands.append(parsed)
        else:
            logger.warning("invalid inventory machine command", extra={"action": {"line": _trim_for_log(line, 260)}})
    return "\n".join(out_lines).strip(), commands


def _find_inventory_item_index(inv: list[dict[str, Any]], name_or_id: str) -> Optional[int]:
    needle_name = str(name_or_id or "").strip().lower()
    if not needle_name:
        return None
    needle_id = _slugify_inventory_id(name_or_id, name_or_id, 1)
    for idx, raw_item in enumerate(inv):
        if not isinstance(raw_item, dict):
            continue
        item_name = str(raw_item.get("name") or "").strip().lower()
        item_id = str(raw_item.get("id") or "").strip().lower()
        if item_name == needle_name or item_id == needle_id:
            return idx
    return None


def _inv_add_on_character(
    ch: Character,
    *,
    name: str,
    qty: int,
    tags: Optional[list[str]] = None,
    notes: Optional[str] = None,
) -> bool:
    inv_raw = _character_inventory_from_stats(ch.stats)
    inv: list[dict[str, Any]] = [dict(x) for x in inv_raw if isinstance(x, dict)]
    idx = _find_inventory_item_index(inv, name)
    changed = False
    if idx is not None:
        item = dict(inv[idx])
        cur_qty = _clamp(as_int(item.get("qty"), 1), 1, 99)
        next_qty = _clamp(cur_qty + _clamp(as_int(qty, 1), 1, 99), 1, 99)
        if next_qty != cur_qty:
            item["qty"] = next_qty
            changed = True
        if tags is not None:
            item["tags"] = tags
            changed = True
        if notes:
            item["notes"] = str(notes).strip()[:200]
            changed = True
        inv[idx] = item
    else:
        normalized = _normalize_inventory_item(
            {"id": _slugify_inventory_id("", name, len(inv) + 1), "name": name, "qty": qty, "tags": tags, "notes": notes or ""},
            len(inv) + 1,
        )
        if normalized:
            inv.append(normalized)
            changed = True
    if changed:
        ch.stats = _put_character_inventory_into_stats(ch.stats, inv)
    return changed


def _inv_remove_on_character(ch: Character, *, name: str, qty: int) -> tuple[bool, int, Optional[dict[str, Any]]]:
    inv_raw = _character_inventory_from_stats(ch.stats)
    inv: list[dict[str, Any]] = [dict(x) for x in inv_raw if isinstance(x, dict)]
    idx = _find_inventory_item_index(inv, name)
    if idx is None:
        return False, 0, None
    item = dict(inv[idx])
    cur_qty = _clamp(as_int(item.get("qty"), 1), 1, 99)
    take = min(cur_qty, _clamp(as_int(qty, 1), 1, 99))
    next_qty = cur_qty - take
    if next_qty <= 0:
        inv.pop(idx)
    else:
        item["qty"] = next_qty
        inv[idx] = item
    ch.stats = _put_character_inventory_into_stats(ch.stats, inv)
    removed_item = dict(item)
    removed_item["qty"] = take
    return True, take, removed_item


async def _apply_inventory_machine_commands(db: AsyncSession, sess: Session, commands: list[dict[str, Any]]) -> None:
    if not commands:
        return
    uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
    positions = _get_pc_positions(sess)
    for cmd in commands:
        op = str(cmd.get("op") or "").strip().lower()
        if op == "add":
            uid = as_int(cmd.get("uid"), 0)
            ch = chars_by_uid.get(uid)
            if not ch:
                logger.warning("INV_ADD target not found", extra={"action": {"uid": uid, "name": cmd.get("name")}})
                continue
            _inv_add_on_character(
                ch,
                name=str(cmd.get("name") or ""),
                qty=_clamp(as_int(cmd.get("qty"), 1), 1, 99),
                tags=cmd.get("tags") if isinstance(cmd.get("tags"), list) else None,
                notes=str(cmd.get("notes") or "").strip() or None,
            )
            continue

        if op == "remove":
            uid = as_int(cmd.get("uid"), 0)
            ch = chars_by_uid.get(uid)
            if not ch:
                logger.warning("INV_REMOVE target not found", extra={"action": {"uid": uid, "name": cmd.get("name")}})
                continue
            changed, _qty, _removed = _inv_remove_on_character(
                ch,
                name=str(cmd.get("name") or ""),
                qty=_clamp(as_int(cmd.get("qty"), 1), 1, 99),
            )
            if not changed:
                logger.warning("INV_REMOVE source item not found", extra={"action": {"uid": uid, "name": cmd.get("name")}})
            continue

        if op == "transfer":
            from_uid = as_int(cmd.get("from_uid"), 0)
            to_uid = as_int(cmd.get("to_uid"), 0)
            from_ch = chars_by_uid.get(from_uid)
            to_ch = chars_by_uid.get(to_uid)
            from_pair = uid_map.get(from_uid)
            to_pair = uid_map.get(to_uid)
            if not from_ch or not to_ch or not from_pair or not to_pair:
                logger.warning(
                    "INV_TRANSFER participants not found",
                    extra={"action": {"from_uid": from_uid, "to_uid": to_uid, "name": cmd.get("name")}},
                )
                continue
            from_zone = str(positions.get(str(from_pair[0].player_id), "") or "")
            to_zone = str(positions.get(str(to_pair[0].player_id), "") or "")
            if from_zone != to_zone:
                logger.warning(
                    "INV_TRANSFER blocked due to different zones",
                    extra={
                        "action": {
                            "from_uid": from_uid,
                            "to_uid": to_uid,
                            "name": cmd.get("name"),
                            "from_zone": from_zone,
                            "to_zone": to_zone,
                        }
                    },
                )
                continue
            changed, moved_qty, removed_item = _inv_remove_on_character(
                from_ch,
                name=str(cmd.get("name") or ""),
                qty=_clamp(as_int(cmd.get("qty"), 1), 1, 99),
            )
            if not changed or moved_qty <= 0 or not removed_item:
                logger.warning(
                    "INV_TRANSFER source item not found",
                    extra={"action": {"from_uid": from_uid, "to_uid": to_uid, "name": cmd.get("name")}},
                )
                continue
            _inv_add_on_character(
                to_ch,
                name=str(removed_item.get("name") or cmd.get("name") or ""),
                qty=moved_qty,
                tags=removed_item.get("tags") if isinstance(removed_item.get("tags"), list) else None,
                notes=str(removed_item.get("notes") or "").strip() or None,
            )
            continue


def _inventory_state_line(ch: Optional[Character]) -> str:
    if not ch:
        return "пусто"
    inv = _character_inventory_from_stats(ch.stats)
    parts: list[str] = []
    for item in inv:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        qty = _clamp(as_int(item.get("qty"), 1), 1, 99)
        parts.append(f"{name} x{qty}" if qty > 1 else name)
        if len(parts) >= 20:
            break
    return "; ".join(parts) if parts else "пусто"


def _format_state_text_for_player(sess: Session, player: Player, ch: Optional[Character]) -> str:
    zone = _get_pc_positions(sess).get(str(player.id), "стартовая локация (вместе)")
    char_name = str(ch.name).strip() if ch and str(ch.name or "").strip() else "(персонаж не создан)"
    hp_sta = "HP/STA: —"
    if ch:
        hp_sta = f"HP {as_int(ch.hp, 0)}/{as_int(ch.hp_max, 0)} | STA {as_int(ch.sta, 0)}/{as_int(ch.sta_max, 0)}"
    inv_line = _inventory_state_line(ch)
    return f"Состояние: {char_name}\nЗона: {zone}\n{hp_sta}\nИнвентарь: {inv_line}"


def _inventory_prompt_line(stats_raw: Any, max_len: int = 150) -> str:
    inv = _character_inventory_from_stats(stats_raw)
    if not inv:
        return ""
    parts: list[str] = []
    for item in inv:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        qty = _clamp(as_int(item.get("qty"), 1), 1, 99)
        parts.append(f"{name} x{qty}" if qty > 1 else name)
        if len(parts) >= 12:
            break
    if not parts:
        return ""
    return _short_text("inventory: " + "; ".join(parts), max(120, min(160, max_len)))


def _short_text(text: str, limit: int) -> str:
    txt = str(text or "").strip()
    if len(txt) <= limit:
        return txt
    return txt[:limit].rstrip() + "..."


def _sanitize_gm_output(text: str) -> str:
    txt = str(text or "").strip()
    if not txt:
        return ""
    txt = re.sub(r"<think\b[^>]*>.*?</think\s*>", " ", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"</?think\b[^>]*>", " ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"@@CHECK_RESULT", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"@@CHECK", "", txt, flags=re.IGNORECASE)

    cleaned_lines: list[str] = []
    for line in txt.splitlines():
        ln = line.strip()
        if re.match(r"^(финальный|итоговый)\s+ответ\b[:\s-]*$", ln, flags=re.IGNORECASE):
            continue
        cleaned_lines.append(line)
    txt = "\n".join(cleaned_lines)

    txt = re.sub(r"\b(давайте\s+)?проанализируем\b", "Продолжим сцену", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\b(в\s+)?черновик\w*\b", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\bдрафт\w*\b", "", txt, flags=re.IGNORECASE)

    txt = re.sub(
        r"(извиняюсь|извини(?:те)?|прошу прощения)[^.!?\n]{0,160}(я\s+)?не\s+могу[^.!?\n]{0,220}[.!?]?",
        "Сцена продолжается.",
        txt,
        flags=re.IGNORECASE,
    )
    txt = re.sub(r"\bя\s+не\s+могу[^.!?\n]{0,260}[.!?]?", "Сцена продолжается.", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\bне\s+могу\s+продолжить[^.!?\n]{0,260}[.!?]?", "Сцена продолжается.", txt, flags=re.IGNORECASE)

    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip(" \n\r\t-")


async def _event_actor_label(db: AsyncSession, sess: Session, player: Player) -> str:
    ch = await get_character(db, sess.id, player.id)
    if ch and str(ch.name or "").strip():
        return str(ch.name).strip()
    return str(player.display_name or "").strip() or "Игрок"


def _extract_gm_message_body(event_text: str) -> str:
    txt = str(event_text or "").strip()
    if not txt:
        return ""
    if txt.startswith("[SYSTEM] "):
        txt = txt[9:].strip()
    for prefix in ("🧙 GM:", "🧙 Мастер:"):
        if txt.startswith(prefix):
            return txt[len(prefix):].strip()
    return ""


def _find_latest_gm_text(lines: list[str]) -> str:
    for line in reversed(lines):
        body = _extract_gm_message_body(line)
        if body:
            return body
    return ""


def _common_prefix_len(a: str, b: str) -> int:
    limit = min(len(a), len(b))
    i = 0
    while i < limit and a[i] == b[i]:
        i += 1
    return i


def _looks_truncated_tail(text: str) -> bool:
    tail = str(text or "").rstrip()
    if not tail:
        return False
    if tail.endswith("-"):
        return True
    if tail.endswith(("...", "…")):
        return True
    if tail[-1] not in ".!?\"'»”)]":
        return True
    if tail.count("(") > tail.count(")"):
        return True
    if tail.count("«") > tail.count("»"):
        return True
    return False


async def _load_actor_context(
    db: AsyncSession,
    sess: Session,
) -> tuple[dict[int, tuple[SessionPlayer, Player]], dict[int, Character], dict[uuid.UUID, dict[str, int]]]:
    sps = await list_session_players(db, sess, active_only=True)
    if not sps:
        return {}, {}, {}
    player_ids = [sp.player_id for sp in sps]
    q_players = await db.execute(select(Player).where(Player.id.in_(player_ids)))
    players = q_players.scalars().all()
    players_by_id = {p.id: p for p in players}
    uid_map: dict[int, tuple[SessionPlayer, Player]] = {}
    for sp in sps:
        pl = players_by_id.get(sp.player_id)
        uid = _player_uid(pl)
        if pl and uid is not None and uid > 0:
            uid_map[uid] = (sp, pl)

    q_chars = await db.execute(
        select(Character).where(
            Character.session_id == sess.id,
            Character.player_id.in_(player_ids),
        )
    )
    chars = q_chars.scalars().all()
    chars_by_player = {ch.player_id: ch for ch in chars}
    chars_by_uid: dict[int, Character] = {}
    for uid, (sp, _pl) in uid_map.items():
        ch = chars_by_player.get(sp.player_id)
        if ch:
            chars_by_uid[uid] = ch

    skill_mods_by_char: dict[uuid.UUID, dict[str, int]] = {}
    char_ids = [ch.id for ch in chars]
    if char_ids:
        q_skills = await db.execute(select(Skill).where(Skill.character_id.in_(char_ids)))
        for sk in q_skills.scalars().all():
            skill_mods_by_char.setdefault(sk.character_id, {})[str(sk.skill_key or "").strip().lower()] = _clamp(as_int(sk.rank, 0), 0, 10)
    return uid_map, chars_by_uid, skill_mods_by_char


def _compute_check_mod(
    check: dict[str, Any],
    character: Optional[Character],
    skill_mods_by_char: dict[uuid.UUID, dict[str, int]],
) -> int:
    if not character:
        return 0
    name = _normalize_check_name(check.get("name"))
    kind = _check_kind_for_name(check.get("kind"), name)
    if kind in {"ability", "stat"} or name in CHAR_STAT_KEYS:
        stat_key = STAT_ALIASES.get(name, name)
        if stat_key not in CHAR_STAT_KEYS:
            return 0
        return _ability_mod_from_stats(character.stats, stat_key)

    skill_mods = skill_mods_by_char.get(character.id, {})
    if name in skill_mods:
        return int(skill_mods[name])

    stat_key = SKILL_TO_ABILITY.get(name)
    if not stat_key:
        return 0
    return _ability_mod_from_stats(character.stats, stat_key)


def _roll_check(mode: str) -> tuple[int, Optional[int], int]:
    normalized = _normalize_check_mode(mode)
    if normalized == "advantage":
        r1 = random.randint(1, 20)
        r2 = random.randint(1, 20)
        return r1, r2, max(r1, r2)
    if normalized == "disadvantage":
        r1 = random.randint(1, 20)
        r2 = random.randint(1, 20)
        return r1, r2, min(r1, r2)
    r = random.randint(1, 20)
    return r, None, r


def _build_check_result(check: dict[str, Any], mod: int, roll_a: int, roll_b: Optional[int], roll: int) -> dict[str, Any]:
    dc = max(0, as_int(check.get("dc"), 0))
    total = roll + mod
    result = {
        "actor_uid": as_int(check.get("actor_uid"), 0),
        "kind": _check_kind_for_name(check.get("kind"), _normalize_check_name(check.get("name"))),
        "name": _normalize_check_name(check.get("name")),
        "dc": dc,
        "roll": roll,
        "mod": mod,
        "total": total,
        "success": total >= dc if dc > 0 else True,
        "mode": _normalize_check_mode(check.get("mode")),
    }
    if roll_b is not None:
        result["roll_a"] = roll_a
        result["roll_b"] = roll_b
    if check.get("reason"):
        result["reason"] = str(check.get("reason"))
    return result


def _build_actor_list_for_prompt(uid_map: dict[int, tuple[SessionPlayer, Player]], chars_by_uid: dict[int, Character]) -> str:
    rows: list[str] = []
    for uid, (sp, pl) in sorted(uid_map.items(), key=lambda x: int(x[1][0].join_order or 0)):
        ch = chars_by_uid.get(uid)
        ch_name = str(ch.name).strip() if ch and ch.name else "без персонажа"
        ch_class = ""
        meta = {"gender": "", "race": "", "description": ""}
        if ch:
            ch_class = str(ch.class_skin or "").strip() or str(ch.class_kit or "").strip()
            meta = _character_meta_from_stats(ch.stats)
        parts = [
            f"uid={uid}",
            f"order={sp.join_order}",
            f"player={pl.display_name}",
            f"character={ch_name}",
            f"class={ch_class or '-'}",
            f"gender={meta['gender'] or '-'}",
            f"race={meta['race'] or '-'}",
        ]
        if meta["description"]:
            parts.append(f"description={_short_text(meta['description'], 120)}")
        rows.append("- " + ", ".join(parts))
    return "\n".join(rows) if rows else "- (нет активных игроков)"


def _build_positions_block_for_prompt(
    sess: Session,
    uid_map: dict[int, tuple[SessionPlayer, Player]],
    chars_by_uid: dict[int, Character],
) -> str:
    positions = _get_pc_positions(sess)
    rows: list[str] = []
    for uid, (sp, pl) in sorted(uid_map.items(), key=lambda x: int(x[1][0].join_order or 0)):
        ch = chars_by_uid.get(uid)
        actor_name = (
            str(ch.name).strip()
            if ch and str(ch.name or "").strip()
            else (str(pl.display_name or "").strip() or f"Игрок #{sp.join_order}")
        )
        zone = positions.get(str(sp.player_id), "стартовая локация (вместе)")
        rows.append(f"- {actor_name} (#{uid}): {zone}")
    return "\n".join(rows) if rows else "- (нет активных игроков)"


def _stats_points_used(stats: dict[str, int]) -> int:
    points = 0
    for key in CHAR_STAT_KEYS:
        v = _clamp(as_int(stats.get(key), 50), 0, 100)
        points += int((v - 50) / 5)
    return points


def _resolve_character_stats(class_id: Optional[str], incoming_stats: Any) -> dict[str, int]:
    stats = dict(CHAR_DEFAULT_STATS)
    preset = CLASS_PRESETS.get((class_id or "").lower())
    if preset:
        shifts = preset.get("stats_shift") or {}
        for key in CHAR_STAT_KEYS:
            stats[key] = _clamp(50 + as_int(shifts.get(key), 0), 0, 100)
    if isinstance(incoming_stats, dict):
        for key in CHAR_STAT_KEYS:
            if key in incoming_stats:
                stats[key] = _clamp(as_int(incoming_stats.get(key), 50), 0, 100)
    return stats


def _char_to_payload(ch: Optional[Character]) -> Optional[dict]:
    if not ch:
        return None
    meta = _character_meta_from_stats(ch.stats)
    return {
        "name": ch.name,
        "class_kit": ch.class_kit,
        "class_skin": ch.class_skin,
        "level": int(ch.level or 1),
        "hp": int(ch.hp or 0),
        "hp_max": int(ch.hp_max or 0),
        "sta": int(ch.sta or 0),
        "sta_max": int(ch.sta_max or 0),
        "stats": _normalized_stats(ch.stats),
        "gender": meta["gender"],
        "race": meta["race"],
        "description": meta["description"],
    }


async def get_character(db: AsyncSession, session_id: uuid.UUID, player_id: uuid.UUID) -> Optional[Character]:
    q = await db.execute(
        select(Character)
        .where(
            Character.session_id == session_id,
            Character.player_id == player_id,
        )
        .limit(1)
    )
    return q.scalars().first()


async def create_character(
    db: AsyncSession,
    session_id: uuid.UUID,
    player_id: uuid.UUID,
    name: str,
    class_kit: str = "Adventurer",
    class_skin: str = "Adventurer",
    hp_max: int = 20,
    sta_max: int = 10,
    stats: Optional[dict[str, int]] = None,
) -> Character:
    hp_max = max(1, hp_max)
    sta_max = max(1, sta_max)
    ch = Character(
        session_id=session_id,
        player_id=player_id,
        name=name,
        class_kit=class_kit,
        class_skin=class_skin,
        level=1,
        hp_max=hp_max,
        hp=hp_max,
        sta_max=sta_max,
        sta=sta_max,
        stats=(dict(stats) if isinstance(stats, dict) else dict(CHAR_DEFAULT_STATS)),
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    return ch


async def _upsert_starter_skills(db: AsyncSession, ch: Character, starter: dict[str, Any]) -> None:
    changed = False
    for raw_key, raw_rank in (starter or {}).items():
        key = (str(raw_key or "").strip().lower())[:40]
        if not key:
            continue
        rank = _clamp(as_int(raw_rank, 0), 0, 10)
        q = await db.execute(
            select(Skill).where(
                Skill.character_id == ch.id,
                Skill.skill_key == key,
            )
        )
        sk = q.scalar_one_or_none()
        if sk:
            if int(sk.rank or 0) != rank:
                sk.rank = rank
                changed = True
            continue
        db.add(Skill(character_id=ch.id, skill_key=key, rank=rank, xp=0))
        changed = True
    if changed:
        await db.commit()


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


def _get_last_seen_map(sess: Session) -> dict[str, str]:
    raw = settings_get(sess, "last_seen", {}) or {}
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if k is None or v is None:
            continue
        out[str(k)] = str(v)
    return out


def _get_pc_positions(sess: Session) -> dict[str, str]:
    raw = settings_get(sess, "pc_positions", {}) or {}
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if k is None or v is None:
            continue
        pid = str(k).strip()
        zone = str(v).strip()
        if pid and zone:
            out[pid] = zone[:80]
    return out


def _set_pc_zone(sess: Session, player_id: uuid.UUID, zone: str) -> None:
    z = str(zone or "").strip()
    if not z:
        return
    m = dict(_get_pc_positions(sess))
    m[str(player_id)] = z[:80]
    settings_set(sess, "pc_positions", m)


def _initialize_pc_positions(sess: Session, player_ids: list[uuid.UUID], default_zone: str) -> None:
    zone = str(default_zone or "").strip() or "стартовая локация (вместе)"
    m: dict[str, str] = {}
    for pid in player_ids:
        m[str(pid)] = zone
    settings_set(sess, "pc_positions", m)


def _touch_last_seen(sess: Session, player_id: uuid.UUID) -> None:
    m = dict(_get_last_seen_map(sess))
    m[str(player_id)] = utcnow().isoformat()
    settings_set(sess, "last_seen", m)


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

    pc_positions = dict(_get_pc_positions(sess))
    if pid in pc_positions:
        pc_positions.pop(pid, None)
        settings_set(sess, "pc_positions", pc_positions)


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


def _get_phase(sess: Session) -> str:
    phase = str(settings_get(sess, "phase", "turns") or "turns").strip().lower()
    if phase not in {"lore_pending", "collecting_actions", "gm_pending", "turns"}:
        return "turns"
    return phase


def _set_phase(sess: Session, phase: str) -> None:
    settings_set(sess, "phase", str(phase).strip().lower())


def _new_action_id() -> str:
    return uuid.uuid4().hex


def _get_current_action_id(sess: Session) -> Optional[str]:
    raw = str(settings_get(sess, "current_action_id", "") or "").strip()
    return raw or None


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


def _should_use_round_mode(sess: Session, sps_active: list[SessionPlayer]) -> bool:
    return len(_ready_active_players(sess, sps_active)) >= 2


def _get_free_round(sess: Session) -> int:
    return max(1, as_int(settings_get(sess, "free_round", 1), 1))


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
    all_sps = await list_session_players(db, sess, active_only=False)
    kicked = _get_kicked(sess)
    all_sps = [sp for sp in all_sps if str(sp.player_id) not in kicked]
    active_sps = [sp for sp in all_sps if sp.is_active is not False]
    player_ids = [sp.player_id for sp in all_sps]

    players_by_id: dict = {}
    if player_ids:
        q = await db.execute(select(Player).where(Player.id.in_(player_ids)))
        players_by_id = {p.id: p for p in q.scalars().all()}
    chars_by_player_id: dict[uuid.UUID, Character] = {}
    if player_ids:
        q_chars = await db.execute(
            select(Character).where(
                Character.session_id == sess.id,
                Character.player_id.in_(player_ids),
            )
        )
        for ch in q_chars.scalars().all():
            chars_by_player_id[ch.player_id] = ch

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
    for sp in active_sps:
        if sp.player_id == sess.current_player_id:
            cur_order = sp.join_order
            break

    # UID текущего игрока (нужно для UI, независимо от паузы/таймера)
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
            "round": (as_int(settings_get(sess, "round", 0), 0) or 1) if _initiative_fixed(sess) else None,
        },
        "players": [
            {
                "id": str(sp.player_id),
                "uid": _player_uid(players_by_id.get(sp.player_id)),
                "name": (players_by_id.get(sp.player_id).display_name if players_by_id.get(sp.player_id) else str(sp.player_id)),
                "order": int(sp.join_order or 0),
                "is_admin": bool(sp.is_admin),
                "is_current": (sp.is_active is not False) and sp.player_id == sess.current_player_id,
                "is_active": sp.is_active is not False,
                "is_ready": bool(ready_map.get(str(sp.player_id), False)) if sp.is_active is not False else False,
                "initiative": init_map.get(str(sp.player_id)) if sp.is_active is not False else None,
                "last_seen": last_seen_map.get(str(sp.player_id)),
                "char": _char_to_payload(chars_by_player_id.get(sp.player_id)),
                "has_character": chars_by_player_id.get(sp.player_id) is not None,
            }
            for sp in all_sps
        ],
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
        },
    }


async def broadcast_state(session_id: str) -> None:
    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            return
        state = await build_state(db, sess)
    await manager.broadcast_json(session_id, state)


def _build_turn_draft_prompt(
    session_title: str,
    context_events: list[str],
    actor_uid: Optional[int],
    actors_block: str,
    positions_block: str,
) -> str:
    context = "\n".join(f"- {line}" for line in context_events[-50:]) or "- (контекст пуст)"
    title = (session_title or "Кампания").strip()
    actor_hint = str(actor_uid) if actor_uid is not None else "unknown"
    return (
        "Ты Мастер настольной RPG в стиле D&D. Отвечай только по-русски.\n"
        "Сначала напиши черновик развития сцены (2-6 предложений).\n"
        "Инвентарь персонажей (inventory) — это истина сервера.\n"
        "Нельзя подтверждать использование предмета, которого нет у персонажа в inventory.\n"
        "Если игрок пишет 'достаю/зажигаю факел', а факела нет, прямо скажи, что факела нет, и предложи варианты: поискать, попросить у другого, импровизировать.\n"
        "Если игрок ищет/обыскивает, назначай @@CHECK (например perception/investigation).\n"
        "Если нужна проверка, НЕ проси игрока кидать вручную. В конце добавь машинные строки:\n"
        "@@CHECK {\"actor_uid\":<uid>,\"kind\":\"skill|ability\",\"name\":\"perception|wis|...\",\"dc\":15,\"mode\":\"normal|advantage|disadvantage\",\"reason\":\"...\"}\n"
        "После успешного поиска/получения предмета выдай его ТОЛЬКО машинной строкой:\n"
        "@@INV_ADD(uid=<int>, name=\"<item>\", qty=<int optional>, tags=[... optional], notes=\"...\" optional)\n"
        "Также можно использовать:\n"
        "@@INV_REMOVE(uid=<int>, name=\"<item>\", qty=<int optional>)\n"
        "@@INV_TRANSFER(from_uid=<int>, to_uid=<int>, name=\"<item>\", qty=<int optional>)\n"
        "Можно несколько @@CHECK, каждая в отдельной строке.\n"
        "Можно несколько @@INV_* строк, каждая в отдельной строке.\n"
        "В тексте для игрока не оставляй незакрытых требований формата 'Проверка ... DC ...'.\n"
        "Не пиши @@CHECK_RESULT.\n"
        "Не отвечай отказом. Если тема спорная — смягчай до приключенческого уровня.\n\n"
        "ПРАВИЛА ПО ЗОНАМ (строго):\n"
        "1) НЕЛЬЗЯ телепортировать персонажей между зонами без явного описания перехода.\n"
        "2) Персонаж НЕ знает и НЕ слышит, что было в другой зоне, пока не подошёл/не вошёл/ему не сообщили.\n"
        "3) Если нужно, чтобы персонаж оказался рядом и услышал разговор — явно опиши подход/вход и что это заняло время.\n"
        "4) Не пиши мета-подсказки формата 'X может...': либо описывай действия, либо задавай прямой вопрос персонажу.\n\n"
        f"Название сессии: {title}\n"
        f"Предпочтительный actor_uid для текущего действия: {actor_hint}\n"
        f"Игроки:\n{actors_block}\n\n"
        f"Позиции персонажей (важно):\n{positions_block}\n\n"
        f"Контекст (последние события):\n{context}"
    )


def _build_round_draft_prompt(
    session_title: str,
    lore_text: str,
    recent_events: list[str],
    player_actions: list[str],
    master_notes: str,
    difficulty: str,
    actors_block: str,
    positions_block: str,
) -> str:
    title = (session_title or "Кампания").strip()
    lore = (lore_text or "").strip()
    notes = (master_notes or "").strip()
    context = "\n".join(f"- {line}" for line in recent_events[-40:]) or "- (контекст пуст)"
    acts = "\n".join(f"- {a}" for a in player_actions if a.strip()) or "- (нет действий)"
    diff = {"easy": "лёгкая", "medium": "средняя", "hard": "сложная"}.get(difficulty, "средняя")
    return (
        "Ты Мастер настольной RPG в стиле D&D. Отвечай только по-русски.\n"
        f"Сложность сцены: {diff}.\n"
        "Инвентарь персонажей (inventory) — это истина сервера.\n"
        "Нельзя подтверждать использование предмета, которого нет у персонажа в inventory.\n"
        "Если игрок пишет 'достаю/зажигаю факел', а факела нет, прямо скажи, что факела нет, и предложи варианты: поискать, попросить у другого, импровизировать.\n"
        "Обработай действия КАЖДОГО игрока. Не игнорируй второе/третье действие.\n"
        "Если игроки действуют рядом (например сундук/факел), можно объединить в один связный эпизод.\n"
        "Если игроки далеко друг от друга, опиши обе ветки кратко и параллельно, но за 1-2 раунда создай событие, чтобы партия снова собралась.\n"
        "Запрещены мета-комментарии: 'проанализируем', 'в черновике', 'я модель/ИИ' и подобные.\n"
        "Запрещены отказы и извинения ('я не могу', 'извиняюсь', 'не могу продолжить'). Смягчай и продолжай сцену.\n"
        "Если нужна проверка, не проси бросок в тексте: выдай в конце строки @@CHECK в JSON-формате.\n"
        "Формат строки:\n"
        "@@CHECK {\"actor_uid\":<uid>,\"kind\":\"skill|ability\",\"name\":\"...\",\"dc\":15,\"mode\":\"normal|advantage|disadvantage\",\"reason\":\"...\"}\n"
        "Если после успеха проверки персонаж получает предмет, выдай это ТОЛЬКО машинной строкой:\n"
        "@@INV_ADD(uid=<int>, name=\"<item>\", qty=<int optional>, tags=[... optional], notes=\"...\" optional)\n"
        "Разрешены также:\n"
        "@@INV_REMOVE(uid=<int>, name=\"<item>\", qty=<int optional>)\n"
        "@@INV_TRANSFER(from_uid=<int>, to_uid=<int>, name=\"<item>\", qty=<int optional>)\n"
        "Разрешено несколько @@CHECK. В тексте не оставляй 'Проверка ... DC ...'.\n"
        "Разрешено несколько @@INV_*.\n"
        "Не пиши @@CHECK_RESULT.\n"
        "Не отвечай отказом. Спорные темы смягчай до приключенческого уровня.\n\n"
        "ПРАВИЛА ПО ЗОНАМ (строго):\n"
        "1) НЕЛЬЗЯ телепортировать персонажей между зонами без явного описания перехода.\n"
        "2) Персонаж НЕ знает и НЕ слышит, что было в другой зоне, пока не подошёл/не вошёл/ему не сообщили.\n"
        "3) Если нужно, чтобы персонаж оказался рядом и услышал разговор — явно опиши подход/вход и что это заняло время.\n"
        "4) Не пиши мета-подсказки формата 'X может...': либо описывай действия, либо задавай прямой вопрос персонажу.\n\n"
        f"Название кампании: {title}\n"
        f"ЛОР:\n{lore}\n\n"
        f"Недавние события:\n{context}\n\n"
        f"Игроки:\n{actors_block}\n\n"
        f"Позиции персонажей (важно):\n{positions_block}\n\n"
        f"Действия игроков в этом раунде:\n{acts}\n\n"
        + (f"Заметки мастеру: {notes}\n\n" if notes else "")
        + "Черновик должен закончиться вопросом к партии: что вы делаете дальше?"
    )


def _build_finalize_prompt(draft_text: str, check_results: list[dict[str, Any]]) -> str:
    results_lines = [f"@@CHECK_RESULT {json.dumps(x, ensure_ascii=False)}" for x in check_results]
    results_block = "\n".join(results_lines) if results_lines else "(автопроверок не было)"
    return (
        "Ты Мастер настольной RPG в стиле D&D. Отвечай только по-русски.\n"
        "Ниже черновик сцены и результаты автоматических проверок.\n"
        "Сделай финальный ответ игрокам: учитывай успех/провал, продвигай сцену, добавь последствия.\n"
        "Инвентарь персонажей (inventory) — это истина сервера.\n"
        "Нельзя подтверждать использование предмета, которого нет в inventory персонажа.\n"
        "Если игрок пытается использовать отсутствующий предмет (например факел), скажи, что предмета нет, и предложи варианты: поискать, попросить у другого, импровизировать.\n"
        "Если после успеха проверки или события выдаёшь предмет/забираешь/переносишь, делай это ТОЛЬКО через машинные строки @@INV_*.\n"
        "Форматы:\n"
        "@@INV_ADD(uid=<int>, name=\"<item>\", qty=<int optional>, tags=[... optional], notes=\"...\" optional)\n"
        "@@INV_REMOVE(uid=<int>, name=\"<item>\", qty=<int optional>)\n"
        "@@INV_TRANSFER(from_uid=<int>, to_uid=<int>, name=\"<item>\", qty=<int optional>)\n"
        "Эти строки для сервера: они будут скрыты от игроков.\n"
        "Это финальный ответ игрокам.\n"
        "НЕ упоминай слова черновик/драфт/анализ/проверка/проверку в мета-смысле и не ссылайся на 'черновик'.\n"
        "Не добавляй мета-комментарии ('проанализируем', 'как модель/ИИ', 'в черновике').\n"
        "Не пиши извинения и отказы ('извиняюсь', 'я не могу', 'не могу продолжить'). Вместо этого продолжай сцену мягко.\n"
        "ВАЖНО: в финальном ответе не должно быть @@CHECK и @@CHECK_RESULT.\n"
        "Не проси игроков бросать кости вручную.\n\n"
        f"Черновик:\n{draft_text}\n\n"
        f"Результаты проверок:\n{results_block}"
    )


async def _run_gm_two_pass(
    db: AsyncSession,
    sess: Session,
    *,
    draft_prompt: str,
    default_actor_uid: Optional[int],
    previous_gm_text: str = "",
) -> tuple[str, dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    uid_map, chars_by_uid, skill_mods_by_char = await _load_actor_context(db, sess)

    draft_resp = await generate_from_prompt(
        prompt=draft_prompt,
        timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
    )
    draft_text_raw = str(draft_resp.get("text") or "").strip()
    draft_text, checks, has_human_check = _extract_checks_from_draft(draft_text_raw, default_actor_uid)

    reparsed = False
    forced_reprompt = False
    cleaned_human_check = False
    if not checks and has_human_check:
        inferred = _checks_from_human_text(draft_text, default_actor_uid)
        if inferred:
            checks = inferred
            reparsed = True
        else:
            forced_reprompt = True
            force_prompt = (
                "Перепиши этот же ответ как черновик мастера.\n"
                "Если нужна проверка, добавь @@CHECK JSON-строки в конце. Не пиши текст 'Проверка ... DC ...'.\n\n"
                f"Черновик для исправления:\n{draft_text_raw}"
            )
            forced_resp = await generate_from_prompt(
                prompt=force_prompt,
                timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
            )
            draft_resp = forced_resp
            draft_text_raw = str(forced_resp.get("text") or "").strip()
            draft_text, checks, _has_human_check_2 = _extract_checks_from_draft(draft_text_raw, default_actor_uid)

    normalized_checks: list[dict[str, Any]] = []
    for c in checks:
        if not isinstance(c, dict):
            continue
        actor_uid = as_int(c.get("actor_uid"), 0)
        if actor_uid <= 0 and default_actor_uid is not None:
            actor_uid = default_actor_uid
        if actor_uid is None or actor_uid <= 0:
            continue
        name = _normalize_check_name(c.get("name"))
        if not name:
            continue
        normalized_checks.append(
            {
                "actor_uid": actor_uid,
                "kind": _check_kind_for_name(c.get("kind"), name),
                "name": name,
                "dc": max(0, as_int(c.get("dc"), 0)),
                "mode": _normalize_check_mode(c.get("mode")),
                "reason": str(c.get("reason") or "").strip(),
            }
        )

    check_results: list[dict[str, Any]] = []
    for check in normalized_checks:
        actor_uid = as_int(check.get("actor_uid"), 0)
        character = chars_by_uid.get(actor_uid)
        mod = _compute_check_mod(check, character, skill_mods_by_char)
        roll_a, roll_b, roll = _roll_check(str(check.get("mode") or "normal"))
        result = _build_check_result(check, mod, roll_a, roll_b, roll)
        check_results.append(result)

    final_prompt = _build_finalize_prompt(draft_text, check_results)
    final_resp = await generate_from_prompt(
        prompt=final_prompt,
        timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
    )
    final_text = _sanitize_gm_output(_strip_machine_lines(str(final_resp.get("text") or "").strip()))
    if not final_text:
        fallback_prompt = (
            "Дай финальный ответ мастера игрокам по этому черновику.\n"
            "Не используй служебные строки, не упоминай что это черновик.\n\n"
            f"Черновик:\n{draft_text}"
        )
        fallback_resp = await generate_from_prompt(
            prompt=fallback_prompt,
            timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
        )
        final_text = _sanitize_gm_output(_strip_machine_lines(str(fallback_resp.get("text") or "").strip()))
        if not final_text:
            final_text = "Мастер на миг задумывается и просит описать следующее действие точнее."

    initial_final_len = len(final_text)
    initial_finish_reason = str(final_resp.get("finish_reason") or "").strip().lower()
    continuation_len = 0
    continuation_attempts = 0
    if final_text and (initial_finish_reason == "length" or _looks_truncated_tail(final_text)):
        for _ in range(2):
            if not final_text:
                break
            continuation_attempts += 1
            continuation_prompt = (
                "Продолжи ровно с места обрыва. Не повторяй уже сказанное. Начни с продолжения последней фразы.\n\n"
                f"Последние символы текущего ответа:\n{final_text[-320:]}"
            )
            continuation_resp = await generate_from_prompt(
                prompt=continuation_prompt,
                timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
            )
            continuation_text = _sanitize_gm_output(_strip_machine_lines(str(continuation_resp.get("text") or "").strip()))
            if not continuation_text:
                break
            if final_text[-1].isalnum() and continuation_text[0].isalnum():
                final_text += " "
            final_text += continuation_text
            continuation_len += len(continuation_text)
            if str(continuation_resp.get("finish_reason") or "").strip().lower() != "length" and not _looks_truncated_tail(final_text):
                break

    anti_repeat_prefix_len = 0
    anti_repeat_strategy = "none"
    prev_gm = str(previous_gm_text or "").strip()
    if prev_gm and final_text:
        anti_repeat_prefix_len = _common_prefix_len(prev_gm, final_text)
        if anti_repeat_prefix_len > 200:
            trimmed = final_text[anti_repeat_prefix_len:].lstrip(" \n\r\t-—:,.!?;")
            if len(trimmed) >= 80:
                final_text = trimmed
                anti_repeat_strategy = "trim_prefix"
            else:
                anti_repeat_prompt = (
                    "Не повторяй предыдущий текст, продолжай сцену.\n"
                    "Дай только новое продолжение, без пересказа.\n\n"
                    f"Предыдущий текст мастера:\n{prev_gm}\n\n"
                    f"Текущий вариант:\n{final_text}"
                )
                anti_repeat_resp = await generate_from_prompt(
                    prompt=anti_repeat_prompt,
                    timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
                )
                anti_repeat_text = _sanitize_gm_output(_strip_machine_lines(str(anti_repeat_resp.get("text") or "").strip()))
                if anti_repeat_text:
                    final_text = anti_repeat_text
                    anti_repeat_strategy = "reprompt"

    if TEXTUAL_CHECK_RE.search(final_text):
        cleaned_human_check = True
        cleanup_prompt = (
            "Перепиши текст мастера так, чтобы не было просьб к игроку бросать проверку/DC.\n"
            "Сцена должна продвинуться вперёд сама, с понятными последствиями.\n\n"
            f"Текст:\n{final_text}"
        )
        cleanup_resp = await generate_from_prompt(
            prompt=cleanup_prompt,
            timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
        )
        cleaned = _sanitize_gm_output(_strip_machine_lines(str(cleanup_resp.get("text") or "").strip()))
        if cleaned:
            final_text = cleaned
    final_text = _sanitize_gm_output(final_text)
    if not final_text:
        final_text = "Сцена продолжается: опишите следующее действие."

    logger.info(
        "gm two-pass completed",
        extra={
            "action": {
                "phase": _get_phase(sess),
                "draft_preview": _trim_for_log(draft_text_raw),
                "checks": normalized_checks,
                "check_results": check_results,
                "fallback_textual_check_parse": reparsed,
                "fallback_forced_reprompt": forced_reprompt,
                "fallback_cleanup_human_check_text": cleaned_human_check,
                "llm_draft_finish_reason": draft_resp.get("finish_reason"),
                "llm_draft_usage": draft_resp.get("usage"),
                "llm_final_finish_reason": final_resp.get("finish_reason"),
                "llm_final_usage": final_resp.get("usage"),
                "final_initial_len": initial_final_len,
                "final_initial_finish_reason": initial_finish_reason,
                "final_continuation_attempts": continuation_attempts,
                "final_continuation_len": continuation_len,
                "final_len": len(final_text),
                "anti_repeat_prefix_len": anti_repeat_prefix_len,
                "anti_repeat_strategy": anti_repeat_strategy,
            }
        },
    )
    return final_text, draft_resp, final_resp, normalized_checks, check_results


async def _auto_gm_reply_task(session_id: str, expected_action_id: str) -> None:
    tok_rid = request_id_var.set(_new_request_id())
    tok_sid = session_id_var.set(session_id)
    try:
        lock = _get_session_gm_lock(session_id)
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
                context_events: list[str] = []
                for ev in reversed(events_desc):
                    msg = str(ev.message_text or "").strip()
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
                draft_prompt = _build_turn_draft_prompt(
                    session_title=story_title,
                    context_events=context_events,
                    actor_uid=cur_uid,
                    actors_block=actors_block,
                    positions_block=positions_block,
                )
                gm_text, _draft_meta, _final_meta, _checks, _check_results = await _run_gm_two_pass(
                    db,
                    sess,
                    draft_prompt=draft_prompt,
                    default_actor_uid=cur_uid,
                    previous_gm_text=previous_gm_text,
                )

                await db.refresh(sess)
                if _get_current_action_id(sess) != expected_action_id:
                    logger.info("gm final dropped due to action mismatch", extra={"action": {"expected_action_id": expected_action_id}})
                    return

                gm_text = gm_text.strip()
                gm_text_visible, inv_commands = _extract_inventory_machine_commands(gm_text)
                await _apply_inventory_machine_commands(db, sess, inv_commands)
                gm_text_visible = gm_text_visible.strip()
                if gm_text_visible and not _looks_like_refusal(gm_text_visible):
                    await add_system_event(db, sess, f"🧙 GM: {gm_text_visible}")
                elif not inv_commands:
                    await add_system_event(db, sess, "🧙 GM: (модель отказала. Переформулируй действие проще, без жести и откровенных деталей.)")

                nxt = await advance_turn(db, sess)
                if nxt:
                    sess.current_player_id = nxt.player_id
                    sess.turn_started_at = utcnow()
                    await add_system_event(db, sess, f"Следующий ход: игрок #{nxt.join_order}.")
                _set_phase(sess, "turns")
                _clear_current_action_id(sess)
                await db.commit()

        await broadcast_state(session_id)
    except Exception:
        logger.exception("auto gm reply task failed")
    finally:
        request_id_var.reset(tok_rid)
        session_id_var.reset(tok_sid)


async def _auto_lore_task(session_id: str) -> None:
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


async def _auto_round_task(session_id: str, expected_action_id: str) -> None:
    tok_rid = request_id_var.set(_new_request_id())
    tok_sid = session_id_var.set(session_id)
    try:
        lock = _get_session_gm_lock(session_id)
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
                    await broadcast_state(session_id)
                    return

                sps = await list_session_players(db, sess, active_only=True)
                players_by_id: dict[uuid.UUID, Player] = {}
                if sps:
                    q_players = await db.execute(select(Player).where(Player.id.in_([sp.player_id for sp in sps])))
                    players_by_id = {p.id: p for p in q_players.scalars().all()}

                player_actions: list[str] = []
                chars_by_player_id: dict[uuid.UUID, Character] = {}
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
                gm_text, _draft_meta, _final_meta, _checks, _check_results = await _run_gm_two_pass(
                    db,
                    sess,
                    draft_prompt=draft_prompt,
                    default_actor_uid=None,
                    previous_gm_text=previous_gm_text,
                )

                await db.refresh(sess)
                if _get_current_action_id(sess) != expected_action_id:
                    logger.info("round final dropped due to action mismatch", extra={"action": {"expected_action_id": expected_action_id}})
                    return

                gm_text = gm_text.strip()
                gm_text_visible, inv_commands = _extract_inventory_machine_commands(gm_text)
                await _apply_inventory_machine_commands(db, sess, inv_commands)
                gm_text_visible = gm_text_visible.strip()
                if gm_text_visible:
                    await add_system_event(db, sess, f"🧙 Мастер: {gm_text_visible}")

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
                        await add_system_event(db, sess, f"Следующий ход: игрок #{first.join_order}.")
                    await db.commit()

        await broadcast_state(session_id)
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


# -------------------------
# Routes
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/c/{session_id}", response_class=HTMLResponse)
async def character_create_page(request: Request, session_id: str):
    return templates.TemplateResponse("character_create.html", {"request": request, "session_id": session_id})


@app.get("/story/{session_id}", response_class=HTMLResponse)
async def story_setup_page(request: Request, session_id: str, uid: Optional[int] = None):
    if not uid or uid <= 0:
        return RedirectResponse(url=f"/s/{session_id}", status_code=303)

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_player_by_uid(db, uid)
        if not player:
            return RedirectResponse(url=f"/s/{session_id}", status_code=303)

        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp or not sp.is_admin:
            return RedirectResponse(url=f"/s/{session_id}", status_code=303)

    return templates.TemplateResponse(
        "story_setup.html",
        {"request": request, "session_id": session_id, "uid": uid},
    )


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
    resp = templates.TemplateResponse("session.html", {"request": request, "session_id": session_id})
    # чтобы не ловили старый session.html (кеш ломает cid/x-client-id)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp



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
                _set_ready(sess, player.id, False)
                _touch_last_seen(sess, player.id)
                await db.commit()
                await add_system_event(db, sess, f"Игрок вернулся: {player.display_name} (#{sp.join_order}).")
                await broadcast_state(session_id)
                return JSONResponse({"ok": True})
            _touch_last_seen(sess, player.id)
            await db.commit()
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
        _set_ready(sess, player.id, False)
        _touch_last_seen(sess, player.id)
        await db.commit()

        await add_system_event(db, sess, f"Игрок присоединился: {player.display_name} (#{join_order}).")

    await broadcast_state(session_id)
    return JSONResponse({"ok": True})


@app.get("/api/classes")
async def api_classes():
    items = []
    for class_id, preset in CLASS_PRESETS.items():
        stats = _resolve_character_stats(class_id, None)
        items.append(
            {
                "id": class_id,
                "name": preset.get("display_name") or class_id,
                "hp_max": max(1, as_int(preset.get("hp_max"), 20)),
                "sta_max": max(1, as_int(preset.get("sta_max"), 10)),
                "stats": stats,
            }
        )
    return JSONResponse({"classes": items})


@app.get("/api/story/get")
async def api_story_get(session_id: str, uid: int):
    if uid <= 0:
        raise HTTPException(status_code=400, detail="Bad uid")

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_player_by_uid(db, uid)
        if not player:
            raise HTTPException(status_code=403, detail="Admin access required")

        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp or not sp.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        raw_story = settings_get(sess, "story", {}) or {}
        config = _normalize_story_config(sess, raw_story)
        configured = bool(isinstance(raw_story, dict) and raw_story.get("story_configured"))
        if configured:
            config["story_configured"] = True
            config["configured_at"] = str(raw_story.get("configured_at") or "")
        lore_text = str(settings_get(sess, "lore_text", "") or "")
        lore_generated = bool(settings_get(sess, "lore_generated", False))

    return JSONResponse({"ok": True, "config": config, "lore_text": lore_text, "lore_generated": lore_generated})


@app.post("/api/story/save")
async def api_story_save(payload: dict):
    session_id = str(payload.get("session_id") or "").strip()
    uid = as_int(payload.get("uid"), 0)
    config_raw = payload.get("config")

    if uid <= 0:
        raise HTTPException(status_code=400, detail="Bad uid")
    if not isinstance(config_raw, dict):
        raise HTTPException(status_code=400, detail="Bad config payload")

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_player_by_uid(db, uid)
        if not player:
            raise HTTPException(status_code=403, detail="Admin access required")

        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp or not sp.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        config = _normalize_story_config(sess, config_raw)
        config["story_configured"] = True
        config["configured_at"] = datetime.now(timezone.utc).isoformat()
        settings_set(sess, "story", config)
        if "lore_text" in config_raw:
            lore_text = str(config_raw.get("lore_text") or "").strip()
            if lore_text and not _looks_like_refusal(lore_text):
                settings_set(sess, "lore_text", lore_text)
                settings_set(sess, "lore_generated", True)
                settings_set(sess, "lore_posted", False)
            else:
                # очистка (или защита от сохранения отказа)
                settings_set(sess, "lore_text", "")
                settings_set(sess, "lore_generated", False)
                settings_set(sess, "lore_posted", False)
        await db.commit()

    return JSONResponse({"ok": True})


@app.post("/api/story/lore/generate")
async def api_story_lore_generate(payload: dict):
    session_id = str(payload.get("session_id") or "").strip()
    uid = as_int(payload.get("uid"), 0)
    force = bool(payload.get("force", False))

    if uid <= 0:
        raise HTTPException(status_code=400, detail="Bad uid")

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_player_by_uid(db, uid)
        if not player:
            raise HTTPException(status_code=403, detail="Admin access required")

        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp or not sp.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        existing_lore = str(settings_get(sess, "lore_text", "") or "").strip()
        if existing_lore and not force:
            return JSONResponse({"ok": True, "lore_text": existing_lore})

        story = settings_get(sess, "story", {}) or {}
        if not isinstance(story, dict):
            story = {}
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
            raise HTTPException(status_code=400, detail="Lore generation refused...")
        if _looks_like_refusal(lore_text):
            raise HTTPException(status_code=400, detail="Lore generation refused...")

        settings_set(sess, "lore_text", lore_text)
        settings_set(sess, "lore_generated", True)
        settings_set(sess, "lore_generated_at", datetime.now(timezone.utc).isoformat())
        settings_set(sess, "lore_posted", False)
        await db.commit()

    return JSONResponse({"ok": True, "lore_text": lore_text})


@app.post("/api/character/create")
async def api_character_create(payload: dict):
    session_id = str(payload.get("session_id") or "").strip()
    uid = as_int(payload.get("uid"), 0)
    char_name = str(payload.get("name") or "").strip()
    class_id = str(payload.get("class_id") or "").strip().lower()
    custom_class = str(payload.get("custom_class") or "").strip()
    stats_in = payload.get("stats")
    meta_gender = str(payload.get("gender") or "").strip()[:40]
    meta_race = str(payload.get("race") or "").strip()[:60]
    meta_description = str(payload.get("description") or "").strip()[:1000]

    if uid <= 0:
        raise HTTPException(status_code=400, detail="Bad uid")
    if not char_name:
        raise HTTPException(status_code=400, detail="Character name is required")

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_or_create_player_web(db, uid, "")
        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp:
            raise HTTPException(status_code=403, detail="Join session first")
        if sp.is_active is False:
            raise HTTPException(status_code=403, detail="You are offline in this session")

        existing = await get_character(db, sess.id, player.id)
        if existing:
            return JSONResponse({"detail": "Character already exists"}, status_code=409)

        selected_preset = CLASS_PRESETS.get(class_id) if class_id else None
        class_name = custom_class or (selected_preset.get("display_name") if selected_preset else "Adventurer")
        stats = _resolve_character_stats(class_id if selected_preset else None, stats_in)
        stats = _put_character_meta_into_stats(
            stats,
            gender=meta_gender,
            race=meta_race,
            description=meta_description,
        )
        if _stats_points_used(stats) > 20:
            raise HTTPException(status_code=400, detail="Points budget exceeded (max 20)")

        hp_max = max(1, as_int((selected_preset or {}).get("hp_max"), 20))
        sta_max = max(1, as_int((selected_preset or {}).get("sta_max"), 10))
        ch = await create_character(
            db,
            sess.id,
            player.id,
            name=char_name[:80],
            class_kit=class_name[:40],
            class_skin=class_name[:60],
            hp_max=hp_max,
            sta_max=sta_max,
            stats=stats,
        )
        await _upsert_starter_skills(db, ch, (selected_preset or {}).get("starter_skills") or {})
        await add_system_event(db, sess, f"Character ready: {ch.name} for player #{sp.join_order}.")
        next_url = f"/s/{session_id}"
        if sp.is_admin and not _story_is_configured(sess):
            next_url = f"/story/{session_id}?uid={uid}"
        return JSONResponse({"ok": True, "character": _char_to_payload(ch), "next_url": next_url})


@app.post("/api/character/update_stats")
async def api_character_update_stats(payload: dict):
    session_id = str(payload.get("session_id") or "").strip()
    uid = as_int(payload.get("uid"), 0)
    stats_in = payload.get("stats")

    if uid <= 0:
        raise HTTPException(status_code=400, detail="Bad uid")
    if not isinstance(stats_in, dict):
        raise HTTPException(status_code=400, detail="Bad stats payload")

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_or_create_player_web(db, uid, "")
        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp:
            raise HTTPException(status_code=403, detail="Join session first")
        if sp.is_active is False:
            raise HTTPException(status_code=403, detail="You are offline in this session")

        admin = await is_admin(db, sess, player)
        if sess.is_active and not admin:
            raise HTTPException(status_code=403, detail="Only admin can change stats after start")

        ch = await get_character(db, sess.id, player.id)
        if not ch:
            raise HTTPException(status_code=404, detail="No character. Use: char create ...")

        stats = _resolve_character_stats(None, stats_in)
        if _stats_points_used(stats) > 20:
            raise HTTPException(status_code=400, detail="Points budget exceeded (max 20)")

        ch.stats = stats
        await db.commit()
        await add_system_event(db, sess, f"[STAT] player #{sp.join_order} updated character stats.")
        return JSONResponse({"ok": True, "character": _char_to_payload(ch)})


@app.get("/api/character/me")
async def api_character_me(session_id: str, uid: int):
    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        player = await get_or_create_player_web(db, as_int(uid, 0), "")
        ch = await get_character(db, sess.id, player.id)
        return JSONResponse({"ok": True, "has_character": ch is not None, "character": _char_to_payload(ch)})


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
    async def ws_error(message: str, *, fatal: bool = False, request_id: Optional[str] = None) -> None:
        rid = request_id
        if rid is None:
            try:
                rid = request_id_var.get()
            except LookupError:
                rid = None
        payload = {"type": "error", "message": message, "fatal": fatal, "request_id": rid}
        await ws.send_text(json.dumps(payload, ensure_ascii=False))

    uid_raw = ws.query_params.get("uid")
    if not uid_raw or not uid_raw.isdigit():
        rid = _new_request_id()
        await ws.accept()
        await ws_error("No uid", fatal=True, request_id=rid)
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
            msg_request_id = data.get("request_id") if isinstance(data, dict) else None

            async with AsyncSessionLocal() as db:
                sess = await get_session(db, session_id)
                if not sess:
                    await ws_error("Session not found", request_id=msg_request_id)
                    continue

                # don't overwrite name here; join sets it
                player = await get_or_create_player_web(db, uid, "")

                # kicked check (live)
                if str(player.id) in _get_kicked(sess):
                    await ws_error("You were kicked from this session", fatal=True)
                    await ws.close()
                    return

                q = await db.execute(
                    select(SessionPlayer).where(
                        SessionPlayer.session_id == sess.id,
                        SessionPlayer.player_id == player.id,
                    )
                )
                sp = q.scalar_one_or_none()
                if not sp:
                    await ws_error("Not joined/active. Refresh page.", request_id=msg_request_id)
                    continue
                if sp.is_active is False:
                    if action in ("leave", "quit", "exit"):
                        await ws.close()
                        return
                    await ws_error("You are offline in this session", request_id=msg_request_id)
                    continue

                async def _process_leave_and_broadcast() -> None:
                    if sess.current_player_id == player.id and bool(sess.is_active):
                        await advance_turn(db, sess)

                    sp.is_active = False
                    _remove_player_from_session_settings(sess, player.id)

                    active_left = await list_session_players(db, sess, active_only=True)
                    if not active_left:
                        sess.current_player_id = None
                        sess.turn_started_at = None
                        _clear_paused_remaining(sess)

                    await db.commit()
                    await add_system_event(db, sess, f"Игрок {player.display_name} вышел из игры.")
                    await broadcast_state(session_id)

                if action in ("leave", "quit", "exit"):
                    await _process_leave_and_broadcast()
                    await ws.close()
                    return

                _touch_last_seen(sess, player.id)
                if action == "ping":
                    await db.commit()
                    continue
                await db.commit()

                # ready/unready actions (do not require game started)
                if action in ("ready", "unready"):
                    if action == "ready":
                        my_char = await get_character(db, sess.id, player.id)
                        if not my_char:
                            await ws_error("Create character first", request_id=msg_request_id)
                            continue
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
                        await ws_error("Only admin can start")
                        continue
                    if sess.is_active:
                        await ws_error("Already started")
                        continue

                    sps = await list_session_players(db, sess, active_only=True)
                    if not sps:
                        await ws_error("No players")
                        continue

                    active_ids = [x.player_id for x in sps]
                    missing_sps: list[SessionPlayer] = []
                    if active_ids:
                        q_chars = await db.execute(
                            select(Character).where(
                                Character.session_id == sess.id,
                                Character.player_id.in_(active_ids),
                            )
                        )
                        char_ids = {ch.player_id for ch in q_chars.scalars().all()}
                        missing_sps = [x for x in sps if x.player_id not in char_ids]
                    if missing_sps:
                        q_players = await db.execute(select(Player).where(Player.id.in_([x.player_id for x in missing_sps])))
                        names_by_id = {p.id: p.display_name for p in q_players.scalars().all()}
                        missing_names = ", ".join(
                            f"#{x.join_order} {names_by_id.get(x.player_id, str(x.player_id))}" for x in missing_sps
                        )
                        await add_system_event(db, sess, f"Нельзя стартовать: персонаж не создан у {missing_names}.")
                        await ws_error("Create character first", request_id=msg_request_id)
                        await broadcast_state(session_id)
                        continue

                    # all ready check
                    ready_map = _get_ready_map(sess)
                    if any(not bool(ready_map.get(str(x.player_id), False)) for x in sps):
                        await ws_error("Not all players are ready")
                        continue

                    sess.is_active = True
                    sess.is_paused = False
                    sess.current_player_id = None
                    sess.turn_started_at = None
                    sess.turn_index = 1
                    raw_story = settings_get(sess, "story", {}) or {}
                    if isinstance(raw_story, dict):
                        settings_set(sess, "free_turns", bool(raw_story.get("free_turns")))
                    _set_phase(sess, "lore_pending")
                    _clear_current_action_id(sess)
                    _clear_paused_remaining(sess)
                    await db.commit()
                    await add_system_event(db, sess, "Игра началась. Генерируем вступительную историю...")
                    await broadcast_state(session_id)
                    asyncio.create_task(_auto_lore_task(session_id))
                    continue

                if action == "pause":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can pause")
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
                        await ws_error("Only admin can resume")
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
                        await ws_error("Only admin can skip")
                        continue
                    if _get_phase(sess) == "gm_pending":
                        await ws_error("Ждём ответа мастера...")
                        continue
                    if not sess.current_player_id:
                        await ws_error("Not started")
                        continue
                    if sess.is_paused:
                        await ws_error("Paused. Resume first.")
                        continue

                    nxt = await advance_turn(db, sess)
                    if not nxt:
                        await ws_error("No players")
                        continue
                    await add_system_event(db, sess, f"Ход пропущен. Следующий: #{nxt.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # chat / command parsing
                if action != "say":
                    await ws_error("Unknown action", request_id=msg_request_id)
                    continue

                if not text:
                    continue

                # normalize leading slash for typed commands
                cmdline = text.lstrip()
                if cmdline.startswith("/"):
                    cmdline = cmdline[1:].lstrip()

                lower = cmdline.lower()
                if lower in STATE_COMMAND_ALIASES:
                    ch = await get_character(db, sess.id, player.id)
                    await add_system_event(db, sess, _format_state_text_for_player(sess, player, ch))
                    await broadcast_state(session_id)
                    continue

                phase_now = _get_phase(sess)
                if phase_now == "lore_pending":
                    await ws_error("Ждём вступительную историю...")
                    continue
                if phase_now == "gm_pending":
                    await ws_error("Ждём ответа мастера...")
                    continue

                # OOC (any time, no turn)
                if lower.startswith("ooc ") or cmdline.startswith("//"):
                    msg = cmdline[4:].strip() if lower.startswith("ooc ") else cmdline[2:].strip()
                    await add_event(db, sess, f"[OOC] {player.display_name} (#{sp.join_order}): {msg}")
                    await broadcast_state(session_id)
                    continue

                # GM (admin only, any time, no turn)
                if lower.startswith("gm ") or lower.startswith("gm:"):
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can GM")
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

                if lower == "char":
                    await add_system_event(
                        db,
                        sess,
                        "Character commands: char create <Name> [Class], me, hp <+N|-N|N>, sta <+N|-N|N>, "
                        "stat <str|dex|con|int|wis|cha> <0..100>, check [adv|dis] <stat_or_skill> [dc N] (ручной бросок, опционально).",
                    )
                    await broadcast_state(session_id)
                    continue

                m_char_create = re.match(r"^char\s+create\s+(.+)$", cmdline, re.IGNORECASE)
                if m_char_create:
                    payload = m_char_create.group(1).strip()
                    if not payload:
                        await ws_error("Usage: char create <Name> [Class]", request_id=msg_request_id)
                        continue
                    ch_existing = await get_character(db, sess.id, player.id)
                    if ch_existing:
                        await ws_error("Character already exists", request_id=msg_request_id)
                        continue
                    parts = payload.split()
                    ch_name = parts[0][:80]
                    ch_class = (parts[1] if len(parts) > 1 else "Adventurer")[:40]
                    await create_character(
                        db,
                        sess.id,
                        player.id,
                        name=ch_name,
                        class_kit=ch_class,
                        class_skin=ch_class,
                    )
                    await add_system_event(db, sess, f"Character created: {ch_name} ({ch_class}) for player #{sp.join_order}.")
                    await broadcast_state(session_id)
                    continue

                if lower == "me":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    stats = _normalized_stats(ch.stats)
                    await add_system_event(
                        db,
                        sess,
                        f"[ME] {ch.name} ({ch.class_kit}) lvl {int(ch.level or 1)} | "
                        f"HP {int(ch.hp or 0)}/{int(ch.hp_max or 0)} | STA {int(ch.sta or 0)}/{int(ch.sta_max or 0)} | "
                        f"STR {stats['str']} DEX {stats['dex']} CON {stats['con']} INT {stats['int']} WIS {stats['wis']} CHA {stats['cha']}",
                    )
                    await broadcast_state(session_id)
                    continue

                m_res = re.match(r"^(hp|sta)\s+([+-]?\d+)$", lower, re.IGNORECASE)
                if m_res:
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    key = m_res.group(1).lower()
                    raw_val = m_res.group(2)
                    delta_or_value = as_int(raw_val, 0)
                    cur_attr = "hp" if key == "hp" else "sta"
                    max_attr = "hp_max" if key == "hp" else "sta_max"
                    cur = as_int(getattr(ch, cur_attr), 0)
                    max_v = max(0, as_int(getattr(ch, max_attr), 0))
                    if raw_val.startswith("+") or raw_val.startswith("-"):
                        nxt = _clamp(cur + delta_or_value, 0, max_v)
                    else:
                        nxt = _clamp(delta_or_value, 0, max_v)
                    setattr(ch, cur_attr, nxt)
                    await db.commit()
                    await add_system_event(db, sess, f"{ch.name}: {key.upper()} {cur}->{nxt}/{max_v}")
                    await broadcast_state(session_id)
                    continue

                if lower.startswith("stat "):
                    parts = cmdline.split()
                    if len(parts) < 3 or len(parts) > 4:
                        await ws_error("Usage: stat <str|dex|con|int|wis|cha> <0..100>", request_id=msg_request_id)
                        continue

                    admin = await is_admin(db, sess, player)
                    target_sp = sp

                    if len(parts) == 4:
                        maybe_order = parts[1].lstrip("#")
                        if not maybe_order.isdigit():
                            await ws_error("Usage: stat #<order> <stat> <0..100>", request_id=msg_request_id)
                            continue
                        target_order = as_int(maybe_order, 0)
                        if target_order <= 0:
                            await ws_error("Usage: stat #<order> <stat> <0..100>", request_id=msg_request_id)
                            continue
                        sps_all = await list_session_players(db, sess, active_only=False)
                        target_sp = next((x for x in sps_all if int(x.join_order or 0) == target_order), None)
                        if not target_sp:
                            await ws_error("Player not found", request_id=msg_request_id)
                            continue
                        stat_key = parts[2].lower()
                        stat_val = as_int(parts[3], -1)
                    else:
                        stat_key = parts[1].lower()
                        stat_val = as_int(parts[2], -1)

                    if stat_key not in CHAR_STAT_KEYS:
                        await ws_error("Unknown stat key", request_id=msg_request_id)
                        continue
                    if stat_val < 0 or stat_val > 100:
                        await ws_error("Stat must be 0..100", request_id=msg_request_id)
                        continue
                    if sess.is_active and not admin:
                        await ws_error("Only admin can change stats after start", request_id=msg_request_id)
                        continue
                    if not admin and target_sp.player_id != player.id:
                        await ws_error("You can change only your own stats before start", request_id=msg_request_id)
                        continue

                    target_ch = await get_character(db, sess.id, target_sp.player_id)
                    if not target_ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue

                    stats = _normalized_stats(target_ch.stats)
                    old_val = stats.get(stat_key, 50)
                    stats[stat_key] = stat_val
                    target_ch.stats = stats
                    await db.commit()
                    await add_system_event(
                        db,
                        sess,
                        f"[STAT] #{target_sp.join_order} {target_ch.name}: {stat_key} {old_val}->{stat_val}",
                    )
                    await broadcast_state(session_id)
                    continue

                if lower.startswith("check"):
                    parts = cmdline.split()
                    if len(parts) < 2:
                        await ws_error("Usage: check [adv|dis] <stat_or_skill> [dc N]", request_id=msg_request_id)
                        continue
                    mode = "roll"
                    idx = 1
                    if idx < len(parts) and parts[idx].lower() in ("adv", "dis"):
                        mode = parts[idx].lower()
                        idx += 1
                    if idx >= len(parts):
                        await ws_error("Usage: check [adv|dis] <stat_or_skill> [dc N]", request_id=msg_request_id)
                        continue

                    key = parts[idx].lower()
                    idx += 1
                    dc: Optional[int] = None
                    if idx < len(parts):
                        tok = parts[idx].lower()
                        if tok.startswith("dc"):
                            if tok == "dc":
                                if idx + 1 >= len(parts):
                                    await ws_error("Usage: check ... dc <N>", request_id=msg_request_id)
                                    continue
                                dc = as_int(parts[idx + 1], -1)
                                idx += 2
                            else:
                                dc = as_int(tok[2:], -1)
                                idx += 1
                        else:
                            await ws_error("Usage: check [adv|dis] <stat_or_skill> [dc N]", request_id=msg_request_id)
                            continue
                    if idx != len(parts):
                        await ws_error("Usage: check [adv|dis] <stat_or_skill> [dc N]", request_id=msg_request_id)
                        continue
                    if dc is not None and dc < 0:
                        await ws_error("DC must be >= 0", request_id=msg_request_id)
                        continue

                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue

                    if key in CHAR_STAT_KEYS:
                        stat_val = _normalized_stats(ch.stats).get(key, 50)
                        mod = _clamp(int((stat_val - 50) / 10), -5, 5)
                    else:
                        q_skill = await db.execute(
                            select(Skill).where(
                                Skill.character_id == ch.id,
                                Skill.skill_key == key,
                            )
                        )
                        sk = q_skill.scalar_one_or_none()
                        mod = _clamp(as_int(sk.rank, 0), 0, 10) if sk else 0

                    if mode == "roll":
                        roll = random.randint(1, 20)
                        total = roll + mod
                        rolls_text = str(roll)
                    else:
                        ra = random.randint(1, 20)
                        rb = random.randint(1, 20)
                        roll = max(ra, rb) if mode == "adv" else min(ra, rb)
                        total = roll + mod
                        rolls_text = f"{ra}/{rb}->{roll}"

                    msg = f"[CHECK] {ch.name}: {key} = {rolls_text} + {mod:+d} => {total}"
                    if dc is not None:
                        ok = total >= dc
                        msg += f" (DC {dc}) {'SUCCESS' if ok else 'FAIL'}"
                    await add_system_event(db, sess, msg)
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

                # leave/quit/exit (any time)
                if lower in ("leave", "quit", "exit"):
                    await _process_leave_and_broadcast()
                    await ws.close()
                    return

                # admin: kick <#>
                if lower.startswith("kick "):
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can kick")
                        continue
                    arg = cmdline.split(" ", 1)[1].strip().lstrip("#")
                    target_order = as_int(arg, 0)
                    if target_order <= 0:
                        await ws_error("Usage: kick 2 or kick #2")
                        continue

                    # find target
                    sps_all = await list_session_players(db, sess, active_only=False)
                    target_sp = next((x for x in sps_all if int(x.join_order or 0) == target_order), None)
                    if not target_sp:
                        await ws_error("Player not found")
                        continue
                    if target_sp.player_id == player.id:
                        await ws_error("You can't kick yourself")
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
                        await ws_error("Only admin can change turn")
                        continue
                    arg = cmdline.split(" ", 1)[1].strip().lstrip("#")
                    target_order = as_int(arg, 0)
                    if target_order <= 0:
                        await ws_error("Usage: turn 2 or goto #2")
                        continue
                    target = await set_turn_to_order(db, sess, target_order)
                    if not target:
                        await ws_error("Player not found/active")
                        continue
                    await add_system_event(db, sess, f"Админ передал ход игроку #{target.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # initiative commands (admin)
                if lower.startswith("init"):
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can manage initiative")
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
                            await ws_error("Player not found/active")
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

                    await ws_error("Unknown init command")
                    continue

                # DICE (must be started, not paused, your turn) — does NOT end turn
                dice = parse_dice(cmdline)
                if dice:
                    if not sess.current_player_id:
                        await ws_error("Game not started. Press Start.")
                        continue
                    if sess.is_paused:
                        await ws_error("Paused.")
                        continue
                    if player.id != sess.current_player_id:
                        await ws_error("Not your turn.")
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
                        await ws_error("Game not started. Press Start.")
                        continue
                    if sess.is_paused:
                        await ws_error("Paused.")
                        continue
                    if player.id != sess.current_player_id:
                        await ws_error("Not your turn.")
                        continue
                    nxt = await advance_turn(db, sess)
                    if not nxt:
                        await ws_error("No players")
                        continue
                    await add_system_event(db, sess, f"Игрок #{sp.join_order} пропустил ход. Следующий: #{nxt.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # Normal SAY — ends turn
                if _is_free_turns(sess):
                    phase = _get_phase(sess)
                    if phase == "lore_pending":
                        await ws_error("Ждём вступительную историю...")
                        continue
                    if phase == "gm_pending":
                        await ws_error("Ждём ответа мастера...")
                        continue
                    if phase != "collecting_actions":
                        await ws_error("Сейчас нельзя отправлять действие.")
                        continue

                    sps_active = await list_session_players(db, sess, active_only=True)
                    active_ids = {spx.player_id for spx in sps_active}
                    if player.id not in active_ids:
                        await ws_error("You are offline in this session", request_id=msg_request_id)
                        continue
                    ready_sps = _ready_active_players(sess, sps_active)
                    ready_ids = {spx.player_id for spx in ready_sps}
                    if player.id not in ready_ids:
                        await ws_error("В этом раунде действие принимается только от READY игроков.")
                        continue

                    round_actions = _get_round_actions(sess)
                    pid = str(player.id)
                    if pid in round_actions:
                        await ws_error("В этом раунде вы уже отправили действие.")
                        continue

                    round_actions[pid] = text
                    settings_set(sess, "round_actions", round_actions)
                    current_zone = _get_pc_positions(sess).get(pid, "стартовая локация (вместе)")
                    _set_pc_zone(sess, player.id, infer_zone_from_action(text, current_zone))
                    actor_label = await _event_actor_label(db, sess, player)
                    await add_event(db, sess, f"{actor_label}: {text}", actor_player_id=player.id)
                    await db.commit()

                    all_collected = bool(ready_sps) and all(str(spx.player_id) in round_actions for spx in ready_sps)
                    if all_collected:
                        action_id = _new_action_id()
                        _set_current_action_id(sess, action_id)
                        _set_phase(sess, "gm_pending")
                        await db.commit()
                        await add_system_event(db, sess, "Мастер обрабатывает действия...")
                        await broadcast_state(session_id)
                        asyncio.create_task(_auto_round_task(session_id, action_id))
                    else:
                        await broadcast_state(session_id)
                    continue

                if not sess.current_player_id:
                    await ws_error("Game not started. Press Start.")
                    continue
                if sess.is_paused:
                    await ws_error("Paused.")
                    continue
                if player.id != sess.current_player_id:
                    await ws_error("Not your turn.")
                    continue

                actor_label = await _event_actor_label(db, sess, player)
                await add_event(db, sess, f"{actor_label}: {text}", actor_player_id=player.id)
                pid = str(player.id)
                current_zone = _get_pc_positions(sess).get(pid, "стартовая локация (вместе)")
                _set_pc_zone(sess, player.id, infer_zone_from_action(text, current_zone))
                action_id = _new_action_id()
                _set_current_action_id(sess, action_id)
                _set_phase(sess, "gm_pending")
                sess.turn_started_at = None
                await db.commit()
                await broadcast_state(session_id)
                asyncio.create_task(_auto_gm_reply_task(session_id, action_id))
                continue

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


async def inactive_watcher():
    while True:
        try:
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
                        changed = False
                        try:
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
                                _remove_player_from_session_settings(sess, sp.player_id)
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
                        finally:
                            request_id_var.reset(tok_rid)
                            session_id_var.reset(tok_sid)

                        if changed:
                            await broadcast_state(str(sess.id))
        except Exception:
            logger.exception("inactive_watcher iteration failed")

        await asyncio.sleep(INACTIVE_SCAN_PERIOD_SECONDS)


@app.on_event("startup")
async def on_startup():
    configure_logging()
    logger.info("Web server starting")
    asyncio.create_task(timer_watcher())
    asyncio.create_task(inactive_watcher())
