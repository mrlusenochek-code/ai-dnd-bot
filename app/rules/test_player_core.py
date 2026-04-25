from app.rules.player_core import (
    ability_modifier_from_stat100,
    proficiency_bonus_for_level,
    total_saving_throw_bonus,
    total_skill_bonus,
)


def test_ability_modifier_from_stat100_uses_phb_math() -> None:
    assert ability_modifier_from_stat100(70) == 2


def test_proficiency_bonus_for_level_uses_phb_progression() -> None:
    assert proficiency_bonus_for_level(5) == 3


def test_total_skill_bonus_without_proficiency() -> None:
    assert total_skill_bonus(ability_mod=2) == 2


def test_total_skill_bonus_with_proficiency() -> None:
    assert total_skill_bonus(ability_mod=2, proficient=True, proficiency=3) == 5


def test_total_saving_throw_bonus_without_proficiency() -> None:
    assert total_saving_throw_bonus(ability_mod=1) == 1


def test_total_saving_throw_bonus_with_proficiency() -> None:
    assert total_saving_throw_bonus(ability_mod=1, proficient=True, proficiency=2) == 3
