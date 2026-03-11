from __future__ import annotations

from app.web import ws_handlers


def test_loxodon_serenity_applies_only_to_saves_vs_charmed_or_frightened() -> None:
    race_features = {
        "features": {
            "serenity": {
                "type": "save_advantage_vs_condition",
                "conditions": ["charmed", "frightened"],
            }
        },
        "saves": {"advantage_conditions": ["charmed", "frightened"]},
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="charmed") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="frightened") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "cha", vs_tag="очарование") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "int", vs_tag="испуг") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="poison") == "normal"


def test_non_loxodon_character_gets_no_serenity_reason() -> None:
    race_features = {"saves": {}}

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="charmed") == "normal"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_tag="charmed") == ""
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_tag="frightened") == ""
