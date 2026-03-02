from __future__ import annotations

import re
from typing import Awaitable, Callable

from app.ai.gm import generate_from_prompt
from app.gm import contracts as gm_contracts, sanitize as gm_sanitize


COMBAT_DRIFT_MARKERS = (
    "старик",
    "стражник",
    "стражники",
    "стена",
    "толпа",
    "рынок",
    "таверна",
    "лес",
    "лавка",
    "магазин",
)


def _looks_like_refusal(text: str) -> bool:
    t = str(text or "").strip().lower()
    if not t:
        return False

    cannot = ("не могу" in t) or ("can't" in t) or ("cannot" in t) or ("can’t" in t)
    if not cannot:
        return False

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

    starts_apology = t.startswith(("извини", "простите", "прошу прощения", "sorry", "i'm sorry", "i am sorry"))
    offers_other = any(
        x in t for x in (
            "я могу помочь с другим",
            "могу помочь с другим",
            "могу помочь с чем-то другим",
            "i can help with something else",
            "something else",
        )
    )
    mentions_policy = any(
        x in t for x in (
            "политик",
            "правил",
            "policy",
            "guideline",
            "как модель",
            "как ии",
            "as an ai",
        )
    )

    if starts_apology or offers_other or mentions_policy:
        return True

    return False


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


def _de_numberize_text(text: str) -> str:
    txt = str(text or "")
    txt = re.sub(r"\d+", "", txt)
    txt = gm_sanitize.COMBAT_NARRATION_BANNED_RE.sub("", txt)
    txt = re.sub(r"\s{2,}", " ", txt)
    txt = re.sub(r"\s+([,.;:!?])", r"\1", txt)
    return txt.strip()


def _sanitize_combat_llm_text(text: str) -> str:
    out_lines: list[str] = []
    for line in (text or "").splitlines():
        if line.strip().startswith("@@CHECK"):
            continue
        if line.strip().startswith("@@CHECK_RESULT"):
            continue
        out_lines.append(line)
    txt = gm_sanitize.sanitize_gm_output("\n".join(out_lines).strip())
    return re.sub(r"(?im)^\s*@@COMBAT_[A-Z_]+.*$", "", txt).strip()


def build_combat_narration_prompt(
    campaign_title: str,
    outcome_summary: list[str],
    current_turn: str,
    participants_block: str,
    actor_name: str,
    actor_gender: str,
    actor_pronouns: str,
) -> str:
    return gm_contracts.build_combat_narration_prompt(
        campaign_title=campaign_title,
        outcome_summary=outcome_summary,
        current_turn=current_turn,
        participants_block=participants_block,
        actor_name=actor_name,
        actor_gender=actor_gender,
        actor_pronouns=actor_pronouns,
    )


def sanitize_combat_narration(text: str) -> str:
    return gm_sanitize.sanitize_combat_narration(text)


def _combat_safe_fallback(player_action: str, outcome_summary: list[str]) -> str:
    summary_line = ""
    for item in outcome_summary:
        candidate = _de_numberize_text(item)
        if candidate:
            summary_line = candidate.rstrip(".!?") + "."
            break
    if not summary_line:
        summary_line = "Схватка продолжается в тесном контакте."

    if player_action == "combat_attack":
        action_line = "Ты проводишь атаку в гуще боя, и исход удара сразу меняет темп схватки."
    else:
        action_line = "Твой боевой манёвр сразу влияет на ход столкновения."

    return (
        f"{action_line}\n"
        f"{summary_line}\n"
        "Противники отвечают мгновенно, и бой не даёт передышки.\n"
        "Что делаете дальше?"
    )


