from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _drow_race_features() -> dict[str, object]:
    return {
        "race_key": "elf",
        "subrace": {"key": "drow"},
        "innate_spells": [
            {"ability": "cha", "level": 0, "name": "dancing_lights", "frequency": "at_will", "min_level": 1},
            {"ability": "cha", "level": 1, "name": "faerie_fire", "frequency": "1_per_long_rest", "min_level": 3},
            {"ability": "cha", "level": 2, "name": "darkness", "frequency": "1_per_long_rest", "min_level": 5},
        ],
        "features": {
            "innate_spellcasting": {
                "type": "innate_spellcasting",
                "ability": "cha",
                "spells": [
                    {"name": "dancing_lights", "frequency": "at_will", "min_level": 1},
                    {"name": "faerie_fire", "frequency": "1_per_long_rest", "min_level": 3},
                    {"name": "darkness", "frequency": "1_per_long_rest", "min_level": 5},
                ],
            }
        },
        "runtime": {
            "drow_faerie_fire_used": False,
            "drow_darkness_used": False,
        },
    }


def test_drow_dancing_lights_at_will_and_level_gates_for_other_spells() -> None:
    ch = SimpleNamespace(level=1, race_features=_drow_race_features())

    assert ws_handlers._detect_innate_spell_key("кастую танцующие огни") == "dancing_lights"

    dl_1, dl_err_1, dl_changed_1 = ws_handlers._apply_innate_spell_usage(ch, "dancing_lights")
    dl_2, dl_err_2, dl_changed_2 = ws_handlers._apply_innate_spell_usage(ch, "dancing_lights")
    ff, ff_err, ff_changed = ws_handlers._apply_innate_spell_usage(ch, "faerie_fire")
    dark, dark_err, dark_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")

    assert dl_1 == "Пляшущие огоньки"
    assert dl_2 == "Пляшущие огоньки"
    assert dl_err_1 is None and dl_err_2 is None
    assert dl_changed_1 is False and dl_changed_2 is False
    assert ff is None and ff_changed is False and ff_err is not None and "3 уровня" in ff_err
    assert dark is None and dark_changed is False and dark_err is not None and "5 уровня" in dark_err


def test_drow_faerie_fire_once_per_long_rest_and_runtime_flag() -> None:
    ch = SimpleNamespace(level=3, race_features=_drow_race_features())

    first, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "faerie_fire")
    second, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "faerie_fire")

    runtime = ((ch.race_features or {}).get("runtime") or {})
    assert first == "волшебный огонь"
    assert first_err is None
    assert first_changed is True
    assert second is None
    assert second_err is not None and "долгого отдыха" in second_err
    assert second_changed is False
    assert runtime.get("drow_faerie_fire_used") is True


def test_drow_darkness_once_per_long_rest_and_reset() -> None:
    ch = SimpleNamespace(level=5, race_features=_drow_race_features())

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
    assert runtime_after_reset.get("drow_darkness_used") is False
    assert third == "тьма"
    assert third_err is None
    assert third_changed is True
