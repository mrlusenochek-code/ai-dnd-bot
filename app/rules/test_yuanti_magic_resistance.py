from __future__ import annotations

from app.web import ws_handlers


def test_yuanti_magic_resistance_grants_advantage_on_magic_saves() -> None:
    race_features = {"features": {"magic_resistance": {"applies_to": "all_magic_saves"}}}

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_magic=True) == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "dex", vs_magic=True) == "advantage"


def test_yuanti_magic_resistance_does_not_apply_to_nonmagical_saves() -> None:
    race_features = {"features": {"magic_resistance": {"applies_to": "all_magic_saves"}}}

    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_magic=False) == "normal"
