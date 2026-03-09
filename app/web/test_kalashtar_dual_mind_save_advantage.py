from __future__ import annotations

from app.rules.character_catalog import resolve_race
from app.web import http_routes, ws_handlers


def test_kalashtar_build_race_features_persists_wis_save_advantage() -> None:
    kalashtar = resolve_race("kalashtar")
    assert isinstance(kalashtar, dict)

    race_features = http_routes._build_race_features(kalashtar)
    saves = race_features.get("saves") or {}
    advantage = [str(x).strip().lower() for x in (saves.get("advantage") or [])]
    assert advantage == ["wis"]


def test_kalashtar_effective_save_mode_auto_advantage_for_wis_only() -> None:
    race_features = {"saves": {"advantage": ["wis"]}}
    mode_wis = ws_handlers._effective_save_mode("normal", race_features, "wis")
    mode_cha = ws_handlers._effective_save_mode("normal", race_features, "cha")
    assert mode_wis == "advantage"
    assert mode_cha == "normal"
