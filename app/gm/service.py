from __future__ import annotations

import re
from typing import Any, Awaitable, Callable, Optional

from sqlalchemy import select

from app.ai.gm import generate_from_prompt
from app.db.models import Skill
from app.gm import checks as gm_checks, contracts as gm_contracts, narration, sanitize as gm_sanitize
from app.rules.phb_rest import sync_hit_dice_on_level_change

ENTITY_TOKEN_RE = re.compile(r"\b(?:[А-ЯЁ][а-яё]{2,}|[A-Z][a-z]{2,})\b")
ENTITY_SENTENCE_LEADING_SKIP = " \t\r\n\"'«»“”„-—–([{"
ENTITY_GUARD_STOPWORDS = {
    "Ты",
    "Что",
    "Мы",
    "GM",
    "Мастер",
    "Валера",
    "Игрок",
    "Система",
    "Сцена",
    "Контекст",
    "Ответ",
    "Черновик",
    "Анализ",
    "Final",
    "Response",
    "После",
}
ENTITY_GUARD_ALLOWLIST = {
    "Север",
    "Юг",
    "Запад",
    "Восток",
}
ENTITY_SENTENCE_START_NAME_VERBS = {
    "говорит",
    "сказал",
    "спросил",
    "кивает",
    "взглянул",
}
BACKREF_TRIGGER_ANCHORS: list[tuple[re.Pattern[str], tuple[str, ...], str]] = [
    (
        re.compile(r"\bпосле\s+(?:его|её|этого)\s+предупрежден", re.IGNORECASE),
        ("предупрежд", "опасност"),
        "после его/её/этого предупреждения",
    ),
    (
        re.compile(r"\bпредупрежден(?:ие|ия|ий)\b", re.IGNORECASE),
        ("предупрежд", "опасност"),
        "предупреждение",
    ),
    (
        re.compile(r"\bкак\s+(?:ты|вы|мы|я)\s+(?:уже\s+)?(?:говорил|сказал|обсуждали)\b", re.IGNORECASE),
        ("говор", "сказ", "обсужд"),
        "как мы уже обсуждали/говорили",
    ),
    (
        re.compile(r"\bранее\b|\bдо\s+этого\b|\bв\s+прошлый\s+раз\b", re.IGNORECASE),
        ("ранее", "до этого", "прошлый"),
        "ранее/до этого/в прошлый раз",
    ),
]
PLAYER_ACTION_LINE_RE = re.compile(r"^\s*-\s*(?:игрок|player)\s*:\s*(.+?)\s*$", re.IGNORECASE)
PLAYER_ACTION_INLINE_RE = re.compile(r"^\s*(?:игрок|player)\s*:\s*(.+?)\s*$", re.IGNORECASE)
ACTION_ANCHOR_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]{4,}")
ACTION_ANCHOR_STOPWORDS = {
    "если",
    "когда",
    "потом",
    "после",
    "перед",
    "снова",
    "сейчас",
    "просто",
    "очень",
    "чтобы",
    "этого",
    "этот",
    "эта",
    "эти",
    "того",
    "только",
    "здесь",
    "туда",
    "сюда",
    "почему",
    "тогда",
    "который",
    "которая",
    "которые",
    "игрок",
    "персонаж",
    "действие",
    "своего",
    "своему",
    "своими",
    "чтобы",
}
MOVED_MARKER_RE = re.compile(r"(?im)^\s*MOVED:\s*(true|false)\s*$")
SCENE_JUMP_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bты\s+оказываешься\b", re.IGNORECASE), "ты оказываешься"),
    (re.compile(r"\bвы\s+оказываетесь\b", re.IGNORECASE), "вы оказываетесь"),
    (re.compile(r"\bчерез\s+некоторое\s+время\s+ты\s+уже\b", re.IGNORECASE), "через некоторое время ты уже"),
    (re.compile(r"\bвскоре\s+ты\s+уже\b", re.IGNORECASE), "вскоре ты уже"),
    (re.compile(r"\bты\s+уже\s+выш[её]л\b", re.IGNORECASE), "ты уже вышел"),
    (re.compile(r"\bты\s+стоишь\s+у\s+(?:[A-Za-zА-Яа-яЁё]+\s+){0,2}ворот\b", re.IGNORECASE), "ты стоишь у ворот"),
    (re.compile(r"\bты\s+входишь\s+в\s+таверн\w*\b", re.IGNORECASE), "ты входишь в таверну"),
    (re.compile(r"\bты\s+выходишь\s+из\s+таверн\w*\b", re.IGNORECASE), "ты выходишь из таверны"),
]
SCENE_ENV_KEYWORDS: dict[str, tuple[str, ...]] = {
    "forest": ("лес", "чащ", "рощ"),
    "dungeon": ("подземель", "катакомб", "крипт"),
    "shore": ("берег", "побереж", "пристан"),
    "gates": ("ворот",),
    "tavern": ("таверн", "трактир"),
    "square": ("площад",),
    "city": ("город", "улиц", "квартал"),
}
SCENE_PRISON_COURT_TRIGGERS: list[tuple[str, str]] = [
    ("заключенн", "заключенный вне контекста"),
    ("тюрьм", "тюрьма вне контекста"),
    ("камера", "камера вне контекста"),
    ("надзират", "надзиратель вне контекста"),
    ("по суду", "по суду вне контекста"),
    ("приговор", "приговор вне контекста"),
    ("конвой", "конвой вне контекста"),
    ("арестован", "арестован вне контекста"),
    ("тюремный страж", "тюремный страж вне контекста"),
]


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


