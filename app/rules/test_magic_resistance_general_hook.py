from __future__ import annotations

from app.web import ws_handlers


def test_magic_resistance_grants_advantage_on_spell_and_magical_effect_saves() -> None:
    race_features = {
        "features": {
            "magic_resistance": {
                "type": "magic_resistance",
                "advantage_on_saves_vs": ["spells", "magical_effects"],
            }
        }
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_magic=True) == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "dex", vs_magic=True) == "advantage"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_magic=True) == "Magic Resistance"


def test_magic_resistance_does_not_apply_to_nonmagical_saves() -> None:
    race_features = {
        "features": {
            "magic_resistance": {
                "type": "magic_resistance",
                "advantage_on_saves_vs": ["spells", "magical_effects"],
            }
        }
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_magic=False) == "normal"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_magic=False) == ""


def test_magic_resistance_is_not_applied_without_feature() -> None:
    race_features = {"features": {}}

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_magic=True) == "normal"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_magic=True) == ""
