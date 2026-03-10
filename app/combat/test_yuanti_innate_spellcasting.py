from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _yuanti_rf() -> dict:
    return {
        "race_key": "yuan_ti_pureblood",
        "innate_spells": [
            {"ability": "cha", "level": 0, "name": "poison_spray", "frequency": "at_will", "min_level": 1},
            {
                "ability": "cha",
                "level": 1,
                "name": "animal_friendship",
                "frequency": "at_will",
                "min_level": 1,
                "restriction": {"targets": ["snakes"]},
            },
            {"ability": "cha", "level": 2, "name": "suggestion", "frequency": "1_per_long_rest", "min_level": 3},
        ],
        "runtime": {
            "yuanti_suggestion_used": False,
            "yuanti_last_innate_spell": None,
        },
    }


def test_yuanti_poison_spray_is_at_will_and_detected() -> None:
    ch = SimpleNamespace(level=1, race_features=_yuanti_rf())

    assert ws_handlers._detect_innate_spell_key("кастую ядовитые брызги") == "poison_spray"

    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "poison_spray")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "poison_spray")

    assert err_1 is None and err_2 is None
    assert display_name_1 == "Ядовитые брызги"
    assert display_name_2 == "Ядовитые брызги"
    assert changed_1 is True
    assert changed_2 is False
    runtime = (ch.race_features or {}).get("runtime") or {}
    assert runtime.get("yuanti_last_innate_spell") == "poison_spray"


def test_yuanti_animal_friendship_is_at_will_and_restricted_to_snakes() -> None:
    ch = SimpleNamespace(level=1, race_features=_yuanti_rf())

    assert ws_handlers._detect_innate_spell_key("использую дружбу с животными") == "animal_friendship"

    display_name, err, changed = ws_handlers._apply_innate_spell_usage(ch, "animal_friendship")
    assert err is None
    assert display_name == "Дружба с животными"
    assert changed is True

    spell = next(
        item for item in ((ch.race_features or {}).get("innate_spells") or [])
        if isinstance(item, dict) and str(item.get("name") or "").strip().lower() == "animal_friendship"
    )
    assert ((spell.get("restriction") or {}).get("targets") or []) == ["snakes"]


def test_yuanti_suggestion_level_gate_and_long_rest_reset() -> None:
    low_level = SimpleNamespace(level=2, race_features=_yuanti_rf())
    display_name_low, err_low, changed_low = ws_handlers._apply_innate_spell_usage(low_level, "suggestion")
    assert display_name_low is None
    assert err_low is not None and "3 уровня" in err_low
    assert changed_low is False

    ch = SimpleNamespace(level=3, race_features=_yuanti_rf())
    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "suggestion")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "suggestion")

    assert err_1 is None
    assert display_name_1 == "Внушение"
    assert changed_1 is True
    assert display_name_2 is None
    assert err_2 is not None and "долгого отдыха" in err_2
    assert changed_2 is False
    runtime = (ch.race_features or {}).get("runtime") or {}
    assert runtime.get("yuanti_suggestion_used") is True
    assert runtime.get("yuanti_last_innate_spell") == "suggestion"

    assert ws_handlers._reset_racial_rest_uses(ch, long_rest=True) is True
    runtime_after = (ch.race_features or {}).get("runtime") or {}
    assert runtime_after.get("yuanti_suggestion_used") is False
    assert runtime_after.get("yuanti_last_innate_spell") is None