def _prepend_combat_lock(prompt: str, combat_active: bool) -> str:
    if not combat_active:
        return str(prompt or "")
    base = str(prompt or "").strip()
    if not base:
        return gm_contracts.COMBAT_LOCK_PROMPT
    return f"{gm_contracts.COMBAT_LOCK_PROMPT}\n\n{base}"


def _default_as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _default_clamp(n: int, low: int, high: int) -> int:
    return max(low, min(high, n))


def _is_sentence_start_token(text: str, token_start: int) -> bool:
    i = max(0, token_start) - 1
    while i >= 0 and text[i] in ENTITY_SENTENCE_LEADING_SKIP:
        i -= 1
    if i < 0:
        return True
    return text[i] in ".!?"


def _looks_like_name_token(token: str) -> bool:
    return bool(re.fullmatch(r"[А-ЯЁ][а-яё]{2,}", str(token or "")))


def _sentence_start_name_with_speech_verb(text: str, token: str, token_start: int) -> bool:
    if not _is_sentence_start_token(text, token_start):
        return False
    if not _looks_like_name_token(token):
        return False
    tail = str(text or "")[max(0, token_start + len(token)) :]
    i = 0
    while i < len(tail) and tail[i] in ENTITY_SENTENCE_LEADING_SKIP + ",;:":
        i += 1
    j = i
    while j < len(tail) and tail[j].isalpha():
        j += 1
    if j <= i:
        return False
    return tail[i:j].lower() in ENTITY_SENTENCE_START_NAME_VERBS


def _extract_capitalized_tokens(text: str) -> set[str]:
    txt = str(text or "")
    out: set[str] = set()
    for m in ENTITY_TOKEN_RE.finditer(txt):
        token = m.group(0)
        if not token or token in ENTITY_GUARD_STOPWORDS:
            continue
        if _is_sentence_start_token(txt, m.start()):
            is_name = _looks_like_name_token(token)
            if not is_name:
                continue
            if _sentence_start_name_with_speech_verb(txt, token, m.start()):
                out.add(token)
                continue
        out.add(token)
    return out


def _is_entity_introduced(text: str, name: str) -> bool:
    candidate = str(name or "").strip()
    if not candidate:
        return True
    escaped = re.escape(candidate)
    intro_patterns = (
        rf"\bпо\s+имени\s+{escaped}\b",
        rf"\b(?:его|её)\s+зовут\s+{escaped}\b",
        rf"\b{escaped}\s*[—-]\s+",
    )
    return any(re.search(p, text, flags=re.IGNORECASE) for p in intro_patterns)


