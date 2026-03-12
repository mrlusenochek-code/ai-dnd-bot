from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_race_asi_applied import _setup_create_mocks


def test_earth_genasi_persists_structured_terrain_trait(monkeypatch) -> None:
    captured: dict[str, object] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1006,
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
    movement = race_features.get("movement") or {}
    assert movement.get("ignore_difficult_terrain") == ["earth", "stone"]

    captured_rf = captured.get("race_features") or {}
    captured_movement = captured_rf.get("movement") if isinstance(captured_rf, dict) else {}
    assert captured_movement == {"ignore_difficult_terrain": ["earth", "stone"]}


def test_non_earth_genasi_do_not_get_earth_walk_metadata(monkeypatch) -> None:
    captured: dict[str, object] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1007,
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
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    movement = race_features.get("movement") or {}
    assert "ignore_difficult_terrain" not in movement
