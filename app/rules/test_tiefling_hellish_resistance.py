from __future__ import annotations

from app.rules.character_catalog import resolve_race
from app.web.http_routes import _build_race_features


def test_tiefling_hellish_resistance_is_persisted_in_structured_format() -> None:
    race = resolve_race("tiefling")
    assert race is not None

    race_features = _build_race_features({"details": race})

    resistances = {str(x).strip().lower() for x in (race_features.get("resistances") or [])}
    assert "fire" in resistances

    features = race_features.get("features") or {}
    hellish_resistance = features.get("hellish_resistance") or {}
    assert hellish_resistance.get("type") == "damage_resistance"
    assert hellish_resistance.get("damage") == ["fire"]


def test_non_tiefling_does_not_gain_hellish_resistance() -> None:
    race = resolve_race("human")
    assert race is not None

    race_features = _build_race_features({"details": race})

    resistances = {str(x).strip().lower() for x in (race_features.get("resistances") or [])}
    assert "fire" not in resistances

    features = race_features.get("features") or {}
    assert "hellish_resistance" not in features
