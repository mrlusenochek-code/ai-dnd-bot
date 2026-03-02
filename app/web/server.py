import asyncio
import json
import logging
import os
import random
import re
import zlib
from contextlib import asynccontextmanager
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
from app.combat.apply_machine import apply_combat_machine_commands
from app.combat.live_actions import handle_live_combat_action
from app.combat.log_ui import normalize_combat_log_ui_patch
from app.combat.combat_narration_facts import extract_combat_narration_facts
from app.combat.state import current_turn_label, end_combat, get_combat, restore_combat_state, snapshot_combat_state
from app.combat.sync_pcs import sync_pcs_from_chars
from app.combat.test_actions import handle_admin_combat_test_action
from app.core.logging import configure_logging
from app.core.log_context import request_id_var, session_id_var, uid_var, ws_conn_id_var, client_id_var
from app.db.connection import AsyncSessionLocal
from app.db.models import Session, Player, SessionPlayer, Character, Skill, Event
from app.gm import (
    checks as gm_checks,
    combat_narration as gm_combat_narration,
    contracts as gm_contracts,
    narration,
    sanitize as gm_sanitize,
    service as gm_service,
)
from app.rules.derived_stats import compute_ac
from app.rules.encounters import pick_encounter
from app.rules.enemy_catalog_data import get_enemy
from app.rules.defeat_outcomes import pick_defeat_outcome
from app.rules.equipment_slots import EquipmentSlot, EQUIPMENT_SLOT_ORDER, slot_label_ru
from app.rules.item_catalog import ITEMS
from app.rules.items import ItemDef, is_equipable, can_equip_to_slot
from app.rules.loot_tables import roll_loot
from app.web.dice import parse_dice, roll_dice
from app.web.machine_extract import _trim_for_log, _extract_inventory_machine_commands, _extract_machine_commands
from app.web.machine_lines import (
    _parse_machine_value,
    _split_machine_args,
    _strip_machine_lines,
)
from app.web.utils import as_int, _clamp, _short_text, _slugify_inventory_id
from app.web.regexes import (
    CHAT_COMBAT_ACTION_PATTERNS,
    COMBAT_MECHANICS_EVENT_RE,
    ZONE_MOVE_RE,
)