def _build_entity_repair_prompt(*, final_text: str, unknown_entities: list[str], ctx_line: str) -> str:
    names = ", ".join(unknown_entities) if unknown_entities else "(нет)"
    return (
        "Перепиши текст мастера.\n"
        "НЕ добавляй новых имён/сущностей, которых нет в контексте.\n"
        "Не переносить сцену в тюрьму/суд/камеру, если этого нет в контексте.\n"
        "Если имя необходимо — введи его одной фразой: кто это и почему он/она сейчас в сцене.\n"
        "Не используй мета-комментарии.\n"
        "Не приписывай игроку реплики или мысли.\n"
        "Сохрани смысл действия и завершай строкой: Что делаете дальше?\n\n"
        f"Проблемные имена: {names}\n"
        f"Последняя строка контекста: {ctx_line or '(нет)'}\n\n"
        f"Исходный текст:\n{final_text}"
    )


def _find_unsupported_backreferences(output_text: str, context_text: str) -> list[str]:
    out_text = str(output_text or "")
    ctx_text = str(context_text or "").lower()
    hits: list[str] = []
    for trigger_re, anchors, label in BACKREF_TRIGGER_ANCHORS:
        if not trigger_re.search(out_text):
            continue
        if not any(anchor.lower() in ctx_text for anchor in anchors):
            hits.append(label)
    return sorted(set(hits))


def _build_backref_repair_prompt(*, final_text: str, bad_refs: list[str], ctx_line: str) -> str:
    refs = ", ".join(bad_refs) if bad_refs else "(нет)"
    return (
        "Перепиши текст мастера.\n"
        "Не ссылайся на прошлые события/предупреждения/фразы вроде 'как мы обсуждали', если этого нет в контексте.\n"
        "Описывай только наблюдаемое и то, что реально известно по контексту.\n"
        "Без мета-комментариев.\n"
        "Без реплик и мыслей за игрока.\n"
        "Сохрани смысл сцены и заверши строкой: Что делаете дальше?\n\n"
        f"Проблемные отсылки: {refs}\n"
        f"Последняя строка контекста: {ctx_line or '(нет)'}\n\n"
        f"Исходный текст:\n{final_text}"
    )


def _extract_last_player_action_from_prompt(draft_prompt: str) -> str:
    out = ""
    for raw_line in str(draft_prompt or "").splitlines():
        line = raw_line.strip()
        m = PLAYER_ACTION_LINE_RE.match(line) or PLAYER_ACTION_INLINE_RE.match(line)
        if m:
            out = str(m.group(1) or "").strip()
    return out


def _build_action_anchors(player_action: str, *, limit: int = 8) -> list[str]:
    tokens: set[str] = set()
    for raw in ACTION_ANCHOR_WORD_RE.findall(str(player_action or "").lower()):
        token = raw.strip().lower()
        if len(token) < 4:
            continue
        if token in ACTION_ANCHOR_STOPWORDS:
            continue
        tokens.add(token)
    ranked = sorted(tokens, key=lambda x: (-len(x), x))
    return ranked[:limit]


def _build_action_anchor_repair_prompt(*, final_text: str, player_action: str) -> str:
    return (
        "Перепиши ответ мастера так, чтобы он прямо реагировал на действие игрока.\n"
        f"Действие игрока: {player_action}\n"
        "Не добавляй новых имён или событий.\n"
        "Без мета-комментариев.\n"
        "Без реплик и мыслей за игрока.\n"
        "Сохрани сцену и завершай строкой: Что делаете дальше?\n\n"
        f"Исходный текст:\n{final_text}"
    )


def _extract_moved_flag_from_prompt(draft_prompt: str) -> Optional[bool]:
    value: Optional[bool] = None
    for m in MOVED_MARKER_RE.finditer(str(draft_prompt or "")):
        token = str(m.group(1) or "").strip().lower()
        if token == "true":
            value = True
        elif token == "false":
            value = False
    return value


def _find_scene_env_mentions(text: str) -> set[str]:
    lowered = str(text or "").lower()
    found: set[str] = set()
    for env_key, probes in SCENE_ENV_KEYWORDS.items():
        if any(probe in lowered for probe in probes):
            found.add(env_key)
    return found