def _combat_narration_mentions_action(text: str, action: str) -> bool:
    lowered = str(text or "").lower().replace("ё", "е")
    if action == "combat_attack":
        return bool(re.search(r"(атак|напад|удар|выпад|тыч|пыр|замах|мета|швыр|стрел|лук|арбалет|попад|промах|крит)", lowered))
    if action == "combat_dodge":
        return bool(re.search(r"(уклон|уворот|уворач|защит|оборон|блок|щит|стойк)", lowered))
    if action == "combat_help":
        return bool(re.search(r"(помо|поддерж|страх|отвлек|координ|преимуще|открываю окно|прикр)", lowered))
    if action == "combat_dash":
        return bool(re.search(r"(рывок|рван|спринт|бросок|ринул|стремглав|сокращаю дистанц)", lowered))
    if action == "combat_disengage":
        return bool(re.search(r"(отход|отступ|разрыв дистанц|разрыва|разорва|выхожу из боя|отпрыг|отскоч)", lowered))
    if action == "combat_escape":
        return bool(
            re.search(
                r"(убеж|сбеж|беж|удир|драп|ретир|побег|спас|убег|сбег|свал|бегу\s+прочь|уход\s+из\s+боя|выхожу\s+из\s+боя|выйт[ьи]\s+из\s+боя|выйду\s+из\s+боя|выйти\s+с\s+поля\s+боя|с\s+поля\s+боя|поле\s+боя|разрыв дистанц)",
                lowered,
            )
        )
    if action == "combat_use_object":
        return bool(re.search(r"(предмет|флакон|зелье|свиток|факел|рычаг|кнопк|устройств|активир|включа|поджига|зажига)", lowered))
    if action == "combat_end_turn":
        return bool(re.search(r"(переда(ет|ете) ход|инициатив|пас|пропускаю ход|жду|ничего не делаю)", lowered))
    return True


def _combat_narration_fact_coverage(text: str, facts: list[str]) -> int:
    low = str(text or "").lower().replace("ё", "е")
    if not low or not facts:
        return 0

    key_tokens = (
        "попадает",
        "промахивается",
        "ранен",
        "сильно",
        "едва",
        "вырывается",
        "срывается",
        "помогает",
        "отступает",
        "ускоряется",
        "защиту",
    )

    def _stem(token: str) -> str:
        t = str(token or "").lower().replace("ё", "е").strip()
        if len(t) >= 5:
            return t[:5]
        if len(t) >= 4:
            return t[:4]
        return t

    def _has_token(token: str, *, haystack: str) -> bool:
        st = _stem(token)
        if not st:
            return False
        return re.search(rf"\b{re.escape(st)}\w*\b", haystack, flags=re.IGNORECASE) is not None

    coverage = 0
    for fact in facts:
        fact_low = str(fact or "").lower().replace("ё", "е")
        fact_tokens = re.findall(r"[а-яёa-z0-9]{3,}", fact_low)
        if not fact_tokens:
            continue

        anchor_name = fact_tokens[0]

        key = ""
        for token in key_tokens:
            if _has_token(token, haystack=fact_low):
                key = token
                break
        if not key and len(fact_tokens) > 1:
            key = fact_tokens[1]

        if _has_token(anchor_name, haystack=low) and key and _has_token(key, haystack=low):
            coverage += 1
            continue

        if key and _has_token(key, haystack=low):
            coverage += 1
            continue

        matched = 0
        for tok in fact_tokens[:6]:
            if _has_token(tok, haystack=low):
                matched += 1
        if matched >= 2:
            coverage += 1

    return coverage


