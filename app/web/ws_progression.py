from typing import Any

from app.db.models import Character, Skill
from app.web.gameplay_helpers import CLASS_PRESETS
from app.web.utils import _clamp, as_int


LEVEL_CAP = 20


def _xp_to_next_skill_rank(rank: int) -> int:
    rank = _clamp(as_int(rank, 0), 0, 10)
    return 20 + 15 * rank + 10 * (rank ** 2)


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
