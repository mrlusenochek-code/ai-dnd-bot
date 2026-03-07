from __future__ import annotations

from app.rules.character_catalog import resolve_race
from app.web import http_routes, ws_handlers


def test_build_race_features_persists_vedalken_save_advantage() -> None:
    vedalken = resolve_race("vedalken")
    assert isinstance(vedalken, dict)

    race_features = http_routes._build_race_features(vedalken)
    saves = race_features.get("saves") or {}
    advantage = saves.get("advantage") or []
    assert advantage == ["int", "wis", "cha"]


def test_effective_save_mode_auto_advantage_for_vedalken() -> None:
    race_features = {"saves": {"advantage": ["int", "wis", "cha"]}}
    mode = ws_handlers._effective_save_mode("normal", race_features, "int")
    assert mode == "advantage"


def test_effective_save_mode_does_not_override_disadvantage() -> None:
    race_features = {"saves": {"advantage": ["int", "wis", "cha"]}}
    mode = ws_handlers._effective_save_mode("disadvantage", race_features, "int")
    assert mode == "disadvantage"
