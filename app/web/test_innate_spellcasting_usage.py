from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def test_detect_innate_spell_key_levitate_from_ru_phrase() -> None:
    spell_key = ws_handlers._detect_innate_spell_key("кастую левитацию на себя")
    assert spell_key == "levitate"


def test_apply_innate_spell_usage_allows_air_genasi_levitate_on_level_3() -> None:
    ch = SimpleNamespace(
        level=3,
        race_features={
            "innate_spells": [
                {"ability": "con", "level": 2, "name": "levitate", "frequency": "1_per_long_rest", "min_level": 3}
            ]
        },
    )

    display_name, err, changed = ws_handlers._apply_innate_spell_usage(ch, "levitate")

    assert err is None
    assert display_name == "levitate"
    assert changed is True
    runtime = (ch.race_features or {}).get("runtime") or {}
    uses = runtime.get("innate_spell_uses") or {}
    assert (uses.get("levitate") or {}).get("used") == 1


def test_apply_innate_spell_usage_fire_genasi_at_will_not_blocked() -> None:
    ch = SimpleNamespace(
        level=3,
        race_features={
            "innate_spells": [
                {"ability": "con", "level": 0, "name": "produce_flame", "frequency": "at_will"},
            ]
        },
    )

    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "produce_flame")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "produce_flame")

    assert err_1 is None
    assert err_2 is None
    assert display_name_1 == "produce_flame"
    assert display_name_2 == "produce_flame"
    assert changed_1 is False
    assert changed_2 is False


def test_apply_innate_spell_usage_fire_genasi_long_rest_limited() -> None:
    ch = SimpleNamespace(
        level=3,
        race_features={
            "innate_spells": [
                {"ability": "con", "level": 1, "name": "burning_hands", "frequency": "1_per_long_rest", "min_level": 3}
            ]
        },
    )

    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")

    assert err_1 is None
    assert display_name_1 == "burning_hands"
    assert changed_1 is True
    assert display_name_2 is None
    assert err_2 is not None
    assert "долгого отдыха" in err_2
    assert changed_2 is False
    runtime = (ch.race_features or {}).get("runtime") or {}
    uses = runtime.get("innate_spell_uses") or {}
    assert (uses.get("burning_hands") or {}).get("used") == 1
