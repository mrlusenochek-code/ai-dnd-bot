from __future__ import annotations

from app.web import ws_handlers


def test_fey_ancestry_applies_only_to_saves_vs_charmed() -> None:
    race_features = {
        "features": {
            "fey_ancestry": {
                "type": "fey_ancestry",
                "advantage_on_saves_vs": ["charmed"],
                "immune_to_magical_sleep": True,
            }
        },
        "saves": {"advantage_conditions": ["charmed"]},
        "immunities": {"conditions": ["magic_sleep"]},
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="charmed") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "cha", vs_tag="очарование") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="frightened") == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "dex", vs_tag="charmed") == "advantage"


def test_non_fey_ancestry_character_gets_no_fey_ancestry_reason() -> None:
    race_features = {"saves": {}}

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="charmed") == "normal"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_tag="charmed") == ""
