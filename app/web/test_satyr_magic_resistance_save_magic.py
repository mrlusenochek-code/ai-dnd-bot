from __future__ import annotations

from app.web import ws_handlers


def test_satyr_magic_resistance_grants_advantage_on_save_magic() -> None:
    race_features = {"features": {"magic_resistance": {"applies_to": "all_magic_saves"}}}
    mode = ws_handlers._effective_save_mode("normal", race_features, "wis", vs_magic=True)
    assert mode == "advantage"


def test_satyr_magic_resistance_does_not_override_disadvantage() -> None:
    race_features = {"features": {"magic_resistance": {"applies_to": "all_magic_saves"}}}
    mode = ws_handlers._effective_save_mode("disadvantage", race_features, "wis", vs_magic=True)
    assert mode == "disadvantage"
