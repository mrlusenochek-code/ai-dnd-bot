from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _fairy_race_features() -> dict[str, object]:
    return {
        "race_key": "fairy",
        "innate_spells": [
            {"ability": "wis", "level": 0, "name": "druidcraft", "frequency": "at_will", "min_level": 1},
            {"ability": "wis", "level": 1, "name": "faerie_fire", "frequency": "1_per_long_rest", "min_level": 3},
            {"ability": "wis", "level": 2, "name": "enlarge_reduce", "frequency": "1_per_long_rest", "min_level": 5},
        ],
        "features": {
            "fairy_magic": {
                "type": "innate_spellcasting",
                "ability": "wis",
                "spells": [
                    {"name": "druidcraft", "frequency": "at_will", "min_level": 1},
                    {"name": "faerie_fire", "frequency": "1_per_long_rest", "min_level": 3},
                    {"name": "enlarge_reduce", "frequency": "1_per_long_rest", "min_level": 5},
                ],
            },
            "innate_spellcasting": {
                "type": "innate_spellcasting",
                "ability": "wis",
                "spells": [
                    {"name": "druidcraft", "frequency": "at_will", "min_level": 1},
                    {"name": "faerie_fire", "frequency": "1_per_long_rest", "min_level": 3},
                    {"name": "enlarge_reduce", "frequency": "1_per_long_rest", "min_level": 5},
                ],
            },
        },
    }


def test_fairy_druidcraft_is_at_will_and_other_spells_have_level_gates() -> None:
    ch = SimpleNamespace(level=1, race_features=_fairy_race_features())

    assert ws_handlers._detect_innate_spell_key("кастую искусство друидов") == "druidcraft"
    assert ws_handlers._detect_innate_spell_key("использую огонь фей") == "faerie_fire"
    assert ws_handlers._detect_innate_spell_key("кастую увеличение/уменьшение") == "enlarge_reduce"

    druidcraft_1, druidcraft_err_1, druidcraft_changed_1 = ws_handlers._apply_innate_spell_usage(ch, "druidcraft")
    druidcraft_2, druidcraft_err_2, druidcraft_changed_2 = ws_handlers._apply_innate_spell_usage(ch, "druidcraft")
    fire_low, fire_low_err, fire_low_changed = ws_handlers._apply_innate_spell_usage(ch, "faerie_fire")
    enlarge_low, enlarge_low_err, enlarge_low_changed = ws_handlers._apply_innate_spell_usage(ch, "enlarge_reduce")

    assert druidcraft_1 == "Искусство друидов"
    assert druidcraft_2 == "Искусство друидов"
    assert druidcraft_err_1 is None and druidcraft_err_2 is None
    assert druidcraft_changed_1 is False and druidcraft_changed_2 is False
    assert fire_low is None and fire_low_changed is False and fire_low_err is not None and "3 уровня" in fire_low_err
    assert enlarge_low is None and enlarge_low_changed is False and enlarge_low_err is not None and "5 уровня" in enlarge_low_err


def test_fairy_limited_spells_are_once_per_long_rest_and_reset() -> None:
    fire_ch = SimpleNamespace(level=3, race_features=_fairy_race_features())

    fire_first, fire_first_err, fire_first_changed = ws_handlers._apply_innate_spell_usage(fire_ch, "faerie_fire")
    fire_second, fire_second_err, fire_second_changed = ws_handlers._apply_innate_spell_usage(fire_ch, "faerie_fire")

    assert fire_first == "волшебный огонь"
    assert fire_first_err is None
    assert fire_first_changed is True
    assert fire_second is None
    assert fire_second_err is not None and "долгого отдыха" in fire_second_err
    assert fire_second_changed is False

    reset_changed = ws_handlers._reset_racial_rest_uses(fire_ch)
    runtime_after_reset = ((fire_ch.race_features or {}).get("runtime") or {})
    fire_third, fire_third_err, fire_third_changed = ws_handlers._apply_innate_spell_usage(fire_ch, "faerie_fire")

    assert reset_changed is True
    assert "innate_spell_uses" not in runtime_after_reset
    assert fire_third == "волшебный огонь"
    assert fire_third_err is None
    assert fire_third_changed is True

    enlarge_ch = SimpleNamespace(level=5, race_features=_fairy_race_features())
    enlarge_first, enlarge_first_err, enlarge_first_changed = ws_handlers._apply_innate_spell_usage(enlarge_ch, "enlarge_reduce")
    enlarge_second, enlarge_second_err, enlarge_second_changed = ws_handlers._apply_innate_spell_usage(enlarge_ch, "enlarge_reduce")

    assert enlarge_first == "Увеличение/уменьшение"
    assert enlarge_first_err is None
    assert enlarge_first_changed is True
    assert enlarge_second is None
    assert enlarge_second_err is not None and "долгого отдыха" in enlarge_second_err
    assert enlarge_second_changed is False
