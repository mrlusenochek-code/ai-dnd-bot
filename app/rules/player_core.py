from __future__ import annotations

from app.rules.phb_math import ability_mod_from_stat100, proficiency_bonus


def ability_modifier_from_stat100(stat: int) -> int:
    return ability_mod_from_stat100(stat)


def proficiency_bonus_for_level(level: int) -> int:
    return proficiency_bonus(level)


def total_skill_bonus(
    *,
    ability_mod: int,
    proficient: bool = False,
    expertise: bool = False,
    proficiency: int = 0,
) -> int:
    total = int(ability_mod)
    if expertise:
        return total + (2 * int(proficiency))
    if proficient:
        return total + int(proficiency)
    return total


def total_saving_throw_bonus(
    *,
    ability_mod: int,
    proficient: bool = False,
    proficiency: int = 0,
) -> int:
    total = int(ability_mod)
    if proficient:
        return total + int(proficiency)
    return total
