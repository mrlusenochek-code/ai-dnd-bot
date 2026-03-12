from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def test_air_genasi_levitate_uses_shared_pipeline_and_long_rest_reset() -> None:
    ch = SimpleNamespace(
        level=3,
        race_features={
            "innate_spells": [
                {"ability": "con", "level": 2, "name": "levitate", "frequency": "1_per_long_rest", "min_level": 3},
            ],
            "runtime": {},
        },
    )

    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "levitate")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "levitate")

    assert display_name_1 == "levitate"
    assert err_1 is None
    assert changed_1 is True
    assert display_name_2 is None
    assert err_2 is not None
    assert "долгого отдыха" in err_2
    assert changed_2 is False

    runtime = (ch.race_features or {}).get("runtime") or {}
    assert ((runtime.get("innate_spell_uses") or {}).get("levitate") or {}).get("used") == 1

    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    assert reset_changed is True

    display_name_3, err_3, changed_3 = ws_handlers._apply_innate_spell_usage(ch, "levitate")
    assert display_name_3 == "levitate"
    assert err_3 is None
    assert changed_3 is True


def test_non_air_genasi_does_not_get_air_genasi_levitate() -> None:
    ch = SimpleNamespace(level=3, race_features={"innate_spells": [], "runtime": {}})

    display_name, err, changed = ws_handlers._apply_innate_spell_usage(ch, "levitate")

    assert display_name is None
    assert err is not None
    assert changed is False