TURN_TIMEOUT_SECONDS = int(os.getenv("TURN_TIMEOUT_SECONDS", "300"))
INACTIVE_TIMEOUT_SECONDS = int(os.getenv("DND_INACTIVE_TIMEOUT_SECONDS", "600"))
INACTIVE_SCAN_PERIOD_SECONDS = int(os.getenv("DND_INACTIVE_SCAN_PERIOD_SECONDS", "5"))
ENABLE_WATCHERS = os.getenv("ENABLE_WATCHERS", "1") not in ("0", "false", "False")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Warsaw")
GM_CONTEXT_EVENTS = max(1, int(os.getenv("GM_CONTEXT_EVENTS", "20")))
GM_OLLAMA_TIMEOUT_SECONDS = max(1.0, float(os.getenv("GM_OLLAMA_TIMEOUT_SECONDS", "30")))
GM_DRAFT_NUM_PREDICT = max(200, int(os.getenv("GM_DRAFT_NUM_PREDICT", "1000")))
GM_FINAL_NUM_PREDICT = max(400, int(os.getenv("GM_FINAL_NUM_PREDICT", "1600")))
COMBAT_LOG_HISTORY_KEY = "combat_log_history"
COMBAT_STATE_KEY = "combat_state_v1"
MAX_COMBAT_LOG_LINES = 200
logger = logging.getLogger(__name__)
CHAR_STAT_KEYS = ("str", "dex", "con", "int", "wis", "cha")
CHAR_DEFAULT_STATS = {k: 50 for k in CHAR_STAT_KEYS}
CHECK_LINE_RE = gm_checks.CHECK_LINE_RE
TEXTUAL_CHECK_RE = gm_checks.TEXTUAL_CHECK_RE
COMBAT_DRIFT_MARKERS = gm_combat_narration.COMBAT_DRIFT_MARKERS
START_INTENT_SANITARY_MARKERS = (
    "шлем",
    "латы",
    "броня",
    "доспех",
    "кольчуг",
    "панцир",
    "щит",
    "плащ",
    "перчат",
    "сапог",
    "наруч",
    "понож",
    "шлем",
    "латн",
    "дублет",
    "каск",
    "шпаг",
    "меч",
    "сабл",
    "рапир",
    "кинжал",
    "нож",
    "дубин",
    "топор",
    "секир",
    "булав",
    "молот",
    "копь",
    "пик",
    "арбалет",
    "лук",
    "стрел",
    "болт",
    "пращ",
    "пистолет",
    "мушкет",
    "руж",
    "пул",
    "пуля",
    "патрон",
    "парень",
    "человек",
    "страж",
    "толпа",
    "трактир",
    "таверн",
)
COMBAT_FORBIDDEN_GEAR_MARKERS = (
    "брон",
    "доспех",
    "кольчуг",
    "панцир",
    "лат",
    "шлем",
    "каск",
    "щит",
    "плащ",
    "перчат",
    "сапог",
    "наруч",
    "понож",
    "пояс",
    "шпаг",
    "меч",
    "сабл",
    "рапир",
    "кинжал",
    "нож",
    "дубин",
    "топор",
    "секир",
    "булав",
    "молот",
    "копь",
    "пик",
    "алебард",
    "посох",
    "арбалет",
    "лук",
    "стрел",
    "болт",
    "дротик",
    "пращ",
    "пул",
    "пуля",
    "пистолет",
    "мушкет",
    "руж",
)
START_INTENT_FALLBACK_TEXT = (
    "Ты входишь в дистанцию быстро и без паузы, и противник сразу принимает бой. "
    "Воздух сжимается до коротких рывков и резких смен темпа, где любое движение решает следующий миг. "
    "Ты давишь вперёд и не даёшь схватке расползтись по сторонам. "
    "Противник отвечает жёстко и пытается перехватить инициативу в том же ритме. "
    "Шаги, дыхание и удары сливаются в один плотный момент, где нельзя терять концентрацию. "
    "Ты держишь линию столкновения и ищешь окно для следующего точного действия. "
    "Схватка уже в полном разгаре, и преимущество достанется тому, кто ошибётся последним. Что делаете дальше?"
)
COMBAT_CLARIFY_TEXT = "🧙 GM: Сейчас бой. Уточни: атака/уклон/помощь/рывок/отход/побег/предмет/конец хода.\nЧто делаете дальше?"
MANDATORY_ACTION_PATTERNS_BY_CATEGORY = gm_checks.MANDATORY_ACTION_PATTERNS_BY_CATEGORY
MANDATORY_ALWAYS_CHECK_CATEGORIES = gm_checks.MANDATORY_ALWAYS_CHECK_CATEGORIES
MANDATORY_ACTION_PATTERNS = gm_checks.MANDATORY_ACTION_PATTERNS
MANDATORY_OUTCOME_PATTERNS = gm_checks.MANDATORY_OUTCOME_PATTERNS
MECH_ACTION_RE = gm_checks.MECH_ACTION_RE
MECH_OUTCOME_RE = gm_checks.MECH_OUTCOME_RE
_COMBAT_LOCK_PROMPT = gm_contracts.COMBAT_LOCK_PROMPT
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
    "power_strike": "str",
    "marksmanship": "dex",
    "crafting": "int",
}
ALLOWED_CHECK_KEYS: set[str] = set(CHAR_STAT_KEYS) | set(SKILL_TO_ABILITY.keys())
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
    "wil": "wis",
    "воля": "wis",
    "will": "wis",
    "willpower": "wis",
}
SKILL_ALIASES: dict[str, str] = {
    "акробатика": "acrobatics",
    "атлетика": "athletics",
    "восприятие": "perception",
    "выживание": "survival",
    "выступление": "performance",
    "запугивание": "intimidation",
    "история": "history",
    "ловкость_рук": "sleight_of_hand",
    "медицина": "medicine",
    "обман": "deception",
    "природа": "nature",
    "проницательность": "insight",
    "расследование": "investigation",
    "религия": "religion",
    "скрытность": "stealth",
    "тайная_магия": "arcana",
    "убеждение": "persuasion",
    "уход_за_животными": "animal_handling",
    "sleight_of_hand": "sleight_of_hand",
    "sleight of hand": "sleight_of_hand",
    "sleight-of-hand": "sleight_of_hand",
    "animal_handling": "animal_handling",
    "animal handling": "animal_handling",
    "animal-handling": "animal_handling",
    "listen": "perception",
    "listening": "perception",
    "слух": "perception",
    "прислушивание": "perception",
    "обостренный_слух": "perception",
    "обострённый_слух": "perception",
    "сила_удара": "power_strike",
    "меткость": "marksmanship",
    "воровство": "trickery",
    "внимательность": "perception",
    "наблюдательность": "perception",
    "бдительность": "perception",
    "анализ": "investigation",
    "логика": "investigation",
    "знания_мира": "history",
    "ремесло": "crafting",
    "крафт": "crafting",
    "самоконтроль": "focus",
    "концентрация": "focus",
    "интуиция": "insight",
    "лидерство": "persuasion",
    "сопротивление": "endurance",
    "perc": "perception",
    "percep": "perception",
    "mechanism": "crafting",
    "mechanics": "crafting",
    "mech": "crafting",
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Web server starting")

    if ENABLE_WATCHERS:
        timer_task = asyncio.create_task(timer_watcher(), name="timer_watcher")
        inactive_task = asyncio.create_task(inactive_watcher(), name="inactive_watcher")
        app.state.bg_tasks = [timer_task, inactive_task]

    try:
        yield
    finally:
        tasks = getattr(app.state, "bg_tasks", [])
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(lifespan=lifespan)
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
    flag_modified(sess, "settings")


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
            flag_modified(sess, "settings")
            return True
        return False

    if st.get(COMBAT_STATE_KEY) != snapshot:
        st[COMBAT_STATE_KEY] = snapshot
        flag_modified(sess, "settings")
        return True
    return False


def _maybe_restore_combat_state(sess: Session, session_id: str) -> None:
    if get_combat(session_id) is not None:
        return

    payload = settings_get(sess, COMBAT_STATE_KEY, None)
    if not isinstance(payload, dict):
        return
    restore_combat_state(session_id, payload)


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

    def _known_zone(src: str) -> str:
        if any(k in src for k in ("таверн", "бар", "внутри", "остаюсь")):
            return "таверна"
        if any(k in src for k in ("улиц", "выйду", "выхожу", "на улиц")):
            return "улица у таверны"
        if any(k in src for k in ("центр", "площад")):
            return "центр города"
        if any(k in src for k in ("река", "берег")):
            return "берег реки"
        if "замок" in src:
            if any(k in src for k in ("в замк", "внутри замк", "захожу в зам", "войти в зам", "вхожу в зам")):
                return "замок"
            return "дорога к замку"
        return ""

    m = ZONE_MOVE_RE.search(t)
    if m:
        candidate = re.sub(r"\s+", " ", m.group(1)).strip(" \t\r\n\"'`").lower()
        if len(candidate) > 80:
            candidate = candidate[:80].rstrip()
        known = _known_zone(t)
        if known:
            return known
        if len(candidate) >= 3:
            return candidate

    known = _known_zone(t)
    if known:
        return known
    return current_zone


def _infer_initial_zone(lore_text: str, last_gm_text: str) -> str:
    src = f"{lore_text}\n{last_gm_text}".lower()
    if "таверн" in src:
        return "таверна"
    return "стартовая локация"


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
    return _clamp((val - 50) // 10, -5, 5)


def _skill_bonus_from_rank(rank_raw: Any) -> int:
    rank = _clamp(as_int(rank_raw, 0), 0, 10)
    return _clamp(rank // 2, 0, 5)


def _xp_to_next_skill_rank(rank: int) -> int:
    rank = _clamp(as_int(rank, 0), 0, 10)
    return 20 + 15 * rank + 10 * (rank ** 2)


LEVEL_CAP = 20


def _xp_total_for_level(level: int) -> int:
    return 100 * (max(1, level) - 1) ** 2


def _level_from_xp_total(xp_total: int, current_level: int) -> int:
    level = _clamp(as_int(current_level, 1), 1, LEVEL_CAP)
    xp_total = max(0, as_int(xp_total, 0))
    while level < LEVEL_CAP and xp_total >= _xp_total_for_level(level + 1):
        level += 1
    return level


def _class_preset_from_ids(class_kit: Any, class_skin: Any) -> dict[str, Any]:
    class_kit_key = str(class_kit or "").strip().lower()
    class_skin_key = str(class_skin or "").strip().lower()
    preset = CLASS_PRESETS.get(class_kit_key)
    if preset:
        return preset
    preset = CLASS_PRESETS.get(class_skin_key)
    if preset:
        return preset
    for candidate in CLASS_PRESETS.values():
        display_name = str(candidate.get("display_name") or "").strip().lower()
        if display_name and display_name in {class_kit_key, class_skin_key}:
            return candidate
    return {}


def _starter_rank_for_skill(class_kit: Any, class_skin: Any, skill_key: Any) -> int:
    key = str(skill_key or "").strip().lower()
    if not key:
        return 0
    preset = _class_preset_from_ids(class_kit, class_skin)
    starter_skills = preset.get("starter_skills") if isinstance(preset, dict) else {}
    return _clamp(as_int((starter_skills or {}).get(key), 0), 0, 10)


def _skill_name_from_key(skill_key: Any) -> str:
    key = str(skill_key or "").strip().lower()
    if not key:
        return ""
    return key.replace("_", " ")


def _skill_is_active(skill: Skill, class_kit: Any, class_skin: Any) -> bool:
    rank = _clamp(as_int(getattr(skill, "rank", 0), 0), 0, 10)
    xp = max(0, as_int(getattr(skill, "xp", 0), 0))
    starter_rank = _starter_rank_for_skill(class_kit, class_skin, getattr(skill, "skill_key", ""))
    return xp > 0 or rank != starter_rank


def _skills_payload_for_character(character: Character, skills: list[Skill]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for skill in sorted(skills, key=lambda sk: str(sk.skill_key or "").strip().lower()):
        if not _skill_is_active(skill, character.class_kit, character.class_skin):
            continue
        key = str(skill.skill_key or "").strip().lower()
        rank = _clamp(as_int(skill.rank, 0), 0, 10)
        xp = max(0, as_int(skill.xp, 0))
        xp_to_next = _xp_to_next_skill_rank(rank)
        out.append(
            {
                "key": key,
                "name": _skill_name_from_key(key),
                "rank": rank,
                "xp": xp,
                "xp_to_next": xp_to_next,
                "to_next": max(0, xp_to_next - xp),
            }
        )
    return out


def _level_progress_payload(character: Character) -> dict[str, int]:
    level = _clamp(as_int(character.level, 1), 1, LEVEL_CAP)
    xp_total = max(0, as_int(character.xp_total, 0))
    if level >= LEVEL_CAP:
        next_level_total = xp_total
    else:
        next_level_total = _xp_total_for_level(level + 1)
    return {
        "xp_total": xp_total,
        "next_level_total": next_level_total,
        "to_next_level": max(0, next_level_total - xp_total),
    }


def _character_xp_gain_from_check(result: dict) -> int:
    return _skill_xp_gain(result)


def _dc_xp_bonus(dc: int) -> int:
    dc = max(0, int(dc))
    bonus = 0
    if dc >= 15:
        bonus = 1
    if dc >= 20:
        bonus = 2
    if dc >= 25:
        bonus = 3
    if dc >= 30:
        bonus = 4
    return bonus


def _skill_xp_gain(result: dict) -> int:
    dc = int(result.get("dc") or 0)
    roll = int(result.get("roll") or 0)
    success = bool(result.get("success"))
    base = 6 if roll == 20 else (3 if success else 1)
    return base + _dc_xp_bonus(dc)


def _normalize_check_mode(raw_mode: Any) -> str:
    return gm_checks._normalize_check_mode(raw_mode)


def _normalize_check_name(raw_name: Any) -> str:
    return gm_checks._normalize_check_name(raw_name)


def _check_kind_for_name(raw_kind: Any, normalized_name: str) -> str:
    return gm_checks._check_kind_for_name(raw_kind, normalized_name)


def _extract_checks_from_draft(draft_text: str, default_actor_uid: Optional[int]) -> tuple[str, list[dict[str, Any]], bool]:
    return gm_checks._extract_checks_from_draft(draft_text, default_actor_uid)


def _needs_mandatory_mech_check(draft_text_raw: str) -> bool:
    return _mandatory_check_category(draft_text_raw) is not None


def _mandatory_check_category(draft_text_raw: str) -> Optional[str]:
    return gm_checks._mandatory_check_category(draft_text_raw)


def _normalize_free_text_for_match(text: str) -> str:
    return gm_checks._normalize_free_text_for_match(text)


def _pick_check_key_from_text(text: str, preferred: list[str], forbidden: set[str]) -> Optional[str]:
    return gm_checks._pick_check_key_from_text(text, preferred, forbidden)


def _autogen_check_for_category(cat: str, text: str, actor_uid: Optional[int]) -> Optional[dict[str, Any]]:
    return gm_checks._autogen_check_for_category(cat, text, actor_uid)


def _extract_last_context_line_from_prompt(draft_prompt: str) -> str:
    return gm_checks._extract_last_context_line_from_prompt(draft_prompt)


def _prepend_combat_lock(prompt: str, combat_active: bool) -> str:
    if not combat_active:
        return str(prompt or "")
    base = str(prompt or "").strip()
    if not base:
        return _COMBAT_LOCK_PROMPT
    return f"{_COMBAT_LOCK_PROMPT}\n\n{base}"


def _looks_like_combat_drift(text: str) -> bool:
    txt = str(text or "").strip()
    if not txt:
        return False
    lowered = txt.lower().replace("ё", "е")
    if any(token in lowered for token in ("@@check", "@@check_result", "@@combat_start", "@@combat_end")):
        return True
    drift_patterns = [
        r"\bбой\s+окончен\b",
        r"\bбой\s+законч\w*",
        r"\bпобед\w*",
        r"\bпоражен\w*",
        r"\bперемири\w*",
        r"\bпосле\s+боя\b",
        r"\bна\s+рынок\b",
        r"\bв\s+таверн\w*\b",
        r"\bв\s+магазин\b",
        r"\bв\s+лавк\w*\b",
        r"\bвы\s+уходите\b",
        r"\bвы\s+покидаете\b",
        r"\bпокидаете\s+(?:локаци\w*|место|поле\s+боя)\b",
    ]
    if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in drift_patterns):
        return True
    return any(marker in lowered for marker in COMBAT_DRIFT_MARKERS)


def _combat_narration_fact_coverage(text: str, facts: list[str]) -> int:
    return gm_combat_narration._combat_narration_fact_coverage(text, facts)


def _has_start_intent_sanitary_markers(text: str) -> bool:
    lowered = str(text or "").lower().replace("ё", "е")
    return any(marker in lowered for marker in START_INTENT_SANITARY_MARKERS)


def _combat_text_mentions_forbidden_gear(text: str, *, action_text: str, facts_block: str) -> bool:
    lowered_text = str(text or "").lower().replace("ё", "е")
    if not lowered_text:
        return False
    allowed_source = (
        f"{str(action_text or '').lower().replace('ё', 'е')}\n{str(facts_block or '').lower().replace('ё', 'е')}"
    )
    for marker in COMBAT_FORBIDDEN_GEAR_MARKERS:
        pattern = rf"\b{re.escape(marker)}\w*"
        if re.search(pattern, lowered_text, flags=re.IGNORECASE) and not re.search(
            pattern,
            allowed_source,
            flags=re.IGNORECASE,
        ):
            return True
    return False


def _combat_zone_environment_hint(zone: str) -> str:
    z = str(zone or "").strip().lower().replace("ё", "е")
    if not z:
        return "место рядом с тобой"
    mapping: list[tuple[tuple[str, ...], str]] = [
        (("улиц", "переул", "тракт"), "узкий проход рядом с тобой"),
        (("двор",), "тесный двор рядом с тобой"),
        (("таверн", "трактир"), "душное помещение рядом с тобой"),
        (("лес", "роща", "чащ"), "густой лес рядом с тобой"),
        (("подзем", "катакомб", "склеп"), "сырое подземелье рядом с тобой"),
        (("коридор",), "длинный коридор рядом с тобой"),
        (("камер", "темниц"), "узкая камера рядом с тобой"),
        (("порт", "причал", "док"), "шумный порт рядом с тобой"),
        (("рынок", "базар"), "людное место рядом с тобой"),
        (("арен",), "открытая площадка рядом с тобой"),
    ]
    for keys, value in mapping:
        if any(key in z for key in keys):
            return value
    return "место рядом с тобой"


def _combat_enemy_trait_hint(enemy_name: str, zone: str) -> str:
    traits = (
        "резкий",
        "давит темпом",
        "держит дистанцию",
        "ловит ошибки",
        "идет напролом",
    )
    seed = str(enemy_name or "").strip() or str(zone or "").strip() or "враг"
    idx = sum(ord(ch) for ch in seed) % len(traits)
    return traits[idx]


def _rough_sentence_count(text: str) -> int:
    parts = re.split(r"[.!?]+", str(text or ""))
    return sum(1 for p in parts if re.search(r"[А-Яа-яA-Za-z0-9]", p))


def _start_intent_text_needs_repair(text: str) -> bool:
    txt = str(text or "").strip()
    if not txt:
        return True
    if txt.lower().startswith("сцена продолжается."):
        return True
    if len(txt) < 260:
        return True
    return _rough_sentence_count(txt) < 6


def _checks_from_human_text(draft_text: str, default_actor_uid: Optional[int]) -> list[dict[str, Any]]:
    return gm_checks._checks_from_human_text(draft_text, default_actor_uid)


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


def _gender_to_pronouns(g: str) -> str:
    normalized = str(g or "").strip().lower().replace("ё", "е")
    if normalized.startswith("м") or normalized in {"m", "male"}:
        return "он/его/ему"
    if normalized.startswith("ж") or normalized in {"f", "female"}:
        return "она/ее/ей"
    return ""


def _gender_pronoun_rule_line(g: str) -> str:
    pronouns = _gender_to_pronouns(g)
    if not pronouns:
        return "pronouns=unknown (пиши во 2 лице: ты/вы, избегай он/она)"
    return f"pronouns={pronouns} (строго, не путай)"


def _normalize_inventory_def(raw_def: Any) -> Optional[str]:
    value = str(raw_def or "").strip()[:60]
    if not value:
        return None
    if not re.fullmatch(r"[a-z0-9_]+", value):
        return None
    return value


def _normalize_inventory_item(raw_item: Any, index: int) -> Optional[dict[str, Any]]:
    if isinstance(raw_item, str):
        name = raw_item.strip()
        qty = 1
        item_id_raw = ""
        tags_raw = None
        notes_raw = ""
        def_raw = None
    elif isinstance(raw_item, dict):
        name = str(raw_item.get("name") or "").strip()
        qty = _clamp(as_int(raw_item.get("qty"), 1), 1, 99)
        item_id_raw = str(raw_item.get("id") or "").strip()
        tags_raw = raw_item.get("tags")
        notes_raw = str(raw_item.get("notes") or "").strip()
        def_raw = raw_item.get("def")
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

    item_def = _normalize_inventory_def(def_raw)
    if item_def:
        item["def"] = item_def

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


def _character_equip_from_stats(stats_raw: Any) -> dict[str, str]:
    if not isinstance(stats_raw, dict):
        return {}
    raw = stats_raw.get("_equip")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for slot_raw, item_id_raw in raw.items():
        slot_value = str(slot_raw or "").strip().lower()
        item_id = str(item_id_raw or "").strip().lower()
        if not slot_value or not item_id:
            continue
        try:
            slot = EquipmentSlot(slot_value)
        except Exception:
            continue
        out[slot.value] = item_id
    return out


def _put_character_equip_into_stats(stats_raw: Any, equip_map: dict[str, str]) -> dict[str, Any]:
    stats = dict(stats_raw) if isinstance(stats_raw, dict) else {}
    normalized: dict[str, str] = {}
    if isinstance(equip_map, dict):
        for slot_raw, item_id_raw in equip_map.items():
            slot_value = str(slot_raw or "").strip().lower()
            item_id = str(item_id_raw or "").strip().lower()
            if not slot_value or not item_id:
                continue
            try:
                slot = EquipmentSlot(slot_value)
            except Exception:
                continue
            normalized[slot.value] = item_id
    stats["_equip"] = normalized
    return stats


def _equip_state_line(ch: Optional[Character]) -> str:
    if not ch:
        return "ничего"
    equip = _character_equip_from_stats(ch.stats)
    if not equip:
        return "ничего"
    inv = _character_inventory_from_stats(ch.stats)
    by_id: dict[str, dict[str, Any]] = {}
    for entry in inv:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip().lower()
        if not entry_id:
            continue
        by_id[entry_id] = entry
    parts: list[str] = []
    for slot in EQUIPMENT_SLOT_ORDER:
        item_id = str(equip.get(slot.value) or "").strip().lower()
        if not item_id:
            continue
        item_entry = by_id.get(item_id)
        item_name = str((item_entry or {}).get("name") or item_id).strip()
        if not item_name:
            continue
        parts.append(f"{slot_label_ru(slot)}: {item_name}")
    return "; ".join(parts) if parts else "ничего"


def _item_def_for_inventory_entry(entry: dict[str, Any]) -> ItemDef | None:
    item_def_key = str(entry.get("def") or "").strip()
    if item_def_key and item_def_key in ITEMS:
        return ITEMS[item_def_key]
    entry_name_cf = str(entry.get("name") or "").strip().casefold()
    if not entry_name_cf:
        return None
    for cand in ITEMS.values():
        if cand.name_ru.casefold() == entry_name_cf:
            return cand
    return None


def _equipped_wear_groups(inv: list[dict[str, Any]], equip_map: dict[str, str]) -> dict[str, str]:
    by_id: dict[str, dict[str, Any]] = {}
    for entry in inv:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip().lower()
        if not entry_id:
            continue
        by_id[entry_id] = entry
    out: dict[str, str] = {}
    for equipped_item_id in equip_map.values():
        item_id = str(equipped_item_id or "").strip().lower()
        if not item_id:
            continue
        entry = by_id.get(item_id)
        if not entry:
            continue
        item_def = _item_def_for_inventory_entry(entry)
        wear_group = str(((item_def.equip.wear_group if item_def and item_def.equip else None) or "")).strip().lower()
        if wear_group in ("", "weapon", "ring"):
            continue
        if wear_group not in out:
            out[wear_group] = item_id
    return out


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
    item_def: str | None = None,
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
        if item_def is not None:
            normalized_item_def = _normalize_inventory_def(item_def)
            if normalized_item_def and str(item.get("def") or "") != normalized_item_def:
                item["def"] = normalized_item_def
                changed = True
        inv[idx] = item
    else:
        normalized = _normalize_inventory_item(
            {
                "id": _slugify_inventory_id("", name, len(inv) + 1),
                "name": name,
                "qty": qty,
                "tags": tags,
                "notes": notes or "",
                "def": item_def,
            },
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
    removed_item_id = str(item.get("id") or "").strip().lower()
    if next_qty <= 0:
        inv.pop(idx)
    else:
        item["qty"] = next_qty
        inv[idx] = item
    stats_next = _put_character_inventory_into_stats(ch.stats, inv)
    if next_qty <= 0 and removed_item_id:
        equip_map = _character_equip_from_stats(stats_next)
        equip_changed = False
        for slot_key, equipped_item_id in list(equip_map.items()):
            if str(equipped_item_id or "").strip().lower() == removed_item_id:
                equip_map.pop(slot_key, None)
                equip_changed = True
        if equip_changed:
            stats_next = _put_character_equip_into_stats(stats_next, equip_map)
    ch.stats = stats_next
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

        if op == "equip":
            uid = as_int(cmd.get("uid"), 0)
            slot_raw = str(cmd.get("slot") or "").strip().lower()
            ch = chars_by_uid.get(uid)
            if not ch:
                logger.warning("EQUIP target not found", extra={"action": {"uid": uid, "name": cmd.get("name"), "slot": slot_raw}})
                continue
            try:
                slot = EquipmentSlot(slot_raw)
            except Exception:
                logger.warning("EQUIP invalid slot", extra={"action": {"uid": uid, "name": cmd.get("name"), "slot": slot_raw}})
                continue
            inv_raw = _character_inventory_from_stats(ch.stats)
            inv: list[dict[str, Any]] = [dict(x) for x in inv_raw if isinstance(x, dict)]
            idx = _find_inventory_item_index(inv, str(cmd.get("name") or ""))
            if idx is None:
                logger.warning("EQUIP item not found", extra={"action": {"uid": uid, "name": cmd.get("name"), "slot": slot.value}})
                continue
            item_entry = inv[idx]
            item_id = str(item_entry.get("id") or "").strip().lower()
            if not item_id:
                item_id = _slugify_inventory_id("", str(item_entry.get("name") or ""), idx + 1)

            item_def = _item_def_for_inventory_entry(item_entry)
            if not item_def:
                logger.warning("EQUIP item definition not found", extra={"action": {"uid": uid, "name": cmd.get("name"), "slot": slot.value}})
                continue
            if not is_equipable(item_def):
                logger.warning("EQUIP item is not equipable", extra={"action": {"uid": uid, "name": cmd.get("name"), "slot": slot.value, "item_def": item_def.key}})
                continue
            if not can_equip_to_slot(item_def, slot):
                logger.warning(
                    "EQUIP blocked by slot rules",
                    extra={"action": {"uid": uid, "name": cmd.get("name"), "slot": slot.value, "item_def": item_def.key, "allowed_slots": [s.value for s in item_def.equip.allowed_slots] if item_def.equip else []}},
                )
                continue

            equip_map = _character_equip_from_stats(ch.stats)
            wear_group = str(((item_def.equip.wear_group if item_def.equip else None) or "")).strip().lower()
            if wear_group and wear_group not in ("weapon", "ring"):
                groups = _equipped_wear_groups(inv, equip_map)
                existing_item_id = str(groups.get(wear_group) or "").strip().lower()
                if existing_item_id and existing_item_id != item_id:
                    logger.warning(
                        "EQUIP blocked by wear_group exclusivity",
                        extra={
                            "action": {
                                "uid": uid,
                                "name": cmd.get("name"),
                                "slot": slot.value,
                                "item_id": item_id,
                                "wear_group": wear_group,
                                "existing_item_id": existing_item_id,
                            }
                        },
                    )
                    continue
            if item_def.equip and item_def.equip.two_handed and slot in (EquipmentSlot.main_hand, EquipmentSlot.off_hand):
                other_slot = EquipmentSlot.off_hand if slot == EquipmentSlot.main_hand else EquipmentSlot.main_hand
                other_item_id = str(equip_map.get(other_slot.value) or "").strip().lower()
                if other_item_id and other_item_id != item_id:
                    logger.warning(
                        "EQUIP two_handed blocked by occupied other hand",
                        extra={"action": {"uid": uid, "name": cmd.get("name"), "slot": slot.value, "other_slot": other_slot.value, "other_item_id": other_item_id}},
                    )
                    continue
                equip_map[slot.value] = item_id
                equip_map[other_slot.value] = item_id
            else:
                if slot == EquipmentSlot.off_hand and str(item_def.kind) == "shield":
                    main_item_id = str(equip_map.get(EquipmentSlot.main_hand.value) or "").strip().lower()
                    if main_item_id:
                        main_idx = _find_inventory_item_index(inv, main_item_id)
                        if main_idx is not None:
                            main_entry = inv[main_idx]
                            main_def = _item_def_for_inventory_entry(main_entry)
                            if main_def and main_def.equip and main_def.equip.two_handed:
                                logger.warning(
                                    "EQUIP shield blocked by two_handed in main_hand",
                                    extra={"action": {"uid": uid, "name": cmd.get("name"), "slot": slot.value, "main_item_id": main_item_id, "main_item_def": main_def.key}},
                                )
                                continue
                equip_map[slot.value] = item_id
            ch.stats = _put_character_equip_into_stats(ch.stats, equip_map)
            continue

        if op == "unequip":
            uid = as_int(cmd.get("uid"), 0)
            slot_raw = str(cmd.get("slot") or "").strip().lower()
            ch = chars_by_uid.get(uid)
            if not ch:
                logger.warning("UNEQUIP target not found", extra={"action": {"uid": uid, "slot": slot_raw}})
                continue
            try:
                slot = EquipmentSlot(slot_raw)
            except Exception:
                logger.warning("UNEQUIP invalid slot", extra={"action": {"uid": uid, "slot": slot_raw}})
                continue
            equip_map = _character_equip_from_stats(ch.stats)
            removed_item_id = str(equip_map.pop(slot.value, "") or "").strip().lower()
            if not removed_item_id:
                continue
            if slot in (EquipmentSlot.main_hand, EquipmentSlot.off_hand):
                other_slot = EquipmentSlot.off_hand if slot == EquipmentSlot.main_hand else EquipmentSlot.main_hand
                if str(equip_map.get(other_slot.value) or "").strip().lower() == removed_item_id:
                    equip_map.pop(other_slot.value, None)
            ch.stats = _put_character_equip_into_stats(ch.stats, equip_map)
            continue


async def _apply_zone_set_machine_commands(db: AsyncSession, sess: Session, commands: list[dict[str, Any]]) -> None:
    if not commands:
        return
    uid_map, _chars_by_uid, _skill_mods_by_char = await _load_actor_context(db, sess)
    for cmd in commands:
        uid = as_int(cmd.get("uid"), 0)
        zone = str(cmd.get("zone") or "").strip()
        actor_pair = uid_map.get(uid)
        if uid <= 0 or not zone or not actor_pair:
            logger.warning("ZONE_SET target not found", extra={"action": {"uid": uid, "zone": zone}})
            continue
        sp, _pl = actor_pair
        _set_pc_zone(sess, sp.player_id, zone)


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
    zone = _get_pc_positions(sess).get(str(player.id), "стартовая локация")
    char_name = str(ch.name).strip() if ch and str(ch.name or "").strip() else "(персонаж не создан)"
    hp_sta = "HP/STA: —"
    if ch:
        hp_sta = f"HP {as_int(ch.hp, 0)}/{as_int(ch.hp_max, 0)} | STA {as_int(ch.sta, 0)}/{as_int(ch.sta_max, 0)}"
    equip_line = _equip_state_line(ch)
    inv_line = _inventory_state_line(ch)
    return f"Состояние: {char_name}\nЗона: {zone}\n{hp_sta}\nОдето: {equip_line}\nИнвентарь: {inv_line}"


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


async def _build_combat_scene_facts_for_llm(
    db: AsyncSession,
    sess: Session,
    player: Player,
    *,
    enemy_name: str,
    max_lines: int = 10,
) -> str:
    ch = await get_character(db, sess.id, player.id)
    zone = _get_pc_positions(sess).get(str(player.id), "стартовая локация")
    meta = _character_meta_from_stats(ch.stats) if ch else {"gender": "", "race": "", "description": ""}
    inv_line = _inventory_prompt_line(ch.stats, max_len=120) if ch else ""
    inv_summary = str(inv_line or "").strip()
    if inv_summary.lower().startswith("inventory:"):
        inv_summary = inv_summary.split(":", 1)[1].strip()
    if not inv_summary:
        inv_summary = "без уточнений"

    q_events = await db.execute(
        select(Event)
        .where(Event.session_id == sess.id)
        .order_by(Event.created_at.desc())
        .limit(20)
    )
    rows = list(reversed(q_events.scalars().all()))

    mechanics_re = re.compile(r"(⚔|\bd20\b|\bHP\b|\bAC\b|Бросок|Урон|Раунд|Ход)", flags=re.IGNORECASE)
    scene_lines: list[str] = []
    for ev in rows:
        raw = str(ev.message_text or "").strip()
        if not raw:
            continue

        gm_body = _extract_gm_message_body(raw)
        candidate = ""
        if gm_body:
            candidate = gm_body
        else:
            if raw.startswith("[SYSTEM]"):
                continue
            if raw.startswith("[OOC]"):
                continue
            if re.match(r"^[^:\n\[\]]{1,80}:\s+\S", raw):
                candidate = raw

        candidate = str(candidate or "").strip()
        if not candidate:
            continue
        if candidate.lower().startswith("мастер обрабатывает"):
            continue
        if "Следующий ход" in candidate:
            continue
        if mechanics_re.search(candidate) or COMBAT_MECHANICS_EVENT_RE.search(candidate):
            continue

        denum = _de_numberize_text(candidate)
        scene_lines.append(_short_text(denum or candidate, 220))

    tail = scene_lines[-max(1, min(6, int(max_lines))):]
    facts_lines: list[str] = []
    facts_lines.append(f"- Зона игрока: {_short_text(zone, 90)}")
    facts_lines.append(f"- Окружение: {_combat_zone_environment_hint(zone)}.")
    facts_lines.append(f"- Инвентарь: {_short_text(inv_summary, 100)}.")
    appearance = _short_text(str(meta.get("description") or "").strip(), 130)
    if appearance:
        facts_lines.append(f"- Персонаж: {appearance}")
    facts_lines.append(
        f"- Враг: {_short_text(enemy_name or 'противник', 60)}, {_combat_enemy_trait_hint(enemy_name, zone)}."
    )
    if tail:
        facts_lines.append(f"- Недавняя сцена: {_short_text(' / '.join(tail), 240)}")
    limit = max(1, int(max_lines))
    return "\n".join(facts_lines[:limit])


def _sanitize_gm_output(text: str) -> str:
    return gm_sanitize.sanitize_gm_output(text)


async def _event_actor_label(db: AsyncSession, sess: Session, player: Player) -> str:
    ch = await get_character(db, sess.id, player.id)
    if ch and str(ch.name or "").strip():
        return str(ch.name).strip()
    return str(player.display_name or "").strip() or "Персонаж"


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


def _detect_chat_combat_action(text: str) -> Optional[str]:
    txt = str(text or "").strip()
    if not txt:
        return None
    for action, pattern in CHAT_COMBAT_ACTION_PATTERNS:
        if pattern.search(txt):
            return action
    return None


def _apply_world_move_from_text(sess, session_id: str, text: object) -> tuple[str, bool]:
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    st = _ensure_settings(sess)
    combat_state = get_combat(session_id)
    combat_active = bool(combat_state and combat_state.active)
    moved_text, moved = narration.apply_world_move_to_player_text(
        st,
        session_id,
        text,
        combat_active=combat_active,
    )
    try:
        flag_modified(sess, "settings")
    except Exception:
        pass
    return moved_text, moved


async def _build_player_gm_action_text(
    db: AsyncSession,
    sess: Session,
    session_id: str,
    text: object,
    *,
    include_encounter_after_move: bool,
) -> tuple[str, bool, Optional[dict[str, Any]]]:
    text_for_gm, moved = _apply_world_move_from_text(sess, session_id, text)
    gm_action_text = narration.build_gm_input_text(
        _ensure_settings(sess),
        session_id,
        text_for_gm if isinstance(text_for_gm, str) else str(text),
        moved=moved,
    )
    encounter_patch: Optional[dict[str, Any]] = None
    if include_encounter_after_move and moved:
        encounter_patch, encounter_note = await _maybe_start_encounter_after_move(db, sess, session_id)
        if encounter_note:
            gm_action_text = f"{gm_action_text}\n\n{encounter_note}"
    return gm_action_text, moved, encounter_patch


async def _estimate_party_level(db: AsyncSession, sess: Session) -> int:
    _uid_map, chars_by_uid, _skill_mods_by_char = await _load_actor_context(db, sess)
    levels: list[int] = []
    for ch in chars_by_uid.values():
        lvl = 1
        stats = getattr(ch, "stats", None)
        if isinstance(stats, dict):
            raw_level = stats.get("level")
            if isinstance(raw_level, int):
                lvl = max(1, int(raw_level))
        levels.append(lvl)
    if not levels:
        return 1
    avg = float(sum(levels)) / float(len(levels))
    return max(1, int(round(avg)))


async def _maybe_start_encounter_after_move(db: AsyncSession, sess: Session, session_id: str) -> tuple[Optional[dict[str, Any]], str]:
    combat_state = get_combat(session_id)
    if combat_state is not None and combat_state.active:
        return None, ""

    world = settings_get(sess, "world", {}) or {}
    if not isinstance(world, dict):
        return None, ""

    env = str(world.get("env") or "").strip()
    seed = str(world.get("seed") or "").strip()
    x = world.get("x")
    y = world.get("y")
    if not env or not seed or not isinstance(x, int) or not isinstance(y, int):
        return None, ""

    party_level = await _estimate_party_level(db, sess)
    enc = pick_encounter(seed=seed, x=x, y=y, env=env, party_level=party_level)
    if enc is None:
        return None, ""

    enemy = get_enemy(enc.enemy_key)
    if not isinstance(enemy, dict):
        return None, "ВОЗМОЖНА ВСТРЕЧА."

    enemy_name = str(enemy.get("name_ru") or enemy.get("key") or "Противник").strip() or "Противник"
    enemy_id = str(enemy.get("key") or "enemy").strip() or "enemy"
    hp = max(1, as_int(enemy.get("hp_avg"), 10))
    ac = max(1, as_int(enemy.get("ac"), 10))
    zone = env.replace('"', '\\"')
    enemy_name_escaped = enemy_name.replace('"', '\\"')
    enemy_id_escaped = enemy_id.replace('"', '\\"')
    gm_machine = (
        f'@@COMBAT_START(zone="{zone}", cause="bootstrap")\n'
        f'@@COMBAT_ENEMY_ADD(id={enemy_id_escaped}, name="{enemy_name_escaped}", hp={hp}, ac={ac}, threat=1)'
    )

    patch = apply_combat_machine_commands(session_id, gm_machine)
    if patch is None:
        return None, f"ВОЗМОЖНА ВСТРЕЧА: {enemy_name}."

    _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
    sync_pcs_from_chars(session_id, chars_by_uid)
    patch = _append_combat_patch_lines(
        patch,
        [{"text": f"Стычка: {enemy_name}.", "muted": True}],
        prepend=True,
    )
    state = get_combat(session_id)
    if state is not None and state.active:
        if patch.get("reset") is True:
            state.round_no = 1
            state.turn_index = 0
        patch["status"] = f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}"
    return patch, ""


def _hp_state_label(hp_current: int, hp_max: int) -> str:
    hp_max_norm = max(1, int(hp_max))
    hp_cur_norm = max(0, int(hp_current))
    if hp_cur_norm <= 0:
        return "повержен"
    ratio = hp_cur_norm / hp_max_norm
    if ratio <= 0.1:
        return "при смерти"
    if ratio <= 0.3:
        return "тяжело ранен"
    if ratio <= 0.6:
        return "ранен"
    if ratio <= 0.85:
        return "слегка ранен"
    return "цел"


def _hit_force_label(total_damage: int) -> str:
    dmg = max(0, int(total_damage))
    if dmg <= 3:
        return "легко"
    if dmg <= 7:
        return "сильно"
    return "тяжело"


def _de_numberize_text(text: str) -> str:
    txt = str(text or "")
    txt = re.sub(r"\d+", "", txt)
    txt = gm_sanitize.COMBAT_NARRATION_BANNED_RE.sub("", txt)
    txt = re.sub(r"\s{2,}", " ", txt)
    txt = re.sub(r"\s+([,.;:!?])", r"\1", txt)
    return txt.strip()


def _combat_outcome_summary_from_patch(
    action: str,
    combat_patch: Optional[dict[str, Any]],
) -> list[str]:
    combat_line_re = re.compile(
        r"(?:^Атака:|^Результат:|^Урон:|:\s*HP\s*\d+/\d+|Ход автоматически передан|повержен|промах|попадание|крит)",
        flags=re.IGNORECASE,
    )
    patch = combat_patch if isinstance(combat_patch, dict) else {}
    lines: list[str] = []
    for item in patch.get("lines", []):
        if isinstance(item, dict):
            txt = str(item.get("text") or "").strip()
            if txt and combat_line_re.search(txt):
                lines.append(txt)
    if not lines:
        return ["Схватка продолжается в напряжённом темпе."]

    if action == "combat_attack":
        actor = "боец"
        target = "цель"
        for line in lines:
            m_attack = re.search(r"^Атака:\s*(.+?)\s*[→-]\s*(.+)$", line)
            if m_attack:
                actor = m_attack.group(1).strip() or actor
                target = m_attack.group(2).strip() or target
                break

        outcome = "промах"
        for line in lines:
            low = line.lower()
            if "крит" in low:
                outcome = "крит"
                break
            if "попадание" in low:
                outcome = "попадание"
                break
            if "промах" in low:
                outcome = "промах"

        hp_state = "цел"
        for line in lines:
            m_hp = re.search(r":\s*HP\s*(\d+)\s*/\s*(\d+)", line, flags=re.IGNORECASE)
            if m_hp:
                hp_state = _hp_state_label(int(m_hp.group(1)), int(m_hp.group(2)))
                break
            if "повержен" in line.lower():
                hp_state = "повержен"
                break

        hit_force = "легко"
        for line in lines:
            m_dmg = re.search(r"Урон:\s*.+?=\s*(\d+)", line, flags=re.IGNORECASE)
            if m_dmg:
                hit_force = _hit_force_label(int(m_dmg.group(1)))
                break

        summary = f"{actor} атакует {target}: {outcome}; цель {hp_state}; удар {hit_force}."
        return [_de_numberize_text(summary)]

    action_summaries = {
        "combat_dodge": "ушёл в оборону и сбил темп противника.",
        "combat_help": "помог союзнику и открыл окно для атаки.",
        "combat_dash": "рванул вперёд и резко сменил позицию.",
        "combat_disengage": "отступил без раскрытия и разорвал дистанцию.",
        "combat_escape": "попытался вырваться из схватки и уйти из боя.",
        "combat_use_object": "использовал объект в гуще схватки.",
        "combat_end_turn": "передал ход следующему бойцу.",
    }
    base = action_summaries.get(action, "действует в бою.")
    for line in lines:
        if line.startswith("Атака:"):
            continue
        if "повержен" in line.lower():
            base = f"{base.rstrip('.')} Один из противников повержен."
            break
    return [_de_numberize_text(base)]


def _merge_combat_patches(patches: list[dict[str, Any]]) -> dict[str, Any]:
    if not patches:
        return {"open": True, "lines": []}
    last = patches[-1]
    merged_lines: list[dict[str, Any]] = []
    for patch in patches:
        for item in patch.get("lines", []):
            if isinstance(item, dict):
                merged_lines.append(item)
    out = dict(last)
    out["lines"] = merged_lines
    return out


def _append_combat_patch_lines(
    combat_patch: Optional[dict[str, Any]],
    lines_to_add: list[dict[str, Any]],
    *,
    prepend: bool = False,
) -> dict[str, Any]:
    patch = combat_patch if isinstance(combat_patch, dict) else {}
    lines = patch.get("lines")
    if not isinstance(lines, list):
        lines = []
        patch["lines"] = lines
    prepared_lines: list[dict[str, Any]] = []
    for line in lines_to_add:
        text = str(line.get("text") or "").strip() if isinstance(line, dict) else ""
        if not text:
            continue
        prepared_lines.append(line)
    if prepend:
        patch["lines"] = prepared_lines + lines
    else:
        lines.extend(prepared_lines)
    return patch


def _build_combat_start_preamble_lines(
    *,
    player: Optional[Player],
    chars_by_uid: dict[int, Character],
    combat_state: Any,
) -> list[dict[str, Any]]:
    if combat_state is None or not getattr(combat_state, "active", False):
        return []

    player_uid = _player_uid(player)
    player_name = str(getattr(player, "display_name", "") or "").strip() or "Игрок"
    level = 1
    class_kit = "Adventurer"
    stats = dict(CHAR_DEFAULT_STATS)
    hp_cur = 0
    hp_max = 1
    ac = 10

    if player_uid is not None:
        character = chars_by_uid.get(player_uid)
        if character is not None:
            char_name = str(character.name or "").strip()
            if char_name:
                player_name = char_name
            level = max(1, as_int(character.level, 1))
            class_kit = str(character.class_kit or "").strip() or "Adventurer"
            stats = _normalized_stats(character.stats)
            equip_map = _character_equip_from_stats(character.stats)
            inv = _character_inventory_from_stats(character.stats)
            ac = compute_ac(stats=character.stats, inventory=inv, equip_map=equip_map)
            hp_max = max(1, as_int(character.hp_max, hp_max))
            hp_cur = _clamp(as_int(character.hp, hp_cur), 0, hp_max)

        combatants = getattr(combat_state, "combatants", {})
        if isinstance(combatants, dict):
            pc_key = f"pc_{player_uid}"
            player_combatant = combatants.get(pc_key)
            if player_combatant is not None:
                hp_max = max(1, as_int(getattr(player_combatant, "hp_max", hp_max), hp_max))
                hp_cur = _clamp(as_int(getattr(player_combatant, "hp_current", hp_cur), hp_cur), 0, hp_max)
                ac = max(0, as_int(getattr(player_combatant, "ac", ac), ac))

    enemy_name = "противником"
    combatants = getattr(combat_state, "combatants", {})
    if isinstance(combatants, dict):
        for combatant in combatants.values():
            if getattr(combatant, "side", "") != "enemy":
                continue
            candidate = str(getattr(combatant, "name", "") or "").strip()
            if candidate:
                enemy_name = candidate
            break

    battle_line = f'Бой начался между "{player_name}" и "{enemy_name}".'
    player_line = (
        f"Добавлен в бой: {player_name} (ур. {level}, класс {class_kit}) "
        f"HP {hp_cur}/{hp_max}, AC {ac}, "
        f"СИЛ {stats['str']} ЛОВ {stats['dex']} ТЕЛ {stats['con']} "
        f"ИНТ {stats['int']} МДР {stats['wis']} ХАР {stats['cha']}"
    )
    return [{"text": battle_line}, {"text": player_line}]


def _maybe_apply_opening_combat_action(
    *,
    session_id: str,
    combat_action: Optional[str],
    player_uid: Optional[int],
    player_id: uuid.UUID,
    combat_patch: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    _ = player_id
    if combat_action is None:
        return combat_patch

    state = get_combat(session_id)
    if state is None or not state.active:
        return combat_patch

    player_key = f"pc_{player_uid}" if player_uid is not None else ""
    if player_key and player_key in state.order:
        state.turn_index = state.order.index(player_key)
        state.round_no = max(1, int(state.round_no or 0))

    merge_items: list[dict[str, Any]] = []
    if isinstance(combat_patch, dict):
        merge_items.append(combat_patch)
    merge_items.append(
        {
            "open": True,
            "lines": [
                {
                    "text": f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}",
                    "muted": True,
                    "kind": "status",
                }
            ],
        }
    )

    opening_patch, _opening_err = handle_live_combat_action(combat_action, session_id)
    if isinstance(opening_patch, dict):
        merge_items.append(opening_patch)

        max_enemy_steps = 3
        enemy_steps = 0
        while enemy_steps < max_enemy_steps:
            state_now = get_combat(session_id)
            if state_now is None or not state_now.active or not state_now.order:
                break
            if state_now.turn_index < 0 or state_now.turn_index >= len(state_now.order):
                break
            turn_key_now = state_now.order[state_now.turn_index]
            turn_actor = state_now.combatants.get(turn_key_now)
            if not turn_actor or turn_actor.side != "enemy":
                break

            enemy_patch, enemy_err = handle_live_combat_action("combat_attack", session_id)
            if enemy_err:
                logger.warning("enemy auto combat action failed", extra={"action": {"error": enemy_err}})
                break
            if isinstance(enemy_patch, dict):
                merge_items.append(enemy_patch)
            enemy_steps += 1

    return _merge_combat_patches(merge_items) if merge_items else combat_patch


async def _recent_narrative_events_for_combat_prompt(
    db: AsyncSession,
    sess: Session,
    limit: int = 10,
) -> list[str]:
    q_events = await db.execute(
        select(Event)
        .where(Event.session_id == sess.id)
        .order_by(Event.created_at.desc())
        .limit(80)
    )
    rows = q_events.scalars().all()
    out: list[str] = []
    for ev in reversed(rows):
        payload = ev.result_json if isinstance(ev.result_json, dict) else {}
        ev_type = str(payload.get("type") or "").strip().lower()
        is_combat_chat = ev_type == "combat_chat_gm_reply"
        is_combat_action = ev_type == "player_action" and bool(payload.get("combat_chat_action"))
        if not (is_combat_chat or is_combat_action):
            continue
        raw = str(ev.message_text or "").strip()
        if not raw:
            continue
        if raw.startswith("[SYSTEM] "):
            raw = raw[9:].strip()
        if COMBAT_MECHANICS_EVENT_RE.search(raw):
            continue
        gm_body = _extract_gm_message_body(raw)
        candidate = gm_body if gm_body else raw
        candidate = _de_numberize_text(candidate)
        if not candidate:
            continue
        out.append(candidate)
    if not out:
        out.append("Схватка продолжается: стороны держат строй и ищут уязвимость.")
    return out[-max(1, int(limit)) :]


async def _combat_clarify_already_sent(
    db: AsyncSession,
    sess: Session,
    request_id: Optional[str],
) -> bool:
    rid = str(request_id or "").strip()
    if not rid:
        return False
    q_events = await db.execute(
        select(Event)
        .where(Event.session_id == sess.id)
        .order_by(Event.created_at.desc())
        .limit(25)
    )
    for ev in q_events.scalars().all():
        payload = ev.result_json if isinstance(ev.result_json, dict) else {}
        if str(payload.get("type") or "") != "combat_chat_gm_reply":
            continue
        if payload.get("combat_action") is not None:
            continue
        if str(payload.get("request_id") or "").strip() != rid:
            continue
        if COMBAT_CLARIFY_TEXT in str(ev.message_text or ""):
            return True
    return False


def _build_combat_narration_prompt(
    campaign_title: str,
    outcome_summary: list[str],
    current_turn: str,
    participants_block: str,
    actor_name: str,
    actor_gender: str,
    actor_pronouns: str,
) -> str:
    return gm_combat_narration.build_combat_narration_prompt(
        campaign_title=campaign_title,
        outcome_summary=outcome_summary,
        current_turn=current_turn,
        participants_block=participants_block,
        actor_name=actor_name,
        actor_gender=actor_gender,
        actor_pronouns=actor_pronouns,
    )


def _sanitize_combat_narration(text: str) -> str:
    return gm_combat_narration.sanitize_combat_narration(text)


def _combat_safe_fallback(player_action: str, outcome_summary: list[str]) -> str:
    return gm_combat_narration._combat_safe_fallback(player_action, outcome_summary)


def _combat_narration_mentions_action(text: str, action: str) -> bool:
    return gm_combat_narration._combat_narration_mentions_action(text, action)


def _combat_participant_line(actor: Any) -> str:
    name = str(getattr(actor, "name", "") or getattr(actor, "key", "") or "боец").strip()
    hp_cur = int(getattr(actor, "hp_current", 0) or 0)
    hp_max = int(getattr(actor, "hp_max", 1) or 1)
    state = _hp_state_label(hp_cur, hp_max)
    return f"{name} ({state})"


def _combat_participants_block(state: Any) -> str:
    combatants = getattr(state, "combatants", {}) if state is not None else {}
    if not isinstance(combatants, dict) or not combatants:
        return "- PC: (нет)\n- ENEMY: (нет)"

    pcs: list[str] = []
    enemies: list[str] = []
    for key in getattr(state, "order", []) or []:
        actor = combatants.get(key)
        if actor is None:
            continue
        label = _combat_participant_line(actor)
        side = str(getattr(actor, "side", "")).lower()
        if side == "pc":
            pcs.append(label)
        elif side == "enemy":
            enemies.append(label)

    if not pcs or not enemies:
        for key, actor in combatants.items():
            label = _combat_participant_line(actor)
            side = str(getattr(actor, "side", "")).lower()
            if side == "pc" and label not in pcs:
                pcs.append(label)
            elif side == "enemy" and label not in enemies:
                enemies.append(label)

    pcs_text = ", ".join(pcs) if pcs else "(нет)"
    enemies_text = ", ".join(enemies) if enemies else "(нет)"
    return f"- PC: {pcs_text}\n- ENEMY: {enemies_text}"


async def _generate_combat_narration(
    campaign_title: str,
    outcome_summary: list[str],
    player_action: str,
    current_turn: str,
    participants_block: str,
    actor_name: str,
    actor_gender: str,
    actor_pronouns: str,
) -> str:
    return await gm_combat_narration.generate_combat_narration(
        campaign_title=campaign_title,
        outcome_summary=outcome_summary,
        player_action=player_action,
        current_turn=current_turn,
        participants_block=participants_block,
        actor_name=actor_name,
        actor_gender=actor_gender,
        actor_pronouns=actor_pronouns,
        timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
        num_predict=max(240, GM_FINAL_NUM_PREDICT // 3),
    )


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
            skill_mods_by_char.setdefault(sk.character_id, {})[str(sk.skill_key or "").strip().lower()] = _skill_bonus_from_rank(sk.rank)
    return uid_map, chars_by_uid, skill_mods_by_char


def _compute_check_mod(
    check: dict[str, Any],
    character: Optional[Character],
    skill_mods_by_char: dict[uuid.UUID, dict[str, int]],
) -> int:
    if not character:
        return 0
    name = _normalize_check_name(check.get("name"))
    skill_mods = skill_mods_by_char.get(character.id, {})

    if "|" in name:
        candidates = [x.strip() for x in name.split("|") if x.strip()]
        if not candidates:
            return 0
        candidate_mods: list[int] = []
        for candidate in candidates:
            candidate_kind = _check_kind_for_name(check.get("kind"), candidate)
            if candidate_kind in {"ability", "stat"} or candidate in CHAR_STAT_KEYS:
                stat_key = STAT_ALIASES.get(candidate, candidate)
                if stat_key in CHAR_STAT_KEYS:
                    candidate_mods.append(_ability_mod_from_stats(character.stats, stat_key))
                else:
                    candidate_mods.append(0)
                continue
            ability_key = SKILL_TO_ABILITY.get(candidate)
            ability_mod = _ability_mod_from_stats(character.stats, ability_key) if ability_key else 0
            skill_bonus = int(skill_mods.get(candidate, 0))
            candidate_mods.append(ability_mod + skill_bonus)
        return max(candidate_mods) if candidate_mods else 0

    kind = _check_kind_for_name(check.get("kind"), name)
    if kind in {"ability", "stat"} or name in CHAR_STAT_KEYS:
        stat_key = STAT_ALIASES.get(name, name)
        if stat_key not in CHAR_STAT_KEYS:
            return 0
        return _ability_mod_from_stats(character.stats, stat_key)

    ability_key = SKILL_TO_ABILITY.get(name)
    ability_mod = _ability_mod_from_stats(character.stats, ability_key) if ability_key else 0
    skill_bonus = int(skill_mods.get(name, 0))
    return ability_mod + skill_bonus


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
            _gender_pronoun_rule_line(meta["gender"]),
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
            else (str(pl.display_name or "").strip() or f"Персонаж #{sp.join_order}")
        )
        zone = positions.get(str(sp.player_id), "стартовая локация")
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
        "xp_total": int(ch.xp_total or 0),
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


def _safe_event_text(text: Any) -> str:
    s = str(text or "")
    s = s.replace("\x00", "")
    s = s.encode("utf-8", "replace").decode("utf-8")
    return s[:8000]


async def add_event(
    db: AsyncSession,
    sess: Session,
    text: Any,
    actor_player_id: Optional[uuid.UUID] = None,
    actor_character_id: Optional[uuid.UUID] = None,
    parsed_json: Optional[dict] = None,
    result_json: Optional[dict] = None,
) -> None:
    text = _safe_event_text(text)
    ev = Event(
        session_id=sess.id,
        turn_index=sess.turn_index or 0,
        actor_player_id=actor_player_id,
        actor_character_id=actor_character_id,
        message_text=text,
        parsed_json=parsed_json,
        result_json=result_json,
    )
    db.add(ev)
    await db.commit()


async def add_system_event(
    db: AsyncSession,
    sess: Session,
    text: str,
    *,
    result_json: Optional[dict] = None,
    parsed_json: Optional[dict] = None,
) -> None:
    await add_event(db, sess, f"[SYSTEM] {text}", actor_player_id=None, parsed_json=parsed_json, result_json=result_json)


def _gm_show_check_results_enabled() -> bool:
    return str(os.getenv("GM_SHOW_CHECK_RESULTS", "0")).strip() == "1"


def _format_check_result_line(result: dict[str, Any]) -> str:
    actor_uid = as_int(result.get("actor_uid"), 0)
    name = _normalize_check_name(result.get("name"))
    if not name:
        name = "check"
    mod = as_int(result.get("mod"), 0)
    total = as_int(result.get("total"), 0)
    dc = max(0, as_int(result.get("dc"), 0))
    mode = _normalize_check_mode(result.get("mode"))
    roll = as_int(result.get("roll"), 0)
    roll_a = as_int(result.get("roll_a"), 0)
    roll_b = as_int(result.get("roll_b"), 0)
    success = bool(result.get("success"))

    actor_prefix = f"#{actor_uid} " if actor_uid > 0 else ""
    if mode in {"advantage", "disadvantage"} and (roll_a > 0 or roll_b > 0):
        roll_part = f"d20({roll_a},{roll_b})"
    else:
        roll_part = f"d20={roll}"
    mod_part = f"+{mod}" if mod > 0 else str(mod)
    dc_part = f" vs DC {dc}" if dc > 0 else ""
    outcome = "успех" if success else "провал"
    return f"🎲 {actor_prefix}{name}: {roll_part}, мод {mod_part}, итог {total}{dc_part} — {outcome}"


def _build_check_results_system_text(check_results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for result in check_results or []:
        if isinstance(result, dict):
            lines.append(_format_check_result_line(result))
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]
    return "🎲 Результаты проверок:\n" + "\n".join(lines)


async def _emit_check_results_if_enabled(db: AsyncSession, sess: Session, check_results: list[dict[str, Any]]) -> None:
    if not _gm_show_check_results_enabled():
        return
    text = _build_check_results_system_text(check_results)
    if not text:
        return
    await add_system_event(
        db,
        sess,
        text,
        result_json={"type": "check_results", "check_results": check_results},
    )


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
    zone = str(default_zone or "").strip() or "стартовая локация"
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
    skills_by_character_id: dict[uuid.UUID, list[Skill]] = {}
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

    # ---------------------------------------
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
    positions = _get_pc_positions(sess)
    players_payload = []
    for sp in all_sps:
        pl = players_by_id.get(sp.player_id)
        char = chars_by_player_id.get(sp.player_id)
        char_payload = _char_to_payload(char)
        if char and char_payload is not None:
            char_payload["level_progress"] = _level_progress_payload(char)
            char_payload["skills"] = _skills_payload_for_character(char, skills_by_character_id.get(char.id, []))
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
                "zone": positions.get(str(sp.player_id), "стартовая локация"),
            }
        )

    pc_positions: dict[str, str] = {}
    for sp in all_sps:
        pl = players_by_id.get(sp.player_id)
        uid = _player_uid(pl)
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
            "pc_positions": pc_positions,
        },
    }


