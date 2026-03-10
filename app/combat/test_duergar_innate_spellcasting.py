from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _duergar_race_features() -> dict[str, object]:
    return {
        "race_key": "dwarf",
        "subrace": {"key": "duergar"},
        "innate_spells": [
            {"ability": "int", "level": 2, "name": "enlarge", "frequency": "1_per_long_rest", "min_level": 3},
            {"ability": "int", "level": 2, "name": "invisibility", "frequency": "1_per_long_rest", "min_level": 5},
        ],
        "features": {
            "innate_spellcasting": {
                "type": "innate_spellcasting",
                "ability": "int",
                "spells": [
                    {"name": "enlarge", "frequency": "1_per_long_rest", "min_level": 3},
                    {"name": "invisibility", "frequency": "1_per_long_rest", "min_level": 5},
                ],
            },
            "duergar_magic": {
                "type": "innate_spellcasting",
                "ability": "int",
                "spells": [
                    {"name": "enlarge", "frequency": "1_per_long_rest", "min_level": 3},
                    {"name": "invisibility", "frequency": "1_per_long_rest", "min_level": 5},
                ],
            },
        },
        "runtime": {
            "duergar_enlarge_used": False,
            "duergar_invisibility_used": False,
        },
    }


def test_duergar_enlarge_level_gate_and_long_rest_cycle() -> None:
    low_level = SimpleNamespace(level=2, race_features=_duergar_race_features())
    ch = SimpleNamespace(level=3, race_features=_duergar_race_features())

    assert ws_handlers._detect_innate_spell_key("кастую увеличение") == "enlarge"

    low_name, low_err, low_changed = ws_handlers._apply_innate_spell_usage(low_level, "enlarge")
    first, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "enlarge")
    second, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "enlarge")
    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    runtime_after_reset = ((ch.race_features or {}).get("runtime") or {})
    third, third_err, third_changed = ws_handlers._apply_innate_spell_usage(ch, "enlarge")

    assert low_name is None
    assert low_err is not None and "3 уровня" in low_err
    assert low_changed is False
    assert first == "Увеличение"
    assert first_err is None
    assert first_changed is True
    assert second is None
    assert second_err is not None and "долгого отдыха" in second_err
    assert second_changed is False
    assert reset_changed is True
    assert runtime_after_reset.get("duergar_enlarge_used") is False
    assert third == "Увеличение"
    assert third_err is None
    assert third_changed is True


def test_duergar_invisibility_level_gate_and_long_rest_cycle() -> None:
    low_level = SimpleNamespace(level=4, race_features=_duergar_race_features())
    ch = SimpleNamespace(level=5, race_features=_duergar_race_features())

    assert ws_handlers._detect_innate_spell_key("кастую невидимость") == "invisibility"

    low_name, low_err, low_changed = ws_handlers._apply_innate_spell_usage(low_level, "invisibility")
    first, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "invisibility")
    second, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "invisibility")
    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    runtime_after_reset = ((ch.race_features or {}).get("runtime") or {})
    third, third_err, third_changed = ws_handlers._apply_innate_spell_usage(ch, "invisibility")

    assert low_name is None
    assert low_err is not None and "5 уровня" in low_err
    assert low_changed is False
    assert first == "Невидимость"
    assert first_err is None
    assert first_changed is True
    assert second is None
    assert second_err is not None and "долгого отдыха" in second_err
    assert second_changed is False
    assert reset_changed is True
    assert runtime_after_reset.get("duergar_invisibility_used") is False
    assert third == "Невидимость"
    assert third_err is None
    assert third_changed is True
