import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event, Player, Session
from app.gm import combat_narration as gm_combat_narration, contracts as gm_contracts, sanitize as gm_sanitize
from app.web.gameplay_helpers import _character_meta_from_stats, get_character
from app.web.inventory_helpers import _inventory_prompt_line
from app.web.regexes import COMBAT_MECHANICS_EVENT_RE
from app.web.session_state import _get_pc_positions
from app.web.utils import _short_text
from app.web.combat_helpers import _de_numberize_text


COMBAT_DRIFT_MARKERS = gm_combat_narration.COMBAT_DRIFT_MARKERS
_COMBAT_LOCK_PROMPT = gm_contracts.COMBAT_LOCK_PROMPT
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


def _gender_to_pronouns(g: str) -> str:
    normalized = str(g or "").strip().lower().replace("ё", "е")
    if normalized.startswith("м") or normalized in {"m", "male"}:
        return "он/его/ему"
    if normalized.startswith("ж") or normalized in {"f", "female"}:
        return "она/ее/ей"
    return ""
