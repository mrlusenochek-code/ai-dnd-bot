from __future__ import annotations

import asyncio
import json
from typing import Any

from app.web import http_routes
from app.web.test_race_asi_applied import _setup_create_mocks


def _create_fire_genasi(monkeypatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 2001,
                "name": "Fire Genasi",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "genasi",
                "subrace_id": "fire_genasi",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200
    return ((json.loads(response.body).get("character") or {}).get("race_features") or {})


def test_fire_genasi_persists_structured_package(monkeypatch) -> None:
    race_features = _create_fire_genasi(monkeypatch)

    resistances = {str(x).strip().lower() for x in (race_features.get("resistances") or [])}
    assert "fire" in resistances

    features = race_features.get("features") or {}
    fire_resistance = features.get("fire_resistance") or {}
    assert fire_resistance.get("type") == "damage_resistance"
    assert fire_resistance.get("damage") == ["fire"]

    innate_spellcasting = features.get("innate_spellcasting") or {}
    assert innate_spellcasting.get("type") == "innate_spellcasting"
    assert innate_spellcasting.get("ability") == "con"
    spells = innate_spellcasting.get("spells") or []
    spell_map = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in spells
        if isinstance(item, dict)
    }
    assert (spell_map.get("produce_flame") or {}).get("frequency") == "at_will"
    assert (spell_map.get("burning_hands") or {}).get("frequency") == "1_per_long_rest"
    assert int((spell_map.get("burning_hands") or {}).get("min_level") or 0) == 3


def test_non_fire_genasi_does_not_gain_fire_package(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 2002,
                "name": "Water Genasi",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "genasi",
                "subrace_id": "water_genasi",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})

    resistances = {str(x).strip().lower() for x in (race_features.get("resistances") or [])}
    assert "fire" not in resistances
    assert "fire_resistance" not in ((race_features.get("features") or {}))
