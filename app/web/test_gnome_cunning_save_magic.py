from __future__ import annotations

from app.web import ws_handlers


def test_save_magic_mode_auto_advantage_for_gnome_cunning() -> None:
    race_features = {"saves": {"advantage_vs_magic": ["int", "wis", "cha"]}}
    mode = ws_handlers._effective_save_mode("normal", race_features, "wis", vs_magic=True)
    assert mode == "advantage"


def test_save_magic_disadvantage_is_not_overridden() -> None:
    race_features = {"saves": {"advantage_vs_magic": ["int", "wis", "cha"]}}
    mode = ws_handlers._effective_save_mode("disadvantage", race_features, "wis", vs_magic=True)
    assert mode == "disadvantage"
