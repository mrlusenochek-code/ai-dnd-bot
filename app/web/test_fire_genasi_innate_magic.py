from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def test_fire_genasi_innate_magic_uses_shared_pipeline_and_long_rest_reset() -> None:
    ch = SimpleNamespace(
        level=3,
        race_features={
            "innate_spells": [
                {"ability": "con", "level": 0, "name": "produce_flame", "frequency": "at_will"},
                {"ability": "con", "level": 1, "name": "burning_hands", "frequency": "1_per_long_rest", "min_level": 3},
            ],
            "runtime": {},
        },
    )

    at_will_display_1, at_will_err_1, at_will_changed_1 = ws_handlers._apply_innate_spell_usage(ch, "produce_flame")
    at_will_display_2, at_will_err_2, at_will_changed_2 = ws_handlers._apply_innate_spell_usage(ch, "produce_flame")
    assert at_will_display_1 == "produce_flame"
    assert at_will_display_2 == "produce_flame"
    assert at_will_err_1 is None
    assert at_will_err_2 is None
    assert at_will_changed_1 is False
    assert at_will_changed_2 is False

    limited_display_1, limited_err_1, limited_changed_1 = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")
    limited_display_2, limited_err_2, limited_changed_2 = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")
    assert limited_display_1 == "burning_hands"
    assert limited_err_1 is None
    assert limited_changed_1 is True
    assert limited_display_2 is None
    assert limited_err_2 is not None
    assert "долгого отдыха" in limited_err_2
    assert limited_changed_2 is False

    runtime = (ch.race_features or {}).get("runtime") or {}
    assert ((runtime.get("innate_spell_uses") or {}).get("burning_hands") or {}).get("used") == 1

    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    assert reset_changed is True

    limited_display_3, limited_err_3, limited_changed_3 = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")
    assert limited_display_3 == "burning_hands"
    assert limited_err_3 is None
    assert limited_changed_3 is True


def test_non_fire_genasi_does_not_get_fire_genasi_innate_spells() -> None:
    ch = SimpleNamespace(level=3, race_features={"innate_spells": [], "runtime": {}})

    display_name, err, changed = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")

    assert display_name is None
    assert err is not None
    assert changed is False
