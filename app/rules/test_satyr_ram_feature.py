from __future__ import annotations

from app.rules.character_catalog import resolve_race
from app.web.http_routes import _build_race_features


def test_satyr_ram_is_persisted_as_structured_natural_weapon() -> None:
    race = resolve_race("satyr")
    assert race is not None

    race_features = _build_race_features({"details": race})

    natural_weapons = race_features.get("natural_weapons") or []
    ram = next((x for x in natural_weapons if str((x or {}).get("key") or "").strip().lower() == "ram"), {})
    assert str(ram.get("kind") or "").strip().lower() == "unarmed"
    assert str(ram.get("damage_dice") or "").strip().lower() == "1d4"
    assert str(ram.get("damage_type") or "").strip().lower() == "bludgeoning"
    assert str(ram.get("ability") or "").strip().lower() == "str"

    features = race_features.get("features") or {}
    ram_feature = features.get("ram") or {}
    assert ram_feature.get("type") == "natural_weapon"
    assert ram_feature.get("name") == "ram"
    assert ram_feature.get("name_ru") == "Таран"
    assert ram_feature.get("damage_dice") == "1d4"
    assert ram_feature.get("damage_type") == "bludgeoning"
    assert ram_feature.get("ability") == "str"
    assert ram_feature.get("kind") == "unarmed"


def test_non_satyr_does_not_gain_ram_feature() -> None:
    race = resolve_race("human")
    assert race is not None

    race_features = _build_race_features({"details": race})

    natural_weapon_keys = {
        str((x or {}).get("key") or "").strip().lower()
        for x in (race_features.get("natural_weapons") or [])
        if isinstance(x, dict)
    }
    assert "ram" not in natural_weapon_keys

    features = race_features.get("features") or {}
    assert "ram" not in features
