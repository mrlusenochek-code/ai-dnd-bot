import json
import re
from typing import Any, Optional

CHAR_STAT_KEYS = ("str", "dex", "con", "int", "wis", "cha")

CHECK_LINE_RE = re.compile(r"^\s*@@CHECK\s+(\{.*\})\s*$", re.IGNORECASE)
TEXTUAL_CHECK_RE = re.compile(
    r"(?:проверка|check)\s*[:\-]?\s*([a-zA-Zа-яА-Я_]+)[^\n]{0,40}?\bdc\s*[:=]?\s*(\d+)",
    re.IGNORECASE,
)

MANDATORY_ACTION_PATTERNS_BY_CATEGORY: list[tuple[str, list[str]]] = [
    (
        "mechanics",
        [
            r"замок\w*",
            r"замоч\w*",
            r"механизм\w*",
            r"ловушк\w*",
            r"устройств\w*",
            r"пружин\w*",
            r"шестер\w*",
            r"вскры\w*",
            r"взлом\w*",
            r"отпер\w*",
            r"откр\w*",
            r"подкрут\w*",
            r"настро\w*",
            r"обезвред\w*",
            r"размини\w*",
            r"перекус\w*",
            r"перерез\w*",
            r"заклин\w*",
            r"слом\w*",
            r"откруч\w*",
            r"проверн\w*",
            r"проворач\w*",
            r"ковыр\w*",
            r"подцеп\w*",
            r"поддев\w*",
            r"щуп\w*",
            r"вставля\w*",
            r"всовыва\w*",
            r"впихива\w*",
            r"подпира\w*",
            r"фиксир\w*",
            r"выровня\w*",
            r"нажим\w*",
            r"дерга\w*",
            r"тян\w*",
            r"дёрга\w*",
        ],
    ),
    (
        "theft",
        [
            r"карман\w*",
            r"обчист\w*",
            r"похит\w*",
            r"укра\w*",
            r"стащ\w*",
            r"спер\w*",
            r"свист\w*",
            r"вытащ\w*",
            r"дост\w+_?незамет\w*",
            r"незамет\w+_?дост\w*",
            r"незамет\w+_?вытащ\w*",
            r"подмен\w*",
            r"подброс\w*",
            r"подкин\w*",
            r"спрят\w*",
            r"припрят\w*",
            r"сунул\w*",
            r"засунул\w*",
            r"срез\w*",
            r"подрез\w*",
            r"сорва\w*",
            r"сня\w*_(ремешок|ремень|петл\w*)",
            r"вынул\w*",
            r"выуд\w*",
            r"утаил\w*",
            r"крад\w*",
            r"пряч\w*",
            r"прят\w*",
            r"спряч\w*",
            r"скрыва\w*",
            r"утаива\w*",
            r"занык\w*",
            r"ныч\w*",
            r"доста(ё|е)\w*",
            r"вынима\w*",
            r"извлека\w*",
            r"вытаскива\w*",
            r"снима\w*",
            r"подхват\w*",
            r"убира\w*",
            r"прибира\w*",
            r"перекладыва\w*",
            r"перелож\w*",
            r"засовыва\w*",
            r"всу(н|ё|ю)\w*",
            r"впихива\w*",
            r"подменя\w*",
            r"подсовыва\w*",
            r"подкладыва\w*",
        ],
    ),
    (
        "stealth",
        [
            r"проскольз\w*",
            r"тих\w+_?пройти\w*",
            r"незамет\w+_?пройти\w*",
            r"затаил\w*",
            r"след\w+_?за\w*",
            r"подкрад\w*",
            r"обойти\w+_?(охран\w*|страж\w*)",
            r"проник\w*",
            r"влез\w*",
            r"перелез\w*",
            r"взобра\w*",
            r"скрыва\w*",
            r"пряч\w*",
            r"затаива\w*",
            r"таю\w*",
            r"шмыг\w*",
            r"юрк\w*",
            r"слива\w+_?в\s+толп\w*",
            r"растворя\w+_?в\s+толп\w*",
        ],
    ),
    (
        "social",
        [
            r"убед\w*",
            r"уговор\w*",
            r"давл\w*",
            r"надав\w*",
            r"припуг\w*",
            r"запуг\w*",
            r"пригроз\w*",
            r"обман\w*",
            r"совр\w*",
            r"блеф\w*",
            r"прикин\w*_(что|будто)",
            r"допрос\w*",
            r"выпрос\w*",
            r"выман\w*",
            r"развод\w*",
            r"манипул\w*",
            r"льст\w*",
            r"умасл\w*",
            r"подлиза\w*",
            r"выклянч\w*",
            r"выпрашива\w*",
            r"выторгов\w*",
        ],
    ),
    (
        "search",
        [
            r"осмотр\w*",
            r"обыск\w*",
            r"обслед\w*",
            r"иск\w+_?след\w*",
            r"иск\w+_?ули\w*",
            r"высмат\w*",
            r"прислуш\w*",
            r"замет\w*",
            r"обнаруж\w*",
            r"най\w+_?ули\w*",
            r"вычисл\w*",
            r"раскры\w*",
            r"вглядыва\w*",
            r"выслежива\w*",
            r"шар\w+_?по\s+карман\w*",
            r"прощуп\w*",
            r"перерыва\w*",
            r"рыщ\w*",
            r"прочёсыва\w*",
        ],
    ),
]
MANDATORY_ALWAYS_CHECK_CATEGORIES = {"theft", "stealth"}
MANDATORY_ACTION_PATTERNS: list[str] = [
    pattern
    for _category, patterns in MANDATORY_ACTION_PATTERNS_BY_CATEGORY
    for pattern in patterns
]
MANDATORY_OUTCOME_PATTERNS: list[str] = [
    r"успешн\w*",
    r"неуспешн\w*",
    r"провал\w*",
    r"успех\w*",
    r"получил\w*",
    r"не\s+получил\w*",
    r"удал\w*",
    r"не\s+удал\w*",
    r"смог\w*",
    r"не\s+смог\w*",
    r"сумел\w*",
    r"не\s+сумел\w*",
    r"наш[её]л\w*",
    r"не\s+наш[её]л\w*",
    r"обнаруж\w*",
    r"не\s+обнаруж\w*",
    r"замет\w*",
    r"не\s+замет\w*",
    r"вскрыл\w*",
    r"открыл\w*",
    r"отпер\w*",
    r"обезвред\w*",
    r"сломал\w*",
    r"заклинил\w*",
    r"сработал\w*",
    r"украл\w*",
    r"стащил\w*",
    r"вытащил\w*",
    r"достал\w*",
    r"подменил\w*",
    r"спрятал\w*",
    r"забрал\w*",
    r"взял\w*",
    r"урон\w*",
    r"убедил\w*",
    r"обманул\w*",
    r"запугал\w*",
    r"пригрозил\w*",
    r"уговорил\w*",
    r"незамет\w*",
    r"скрылс\w*",
    r"спряталс\w*",
    r"тебя\s+заметил\w*",
    r"вас\s+заметил\w*",
    r"\bуже\b",
    r"в\s+итоге",
    r"в\s+результате",
    r"\bтеперь\b",
    r"оказал\w*",
    r"в\s+тво(ё|е)й\s+рук\w*",
    r"у\s+тебя\s+в\s+рук\w*",
    r"у\s+тебя\s+теперь",
    r"у\s+тебя\s+есть",
    r"в\s+карман\w*\s+у\s+тебя",
    r"в\s+рукав\w*\s+у\s+тебя",
]
MECH_ACTION_RE = re.compile(r"(" + "|".join(MANDATORY_ACTION_PATTERNS) + r")", re.IGNORECASE)
MECH_OUTCOME_RE = re.compile(r"(" + "|".join(MANDATORY_OUTCOME_PATTERNS) + r")", re.IGNORECASE)

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


