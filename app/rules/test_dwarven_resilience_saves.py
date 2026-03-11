from __future__ import annotations

from app.web import ws_handlers


def test_dwarven_resilience_applies_only_to_poison_saves() -> None:
    race_features = {
        "features": {
            "dwarven_resilience": {
                "type": "poison_resilience",
                "advantage_on_saves_vs": ["poison"],
                "damage_resistance": ["poison"],
            }
        },
        "saves": {"advantage_conditions": ["poison"]},
        "resistances": ["poison"],
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="poison") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="poisoned") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="charmed") == "normal"


def test_non_dwarf_character_gets_no_dwarven_resilience_reason() -> None:
    race_features = {"saves": {}}

    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="poison") == "normal"
    assert ws_handlers._auto_save_advantage_reason(race_features, "con", vs_tag="poison") == ""
