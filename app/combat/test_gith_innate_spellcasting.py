from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _githyanki_race_features() -> dict[str, object]:
    return {
        "race_key": "gith",
        "subrace": {"key": "githyanki"},
        "innate_spells": [
            {"ability": "int", "level": 0, "name": "mage_hand", "frequency": "at_will", "min_level": 1, "note": "invisible", "no_material_components": True},
            {"ability": "int", "level": 1, "name": "jump", "frequency": "1_per_long_rest", "min_level": 3, "no_material_components": True},
            {"ability": "int", "level": 2, "name": "misty_step", "frequency": "1_per_long_rest", "min_level": 5, "no_material_components": True},
        ],
        "runtime": {"githyanki_jump_used": False, "githyanki_misty_step_used": False},
    }


def _githzerai_race_features() -> dict[str, object]:
    return {
        "race_key": "gith",
        "subrace": {"key": "githzerai"},
        "innate_spells": [
            {"ability": "wis", "level": 0, "name": "mage_hand", "frequency": "at_will", "min_level": 1, "note": "invisible", "no_material_components": True},
            {"ability": "wis", "level": 1, "name": "shield", "frequency": "1_per_long_rest", "min_level": 3, "no_material_components": True},
            {"ability": "wis", "level": 2, "name": "detect_thoughts", "frequency": "1_per_long_rest", "min_level": 5, "no_material_components": True},
        ],
        "runtime": {"githzerai_shield_used": False, "githzerai_detect_thoughts_used": False},
    }


def test_githyanki_mage_hand_at_will_and_level_gates_for_other_spells() -> None:
    ch = SimpleNamespace(level=1, race_features=_githyanki_race_features())

    assert ws_handlers._detect_innate_spell_key("кастую прыжок") == "jump"
    assert ws_handlers._detect_innate_spell_key("cast misty step") == "misty_step"

    hand_1, hand_err_1, hand_changed_1 = ws_handlers._apply_innate_spell_usage(ch, "mage_hand")
    hand_2, hand_err_2, hand_changed_2 = ws_handlers._apply_innate_spell_usage(ch, "mage_hand")
    jump_name, jump_err, jump_changed = ws_handlers._apply_innate_spell_usage(ch, "jump")
    misty_name, misty_err, misty_changed = ws_handlers._apply_innate_spell_usage(ch, "misty_step")

    assert hand_1 == "Волшебная рука"
    assert hand_2 == "Волшебная рука"
    assert hand_err_1 is None and hand_err_2 is None
    assert hand_changed_1 is False and hand_changed_2 is False
    assert jump_name is None and jump_changed is False and jump_err is not None and "3 уровня" in jump_err
    assert misty_name is None and misty_changed is False and misty_err is not None and "5 уровня" in misty_err


def test_githyanki_jump_and_misty_step_long_rest_cycle() -> None:
    jump_ch = SimpleNamespace(level=3, race_features=_githyanki_race_features())
    misty_ch = SimpleNamespace(level=5, race_features=_githyanki_race_features())

    jump_first, jump_first_err, jump_first_changed = ws_handlers._apply_innate_spell_usage(jump_ch, "jump")
    jump_second, jump_second_err, jump_second_changed = ws_handlers._apply_innate_spell_usage(jump_ch, "jump")
    jump_reset_changed = ws_handlers._reset_racial_rest_uses(jump_ch)
    jump_runtime_after = ((jump_ch.race_features or {}).get("runtime") or {})
    jump_third, jump_third_err, jump_third_changed = ws_handlers._apply_innate_spell_usage(jump_ch, "jump")

    misty_first, misty_first_err, misty_first_changed = ws_handlers._apply_innate_spell_usage(misty_ch, "misty_step")
    misty_second, misty_second_err, misty_second_changed = ws_handlers._apply_innate_spell_usage(misty_ch, "misty_step")
    misty_reset_changed = ws_handlers._reset_racial_rest_uses(misty_ch)
    misty_runtime_after = ((misty_ch.race_features or {}).get("runtime") or {})
    misty_third, misty_third_err, misty_third_changed = ws_handlers._apply_innate_spell_usage(misty_ch, "misty_step")

    assert jump_first == "Прыжок"
    assert jump_first_err is None
    assert jump_first_changed is True
    assert jump_second is None and jump_second_changed is False and jump_second_err is not None and "долгого отдыха" in jump_second_err
    assert jump_reset_changed is True
    assert jump_runtime_after.get("githyanki_jump_used") is False
    assert jump_third == "Прыжок" and jump_third_err is None and jump_third_changed is True

    assert misty_first == "Туманный шаг"
    assert misty_first_err is None
    assert misty_first_changed is True
    assert misty_second is None and misty_second_changed is False and misty_second_err is not None and "долгого отдыха" in misty_second_err
    assert misty_reset_changed is True
    assert misty_runtime_after.get("githyanki_misty_step_used") is False
    assert misty_third == "Туманный шаг" and misty_third_err is None and misty_third_changed is True


