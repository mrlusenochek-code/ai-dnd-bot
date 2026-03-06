from typing import Any

from app.gm import checks as gm_checks
from app.rules.phb_math import ability_mod_from_stat100, proficiency_bonus
from app.web.gameplay_helpers import CHAR_STAT_KEYS, _normalized_stats
from app.web.utils import _clamp, as_int


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


def _ability_mod_from_stats(stats_raw: Any, stat_key: str) -> int:
    stats = _normalized_stats(stats_raw)
    val = stats.get(stat_key, 50)
    return ability_mod_from_stat100(val)


def _proficiency_bonus(level_raw: Any) -> int:
    level = _clamp(as_int(level_raw, 1), 1, 20)
    return proficiency_bonus(level)


def _skill_bonus_from_rank_and_level(rank_raw: Any, level_raw: Any) -> int:
    rank = _clamp(as_int(rank_raw, 0), 0, 10)
    if rank < 1:
        return 0
    prof = _proficiency_bonus(level_raw)
    if rank >= 4:
        return 2 * prof
    return prof


def _normalize_check_name(raw_name: Any) -> str:
    return gm_checks._normalize_check_name(raw_name)
