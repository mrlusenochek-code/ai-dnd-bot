from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_race_asi_applied import _setup_create_mocks


def test_water_genasi_persists_swim_speed_and_amphibious(monkeypatch) -> None:
    captured: dict[str, object] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1008,
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
    speeds = race_features.get("speeds") or {}
    breath = race_features.get("breath") or {}
    features = race_features.get("features") or {}
    resistances = race_features.get("resistances") or []

    assert int(speeds.get("swim_ft") or 0) == 30
    assert breath.get("amphibious") is True
    assert features.get("amphibious") is True
    assert "acid" in resistances

    captured_rf = captured.get("race_features") or {}
    captured_speeds = captured_rf.get("speeds") if isinstance(captured_rf, dict) else {}
    assert int((captured_speeds or {}).get("swim_ft") or 0) == 30


def test_non_water_genasi_do_not_get_swim_speed_or_amphibious(monkeypatch) -> None:
    captured: dict[str, object] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1009,
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
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    speeds = race_features.get("speeds") or {}
    breath = race_features.get("breath") or {}
    assert "swim_ft" not in speeds
    assert breath.get("amphibious") is not True
