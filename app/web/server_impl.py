import asyncio
import json
import logging
import os
import random
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import uuid
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request

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
from app.rules.equipment_slots import EquipmentSlot, EQUIPMENT_SLOT_ORDER, slot_label_ru
from app.rules.item_catalog import ITEMS
from app.rules.items import ItemDef, is_equipable, can_equip_to_slot
from app.web.dice import parse_dice, roll_dice
from app.web.machine_extract import _trim_for_log, _extract_inventory_machine_commands, _extract_machine_commands
from app.web.machine_lines import (
    _parse_machine_value,
    _split_machine_args,
    _strip_machine_lines,
)
from app.web.session_lock import get_session_lock
from app.web.session_state import (
    _ensure_settings,
    settings_get,
    settings_set,
    _get_ready_map,
    _set_ready,
    _get_init_map,
    _set_init_value,
    _initiative_fixed,
    _get_initiative_order,
    _set_initiative_order,
    _get_last_seen_map,
    _touch_last_seen,
    _get_pc_positions,
    _set_pc_zone,
    _initialize_pc_positions,
    _get_phase,
    _set_phase,
)
from app.web.constants import COMBAT_LOG_HISTORY_KEY, COMBAT_STATE_KEY, MAX_COMBAT_LOG_LINES
from app.web.combat_bridge import (
    _append_combat_patch_lines,
    _build_combat_start_preamble_lines,
    _combat_outcome_summary_from_patch,
    _combat_participants_block,
    _generate_combat_narration,
    _maybe_apply_opening_combat_action,
    _merge_combat_patches,
)
from app.web.state_builder import build_state, broadcast_state, _broadcast_state_unlocked, send_state_to_ws
from app.web.inventory_helpers import (
    _normalize_inventory_def,
    _normalize_inventory_item,
    _parse_inventory_text,
    _normalize_inventory_payload,
    _character_inventory_from_stats,
    _put_character_inventory_into_stats,
    _character_equip_from_stats,
    _put_character_equip_into_stats,
    _item_def_for_inventory_entry,
    _equipped_wear_groups,
    _find_inventory_item_index,
    _inv_add_on_character,
    _inv_remove_on_character,
    _inventory_state_line,
    _inventory_prompt_line,
    _equip_state_line,
)
from app.web.utils import as_int, _clamp, _short_text, _slugify_inventory_id
from app.web.watchers import inactive_watcher, timer_watcher
from app.web.regexes import (
    CHAT_COMBAT_ACTION_PATTERNS,
    COMBAT_MECHANICS_EVENT_RE,
    ZONE_MOVE_RE,
)
from app.web import gm_orchestrator
from app.web.combat_helpers import _combat_participant_line, _de_numberize_text, _hit_force_label, _hp_state_label
from app.web.db_helpers import get_or_create_player_web, get_player_by_uid, get_session, list_session_players
from app.web.gameplay_helpers import (
    CHAR_DEFAULT_STATS,
    CHAR_STAT_KEYS,
    CLASS_PRESETS,
    DEFAULT_TIMEZONE,
    GM_FINAL_NUM_PREDICT,
    GM_OLLAMA_TIMEOUT_SECONDS,
    _char_to_payload,
    _character_meta_from_stats,
    _get_kicked,
    _looks_like_refusal,
    _normalize_story_config,
    _put_character_meta_into_stats,
    _resolve_character_stats,
    _stats_points_used,
    _story_is_configured,
    _upsert_starter_skills,
    add_event,
    add_system_event,
    create_character,
    get_character,
    is_admin,
)
from app.web.http_routes import router as http_router


TURN_TIMEOUT_SECONDS = int(os.getenv("TURN_TIMEOUT_SECONDS", "300"))
ENABLE_WATCHERS = os.getenv("ENABLE_WATCHERS", "1") not in ("0", "false", "False")
GM_CONTEXT_EVENTS = max(1, int(os.getenv("GM_CONTEXT_EVENTS", "20")))
GM_DRAFT_NUM_PREDICT = max(200, int(os.getenv("GM_DRAFT_NUM_PREDICT", "1000")))
logger = logging.getLogger("app.web.server")
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
STATE_COMMAND_ALIASES = {"state", "inv", "инв", "inventory"}


def utcnow() -> datetime:
    return datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    from app.web.deploy_guard import ensure_single_worker

    ensure_single_worker()
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
app.include_router(http_router)


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


# -------------------------
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
    from app.web.ws_checks import _ability_mod_from_stats as _ws_ability_mod_from_stats

    return _ws_ability_mod_from_stats(stats_raw, stat_key)


