from __future__ import annotations

import asyncio
import json
from typing import Any

from app.web import http_routes
from app.web.test_race_asi_applied import _setup_create_mocks


def _create_air_genasi(monkeypatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 2101,
                "name": "Air Genasi",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "genasi",
                "subrace_id": "air_genasi",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200
    return ((json.loads(response.body).get("character") or {}).get("race_features") or {})


def test_air_genasi_persists_structured_package(monkeypatch) -> None:
    race_features = _create_air_genasi(monkeypatch)

    breath = race_features.get("breath") or {}
    assert breath.get("hold") == "unlimited"

    features = race_features.get("features") or {}
    hold_breath = features.get("hold_breath") or {}
    assert hold_breath.get("type") == "hold_breath"
    assert hold_breath.get("duration") == "unlimited"

    innate_spellcasting = features.get("innate_spellcasting") or {}
    assert innate_spellcasting.get("type") == "innate_spellcasting"
    assert innate_spellcasting.get("ability") == "con"
    spells = innate_spellcasting.get("spells") or []
    spell_map = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in spells
        if isinstance(item, dict)
    }
    assert (spell_map.get("levitate") or {}).get("frequency") == "1_per_long_rest"
    assert int((spell_map.get("levitate") or {}).get("min_level") or 0) == 3


def test_non_air_genasi_does_not_gain_air_package(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 2102,
                "name": "Earth Genasi",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "genasi",
                "subrace_id": "earth_genasi",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})

    breath = race_features.get("breath") or {}
    assert breath.get("hold") != "unlimited"
    innate_spells = race_features.get("innate_spells") or []
    assert "levitate" not in {
        str((item or {}).get("name") or "").strip().lower()
        for item in innate_spells
        if isinstance(item, dict)
    }