def _find_scene_lock_violations(final_text: str, context_text: str, location_fallback: str | None) -> list[str]:
    txt = str(final_text or "")
    lowered = txt.lower()
    ctx = str(context_text or "").lower()
    loc = str(location_fallback or "").lower()
    hits: list[str] = []

    for pattern, label in SCENE_JUMP_PATTERNS:
        if pattern.search(txt):
            hits.append(label)

    if re.search(r"\b(?:у|к)\s+ворот(?:ам)?\b", lowered) and ("ворот" not in ctx) and ("ворот" not in loc):
        hits.append("ворота вне контекста")

    for probe, label in SCENE_PRISON_COURT_TRIGGERS:
        if (probe in lowered) and (probe not in ctx) and (probe not in loc):
            hits.append(label)

    current_envs = _find_scene_env_mentions(loc)
    output_envs = _find_scene_env_mentions(lowered)
    if current_envs and output_envs and current_envs.isdisjoint(output_envs):
        hits.append("смена окружения вне контекста")

    return sorted(set(hits))


def _build_scene_lock_repair_prompt(*, final_text: str, scene_hits: list[str], location_fallback: str | None) -> str:
    issues = ", ".join(scene_hits) if scene_hits else "(нет)"
    current_loc = str(location_fallback or "").strip() or "(не указана)"
    return (
        "Перепиши текст мастера, НЕ меняя сцену и местоположение.\n"
        "Оставайся в текущей локации из контекста.\n"
        "Можно описывать только то, что видно/слышно рядом, и реакции NPC на действие игрока.\n"
        "Без мета-комментариев.\n"
        "Без реплик и мыслей за игрока.\n"
        "Без новых имён и событий.\n"
        "Заверши строкой: Что делаете дальше?\n\n"
        f"Проблемные фразы: {issues}\n"
        f"Текущая локация: {current_loc}\n\n"
        f"Исходный текст:\n{final_text}"
    )


