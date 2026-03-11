from __future__ import annotations

from app.web import ws_handlers


def test_vedalken_dispassion_applies_only_to_int_wis_cha_saves() -> None:
    race_features = {
        "features": {
            "vedalken_dispassion": {
                "type": "save_advantage",
                "abilities": ["int", "wis", "cha"],
            }
        },
        "saves": {"advantage": ["int", "wis", "cha"]},
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "int") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "cha") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "str") == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "dex") == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "con") == "normal"


def test_non_vedalken_save_data_gets_no_dispassion_reason_or_advantage() -> None:
    race_features = {"saves": {}}

    assert ws_handlers._effective_save_mode("normal", race_features, "wis") == "normal"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis") == ""