def _skill_bonus_from_rank_and_level(rank_raw: Any, level_raw: Any) -> int:
    from app.web.ws_checks import _skill_bonus_from_rank_and_level as _ws_skill_bonus_from_rank_and_level

    return _ws_skill_bonus_from_rank_and_level(rank_raw, level_raw)


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


def _format_state_text_for_player(sess: Session, player: Player, ch: Optional[Character]) -> str:
    zone = _get_pc_positions(sess).get(str(player.id), "стартовая локация")
    char_name = str(ch.name).strip() if ch and str(ch.name or "").strip() else "(персонаж не создан)"
    hp_sta = "HP/STA: —"
    if ch:
        hp_sta = f"HP {as_int(ch.hp, 0)}/{as_int(ch.hp_max, 0)} | STA {as_int(ch.sta, 0)}/{as_int(ch.sta_max, 0)}"
    equip_line = _equip_state_line(ch)
    inv_line = _inventory_state_line(ch)
    return f"Состояние: {char_name}\nЗона: {zone}\n{hp_sta}\nОдето: {equip_line}\nИнвентарь: {inv_line}"


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
    levels_by_char_id = {ch.id: ch.level for ch in chars}
    char_ids = [ch.id for ch in chars]
    if char_ids:
        q_skills = await db.execute(select(Skill).where(Skill.character_id.in_(char_ids)))
        for sk in q_skills.scalars().all():
            skill_mods_by_char.setdefault(sk.character_id, {})[str(sk.skill_key or "").strip().lower()] = _skill_bonus_from_rank_and_level(
                sk.rank,
                levels_by_char_id.get(sk.character_id),
            )
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

    pc_positions = dict(_get_pc_positions(sess))
    if pid in pc_positions:
        pc_positions.pop(pid, None)
        settings_set(sess, "pc_positions", pc_positions)


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
    from app.web import gm_orchestrator

    return await gm_orchestrator.run_two_pass(
        db,
        sess,
        session_id=session_id,
        draft_prompt=draft_prompt,
        default_actor_uid=default_actor_uid,
        previous_gm_text=previous_gm_text,
    )


async def _auto_gm_reply_task(session_id: str, expected_action_id: str) -> None:
    from app.web import gm_orchestrator

    await gm_orchestrator.run_turn_gm(session_id, expected_action_id)


async def _auto_lore_task(session_id: str) -> None:
    from app.web import gm_orchestrator

    await gm_orchestrator.run_lore_generation(session_id)


async def _auto_round_task(session_id: str, expected_action_id: str) -> None:
    from app.web import gm_orchestrator

    await gm_orchestrator.run_round_gm(session_id, expected_action_id)


# -------------------------
# WebSocket room
# -------------------------
from app.web.ws_handlers import ws_room_handler


@app.websocket("/ws/{session_id}")
async def ws_room(ws: WebSocket, session_id: str):
    await ws_room_handler(ws, session_id)


# Re-export helpers extracted from server for compatibility.
from app.web.ws_access import COMBAT_CLARIFY_TEXT, _combat_clarify_already_sent, _event_actor_label, _load_actor_context, _player_uid
from app.web.ws_checks import SKILL_TO_ABILITY, _ability_mod_from_stats, _normalize_check_name, _skill_bonus_from_rank_and_level
from app.web.ws_combat_prompting import (
    START_INTENT_FALLBACK_TEXT,
    _COMBAT_LOCK_PROMPT,
    _build_combat_scene_facts_for_llm,
    _combat_text_mentions_forbidden_gear,
    _gender_to_pronouns,
    _has_start_intent_sanitary_markers,
    _looks_like_combat_drift,
    _sanitize_gm_output,
    _start_intent_text_needs_repair,
)
from app.web.ws_gameplay import STATE_COMMAND_ALIASES, _detect_chat_combat_action, _format_state_text_for_player, infer_zone_from_action
from app.web.ws_rewards import _apply_defeat_effects_once, _grant_combat_rewards_once, _grant_defeat_outcome_once
from app.web.ws_turns import (
    TURN_TIMEOUT_SECONDS,
    _clear_current_action_id,
    _clear_initiative,
    _clear_paused_remaining,
    _compute_remaining,
    _get_paused_remaining,
    _get_round_actions,
    _is_free_turns,
    _new_action_id,
    _ready_active_players,
    _remove_player_from_session_settings,
    _set_current_action_id,
    _set_kicked,
    _set_paused_remaining,
    advance_turn,
    set_turn_to_order,
    utcnow,
)