async def run_two_pass(
    db: Any,
    sess: Any,
    *,
    session_id: str,
    draft_prompt: str,
    default_actor_uid: Optional[int],
    previous_gm_text: str = "",
    location_fallback: str | None = None,
    timeout_seconds: float,
    draft_num_predict: int,
    final_num_predict: int,
    combat_active: bool,
    load_actor_context: Callable[[Any, Any], Awaitable[tuple[dict[int, tuple[Any, Any]], dict[int, Any], dict[Any, dict[str, int]]]]],
    compute_check_mod: Callable[[dict[str, Any], Any, dict[Any, dict[str, int]]], int],
    roll_check: Callable[[str], tuple[int, Optional[int], int]],
    build_check_result: Callable[[dict[str, Any], int, int, Optional[int], int], dict[str, Any]],
    character_xp_gain_from_check: Callable[[dict[str, Any]], int],
    level_from_xp_total: Callable[[int, int], int],
    skill_xp_gain: Callable[[dict[str, Any]], int],
    xp_to_next_skill_rank: Callable[[int], int],
    clamp_fn: Callable[[int, int, int], int] = _default_clamp,
    as_int_fn: Callable[[Any, int], int] = _default_as_int,
    get_phase_fn: Optional[Callable[[Any], str]] = None,
    trim_for_log_fn: Optional[Callable[[str, int], str]] = None,
    looks_like_combat_drift_fn: Optional[Callable[[str], bool]] = None,
    llm_generate: Callable[..., Awaitable[dict[str, Any]]] = generate_from_prompt,
    logger: Any = None,
) -> tuple[str, dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    uid_map, chars_by_uid, skill_mods_by_char = await load_actor_context(db, sess)
    draft_prompt_for_model = _prepend_combat_lock(draft_prompt, combat_active)

    draft_resp = await llm_generate(
        prompt=draft_prompt_for_model,
        timeout_seconds=timeout_seconds,
        num_predict=draft_num_predict,
    )
    draft_text_raw = str(draft_resp.get("text") or "").strip()
    draft_text, checks, has_human_check = gm_checks._extract_checks_from_draft(draft_text_raw, default_actor_uid)

    reparsed = False
    forced_reprompt = False
    cleaned_human_check = False
    fallback_autogen_check = False
    combat_lock_reprompt = False
    entity_guard_reprompt = False
    entity_guard_unknown: list[str] = []
    backref_guard_reprompt = False
    backref_guard_hits: list[str] = []
    action_anchor_reprompt = False
    scene_lock_reprompt = False
    mandatory_cat = None if combat_active else gm_checks._mandatory_check_category(draft_text_raw)
    ctx_line = gm_checks._extract_last_context_line_from_prompt(draft_prompt)
    if not combat_active and mandatory_cat is None and ctx_line:
        mandatory_cat = gm_checks._mandatory_check_category(ctx_line)
    if not checks and mandatory_cat:
        forced_reprompt = True
        required_skill_hint = {
            "mechanics": "mechanics: crafting (обычно) или dex",
            "theft": "theft: sleight_of_hand (обычно) или trickery",
            "stealth": "stealth: stealth",
            "social": "social: deception или persuasion или intimidation (выбери по смыслу)",
            "search": "search: perception или investigation (выбери по смыслу)",
        }.get(mandatory_cat, "используй подходящий каноничный навык или стат")
        force_prompt = (
            "Перепиши этот же ответ как черновик мастера.\n"
            f"ВАЖНО: это обязательное действие категории {mandatory_cat}; подменять его на другое действие запрещено.\n"
            "Сохрани исходное действие игрока по смыслу. НЕ меняй попытку на наблюдение/разговор/переход, если игрок делал карманку/взлом/скрытность.\n"
            "Не утверждай итог (успех/провал/получил/не получил) без проверки.\n"
            "В конце ОБЯЗАТЕЛЬНО добавь минимум одну строку @@CHECK.\n"
            "@@CHECK.name = один ключ, без '|' и без добавления статов.\n"
            f"Шпаргалка по категории: {required_skill_hint}.\n"
            "Запрещено:\n"
            "- для theft нельзя perception/investigation;\n"
            "- для mechanics нельзя perception;\n"
            "- для stealth нельзя perception/investigation.\n"
            "Не пиши текст 'Проверка ... DC ...'.\n\n"
            f"Черновик для исправления:\n{draft_text_raw}"
        )
        forced_resp = await llm_generate(
            prompt=force_prompt,
            timeout_seconds=timeout_seconds,
            num_predict=draft_num_predict,
        )
        draft_resp = forced_resp
        draft_text_raw = str(forced_resp.get("text") or "").strip()
        draft_text, checks, has_human_check = gm_checks._extract_checks_from_draft(draft_text_raw, default_actor_uid)

    if not checks and has_human_check:
        inferred = gm_checks._checks_from_human_text(draft_text, default_actor_uid)
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
            forced_resp = await llm_generate(
                prompt=force_prompt,
                timeout_seconds=timeout_seconds,
                num_predict=draft_num_predict,
            )
            draft_resp = forced_resp
            draft_text_raw = str(forced_resp.get("text") or "").strip()
            draft_text, checks, _has_human_check_2 = gm_checks._extract_checks_from_draft(draft_text_raw, default_actor_uid)

    if not checks and mandatory_cat:
        auto_check = gm_checks._autogen_check_for_category(mandatory_cat, (ctx_line or draft_text_raw), default_actor_uid)
        if auto_check:
            checks = [auto_check]
            reparsed = True
            fallback_autogen_check = True

    normalized_checks: list[dict[str, Any]] = []
    for c in checks:
        if not isinstance(c, dict):
            continue
        actor_uid = as_int_fn(c.get("actor_uid"), 0)
        if actor_uid <= 0 and default_actor_uid is not None:
            actor_uid = default_actor_uid
        if actor_uid is None or actor_uid <= 0:
            continue
        name = gm_checks._normalize_check_name(c.get("name"))
        if not name:
            continue
        normalized_checks.append(
            {
                "actor_uid": actor_uid,
                "kind": gm_checks._check_kind_for_name(c.get("kind"), name),
                "name": name,
                "dc": max(0, as_int_fn(c.get("dc"), 0)),
                "mode": gm_checks._normalize_check_mode(c.get("mode")),
                "reason": str(c.get("reason") or "").strip(),
            }
        )

    check_results: list[dict[str, Any]] = []
    for check in normalized_checks:
        actor_uid = as_int_fn(check.get("actor_uid"), 0)
        character = chars_by_uid.get(actor_uid)
        mod = compute_check_mod(check, character, skill_mods_by_char)
        roll_a, roll_b, roll = roll_check(str(check.get("mode") or "normal"))
        result = build_check_result(check, mod, roll_a, roll_b, roll)
        check_results.append(result)

    xp_changed = False
    for result in check_results:
        actor_uid = as_int_fn(result.get("actor_uid"), 0)
        if actor_uid <= 0:
            continue
        ch = chars_by_uid.get(actor_uid)
        if not ch:
            continue
        gain = character_xp_gain_from_check(result)
        new_xp_total = max(0, as_int_fn(ch.xp_total, 0)) + gain
        new_level = level_from_xp_total(new_xp_total, as_int_fn(ch.level, 1))
        if as_int_fn(ch.xp_total, 0) != new_xp_total:
            ch.xp_total = new_xp_total
            xp_changed = True
        old_level = as_int_fn(ch.level, 1)
        if old_level != new_level:
            hd_max, hd_rem = sync_hit_dice_on_level_change(
                old_level=old_level,
                new_level=new_level,
                hit_dice_max=as_int_fn(getattr(ch, "hit_dice_max", None), old_level),
                hit_dice_remaining=as_int_fn(getattr(ch, "hit_dice_remaining", None), old_level),
            )
            ch.level = new_level
            ch.hit_dice_max = hd_max
            ch.hit_dice_remaining = hd_rem
            xp_changed = True
        name = gm_checks._normalize_check_name(str(result.get("name") or ""))
        skill_key: Optional[str] = None
        if "|" in name:
            best_mod: Optional[int] = None
            for candidate_raw in name.split("|"):
                candidate = gm_checks._normalize_check_name(candidate_raw)
                if not candidate or candidate in gm_checks.CHAR_STAT_KEYS:
                    continue
                if candidate in gm_checks.SKILL_TO_ABILITY:
                    cand_mod = compute_check_mod(
                        {"actor_uid": actor_uid, "kind": "skill", "name": candidate},
                        ch,
                        skill_mods_by_char,
                    )
                    if best_mod is None or cand_mod > best_mod:
                        best_mod = cand_mod
                        skill_key = candidate
        else:
            if name and name not in gm_checks.CHAR_STAT_KEYS and name in gm_checks.SKILL_TO_ABILITY:
                skill_key = name
        if not skill_key:
            continue
        q_skill = await db.execute(
            select(Skill).where(
                Skill.character_id == ch.id,
                Skill.skill_key == skill_key,
            )
        )
        sk = q_skill.scalar_one_or_none()
        if not sk:
            sk = Skill(character_id=ch.id, skill_key=skill_key, rank=0, xp=0)
            db.add(sk)
        xp = max(0, as_int_fn(sk.xp, 0)) + skill_xp_gain(result)
        rank = clamp_fn(as_int_fn(sk.rank, 0), 0, 10)
        while rank < 10:
            need = xp_to_next_skill_rank(rank)
            if xp < need:
                break
            xp -= need
            rank += 1
        if as_int_fn(sk.rank, 0) != rank:
            sk.rank = rank
        if as_int_fn(sk.xp, 0) != xp:
            sk.xp = xp
        xp_changed = True
    if xp_changed:
        await db.commit()

    final_prompt = _prepend_combat_lock(gm_contracts.build_finalize_prompt(draft_text=draft_text, check_results=check_results), combat_active)
    final_resp = await llm_generate(
        prompt=final_prompt,
        timeout_seconds=timeout_seconds,
        num_predict=final_num_predict,
    )
    final_text = gm_sanitize.sanitize_gm_output(gm_sanitize._strip_machine_lines(str(final_resp.get("text") or "").strip()))
    if not final_text:
        fallback_prompt = (
            "Дай финальный ответ мастера игрокам по этому черновику.\n"
            "Не используй служебные строки, не упоминай что это черновик.\n\n"
            f"Черновик:\n{draft_text}"
        )
        fallback_resp = await llm_generate(
            prompt=fallback_prompt,
            timeout_seconds=timeout_seconds,
            num_predict=final_num_predict,
        )
        final_text = gm_sanitize.sanitize_gm_output(gm_sanitize._strip_machine_lines(str(fallback_resp.get("text") or "").strip()))
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
            continuation_resp = await llm_generate(
                prompt=continuation_prompt,
                timeout_seconds=timeout_seconds,
                num_predict=final_num_predict,
            )
            continuation_text = gm_sanitize.sanitize_gm_output(gm_sanitize._strip_machine_lines(str(continuation_resp.get("text") or "").strip()))
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
                anti_repeat_resp = await llm_generate(
                    prompt=anti_repeat_prompt,
                    timeout_seconds=timeout_seconds,
                    num_predict=final_num_predict,
                )
                anti_repeat_text = gm_sanitize.sanitize_gm_output(gm_sanitize._strip_machine_lines(str(anti_repeat_resp.get("text") or "").strip()))
                if anti_repeat_text:
                    final_text = anti_repeat_text
                    anti_repeat_strategy = "reprompt"

    if gm_checks.TEXTUAL_CHECK_RE.search(final_text):
        cleaned_human_check = True
        cleanup_prompt = (
            "Перепиши текст мастера так, чтобы не было просьб к игроку бросать проверку/DC.\n"
            "Сцена должна продвинуться вперёд сама, с понятными последствиями.\n\n"
            f"Текст:\n{final_text}"
        )
        cleanup_resp = await llm_generate(
            prompt=cleanup_prompt,
            timeout_seconds=timeout_seconds,
            num_predict=final_num_predict,
        )
        cleaned = gm_sanitize.sanitize_gm_output(gm_sanitize._strip_machine_lines(str(cleanup_resp.get("text") or "").strip()))
        if cleaned:
            final_text = cleaned
    final_text = gm_sanitize.sanitize_gm_output(final_text)
    final_text = narration.sanitize_gm_output(final_text, location_fallback=location_fallback)
    if not final_text:
        final_text = narration.sanitize_gm_output("", location_fallback=location_fallback)
    else:
        context_text = f"{draft_prompt}\n{previous_gm_text}"
        context_entities = _extract_capitalized_tokens(draft_prompt)
        context_entities.update(_extract_capitalized_tokens(previous_gm_text))
        output_entities = _extract_capitalized_tokens(final_text)
        unknown_entities = sorted(output_entities - context_entities - ENTITY_GUARD_ALLOWLIST)
        unresolved = [name for name in unknown_entities if not _is_entity_introduced(final_text, name)]
        if unresolved:
            entity_guard_reprompt = True
            entity_guard_unknown = unresolved
            entity_repair_prompt = _build_entity_repair_prompt(
                final_text=final_text,
                unknown_entities=unresolved,
                ctx_line=ctx_line,
            )
            entity_repair_resp = await llm_generate(
                prompt=entity_repair_prompt,
                timeout_seconds=timeout_seconds,
                num_predict=final_num_predict,
            )
            repaired = gm_sanitize.sanitize_gm_output(gm_sanitize._strip_machine_lines(str(entity_repair_resp.get("text") or "").strip()))
            repaired = narration.sanitize_gm_output(repaired, location_fallback=location_fallback)
            if repaired:
                final_text = repaired

        bad_refs = _find_unsupported_backreferences(final_text, context_text)
        if bad_refs:
            backref_guard_reprompt = True
            backref_guard_hits = bad_refs
            backref_repair_prompt = _build_backref_repair_prompt(
                final_text=final_text,
                bad_refs=bad_refs,
                ctx_line=ctx_line,
            )
            backref_repair_resp = await llm_generate(
                prompt=backref_repair_prompt,
                timeout_seconds=timeout_seconds,
                num_predict=final_num_predict,
            )
            repaired = gm_sanitize.sanitize_gm_output(gm_sanitize._strip_machine_lines(str(backref_repair_resp.get("text") or "").strip()))
            repaired = narration.sanitize_gm_output(repaired, location_fallback=location_fallback)
            if repaired:
                final_text = repaired

    player_action = _extract_last_player_action_from_prompt(draft_prompt)
    action_anchors = _build_action_anchors(player_action)
    if (not combat_active) and final_text and player_action and action_anchors:
        final_text_lower = final_text.lower()
        if not any(anchor in final_text_lower for anchor in action_anchors):
            action_anchor_reprompt = True
            repair_prompt = _build_action_anchor_repair_prompt(
                final_text=final_text,
                player_action=player_action,
            )
            repair_resp = await llm_generate(
                prompt=repair_prompt,
                timeout_seconds=timeout_seconds,
                num_predict=final_num_predict,
            )
            repaired = gm_sanitize.sanitize_gm_output(gm_sanitize._strip_machine_lines(str(repair_resp.get("text") or "").strip()))
            repaired = narration.sanitize_gm_output(repaired, location_fallback=location_fallback)
            if repaired:
                final_text = repaired

    moved_flag = _extract_moved_flag_from_prompt(draft_prompt)
    if (not combat_active) and (moved_flag is False) and final_text:
        context_text = f"{draft_prompt}\n{previous_gm_text}"
        scene_hits = _find_scene_lock_violations(final_text, context_text, location_fallback)
        if scene_hits:
            scene_lock_reprompt = True
            scene_repair_prompt = _build_scene_lock_repair_prompt(
                final_text=final_text,
                scene_hits=scene_hits,
                location_fallback=location_fallback,
            )
            scene_repair_resp = await llm_generate(
                prompt=scene_repair_prompt,
                timeout_seconds=timeout_seconds,
                num_predict=final_num_predict,
            )
            repaired = gm_sanitize.sanitize_gm_output(gm_sanitize._strip_machine_lines(str(scene_repair_resp.get("text") or "").strip()))
            repaired = narration.sanitize_gm_output(repaired, location_fallback=location_fallback)
            if repaired:
                final_text = repaired

    if combat_active and looks_like_combat_drift_fn is not None and looks_like_combat_drift_fn(final_text):
        combat_lock_reprompt = True
        combat_repair_prompt = (
            f"{gm_contracts.COMBAT_LOCK_PROMPT}\n\n"
            "Перепиши ответ строго в COMBAT MODE.\n"
            "Не добавляй @@CHECK, @@CHECK_RESULT и любые @@COMBAT_* команды.\n"
            "Не завершай бой и не уводи сцену в другую локацию.\n"
            "Не проси цифры/AC/урон/броски.\n"
            "Сделай коротко: несколько предложений.\n"
            "Последняя строка строго: Что делаете дальше?\n\n"
            f"Контекст последнего действия:\n{ctx_line or '(нет)'}\n\n"
            f"Текущий ответ:\n{final_text}"
        )
        combat_repair_resp = await llm_generate(
            prompt=combat_repair_prompt,
            timeout_seconds=timeout_seconds,
            num_predict=final_num_predict,
        )
        repaired = str(combat_repair_resp.get("text") or "").strip()
        repaired = gm_sanitize._strip_machine_lines(repaired)
        repaired = re.sub(r"(?im)^\s*@@COMBAT_[A-Z_]+.*$", "", repaired)
        repaired = gm_sanitize.sanitize_gm_output(repaired)
        if repaired:
            final_text = repaired
    if combat_active:
        final_text = re.sub(r"(?im)^\s*@@COMBAT_[A-Z_]+.*$", "", str(final_text or "")).strip()
        final_text = gm_sanitize.sanitize_gm_output(final_text)
        if looks_like_combat_drift_fn is not None and looks_like_combat_drift_fn(final_text):
            final_text = "Схватка продолжается в том же месте, противники давят без передышки.\nЧто делаете дальше?"

    if logger is not None and trim_for_log_fn is not None and get_phase_fn is not None:
        logger.info(
            "gm two-pass completed",
            extra={
                "action": {
                    "phase": get_phase_fn(sess),
                    "draft_preview": trim_for_log_fn(draft_text_raw),
                    "checks": normalized_checks,
                    "check_results": check_results,
                    "fallback_textual_check_parse": reparsed,
                    "fallback_forced_reprompt": forced_reprompt,
                    "fallback_cleanup_human_check_text": cleaned_human_check,
                    "fallback_autogen_check": bool(fallback_autogen_check),
                    "fallback_combat_lock_reprompt": bool(combat_lock_reprompt),
                    "fallback_entity_guard_reprompt": bool(entity_guard_reprompt),
                    "fallback_entity_guard_unknown": entity_guard_unknown,
                    "fallback_backref_guard_reprompt": bool(backref_guard_reprompt),
                    "fallback_backref_guard_hits": backref_guard_hits,
                    "fallback_action_anchor_reprompt": bool(action_anchor_reprompt),
                    "fallback_scene_lock_reprompt": bool(scene_lock_reprompt),
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