def _normalize_check_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "normal").strip().lower()
    if mode in {"adv", "advantage"}:
        return "advantage"
    if mode in {"dis", "disadvantage"}:
        return "disadvantage"
    return "normal"


def _normalize_check_name(raw_name: Any) -> str:
    name = str(raw_name or "")
    parts: list[str] = []
    for token in name.split("|"):
        normalized = token.strip().lower().replace("ё", "е")
        normalized = re.sub(r"[\s\-]+", "_", normalized)
        normalized = STAT_ALIASES.get(normalized, normalized)
        normalized = SKILL_ALIASES.get(normalized, normalized)
        if not normalized:
            continue
        if re.fullmatch(r"[.…]+", normalized):
            continue
        if normalized not in ALLOWED_CHECK_KEYS:
            continue
        if normalized in parts:
            continue
        parts.append(normalized)
    if any(token in SKILL_TO_ABILITY for token in parts):
        parts = [token for token in parts if token not in CHAR_STAT_KEYS]
    return "|".join(parts)


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


def _mandatory_check_category(draft_text_raw: str) -> Optional[str]:
    txt = str(draft_text_raw or "")
    if not txt:
        return None
    for category, patterns in MANDATORY_ACTION_PATTERNS_BY_CATEGORY:
        if not patterns:
            continue
        compiled = re.compile(r"(" + "|".join(patterns) + r")", re.IGNORECASE)
        for action_match in compiled.finditer(txt):
            window_start = max(0, action_match.start() - 220)
            window_end = min(len(txt), action_match.end() + 220)
            window_txt = txt[window_start:window_end]
            if category in MANDATORY_ALWAYS_CHECK_CATEGORIES:
                return category
            if MECH_OUTCOME_RE.search(window_txt):
                return category
    return None


