from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _tiefling_spells() -> list[dict[str, object]]:
    return [
        {"ability": "cha", "level": 0, "name": "thaumaturgy", "frequency": "at_will", "min_level": 1},
        {"ability": "cha", "level": 2, "spell_level": 2, "name": "hellish_rebuke", "frequency": "1_per_long_rest", "min_level": 3},
        {"ability": "cha", "level": 2, "spell_level": 2, "name": "darkness", "frequency": "1_per_long_rest", "min_level": 5},
    ]


def test_detect_tiefling_innate_spell_keys_ru_and_en() -> None:
    assert ws_handlers._detect_innate_spell_key("использую тауматургию") == "thaumaturgy"
    assert ws_handlers._detect_innate_spell_key("cast thaumaturgy") == "thaumaturgy"
    assert ws_handlers._detect_innate_spell_key("кастую адское возмездие") == "hellish_rebuke"
    assert ws_handlers._detect_innate_spell_key("использую адский отпор") == "hellish_rebuke"
    assert ws_handlers._detect_innate_spell_key("cast hellish rebuke") == "hellish_rebuke"
    assert ws_handlers._detect_innate_spell_key("кастую тьму") == "darkness"
    assert ws_handlers._detect_innate_spell_key("cast darkness") == "darkness"
    assert ws_handlers._detect_innate_spell_key("я думаю про тьму и ночь") is None


def test_tiefling_level_1_thaumaturgy_works_but_hellish_rebuke_blocked_by_level() -> None:
    ch = SimpleNamespace(level=1, race_features={"innate_spells": _tiefling_spells()})

    thaumaturgy_name, thaumaturgy_err, thaumaturgy_changed = ws_handlers._apply_innate_spell_usage(ch, "thaumaturgy")
    hellish_name, hellish_err, hellish_changed = ws_handlers._apply_innate_spell_usage(ch, "hellish_rebuke")

    assert thaumaturgy_name == "Тауматургия"
    assert thaumaturgy_err is None
    assert thaumaturgy_changed is False
    assert hellish_name is None
    assert hellish_changed is False
    assert hellish_err is not None and "3 уровня" in hellish_err


def test_tiefling_hellish_rebuke_and_darkness_limit_and_long_rest_reset() -> None:
    ch = SimpleNamespace(level=3, race_features={"innate_spells": _tiefling_spells()})

    first_hellish, first_hellish_err, first_hellish_changed = ws_handlers._apply_innate_spell_usage(ch, "hellish_rebuke")
    second_hellish, second_hellish_err, second_hellish_changed = ws_handlers._apply_innate_spell_usage(ch, "hellish_rebuke")
    darkness_at_lvl3, darkness_err_lvl3, darkness_changed_lvl3 = ws_handlers._apply_innate_spell_usage(ch, "darkness")

    assert first_hellish == "Адское возмездие"
    assert first_hellish_err is None
    assert first_hellish_changed is True
    assert second_hellish is None
    assert second_hellish_err is not None and "долгого отдыха" in second_hellish_err
    assert second_hellish_changed is False
    assert darkness_at_lvl3 is None
    assert darkness_changed_lvl3 is False
    assert darkness_err_lvl3 is not None and "5 уровня" in darkness_err_lvl3

    ch.level = 5
    first_darkness, first_darkness_err, first_darkness_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")
    second_darkness, second_darkness_err, second_darkness_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")

    assert first_darkness == "тьма"
    assert first_darkness_err is None
    assert first_darkness_changed is True
    assert second_darkness is None
    assert second_darkness_err is not None and "долгого отдыха" in second_darkness_err
    assert second_darkness_changed is False

    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    third_hellish, third_hellish_err, third_hellish_changed = ws_handlers._apply_innate_spell_usage(ch, "hellish_rebuke")
    third_darkness, third_darkness_err, third_darkness_changed = ws_handlers._apply_innate_spell_usage(ch, "darkness")

    assert reset_changed is True
    assert third_hellish == "Адское возмездие"
    assert third_hellish_err is None
    assert third_hellish_changed is True
    assert third_darkness == "тьма"
    assert third_darkness_err is None
    assert third_darkness_changed is True
