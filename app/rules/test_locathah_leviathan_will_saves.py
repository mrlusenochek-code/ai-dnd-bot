from __future__ import annotations

from app.web import ws_handlers


def test_leviathan_will_applies_only_to_matching_condition_saves() -> None:
    race_features = {
        "features": {
            "leviathan_will": {
                "type": "save_advantage_vs_condition",
                "conditions": ["frightened", "poisoned", "charmed", "stunned", "paralyzed", "sleep"],
            }
        },
        "saves": {
            "advantage_conditions": ["frightened", "poisoned", "charmed", "stunned", "paralyzed", "sleep"],
        },
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="charmed") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="frightened") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="paralyzed") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="poisoned") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="poison") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="stunned") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="sleep") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="disease") == "normal"


def test_leviathan_will_reason_only_appears_for_matching_saves() -> None:
    race_features = {
        "features": {
            "leviathan_will": {
                "type": "save_advantage_vs_condition",
                "conditions": ["frightened", "poisoned", "charmed", "stunned", "paralyzed", "sleep"],
            }
        },
        "saves": {
            "advantage_conditions": ["frightened", "poisoned", "charmed", "stunned", "paralyzed", "sleep"],
        },
    }

    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_tag="charmed") == "Leviathan Will"
    assert ws_handlers._auto_save_advantage_reason(race_features, "con", vs_tag="poison") == "Leviathan Will"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_tag="sleep") == "Leviathan Will"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_tag="disease") == ""


def test_non_locathah_character_gets_no_leviathan_will_bonus() -> None:
    race_features = {"features": {}, "saves": {}}

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="charmed") == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="sleep") == "normal"
