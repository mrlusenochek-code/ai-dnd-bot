from __future__ import annotations

from app.rules.character_catalog import resolve_race
from app.web.http_routes import _build_race_features


def test_leonin_claws_are_persisted_as_structured_natural_weapon() -> None:
    race = resolve_race("leonin")
    assert race is not None

    race_features = _build_race_features({"details": race})

    natural_weapons = race_features.get("natural_weapons") or []
    claws = next((x for x in natural_weapons if str((x or {}).get("key") or "").strip().lower() == "claws_leonin"), {})
    assert str(claws.get("kind") or "").strip().lower() == "unarmed"
    assert str(claws.get("damage_dice") or "").strip().lower() == "1d4"
    assert str(claws.get("damage_type") or "").strip().lower() == "slashing"
    assert str(claws.get("ability") or "").strip().lower() == "str"

    features = race_features.get("features") or {}
    claws_feature = features.get("claws_leonin") or {}
    assert claws_feature.get("type") == "natural_weapon"
    assert claws_feature.get("name") == "claws_leonin"
    assert claws_feature.get("name_ru") == "Когти"
    assert claws_feature.get("damage_dice") == "1d4"
    assert claws_feature.get("damage_type") == "slashing"
    assert claws_feature.get("ability") == "str"
    assert claws_feature.get("kind") == "unarmed"


def test_non_leonin_does_not_gain_leonin_claws_feature() -> None:
    race = resolve_race("human")
    assert race is not None

    race_features = _build_race_features({"details": race})

    natural_weapon_keys = {
        str((x or {}).get("key") or "").strip().lower()
        for x in (race_features.get("natural_weapons") or [])
        if isinstance(x, dict)
    }
    assert "claws_leonin" not in natural_weapon_keys

    features = race_features.get("features") or {}
    assert "claws_leonin" not in features
