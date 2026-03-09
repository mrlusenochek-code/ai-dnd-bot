from __future__ import annotations

from app.rules.character_catalog import resolve_race
from app.web import http_routes, ws_handlers


def test_locathah_build_race_features_has_all_leviathans_will_conditions() -> None:
    locathah = resolve_race("locathah")
    assert isinstance(locathah, dict)

    race_features = http_routes._build_race_features(locathah)
    saves = race_features.get("saves") or {}
    conditions = {str(x).strip().lower() for x in (saves.get("advantage_conditions") or [])}
    assert {"frightened", "poisoned", "charmed", "stunned", "paralyzed", "sleep"}.issubset(conditions)


def test_locathah_effective_save_mode_grants_advantage_for_leviathans_will_tags() -> None:
    race_features = {
        "saves": {
            "advantage_conditions": ["frightened", "poisoned", "charmed", "stunned", "paralyzed", "sleep"],
        }
    }
    assert ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="frightened") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="sleep") == "advantage"
