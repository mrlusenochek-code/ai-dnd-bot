from __future__ import annotations

from app.rules.character_catalog import resolve_race
from app.web.http_routes import _build_race_features


def test_aasimar_celestial_resistance_is_persisted_in_structured_format() -> None:
    race = resolve_race("aasimar")
    assert race is not None

    race_features = _build_race_features({"details": race})

    resistances = {str(x).strip().lower() for x in (race_features.get("resistances") or [])}
    assert "necrotic" in resistances
    assert "radiant" in resistances

    features = race_features.get("features") or {}
    celestial_resistance = features.get("celestial_resistance") or {}
    assert celestial_resistance.get("type") == "damage_resistance"
    assert celestial_resistance.get("damage") == ["necrotic", "radiant"]


def test_non_aasimar_does_not_gain_celestial_resistance() -> None:
    race = resolve_race("human")
    assert race is not None

    race_features = _build_race_features({"details": race})

    resistances = {str(x).strip().lower() for x in (race_features.get("resistances") or [])}
    assert "necrotic" not in resistances
    assert "radiant" not in resistances

    features = race_features.get("features") or {}
    assert "celestial_resistance" not in features