def _is_victory_patch(patch: dict[str, Any]) -> bool:
    if not isinstance(patch, dict):
        return False
    if patch.get("status") != "Бой завершён":
        return False
    lines = patch.get("lines")
    if not isinstance(lines, list):
        return False
    for raw_line in lines:
        text: Optional[str] = None
        if isinstance(raw_line, str):
            text = raw_line
        elif isinstance(raw_line, dict):
            candidate = raw_line.get("text")
            if isinstance(candidate, str):
                text = candidate
        if isinstance(text, str) and text.startswith("Победа:"):
            return True
    return False


def _is_defeat_patch(patch: dict[str, Any]) -> bool:
    if not isinstance(patch, dict):
        return False
    if patch.get("status") != "Бой завершён":
        return False
    lines = patch.get("lines")
    if not isinstance(lines, list):
        return False
    for raw_line in lines:
        text: Optional[str] = None
        if isinstance(raw_line, str):
            text = raw_line
        elif isinstance(raw_line, dict):
            candidate = raw_line.get("text")
            if isinstance(candidate, str):
                text = candidate
        if isinstance(text, str) and text.startswith("Поражение:"):
            return True
    return False


def _combat_started_at_from_settings(sess: Session) -> str | None:
    payload = settings_get(sess, COMBAT_STATE_KEY, None)
    if not isinstance(payload, dict):
        return None
    raw = payload.get("started_at_iso")
    return raw if isinstance(raw, str) else None


