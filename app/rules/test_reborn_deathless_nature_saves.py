from __future__ import annotations

from app.web import ws_handlers


def test_reborn_deathless_nature_grants_advantage_for_disease_poison_and_poisoned() -> None:
    race_features = {
        "features": {
            "deathless_nature": {
                "type": "deathless_nature",
                "advantage_on_saves": ["disease", "poisoned", "death_saves"],
            }
        },
        "saves": {
            "advantage_conditions": ["disease", "poisoned", "death_saves"],
        },
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="disease") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="poison") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="poisoned") == "advantage"
    assert ws_handlers._auto_save_advantage_reason(race_features, "con", vs_tag="disease") == "Deathless Nature"
    assert ws_handlers._auto_save_advantage_reason(race_features, "con", vs_tag="poison") == "Deathless Nature"


def test_reborn_deathless_nature_does_not_apply_to_unrelated_saves() -> None:
    race_features = {
        "features": {
            "deathless_nature": {
                "type": "deathless_nature",
                "advantage_on_saves": ["disease", "poisoned", "death_saves"],
            }
        },
        "saves": {
            "advantage_conditions": ["disease", "poisoned", "death_saves"],
        },
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="frightened") == "normal"
    assert ws_handlers._auto_save_advantage_reason(race_features, "con", vs_tag="frightened") == ""


def test_character_without_deathless_nature_has_no_bonus() -> None:
    race_features = {"features": {}, "saves": {}}

    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="disease") == "normal"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="poison") == "normal"
