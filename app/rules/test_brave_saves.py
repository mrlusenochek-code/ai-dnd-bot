from __future__ import annotations

from app.web import ws_handlers


def test_brave_applies_only_to_saves_vs_frightened() -> None:
    race_features = {
        "features": {
            "brave": {
                "type": "save_advantage_vs_condition",
                "conditions": ["frightened"],
            }
        },
        "saves": {"advantage_conditions": ["frightened"]},
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="frightened") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "cha", vs_tag="испуг") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="charmed") == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "str", vs_tag="frightened") == "advantage"


def test_non_brave_character_gets_no_brave_reason() -> None:
    race_features = {"saves": {}}

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="frightened") == "normal"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_tag="frightened") == ""
