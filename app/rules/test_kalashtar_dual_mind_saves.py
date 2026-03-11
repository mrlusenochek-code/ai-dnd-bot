from __future__ import annotations

from app.web import ws_handlers


def test_kalashtar_dual_mind_applies_only_to_wis_saves() -> None:
    race_features = {
        "features": {
            "dual_mind": {
                "type": "save_advantage",
                "abilities": ["wis"],
            }
        },
        "saves": {"advantage": ["wis"]},
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "wis") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "int") == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "cha") == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "str") == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "dex") == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "con") == "normal"


def test_non_kalashtar_character_gets_no_dual_mind_reason() -> None:
    race_features = {"saves": {}}

    assert ws_handlers._effective_save_mode("normal", race_features, "wis") == "normal"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis") == ""