def test_githzerai_mage_hand_at_will_and_level_gates_for_other_spells() -> None:
    ch = SimpleNamespace(level=1, race_features=_githzerai_race_features())

    assert ws_handlers._detect_innate_spell_key("кастую щит") == "shield"
    assert ws_handlers._detect_innate_spell_key("использую обнаружение мыслей") == "detect_thoughts"

    hand_1, hand_err_1, hand_changed_1 = ws_handlers._apply_innate_spell_usage(ch, "mage_hand")
    hand_2, hand_err_2, hand_changed_2 = ws_handlers._apply_innate_spell_usage(ch, "mage_hand")
    shield_name, shield_err, shield_changed = ws_handlers._apply_innate_spell_usage(ch, "shield")
    thoughts_name, thoughts_err, thoughts_changed = ws_handlers._apply_innate_spell_usage(ch, "detect_thoughts")

    assert hand_1 == "Волшебная рука"
    assert hand_2 == "Волшебная рука"
    assert hand_err_1 is None and hand_err_2 is None
    assert hand_changed_1 is False and hand_changed_2 is False
    assert shield_name is None and shield_changed is False and shield_err is not None and "3 уровня" in shield_err
    assert thoughts_name is None and thoughts_changed is False and thoughts_err is not None and "5 уровня" in thoughts_err


def test_githzerai_shield_and_detect_thoughts_long_rest_cycle() -> None:
    shield_ch = SimpleNamespace(level=3, race_features=_githzerai_race_features())
    thoughts_ch = SimpleNamespace(level=5, race_features=_githzerai_race_features())

    shield_first, shield_first_err, shield_first_changed = ws_handlers._apply_innate_spell_usage(shield_ch, "shield")
    shield_second, shield_second_err, shield_second_changed = ws_handlers._apply_innate_spell_usage(shield_ch, "shield")
    shield_reset_changed = ws_handlers._reset_racial_rest_uses(shield_ch)
    shield_runtime_after = ((shield_ch.race_features or {}).get("runtime") or {})
    shield_third, shield_third_err, shield_third_changed = ws_handlers._apply_innate_spell_usage(shield_ch, "shield")

    thoughts_first, thoughts_first_err, thoughts_first_changed = ws_handlers._apply_innate_spell_usage(thoughts_ch, "detect_thoughts")
    thoughts_second, thoughts_second_err, thoughts_second_changed = ws_handlers._apply_innate_spell_usage(thoughts_ch, "detect_thoughts")
    thoughts_reset_changed = ws_handlers._reset_racial_rest_uses(thoughts_ch)
    thoughts_runtime_after = ((thoughts_ch.race_features or {}).get("runtime") or {})
    thoughts_third, thoughts_third_err, thoughts_third_changed = ws_handlers._apply_innate_spell_usage(thoughts_ch, "detect_thoughts")

    assert shield_first == "Щит"
    assert shield_first_err is None
    assert shield_first_changed is True
    assert shield_second is None and shield_second_changed is False and shield_second_err is not None and "долгого отдыха" in shield_second_err
    assert shield_reset_changed is True
    assert shield_runtime_after.get("githzerai_shield_used") is False
    assert shield_third == "Щит" and shield_third_err is None and shield_third_changed is True

    assert thoughts_first == "Обнаружение мыслей"
    assert thoughts_first_err is None
    assert thoughts_first_changed is True
    assert thoughts_second is None and thoughts_second_changed is False and thoughts_second_err is not None and "долгого отдыха" in thoughts_second_err
    assert thoughts_reset_changed is True
    assert thoughts_runtime_after.get("githzerai_detect_thoughts_used") is False
    assert thoughts_third == "Обнаружение мыслей" and thoughts_third_err is None and thoughts_third_changed is True
