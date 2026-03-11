from __future__ import annotations

from app.web import ws_handlers


def test_gnome_cunning_applies_only_to_int_wis_cha_saves_vs_magic() -> None:
    race_features = {
        "features": {
            "gnome_cunning": {
                "type": "save_advantage_vs_magic",
                "abilities": ["int", "wis", "cha"],
            }
        },
        "saves": {"advantage_vs_magic": ["int", "wis", "cha"]},
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "int", vs_magic=True) == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_magic=True) == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "cha", vs_magic=True) == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "str", vs_magic=True) == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "dex", vs_magic=True) == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_magic=True) == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "int", vs_magic=False) == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_magic=False) == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "cha", vs_magic=False) == "normal"


def test_non_gnome_character_gets_no_gnome_cunning_reason() -> None:
    race_features = {"saves": {}}

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_magic=True) == "normal"
    assert ws_handlers._auto_save_advantage_reason(race_features, "wis", vs_magic=True) == ""
