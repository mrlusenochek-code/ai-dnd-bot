from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _drow_spells() -> list[dict[str, object]]:
    return [
        {"ability": "cha", "level": 0, "name": "dancing_lights", "frequency": "at_will"},
        {"ability": "cha", "level": 1, "name": "faerie_fire", "frequency": "1_per_long_rest", "min_level": 3},
        {"ability": "cha", "level": 2, "name": "darkness", "frequency": "1_per_long_rest", "min_level": 5},
    ]


def test_detect_drow_innate_spell_keys_from_ru_and_en_phrases() -> None:
    assert ws_handlers._detect_innate_spell_key("кастую танцующие огни") == "dancing_lights"
    assert ws_handlers._detect_innate_spell_key("использую волшебный огонь") == "faerie_fire"
    assert ws_handlers._detect_innate_spell_key("cast darkness now") == "darkness"
    assert ws_handlers._detect_innate_spell_key("я думаю про тьму и ночь") is None


def test_drow_level_1_dancing_lights_repeatable_and_faerie_fire_blocked() -> None:
    ch = SimpleNamespace(level=1, race_features={"innate_spells": _drow_spells()})

    dl_1, dl_err_1, dl_changed_1 = ws_handlers._apply_innate_spell_usage(ch, "dancing_lights")
    dl_2, dl_err_2, dl_changed_2 = ws_handlers._apply_innate_spell_usage(ch, "dancing_lights")
    ff, ff_err, ff_changed = ws_handlers._apply_innate_spell_usage(ch, "faerie_fire")

    assert dl_1 is not None and dl_err_1 is None and dl_changed_1 is False
    assert dl_2 is not None and dl_err_2 is None and dl_changed_2 is False
    assert ff is None
    assert ff_changed is False
    assert ff_err is not None
    assert "3 уровня" in ff_err


def test_drow_level_3_faerie_fire_once_per_long_rest() -> None:
    ch = SimpleNamespace(level=3, race_features={"innate_spells": _drow_spells()})

    first, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "faerie_fire")
    second, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "faerie_fire")

    assert first == "волшебный огонь"
    assert first_err is None
    assert first_changed is True
    assert second is None
    assert second_err is not None and "долгого отдыха" in second_err
    assert second_changed is False


def test_drow_level_5_darkness_resets_after_long_rest() -> None:
    ch = SimpleNamespace(level=5, race_features={"innate_spells": _drow_spells()})

    first, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")
    second, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")
    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    third, third_err, third_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")

    assert first == "тьма"
    assert first_err is None
    assert first_changed is True
    assert second is None
    assert second_err is not None and "долгого отдыха" in second_err
    assert second_changed is False
    assert reset_changed is True
    assert third == "тьма"
    assert third_err is None
    assert third_changed is True