async def generate_combat_narration(
    campaign_title: str,
    outcome_summary: list[str],
    player_action: str,
    current_turn: str,
    participants_block: str,
    actor_name: str,
    actor_gender: str,
    actor_pronouns: str,
    *,
    timeout_seconds: float,
    num_predict: int,
) -> str:
    prompt = build_combat_narration_prompt(
        campaign_title=campaign_title,
        outcome_summary=outcome_summary,
        current_turn=current_turn,
        participants_block=participants_block,
        actor_name=actor_name,
        actor_gender=actor_gender,
        actor_pronouns=actor_pronouns,
    )
    resp = await generate_from_prompt(
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        num_predict=num_predict,
    )
    text = sanitize_combat_narration(str(resp.get("text") or "").strip())
    if (
        _looks_like_refusal(text)
        or not text
        or _looks_like_combat_drift(text)
        or any(marker in text.lower().replace("ё", "е") for marker in COMBAT_DRIFT_MARKERS)
    ):
        return _combat_safe_fallback(player_action, outcome_summary)
    if not _combat_narration_mentions_action(text, player_action):
        repaired = sanitize_combat_narration(f"{_combat_safe_fallback(player_action, outcome_summary)}\n{text}")
        if repaired:
            return repaired
    return text


async def generate_combat_narration_from_facts(
    *,
    combat_lock_prompt: str,
    facts: list[str],
    required_fact_count: int,
    scene_facts_block: str,
    player_raw_action: str,
    player_name: str,
    ended: bool,
    timeout_seconds: float,
    num_predict: int,
    mentions_forbidden_gear_fn: Callable[[str], bool] | None = None,
    llm_generate: Callable[..., Awaitable[dict]] = generate_from_prompt,
) -> str:
    prompt = (
        f"{combat_lock_prompt}\n\n"
        "Сейчас идёт бой. Напиши КРАСИВОЕ подробное описание этого обмена ударами по фактам ниже.\n"
        "Правила (строго):\n"
        "- НЕЛЬЗЯ: числа, кубики, броски, урон, HP, AC, раунды, 'ход', формулы.\n"
        "- НЕЛЬЗЯ уводить сцену в другую локацию, мирные сцены, расследование, разговоры с третьими лицами.\n"
        "- Описывай ТОЛЬКО бой здесь и сейчас.\n"
        f"- Обязательно встроить в повествование (не списком) минимум {required_fact_count} разных пункта из блока 'Факты (без чисел)'.\n"
        "- Обязательно использовать минимум 1 деталь окружения из блока 'Факты сцены' (зона/окружение).\n"
        "- Если в 'Факты (без чисел)' есть состояние цели ('почти не ранен'/'ранен'/'сильно ранен'/'едва держится' или аналог), обязательно явно отрази это в описании.\n"
        "- Обязательная связка в тексте: действие игрока -> реакция врага -> исход -> текущее состояние/давление (без чисел).\n"
        "- НЕЛЬЗЯ добавлять новых NPC, случайных прохожих, толпу, новые предметы или новые сущности.\n"
        "- Предметы можно упоминать только если они есть в inventory facts.\n"
        "- Нельзя называть конкретные оружие/броню/экипировку, если этого нет в фактах сцены или в действии игрока; можно только нейтральные формулировки ('удар', 'выпад', 'замах', 'толчок', 'рывок').\n"
        "- Пиши во 2 лице: 'ты'. Реплики персонажа игрока НЕ писать.\n"
        "- Должно быть видно и твоё действие, и ответ врага (если он есть в фактах).\n"
        "- 10–14 предложений, 1–2 абзаца, кинематографично.\n"
        + ("- Заверши кратко финалом схватки без вопроса.\n" if ended else "- Заверши строкой: Что делаете дальше?\n")
        + f"\nФакты сцены (не выдумывать сверх этого):\n{scene_facts_block}\n"
        + f"\nПоследнее действие игрока: {player_raw_action[:180]}\n"
        + "\nФакты (без чисел):\n- "
        + "\n- ".join(facts)
        + "\n"
        f"\nИмя героя (для ориентира): {player_name}\n"
    )
    resp = await llm_generate(
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        num_predict=num_predict,
    )
    text = _sanitize_combat_llm_text(str(resp.get("text") or "").strip())
    has_mechanics = bool(re.search(r"(?:\d|\bd20\b|\bhp\b|\bac\b|урон|бросок)", text, flags=re.IGNORECASE))
    has_forbidden_gear = bool(mentions_forbidden_gear_fn(text)) if mentions_forbidden_gear_fn else False
    coverage = _combat_narration_fact_coverage(text, facts)
    has_low_fact_coverage = coverage < required_fact_count
    zone_low = (scene_facts_block or "").lower().replace("ё", "е")
    text_low = (text or "").lower().replace("ё", "е")
    drift = _looks_like_combat_drift(text)
    if drift:
        for stem in ("таверн", "рынок", "магазин", "лавк", "лес"):
            if stem in zone_low and stem in text_low:
                drift = False
                break
    if text and (has_mechanics or drift or has_forbidden_gear or has_low_fact_coverage):
        reprompt = (
            f"{combat_lock_prompt}\n\n"
            "Перепиши строго без механики и без чисел. "
            "Никаких бросков, HP, AC, урона, формул или раундов. "
            "Никакого ухода сцены из текущего боя. "
            f"Обязательно встроить в повествование (не списком) минимум {required_fact_count} разных пункта из блока 'Факты (без чисел)'. "
            f"Твой текст обязан отразить {required_fact_count} факта(ов) из блока фактов; сейчас отражено: {coverage}. "
            "Обязательно использовать минимум 1 деталь окружения из блока 'Факты сцены' (зона/окружение). "
            "Если в фактах есть состояние цели ('почти не ранен'/'ранен'/'сильно ранен'/'едва держится' или аналог), обязательно явно отрази это в описании. "
            "Соблюдай связку: действие игрока -> реакция врага -> исход -> текущее состояние/давление (без чисел). "
            "Нельзя добавлять новых NPC, случайных прохожих, толпу, новые предметы или новые сущности. "
            "Нельзя называть конкретные оружие/броню/экипировку, если этого нет в фактах сцены или в действии игрока; можно только нейтральные формулировки ('удар', 'выпад', 'замах', 'толчок', 'рывок').\n\n"
            f"Факты сцены (не выдумывать сверх этого):\n{scene_facts_block}\n\n"
            f"Последнее действие игрока: {player_raw_action[:180]}\n\n"
            "Факты (без чисел):\n- "
            + "\n- ".join(facts)
            + "\n\n"
            "Текущий текст:\n"
            f"{text}"
        )
        reprompt_resp = await llm_generate(
            prompt=reprompt,
            timeout_seconds=timeout_seconds,
            num_predict=num_predict,
        )
        text = _sanitize_combat_llm_text(str(reprompt_resp.get("text") or "").strip())
        has_mechanics = bool(re.search(r"(?:\d|\bd20\b|\bhp\b|\bac\b|урон|бросок)", text, flags=re.IGNORECASE))
        has_forbidden_gear = bool(mentions_forbidden_gear_fn(text)) if mentions_forbidden_gear_fn else False
        zone_low = (scene_facts_block or "").lower().replace("ё", "е")
        text_low = (text or "").lower().replace("ё", "е")
        drift = _looks_like_combat_drift(text)
        if drift:
            for stem in ("таверн", "рынок", "магазин", "лавк", "лес"):
                if stem in zone_low and stem in text_low:
                    drift = False
                    break
        if not text or has_mechanics or drift or has_forbidden_gear:
            text = "Схватка вспыхивает снова: ты давишь на противника, он отвечает резким выпадом."
            if not ended:
                text += " Что делаете дальше?"
    if ended:
        text = re.sub(r"(?:\s*[\r\n]+)?\s*Что\s+делаете\s+дальше\??\s*$", "", text, flags=re.IGNORECASE).strip()
        if not text:
            text = "Схватка обрывается в последний резкий обмен, и бой затихает в этом же месте."
    elif text and not re.search(r"Что\s+делаете\s+дальше\??\s*$", text, flags=re.IGNORECASE):
        text = text.rstrip(".!? \n") + "\nЧто делаете дальше?"
    return text