def _normalize_free_text_for_match(text: str) -> str:
    normalized = str(text or "").lower().replace("ё", "е")
    normalized = re.sub(r"[\s\-]+", "_", normalized)
    normalized = re.sub(r"[^a-zа-я0-9_]", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized


def _pick_check_key_from_text(text: str, preferred: list[str], forbidden: set[str]) -> Optional[str]:
    norm = _normalize_free_text_for_match(text)
    candidates: list[str] = []

    for key, candidate in SKILL_ALIASES.items():
        if _normalize_free_text_for_match(key) in norm:
            normalized = _normalize_check_name(candidate)
            if normalized:
                candidates.append(normalized)

    for key, candidate in STAT_ALIASES.items():
        if _normalize_free_text_for_match(key) in norm:
            normalized = _normalize_check_name(candidate)
            if normalized:
                candidates.append(normalized)

    canonical_sources = list(SKILL_TO_ABILITY.keys()) + list(CHAR_STAT_KEYS)
    for candidate in canonical_sources:
        if _normalize_free_text_for_match(candidate) in norm:
            normalized = _normalize_check_name(candidate)
            if normalized:
                candidates.append(normalized)

    uniq: list[str] = []
    for candidate in candidates:
        if candidate not in ALLOWED_CHECK_KEYS:
            continue
        if candidate in forbidden:
            continue
        if candidate in uniq:
            continue
        uniq.append(candidate)

    for candidate in uniq:
        if candidate in preferred:
            return candidate
    return uniq[0] if uniq else None


def _autogen_check_for_category(cat: str, text: str, actor_uid: Optional[int]) -> Optional[dict[str, Any]]:
    if actor_uid is None or actor_uid <= 0:
        return None

    preferred, forbidden = {
        "mechanics": (["crafting"], {"perception"}),
        "theft": (["sleight_of_hand", "trickery"], {"perception", "investigation"}),
        "stealth": (["stealth"], {"perception", "investigation"}),
        "social": (["deception", "persuasion", "intimidation"], set()),
        "search": (["investigation", "perception"], set()),
    }.get(cat, ([], set()))

    key = _pick_check_key_from_text(text, preferred, forbidden)
    if not key:
        key = {
            "mechanics": "crafting",
            "theft": "sleight_of_hand",
            "stealth": "stealth",
            "social": "persuasion",
            "search": "perception",
        }.get(cat)
    if not key:
        return None

    return {
        "actor_uid": actor_uid,
        "kind": "skill" if key in SKILL_TO_ABILITY else "ability",
        "name": key,
        "dc": 15,
        "mode": "normal",
        "reason": f"auto:{cat}",
    }


def _extract_last_context_line_from_prompt(draft_prompt: str) -> str:
    marker = "Контекст (последние события):"
    txt = str(draft_prompt or "")
    marker_index = txt.find(marker)
    if marker_index < 0:
        return ""
    context_block = txt[marker_index + len(marker):]
    lines = []
    for raw_line in context_block.splitlines():
        line = raw_line.strip()
        if not line.startswith("- "):
            continue
        content = line[2:].strip()
        if content:
            lines.append(content)
    # Предпочитаем последнее действие игрока, чтобы не подхватывать системные/GM строки в контексте.
    systemish_prefixes = ("следующий ход", "пауза", "продолжили игру", "мастер обрабатывает")
    for line in reversed(lines):
        if line.startswith("[SYSTEM]") or line.startswith("🧙"):
            continue
        if not any(line.lower().startswith(prefix) for prefix in systemish_prefixes):
            if ":" in line and line.split(":", 1)[1].strip():
                return line
    return lines[-1] if lines else ""


def _checks_from_human_text(draft_text: str, default_actor_uid: Optional[int]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in TEXTUAL_CHECK_RE.finditer(draft_text or ""):
        name = _normalize_check_name(m.group(1))
        dc = int(m.group(2) or 0)
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
