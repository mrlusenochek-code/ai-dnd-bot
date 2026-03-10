from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _tiefling_race_features() -> dict[str, object]:
    return {
        "race_key": "tiefling",
        "innate_spells": [
            {"ability": "cha", "level": 0, "name": "thaumaturgy", "frequency": "at_will", "min_level": 1},
            {"ability": "cha", "level": 2, "spell_level": 2, "name": "hellish_rebuke", "frequency": "1_per_long_rest", "min_level": 3},
            {"ability": "cha", "level": 2, "spell_level": 2, "name": "darkness", "frequency": "1_per_long_rest", "min_level": 5},
        ],
        "features": {
            "innate_spellcasting": {
                "type": "innate_spellcasting",
                "ability": "cha",
                "spells": [
                    {"name": "thaumaturgy", "frequency": "at_will", "min_level": 1},
                    {"name": "hellish_rebuke", "frequency": "1_per_long_rest", "min_level": 3},
                    {"name": "darkness", "frequency": "1_per_long_rest", "min_level": 5},
                ],
            }
        },
        "runtime": {
            "tiefling_hellish_rebuke_used": False,
            "tiefling_darkness_used": False,
        },
    }


def test_tiefling_thaumaturgy_at_will_and_level_gates_for_other_spells() -> None:
    ch = SimpleNamespace(level=1, race_features=_tiefling_race_features())

    assert ws_handlers._detect_innate_spell_key("использую тауматургию") == "thaumaturgy"

    thaum_1, thaum_err_1, thaum_changed_1 = ws_handlers._apply_innate_spell_usage(ch, "thaumaturgy")
    thaum_2, thaum_err_2, thaum_changed_2 = ws_handlers._apply_innate_spell_usage(ch, "thaumaturgy")
    hellish, hellish_err, hellish_changed = ws_handlers._apply_innate_spell_usage(ch, "hellish_rebuke")
    darkness, darkness_err, darkness_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")

    assert thaum_1 == "Тауматургия"
    assert thaum_2 == "Тауматургия"
    assert thaum_err_1 is None and thaum_err_2 is None
    assert thaum_changed_1 is False and thaum_changed_2 is False
    assert hellish is None and hellish_changed is False and hellish_err is not None and "3 уровня" in hellish_err
    assert darkness is None and darkness_changed is False and darkness_err is not None and "5 уровня" in darkness_err


def test_tiefling_hellish_rebuke_once_per_long_rest_and_runtime_flag() -> None:
    ch = SimpleNamespace(level=3, race_features=_tiefling_race_features())

    first, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "hellish_rebuke")
    second, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "hellish_rebuke")

    runtime = ((ch.race_features or {}).get("runtime") or {})
    assert first == "Адское возмездие"
    assert first_err is None
    assert first_changed is True
    assert second is None
    assert second_err is not None and "долгого отдыха" in second_err
    assert second_changed is False
    assert runtime.get("tiefling_hellish_rebuke_used") is True


def test_tiefling_darkness_once_per_long_rest_and_reset() -> None:
    ch = SimpleNamespace(level=5, race_features=_tiefling_race_features())

    first, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")
    second, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")
    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    runtime_after_reset = ((ch.race_features or {}).get("runtime") or {})
    third, third_err, third_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")

    assert first == "тьма"
    assert first_err is None
    assert first_changed is True
    assert second is None
    assert second_err is not None and "долгого отдыха" in second_err
    assert second_changed is False
    assert reset_changed is True
    assert runtime_after_reset.get("tiefling_darkness_used") is False
    assert third == "тьма"
    assert third_err is None
    assert third_changed is True