def _enemy_ids_from_combat_state_payload(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    combatants = payload.get("combatants")
    if not isinstance(combatants, dict):
        return []
    out: list[str] = []
    for key, raw in combatants.items():
        if not isinstance(key, str) or not isinstance(raw, dict):
            continue
        if raw.get("side") == "enemy":
            out.append(key)
    return out


def _compute_rewards_from_combat_state_payload(payload: Any) -> tuple[list[int], int | None, int, dict[str, int]]:
    if not isinstance(payload, dict):
        return [], None, 0, {}

    combatants = payload.get("combatants")
    if not isinstance(combatants, dict):
        return [], None, 0, {}

    pc_uids: list[int] = []
    seen_pc_uids: set[int] = set()
    enemies: list[tuple[str, int]] = []

    for key, raw in combatants.items():
        if not isinstance(key, str):
            continue
        if key.startswith("pc_"):
            uid_raw = key[3:]
            if uid_raw.isdigit():
                uid = int(uid_raw)
                if uid not in seen_pc_uids:
                    seen_pc_uids.add(uid)
                    pc_uids.append(uid)
        if isinstance(raw, dict) and raw.get("side") == "enemy":
            enemies.append((key, max(0, as_int(raw.get("hp_max"), 0))))

    leader_uid: int | None = None
    order_raw = payload.get("order")
    order = order_raw if isinstance(order_raw, list) else []
    for key in order:
        if not isinstance(key, str) or not key.startswith("pc_"):
            continue
        uid_raw = key[3:]
        if uid_raw.isdigit():
            uid = int(uid_raw)
            if uid in seen_pc_uids:
                leader_uid = uid
                break
    if leader_uid is None and pc_uids:
        leader_uid = pc_uids[0]

    xp_total_enemy_sum = sum(max(10, hp_max * 5) for _enemy_id, hp_max in enemies)
    xp_each = xp_total_enemy_sum // max(1, len(pc_uids))

    started_at = payload.get("started_at_iso")
    started_at_str = started_at if isinstance(started_at, str) else ""
    loot_dict: dict[str, int] = {}
    for enemy_id, _hp_max in enemies:
        rng = random.Random(zlib.adler32((started_at_str + ":" + enemy_id).encode("utf-8")))
        drops = roll_loot(enemy_id, rng=rng)
        for drop in drops:
            if not isinstance(drop, dict):
                continue
            def_key = drop.get("def")
            if not isinstance(def_key, str) or not def_key:
                continue
            qty = max(0, as_int(drop.get("qty"), 0))
            if qty <= 0:
                continue
            loot_dict[def_key] = loot_dict.get(def_key, 0) + qty

    return pc_uids, leader_uid, xp_each, loot_dict


def _apply_defeat_outcome_to_settings(sess: Session, started_at: str) -> dict[str, Any]:
    outcome = pick_defeat_outcome(started_at_iso=started_at, rng=None)
    payload = {
        "started_at_iso": started_at,
        "key": outcome.key,
        "title_ru": outcome.title_ru,
        "description_ru": outcome.description_ru,
        "tags": list(outcome.tags),
    }
    settings_set(sess, "combat_defeat_outcome_for", started_at)
    settings_set(sess, "combat_defeat_outcome", payload)
    return payload


def _revive_characters_to_1hp(chars: list[Any]) -> bool:
    changed = False
    for ch in chars:
        hp = as_int(getattr(ch, "hp", 0), 0)
        if hp <= 0:
            setattr(ch, "hp", 1)
            if hasattr(ch, "is_alive"):
                setattr(ch, "is_alive", True)
            changed = True
    return changed


def _apply_left_for_dead_character_state(chars_by_uid: dict[int, Any]) -> int | None:
    if not chars_by_uid:
        return None
    leader_uid = min(chars_by_uid.keys())
    for uid, ch in chars_by_uid.items():
        hp = as_int(getattr(ch, "hp", 0), 0)
        if uid == leader_uid:
            if hp <= 0:
                setattr(ch, "hp", 1)
        elif hp <= 0:
            setattr(ch, "hp", 0)
        if hasattr(ch, "is_alive"):
            setattr(ch, "is_alive", True)
    return leader_uid


def _compute_robbed_removals(inv: list[dict[str, Any]], max_take: int = 2) -> list[str]:
    if not isinstance(inv, list):
        return []
    candidates: list[tuple[str, str]] = []
    for entry in inv:
        if not isinstance(entry, dict):
            continue
        def_key = str(entry.get("def") or "").strip()
        item_def = ITEMS.get(def_key) if def_key else None
        if item_def is not None and item_def.kind == "quest":
            continue
        entry_id = str(entry.get("id") or "").strip().lower()
        entry_name = str(entry.get("name") or "").strip()
        if not entry_id and not entry_name:
            continue
        sort_key = entry_id or entry_name.lower()
        remove_name = entry_id or entry_name
        candidates.append((sort_key, remove_name))
    candidates.sort(key=lambda x: x[0])
    take = max(0, as_int(max_take, 2))
    return [remove_name for _sort_key, remove_name in candidates[:take]]


async def _apply_defeat_effects_once(
    db: AsyncSession,
    sess: Session,
) -> bool:
    outcome_payload = settings_get(sess, "combat_defeat_outcome", None)
    if not isinstance(outcome_payload, dict):
        return False

    started_at = str(outcome_payload.get("started_at_iso") or "").strip()
    key = str(outcome_payload.get("key") or "").strip()
    if not started_at or not key:
        return False

    if settings_get(sess, "combat_defeat_effects_applied_for", "") == started_at:
        return False

    uid_map, chars_by_uid, _skill_mods_by_char = await _load_actor_context(db, sess)
    all_chars = list(chars_by_uid.values())

    if key == "enemies_withdraw":
        _revive_characters_to_1hp(all_chars)
        settings_set(sess, "combat_defeat_effects_applied_for", started_at)
        await add_system_event(db, sess, "☠ Поражение: враги отступили. Вы приходите в себя (1 HP).")
        return True

    if key == "robbed":
        _revive_characters_to_1hp(all_chars)
        if not chars_by_uid:
            return False
        victim_uid = sorted(chars_by_uid.keys())[0]
        victim = chars_by_uid.get(victim_uid)
        if victim is None:
            return False

        inv = _character_inventory_from_stats(victim.stats)
        to_remove = _compute_robbed_removals(inv, max_take=2)
        removed_names: list[str] = []
        for remove_name in to_remove:
            changed, _qty, removed_item = _inv_remove_on_character(victim, name=remove_name, qty=1)
            if not changed:
                continue
            removed_name = str((removed_item or {}).get("name") or remove_name).strip() or remove_name
            removed_names.append(removed_name)

        settings_set(sess, "combat_defeat_effects_applied_for", started_at)
        removed_text = ", ".join(removed_names) if removed_names else "ничего"
        await add_system_event(db, sess, f"☠ Поражение: вас ограбили. Потеряно: {removed_text}.")
        return True

    if key == "captured":
        _revive_characters_to_1hp(all_chars)
        for uid in sorted(uid_map.keys()):
            sp, _pl = uid_map[uid]
            _set_pc_zone(sess, sp.player_id, "prison_cell")
        settings_set(sess, "combat_defeat_effects_applied_for", started_at)
        await add_system_event(db, sess, "☠ Поражение: вас взяли в плен. Вы очнулись в камере (prison_cell).")
        return True

    if key == "rescued":
        _revive_characters_to_1hp(all_chars)
        for uid in sorted(uid_map.keys()):
            sp, _pl = uid_map[uid]
            _set_pc_zone(sess, sp.player_id, "safehouse")
        for uid in sorted(chars_by_uid.keys()):
            ch = chars_by_uid[uid]
            _inv_add_on_character(
                ch,
                name=ITEMS["healing_potion"].name_ru,
                qty=1,
                item_def="healing_potion",
                tags=["rescue"],
                notes="defeat:rescued",
            )
        settings_set(sess, "combat_defeat_effects_applied_for", started_at)
        await add_system_event(
            db,
            sess,
            "☠ Поражение: вас спасли и доставили в убежище (safehouse). Получено: Зелье лечения x1 каждому.",
        )
        return True

    if key == "left_for_dead":
        _apply_left_for_dead_character_state(chars_by_uid)
        for uid in sorted(uid_map.keys()):
            sp, _pl = uid_map[uid]
            _set_pc_zone(sess, sp.player_id, "wilderness_edge")
        settings_set(sess, "combat_defeat_effects_applied_for", started_at)
        await add_system_event(
            db,
            sess,
            "☠ Поражение: вас бросили умирать. Вы приходите в себя на обочине (wilderness_edge).",
        )
        return True

    return False


async def _grant_defeat_outcome_once(
    db: AsyncSession,
    sess: Session,
    patch: dict[str, Any],
) -> bool:
    if not _is_defeat_patch(patch):
        return False

    started_at = _combat_started_at_from_settings(sess)
    if not started_at:
        return False

    if settings_get(sess, "combat_defeat_outcome_for", "") == started_at:
        return False

    outcome_payload = _apply_defeat_outcome_to_settings(sess, started_at)
    await add_system_event(
        db,
        sess,
        f"☠ Поражение. Исход: {outcome_payload['title_ru']}. {outcome_payload['description_ru']}",
    )
    return True


async def _grant_combat_rewards_once(
    db: AsyncSession,
    sess: Session,
    patch: dict[str, Any],
) -> bool:
    if not _is_victory_patch(patch):
        return False

    started_at = _combat_started_at_from_settings(sess)
    if not started_at:
        return False

    if settings_get(sess, "combat_rewards_granted_for", "") == started_at:
        return False

    payload = settings_get(sess, COMBAT_STATE_KEY, None)
    if not isinstance(payload, dict):
        return False

    pc_uids, leader_uid, xp_each, loot_dict = _compute_rewards_from_combat_state_payload(payload)
    _uid_map, chars_by_uid, _skill_mods_by_char = await _load_actor_context(db, sess)

    for uid in pc_uids:
        ch = chars_by_uid.get(uid)
        if ch is None:
            continue
        ch.xp_total = max(0, as_int(ch.xp_total, 0)) + max(0, xp_each)
        ch.level = _level_from_xp_total(ch.xp_total, as_int(ch.level, 1))

    if leader_uid is not None:
        leader_ch = chars_by_uid.get(leader_uid)
        if leader_ch is not None:
            for enemy_id in _enemy_ids_from_combat_state_payload(payload):
                rng = random.Random(zlib.adler32((started_at + ":" + enemy_id).encode("utf-8")))
                drops = roll_loot(enemy_id, rng=rng)
                enemy_loot: dict[str, int] = {}
                for drop in drops:
                    if not isinstance(drop, dict):
                        continue
                    def_key = drop.get("def")
                    if not isinstance(def_key, str) or not def_key:
                        continue
                    qty = max(0, as_int(drop.get("qty"), 0))
                    if qty <= 0:
                        continue
                    enemy_loot[def_key] = enemy_loot.get(def_key, 0) + qty
                for def_key, qty in enemy_loot.items():
                    item = ITEMS[def_key]
                    _inv_add_on_character(
                        leader_ch,
                        name=item.name_ru,
                        qty=qty,
                        item_def=def_key,
                        tags=["loot"],
                        notes=f"combat:{enemy_id}",
                    )

    settings_set(sess, "combat_rewards_granted_for", started_at)

    loot_chunks: list[str] = []
    for def_key, qty in sorted(loot_dict.items()):
        item = ITEMS.get(def_key)
        item_name = item.name_ru if item is not None else def_key
        loot_chunks.append(f"{item_name} x{qty}")
    loot_text = ", ".join(loot_chunks) if loot_chunks else "нет"
    await add_system_event(db, sess, f"🏆 Победа! XP: +{xp_each} каждому. Лут: {loot_text} (лидеру)")
    return True


async def broadcast_state(
    session_id: str,
    combat_log_ui_patch: Optional[dict[str, Any]] = None,
) -> None:
    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            return
        changed = False
        if combat_log_ui_patch is not None:
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
            changed = True
            rewards_granted = await _grant_combat_rewards_once(db, sess, combat_log_ui_patch)
            if rewards_granted:
                changed = True
            defeat_outcome_granted = await _grant_defeat_outcome_once(db, sess, combat_log_ui_patch)
            if defeat_outcome_granted:
                changed = True
            defeat_effects_applied = await _apply_defeat_effects_once(db, sess)
            if defeat_effects_applied:
                changed = True

        changed = _persist_combat_state(sess, session_id) or changed
        if changed:
            await db.commit()
        state = await build_state(db, sess)
    if combat_log_ui_patch is not None:
        state["combat_log_ui_patch"] = combat_log_ui_patch
    await manager.broadcast_json(session_id, state)


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


def _build_turn_draft_prompt(
    session_title: str,
    context_events: list[str],
    actor_uid: Optional[int],
    actors_block: str,
    positions_block: str,
) -> str:
    return gm_contracts.build_turn_draft_prompt(
        session_title=session_title,
        context_events=context_events,
        actor_uid=actor_uid,
        actors_block=actors_block,
        positions_block=positions_block,
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
    return gm_contracts.build_round_draft_prompt(
        session_title=session_title,
        lore_text=lore_text,
        recent_events=recent_events,
        player_actions=player_actions,
        master_notes=master_notes,
        difficulty=difficulty,
        actors_block=actors_block,
        positions_block=positions_block,
    )


def _build_finalize_prompt(draft_text: str, check_results: list[dict[str, Any]]) -> str:
    return gm_contracts.build_finalize_prompt(draft_text=draft_text, check_results=check_results)


async def _run_gm_two_pass(
    db: AsyncSession,
    sess: Session,
    session_id: str,
    *,
    draft_prompt: str,
    default_actor_uid: Optional[int],
    previous_gm_text: str = "",
) -> tuple[str, dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    settings = _ensure_settings(sess)
    location_fallback = narration.build_location_block(settings, session_id)
    combat_state = get_combat(session_id)
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
        load_actor_context=_load_actor_context,
        compute_check_mod=_compute_check_mod,
        roll_check=_roll_check,
        build_check_result=_build_check_result,
        character_xp_gain_from_check=_character_xp_gain_from_check,
        level_from_xp_total=_level_from_xp_total,
        skill_xp_gain=_skill_xp_gain,
        xp_to_next_skill_rank=_xp_to_next_skill_rank,
        clamp_fn=_clamp,
        as_int_fn=as_int,
        get_phase_fn=_get_phase,
        trim_for_log_fn=_trim_for_log,
        looks_like_combat_drift_fn=_looks_like_combat_drift,
        llm_generate=generate_from_prompt,
        logger=logger,
    )


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
                gm_text, _draft_meta, _final_meta, _checks, _check_results = await _run_gm_two_pass(
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

        await broadcast_state(session_id, combat_log_ui_patch=combat_log_ui_patch)
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
                gm_text, _draft_meta, _final_meta, _checks, _check_results = await _run_gm_two_pass(
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

        await broadcast_state(session_id, combat_log_ui_patch=combat_log_ui_patch)
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
        await send_state_to_ws(session_id, ws)

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
                _maybe_restore_combat_state(sess, session_id)

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

                if action.startswith("admin_combat_test_"):
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can run combat UI test")
                        continue
                    combat_patch, combat_err = handle_admin_combat_test_action(action, session_id)
                    if combat_err:
                        await ws_error(combat_err)
                        continue
                    if combat_patch is not None:
                        await broadcast_state(session_id, combat_log_ui_patch=combat_patch)
                        continue

                if action == "admin_combat_live_start":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can run live combat")
                        continue
                    before_state = get_combat(session_id)
                    before_active = bool(before_state and before_state.active)
                    # If a previous combat is still active (often due to persisted restore),
                    # hard-reset it so @@COMBAT_START is not ignored and we always start from round 1.
                    if before_active:
                        end_combat(session_id)
                        before_state = None
                        before_active = False
                    bootstrap_zone = "arena"
                    bootstrap_enemies = [
                        {"id": "band1", "name": "Разбойник", "hp": 18, "ac": 13, "init_mod": 2, "threat": 2},
                    ]
                    settings_set(
                        sess,
                        "combat_live_bootstrap",
                        {
                            "zone": bootstrap_zone,
                            "enemies": bootstrap_enemies,
                        },
                    )
                    if sess.is_paused:
                        sess.is_paused = False
                        _clear_paused_remaining(sess)
                        if sess.current_player_id and not sess.turn_started_at:
                            sess.turn_started_at = utcnow()
                    await db.commit()
                    gm_text = (
                        f'@@COMBAT_START(zone="{bootstrap_zone}", cause="admin")\n'
                        '@@COMBAT_ENEMY_ADD(id=band1, name="Разбойник", hp=18, ac=13, init_mod=2, threat=2)'
                    )
                    combat_patch = apply_combat_machine_commands(session_id, gm_text)
                    uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                    sync_pcs_from_chars(session_id, chars_by_uid)
                    if combat_patch is None:
                        combat_patch = {
                            "reset": True,
                            "open": True,
                            "lines": [{"text": "Live бой запущен админом.", "muted": True}],
                        }
                    combat_state = get_combat(session_id)
                    after_active = bool(combat_state and combat_state.active)
                    if after_active and combat_state is not None and combat_state.active:
                        preamble_lines = _build_combat_start_preamble_lines(
                            player=player,
                            chars_by_uid=chars_by_uid,
                            combat_state=combat_state,
                        )
                        if not isinstance(combat_patch, dict):
                            combat_patch = {}
                        patch_lines = combat_patch.get("lines")
                        already = False
                        if isinstance(patch_lines, list):
                            for it in patch_lines:
                                t = None
                                if isinstance(it, dict):
                                    t = it.get("text")
                                elif isinstance(it, str):
                                    t = it
                                if isinstance(t, str) and (
                                    t.startswith("Бой начался между") or t.startswith("Добавлен в бой:")
                                ):
                                    already = True
                                    break
                        if preamble_lines and not already:
                            combat_patch = _append_combat_patch_lines(combat_patch, preamble_lines, prepend=True)
                        combat_patch["reset"] = True
                    if combat_state is not None and combat_state.active:
                        if combat_patch.get("reset") is True:
                            combat_state.round_no = 1
                            combat_state.turn_index = 0
                        combat_patch["status"] = (
                            f"⚔ Бой • Раунд {combat_state.round_no} • Ход: {current_turn_label(combat_state)}"
                        )
                    await broadcast_state(session_id, combat_log_ui_patch=combat_patch)
                    continue

                if action == "admin_combat_live_end":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can end live combat")
                        continue
                    end_combat(session_id)
                    await broadcast_state(
                        session_id,
                        combat_log_ui_patch={
                            "status": "Бой завершён",
                            "open": False,
                            "lines": [{"text": "Live бой завершён админом.", "muted": True}],
                        },
                    )
                    continue

                if action == "combat_log_clear":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can clear combat log")
                        continue
                    state = get_combat(session_id)
                    lines = [{"text": "Журнал очищен.", "muted": True}]
                    if state is not None and state.active:
                        lines.append(
                            {
                                "text": f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}",
                                "muted": True,
                                "kind": "status",
                            }
                        )
                    patch = {"reset": True, "open": True, "lines": lines}
                    await broadcast_state(session_id, combat_log_ui_patch=patch)
                    continue

                if action in {
                    "combat_attack",
                    "combat_end_turn",
                    "combat_dodge",
                    "combat_dash",
                    "combat_disengage",
                    "combat_escape",
                    "combat_use_object",
                    "combat_help",
                }:
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can use combat actions")
                        continue
                    combat_patch, combat_err = handle_live_combat_action(action, session_id)
                    if combat_err:
                        await ws_error(combat_err)
                        continue
                    if combat_patch:
                        await broadcast_state(session_id, combat_log_ui_patch=combat_patch)
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

                combat_action = _detect_chat_combat_action(text)
                _maybe_restore_combat_state(sess, session_id)
                combat_state = get_combat(session_id)
                if combat_state is None:
                    bootstrap = settings_get(sess, "combat_live_bootstrap", None)
                    if isinstance(bootstrap, dict):
                        zone_raw = str(bootstrap.get("zone") or "arena").strip() or "arena"
                        zone = zone_raw.replace('"', '\\"')
                        enemies = bootstrap.get("enemies")
                        if isinstance(enemies, list):
                            lines = [f'@@COMBAT_START(zone="{zone}", cause="bootstrap")']
                            for enemy in enemies:
                                if not isinstance(enemy, dict):
                                    continue
                                enemy_id = str(enemy.get("id") or "").strip()
                                enemy_name = str(enemy.get("name") or "").strip()
                                if not enemy_id or not enemy_name:
                                    continue
                                enemy_id_escaped = enemy_id.replace('"', '\\"')
                                enemy_name_escaped = enemy_name.replace('"', '\\"')
                                hp = max(1, as_int(enemy.get("hp"), 1))
                                ac = max(1, as_int(enemy.get("ac"), 10))
                                init_mod = as_int(enemy.get("init_mod"), 0)
                                threat = max(0, as_int(enemy.get("threat"), 1))
                                lines.append(
                                    f'@@COMBAT_ENEMY_ADD(id={enemy_id_escaped}, name="{enemy_name_escaped}", '
                                    f"hp={hp}, ac={ac}, init_mod={init_mod}, threat={threat})"
                                )
                            if len(lines) > 1:
                                gm_text = "\n".join(lines)
                                before_state = get_combat(session_id)
                                before_active = bool(before_state and before_state.active)
                                combat_patch = apply_combat_machine_commands(session_id, gm_text)
                                uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                                sync_pcs_from_chars(session_id, chars_by_uid)
                                combat_state = get_combat(session_id)
                                after_active = bool(combat_state and combat_state.active)
                                if after_active and combat_state is not None and combat_state.active:
                                    preamble_lines = _build_combat_start_preamble_lines(
                                        player=player,
                                        chars_by_uid=chars_by_uid,
                                        combat_state=combat_state,
                                    )
                                    if not isinstance(combat_patch, dict):
                                        combat_patch = {}
                                    patch_lines = combat_patch.get("lines")
                                    already = False
                                    if isinstance(patch_lines, list):
                                        for it in patch_lines:
                                            t = None
                                            if isinstance(it, dict):
                                                t = it.get("text")
                                            elif isinstance(it, str):
                                                t = it
                                            if isinstance(t, str) and (
                                                t.startswith("Бой начался между") or t.startswith("Добавлен в бой:")
                                            ):
                                                already = True
                                                break
                                    if preamble_lines and not already:
                                        combat_patch = _append_combat_patch_lines(combat_patch, preamble_lines, prepend=True)
                                    combat_patch["reset"] = True
                                    combat_patch["open"] = True
                                    combat_patch["status"] = (
                                        f"⚔ Бой • Раунд {combat_state.round_no} • Ход: {current_turn_label(combat_state)}"
                                    )
                                    await broadcast_state(session_id, combat_log_ui_patch=combat_patch)
                combat_active = bool(combat_state and combat_state.active)
                start_intent = ("войти в бой" in lower) or lower.startswith("бой с") or ("начать бой" in lower)

                if start_intent and combat_active:
                    await ws_error("Бой уже идёт.")
                    continue

                if start_intent and not combat_active:
                    actor_label = await _event_actor_label(db, sess, player)
                    await add_event(
                        db,
                        sess,
                        f"{actor_label}: {text}",
                        actor_player_id=player.id,
                        result_json={
                            "type": "player_action",
                            "raw_text": text,
                            "combat_chat_action": "start",
                        },
                    )
                    await db.commit()

                    enemy_name = "Разбойник" if "разбойник" in lower else ""
                    if not enemy_name:
                        enemy_match = re.search(r"бой с\s+([^\n,.;:!?]+)", lower, flags=re.IGNORECASE)
                        if enemy_match:
                            enemy_raw = enemy_match.group(1).strip(" \"'`")
                            if enemy_raw:
                                enemy_name = enemy_raw[:40].strip()
                    if not enemy_name:
                        enemy_name = "Разбойник"
                    enemy_name = enemy_name[0].upper() + enemy_name[1:] if enemy_name else "Разбойник"

                    enemy_name_escaped = enemy_name.replace('"', '\\"')
                    gm_text = (
                        '@@COMBAT_START(zone="arena", cause="bootstrap")\n'
                        f'@@COMBAT_ENEMY_ADD(id=band1, name="{enemy_name_escaped}", hp=18, ac=13, init_mod=2, threat=2)'
                    )
                    combat_patch = apply_combat_machine_commands(session_id, gm_text)
                    _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                    sync_pcs_from_chars(session_id, chars_by_uid)
                    combat_state = get_combat(session_id)
                    if combat_patch is None:
                        combat_patch = {}
                    if combat_state and combat_state.active:
                        preamble_lines = _build_combat_start_preamble_lines(
                            player=player,
                            chars_by_uid=chars_by_uid,
                            combat_state=combat_state,
                        )
                        patch_lines = combat_patch.get("lines")
                        already = False
                        if isinstance(patch_lines, list):
                            for it in patch_lines:
                                t = None
                                if isinstance(it, dict):
                                    t = it.get("text")
                                elif isinstance(it, str):
                                    t = it
                                if isinstance(t, str) and (
                                    t.startswith("Бой начался между") or t.startswith("Добавлен в бой:")
                                ):
                                    already = True
                                    break
                        if preamble_lines and not already:
                            combat_patch = _append_combat_patch_lines(combat_patch, preamble_lines, prepend=True)

                    combat_patch["reset"] = True
                    combat_patch["open"] = True
                    if combat_state and combat_state.active:
                        combat_patch["status"] = (
                            f"⚔ Бой • Раунд {combat_state.round_no} • Ход: {current_turn_label(combat_state)}"
                        )
                    await broadcast_state(session_id, combat_log_ui_patch=combat_patch)

                    ch = await get_character(db, sess.id, player.id)
                    player_name = (ch.name if ch and ch.name else player.display_name)
                    facts_block = await _build_combat_scene_facts_for_llm(
                        db,
                        sess,
                        player,
                        enemy_name=enemy_name,
                        max_lines=10,
                    )
                    prompt = (
                        f"{_COMBAT_LOCK_PROMPT}\n\n"
                        "ЗАПРЕЩЕНО ДОБАВЛЯТЬ НОВЫЕ СУЩНОСТИ:\n"
                        "- никаких новых NPC (никаких 'человек', 'парень', 'толпа', 'стражник' и т.п.)\n"
                        "- никаких новых предметов/оружия/именованных артефактов\n"
                        "- можно упоминать оружие/предметы только если они есть в фактах сцены или в действии игрока\n"
                        "Разрешено только:\n"
                        "- ты\n"
                        f"- {enemy_name}\n"
                        "- нейтральное окружение (улица/двор/пыль/камни/фонари) без новых персонажей\n\n"
                        "Сейчас идёт бой. Напиши вступление к схватке здесь и сейчас.\n"
                        "Правила (строго):\n"
                        "- Только бой здесь и сейчас.\n"
                        "- НЕЛЬЗЯ: числа, кубики, HP, AC, урон, раунды, ходы, формулы.\n"
                        "- 8-12 предложений, ровно 1 абзац.\n"
                        "- Динамично, но без деталей инвентаря.\n"
                        "- Пиши во 2 лице: 'ты'.\n"
                        "- Герой текущего игрока всегда 'ты'. Нельзя писать про героя в 3-м лице по имени (запрещено 'Валерикус делает/устает/падает'). Имя героя можно упомянуть максимум 1 раз только как уточнение-метку, например: 'ты (Валерикус)...'.\n"
                        "- Нельзя упоминать броню/экипировку/оружие, если этого нет в фактах или в действии игрока.\n"
                        "- Последняя строка строго: Что делаете дальше?\n\n"
                        f"Факты сцены (не выдумывать сверх этого):\n{facts_block}\n\n"
                        f"Контекст: Ты вступаешь в бой с {enemy_name}. "
                        f"Имя героя (для ориентира): {player_name}\n"
                    )
                    resp = await generate_from_prompt(
                        prompt=prompt,
                        timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
                        num_predict=GM_FINAL_NUM_PREDICT,
                    )
                    gm_text = _sanitize_gm_output(_strip_machine_lines(str(resp.get("text") or "").strip()))
                    gm_text = re.sub(r"(?im)^\s*@@COMBAT_[A-Z_]+.*$", "", gm_text).strip()

                    has_mechanics = bool(
                        re.search(r"(?:\d|\bd20\b|\bhp\b|\bac\b|урон|бросок|раунд|ход)", gm_text, flags=re.IGNORECASE)
                    )
                    has_forbidden_gear = _combat_text_mentions_forbidden_gear(
                        gm_text,
                        action_text=text,
                        facts_block=facts_block,
                    )
                    has_markers = _has_start_intent_sanitary_markers(gm_text)
                    needs_repair = _start_intent_text_needs_repair(gm_text)
                    if has_markers or has_forbidden_gear or needs_repair:
                        reprompt = (
                            f"{prompt}\n"
                            "Перепиши расширенно на 8–12 предложений, 1 абзац. "
                            "Герой игрока всегда 'ты': не пиши про героя в 3-м лице по имени; имя можно упомянуть максимум 1 раз как метку вида 'ты (Имя)'. "
                            "Запрещено: броня/экипировка/оружие, если этого нет в фактах или в действии игрока. "
                            "Никаких новых сущностей. Только здесь-и-сейчас.\n"
                            f"Черновик для переписывания:\n{gm_text}\n"
                        )
                        repair_resp = await generate_from_prompt(
                            prompt=reprompt,
                            timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
                            num_predict=GM_FINAL_NUM_PREDICT,
                        )
                        gm_text = _sanitize_gm_output(_strip_machine_lines(str(repair_resp.get("text") or "").strip()))
                        gm_text = re.sub(r"(?im)^\s*@@COMBAT_[A-Z_]+.*$", "", gm_text).strip()
                        has_mechanics = bool(
                            re.search(r"(?:\d|\bd20\b|\bhp\b|\bac\b|урон|бросок|раунд|ход)", gm_text, flags=re.IGNORECASE)
                        )
                        has_markers = _has_start_intent_sanitary_markers(gm_text)
                        has_forbidden_gear = _combat_text_mentions_forbidden_gear(
                            gm_text,
                            action_text=text,
                            facts_block=facts_block,
                        )
                        needs_repair = _start_intent_text_needs_repair(gm_text)
                    if (
                        not gm_text
                        or has_mechanics
                        or _looks_like_combat_drift(gm_text)
                        or has_markers
                        or has_forbidden_gear
                        or needs_repair
                    ):
                        gm_text = START_INTENT_FALLBACK_TEXT

                    await add_system_event(db, sess, f"🧙 GM: {gm_text}")
                    await db.commit()
                    await broadcast_state(session_id)
                    continue

                phase_now = _get_phase(sess)
                if phase_now == "lore_pending":
                    await ws_error("Ждём вступительную историю...")
                    continue
                if phase_now == "gm_pending" and not combat_active:
                    await ws_error("Ждём ответа мастера...")
                    continue

                # Combat Lock: during active combat only combat actions are allowed.
                if combat_active:
                    is_admin_user = await is_admin(db, sess, player)
                    if lower.startswith("ooc ") or cmdline.startswith("//"):
                        pass
                    elif (lower.startswith("gm ") or lower.startswith("gm:")) and is_admin_user:
                        pass
                    elif combat_action:
                        actor_label = await _event_actor_label(db, sess, player)
                        await add_event(
                            db,
                            sess,
                            f"{actor_label}: {text}",
                            actor_player_id=player.id,
                            result_json={
                                "type": "player_action",
                                "raw_text": text,
                                "combat_chat_action": combat_action,
                            },
                        )
                        await db.commit()

                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        turn_key: Optional[str] = None
                        if combat_state and combat_state.order and 0 <= combat_state.turn_index < len(combat_state.order):
                            turn_key = combat_state.order[combat_state.turn_index]
                        if not turn_key or turn_key != player_key:
                            current_name = current_turn_label(combat_state) if combat_state else "другой участник"
                            await add_system_event(db, sess, f"Сейчас ходит {current_name}. Дождись своего хода.")
                            await broadcast_state(session_id)
                            continue

                        all_patches: list[dict[str, Any]] = []
                        combat_patch, combat_err = handle_live_combat_action(combat_action, session_id)
                        if combat_err:
                            await ws_error(combat_err, request_id=msg_request_id)
                            continue
                        if combat_patch:
                            all_patches.append(combat_patch)

                        while True:
                            state_now = get_combat(session_id)
                            if not state_now or not state_now.active or not state_now.order:
                                break
                            if state_now.turn_index < 0 or state_now.turn_index >= len(state_now.order):
                                break
                            turn_key_now = state_now.order[state_now.turn_index]
                            turn_actor = state_now.combatants.get(turn_key_now)
                            if not turn_actor or turn_actor.side != "enemy":
                                break
                            enemy_patch, enemy_err = handle_live_combat_action("combat_attack", session_id)
                            if enemy_err:
                                logger.warning("enemy auto combat action failed", extra={"action": {"error": enemy_err}})
                                break
                            if enemy_patch:
                                all_patches.append(enemy_patch)

                        merged_patch = _merge_combat_patches(all_patches) if all_patches else None
                        await broadcast_state(session_id, combat_log_ui_patch=merged_patch)
                        facts = extract_combat_narration_facts(merged_patch)
                        if facts:
                            required_fact_count = 3 if len(facts) >= 3 else len(facts)
                            player_raw_action = str(text or "").strip()
                            ch = await get_character(db, sess.id, player.id)
                            player_name = (ch.name if ch and ch.name else player.display_name)
                            ended = any("бой заверш" in f.lower() or "победа" in f.lower() for f in facts)
                            enemy_name_for_facts = "противник"
                            state_for_facts = get_combat(session_id)
                            if state_for_facts and isinstance(state_for_facts.combatants, dict):
                                for actor in state_for_facts.combatants.values():
                                    if str(getattr(actor, "side", "")).lower() != "enemy":
                                        continue
                                    actor_name = str(getattr(actor, "name", "") or "").strip()
                                    if actor_name:
                                        enemy_name_for_facts = actor_name
                                        break
                            scene_facts_block = await _build_combat_scene_facts_for_llm(
                                db,
                                sess,
                                player,
                                enemy_name=enemy_name_for_facts,
                                max_lines=10,
                            )
                            if not str(scene_facts_block or "").strip():
                                scene_facts_block = "- Зона игрока: место рядом с тобой\n- Окружение: место рядом с тобой."
                            text = await gm_combat_narration.generate_combat_narration_from_facts(
                                combat_lock_prompt=_COMBAT_LOCK_PROMPT,
                                facts=facts,
                                required_fact_count=required_fact_count,
                                scene_facts_block=scene_facts_block,
                                player_raw_action=_short_text(player_raw_action, 180),
                                player_name=player_name,
                                ended=ended,
                                timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
                                num_predict=GM_FINAL_NUM_PREDICT,
                                mentions_forbidden_gear_fn=lambda candidate_text: _combat_text_mentions_forbidden_gear(
                                    candidate_text,
                                    action_text=player_raw_action,
                                    facts_block=scene_facts_block,
                                ),
                            )
                            if text:
                                await add_system_event(
                                    db,
                                    sess,
                                    f"🧙 GM: {text}",
                                    result_json={"type": "combat_narration", "facts": facts},
                                )
                                await db.commit()
                                await broadcast_state(session_id)
                        continue
                    else:
                        await ws_error(
                            "Combat Lock: в бою доступны только боевые команды (атака/конец хода/уклон/рывок/отход/помощь/побег) или OOC.",
                            request_id=msg_request_id,
                        )
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
                    while idx < len(parts) and not parts[idx].lower().startswith("dc"):
                        key += f" {parts[idx].lower()}"
                        idx += 1
                    key = _normalize_check_name(key)
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

                    def _manual_candidate_mod(candidate: str, skills_by_key: dict[str, Skill]) -> int:
                        if candidate in CHAR_STAT_KEYS:
                            return _ability_mod_from_stats(ch.stats, candidate)
                        ability_key = SKILL_TO_ABILITY.get(candidate)
                        ability_mod = _ability_mod_from_stats(ch.stats, ability_key) if ability_key else 0
                        sk = skills_by_key.get(candidate)
                        skill_bonus = _skill_bonus_from_rank(sk.rank) if sk else 0
                        return ability_mod + skill_bonus

                    skills_by_key: dict[str, Skill] = {}
                    if "|" in key:
                        candidates = [x.strip() for x in key.split("|") if x.strip()]
                        if not candidates:
                            mod = 0
                        else:
                            skill_candidates = [c for c in candidates if c not in CHAR_STAT_KEYS]
                            if skill_candidates:
                                q_skills = await db.execute(
                                    select(Skill).where(
                                        Skill.character_id == ch.id,
                                        Skill.skill_key.in_(skill_candidates),
                                    )
                                )
                                skills_by_key = {str(sk.skill_key or "").strip().lower(): sk for sk in q_skills.scalars().all()}
                            mod = max(_manual_candidate_mod(c, skills_by_key) for c in candidates)
                    elif key in CHAR_STAT_KEYS:
                        mod = _ability_mod_from_stats(ch.stats, key)
                    else:
                        q_skill = await db.execute(
                            select(Skill).where(
                                Skill.character_id == ch.id,
                                Skill.skill_key == key,
                            )
                        )
                        sk = q_skill.scalar_one_or_none()
                        ability_key = SKILL_TO_ABILITY.get(key)
                        ability_mod = _ability_mod_from_stats(ch.stats, ability_key) if ability_key else 0
                        skill_bonus = _skill_bonus_from_rank(sk.rank) if sk else 0
                        mod = ability_mod + skill_bonus

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

                if combat_active:
                    actor_label = await _event_actor_label(db, sess, player)
                    pid = str(player.id)
                    current_zone = _get_pc_positions(sess).get(pid, "стартовая локация")
                    new_zone_preview = current_zone
                    payload = {
                        "type": "player_action",
                        "actor_uid": _player_uid(player),
                        "actor_player_id": str(player.id),
                        "join_order": int(sp.join_order or 0),
                        "raw_text": text,
                        "mode": "free_turns" if _is_free_turns(sess) else "turns",
                        "phase": _get_phase(sess),
                        "zone_before": current_zone,
                        "zone_after": new_zone_preview,
                        "turn_index": int(sess.turn_index or 0),
                        "combat_chat_action": combat_action,
                    }
                    await add_event(
                        db,
                        sess,
                        f"{actor_label}: {text}",
                        actor_player_id=player.id,
                        result_json=payload,
                    )
                    await db.commit()
                    await broadcast_state(session_id)

                    if combat_action:
                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        turn_key: Optional[str] = None
                        if combat_state and combat_state.order and 0 <= combat_state.turn_index < len(combat_state.order):
                            turn_key = combat_state.order[combat_state.turn_index]
                        if not turn_key or turn_key != player_key:
                            current_name = current_turn_label(combat_state) if combat_state else "другой участник"
                            await add_system_event(db, sess, f"Сейчас ходит {current_name}. Дождись своего хода.")
                            await broadcast_state(session_id)
                            continue

                        all_patches: list[dict[str, Any]] = []
                        outcome_summary: list[str] = []
                        combat_patch, combat_err = handle_live_combat_action(combat_action, session_id)
                        if combat_err:
                            await ws_error(combat_err)
                            continue
                        if combat_patch:
                            all_patches.append(combat_patch)
                            outcome_summary.extend(_combat_outcome_summary_from_patch(combat_action, combat_patch))

                        while True:
                            state_now = get_combat(session_id)
                            if not state_now or not state_now.active or not state_now.order:
                                break
                            if state_now.turn_index < 0 or state_now.turn_index >= len(state_now.order):
                                break
                            turn_key_now = state_now.order[state_now.turn_index]
                            turn_actor = state_now.combatants.get(turn_key_now)
                            if not turn_actor or turn_actor.side != "enemy":
                                break
                            enemy_patch, enemy_err = handle_live_combat_action("combat_attack", session_id)
                            if enemy_err:
                                logger.warning("enemy auto combat action failed", extra={"action": {"error": enemy_err}})
                                break
                            if enemy_patch:
                                all_patches.append(enemy_patch)
                                outcome_summary.extend(_combat_outcome_summary_from_patch("combat_attack", enemy_patch))

                        state_after_actions = get_combat(session_id)
                        if state_after_actions is None:
                            # Keep combat_live_bootstrap in settings until explicit reset
                            # (admin_combat_live_end or a dedicated reset command).
                            pass

                        merged_patch = _merge_combat_patches(all_patches) if all_patches else None
                        await broadcast_state(session_id, combat_log_ui_patch=merged_patch)
                        state_for_prompt = state_after_actions
                        story = settings_get(sess, "story", {}) or {}
                        if not isinstance(story, dict):
                            story = {}
                        campaign_title = str(story.get("story_title") or "").strip() or str(sess.title or "Campaign").strip() or "Campaign"
                        turn_label = current_turn_label(state_for_prompt) if state_for_prompt else "-"
                        participants_block = _combat_participants_block(state_for_prompt)
                        ch = await get_character(db, sess.id, player.id)
                        meta = _character_meta_from_stats(ch.stats) if ch else {"gender": "", "race": "", "description": ""}
                        actor_gender = meta["gender"]
                        actor_pronouns = _gender_to_pronouns(actor_gender) or "unknown"
                        actor_name = str(ch.name).strip() if ch and str(ch.name or "").strip() else actor_label
                        gm_text = await _generate_combat_narration(
                            campaign_title=campaign_title,
                            outcome_summary=outcome_summary,
                            player_action=combat_action,
                            current_turn=turn_label,
                            participants_block=participants_block,
                            actor_name=actor_name,
                            actor_gender=actor_gender,
                            actor_pronouns=actor_pronouns,
                        )
                        await add_system_event(
                            db,
                            sess,
                            f"🧙 GM: {gm_text}",
                            result_json={
                                "type": "combat_chat_gm_reply",
                                "combat_action": combat_action,
                                "combat_summary": outcome_summary,
                            },
                        )
                        await broadcast_state(session_id)
                        continue

                    player_uid = _player_uid(player)
                    player_key = f"pc_{player_uid}" if player_uid is not None else ""
                    state_now = get_combat(session_id)
                    turn_key_now = ""
                    if state_now and state_now.order and 0 <= state_now.turn_index < len(state_now.order):
                        turn_key_now = state_now.order[state_now.turn_index]
                    if not turn_key_now or turn_key_now != player_key:
                        current_name = current_turn_label(state_now) if state_now else "другой участник"
                        await add_system_event(db, sess, f"Сейчас ходит {current_name}. Дождись своего хода.")
                        await broadcast_state(session_id)
                        continue

                    already_sent = await _combat_clarify_already_sent(db, sess, msg_request_id)
                    settings = sess.settings if isinstance(sess.settings, dict) else {}
                    if not isinstance(sess.settings, dict):
                        sess.settings = settings
                    marker_player_key = player_key or f"player_{player.id}"
                    marker = f"{turn_key_now}:{marker_player_key}"
                    previous_marker = str(settings.get("combat_clarify_marker") or "")
                    if marker != previous_marker and not already_sent:
                        settings["combat_clarify_marker"] = marker
                        flag_modified(sess, "settings")
                        await db.commit()
                        await add_system_event(
                            db,
                            sess,
                            COMBAT_CLARIFY_TEXT,
                            result_json={
                                "type": "combat_chat_gm_reply",
                                "combat_action": None,
                                "combat_summary": ["Схватка продолжается в текущем темпе."],
                                "request_id": str(msg_request_id or ""),
                            },
                        )
                        await broadcast_state(session_id)
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

                    gm_action_text, _moved, _encounter_patch = await _build_player_gm_action_text(
                        db,
                        sess,
                        session_id,
                        text,
                        include_encounter_after_move=False,
                    )
                    round_actions[pid] = gm_action_text
                    settings_set(sess, "round_actions", round_actions)
                    current_zone = _get_pc_positions(sess).get(pid, "стартовая локация")
                    new_zone = infer_zone_from_action(text, current_zone)
                    _set_pc_zone(sess, player.id, new_zone)
                    actor_label = await _event_actor_label(db, sess, player)
                    payload = {
                        "type": "player_action",
                        "actor_uid": _player_uid(player),
                        "actor_player_id": str(player.id),
                        "join_order": int(sp.join_order or 0),
                        "raw_text": gm_action_text,
                        "mode": "free_turns",
                        "phase": phase,
                        "zone_before": current_zone,
                        "zone_after": new_zone,
                        "turn_index": int(sess.turn_index or 0),
                        "combat_chat_action": combat_action,
                    }
                    await add_event(
                        db,
                        sess,
                        f"{actor_label}: {text}",
                        actor_player_id=player.id,
                        result_json=payload,
                    )
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
                pid = str(player.id)
                phase = _get_phase(sess)
                current_zone = _get_pc_positions(sess).get(pid, "стартовая локация")
                new_zone = infer_zone_from_action(text, current_zone)
                _set_pc_zone(sess, player.id, new_zone)
                gm_action_text, _moved, encounter_patch = await _build_player_gm_action_text(
                    db,
                    sess,
                    session_id,
                    text,
                    include_encounter_after_move=True,
                )
                payload = {
                    "type": "player_action",
                    "actor_uid": _player_uid(player),
                    "actor_player_id": str(player.id),
                    "join_order": int(sp.join_order or 0),
                    "raw_text": gm_action_text,
                    "mode": "free_turns" if _is_free_turns(sess) else "turns",
                    "phase": phase,
                    "zone_before": current_zone,
                    "zone_after": new_zone,
                    "turn_index": int(sess.turn_index or 0),
                    "combat_chat_action": combat_action,
                }
                await add_event(
                    db,
                    sess,
                    f"{actor_label}: {text}",
                    actor_player_id=player.id,
                    result_json=payload,
                )
                action_id = _new_action_id()
                _set_current_action_id(sess, action_id)
                _set_phase(sess, "gm_pending")
                sess.turn_started_at = None
                await db.commit()
                await add_system_event(db, sess, "Мастер обрабатывает действие...")
                await broadcast_state(session_id, combat_log_ui_patch=encounter_patch)
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
