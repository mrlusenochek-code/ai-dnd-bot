from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_verdan_race_features import _setup_create_mocks


def test_verdan_growth_spurt_persists_structured_metadata(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 3013,
                "name": "Verdan Growth",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "verdan",
                "race_choices": {"languages": ["elvish"]},
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )

    assert response.status_code == 200
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})

    assert str(race_features.get("size") or "").strip().lower() == "small"

    features = race_features.get("features") or {}
    growth_spurt = features.get("growth_spurt") or {}
    assert growth_spurt.get("type") == "size_change"
    assert str(growth_spurt.get("from") or "").strip().lower() == "small"
    assert str(growth_spurt.get("to") or growth_spurt.get("size") or "").strip().lower() == "medium"
    assert int(growth_spurt.get("at_level") or growth_spurt.get("level_from") or 0) == 5

    assert isinstance(features.get("limited_telepathy"), dict)
    assert isinstance(features.get("hit_dice_reroll"), dict)


def test_non_verdan_does_not_gain_growth_spurt(monkeypatch) -> None:
    from app.web.test_race_asi_applied import _setup_create_mocks as _setup_other_race_mocks

    captured: dict[str, object] = {}
    _setup_other_race_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 3014,
                "name": "Tiefling",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "tiefling",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )

    assert response.status_code == 200
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    assert "growth_spurt" not in ((race_features.get("features") or {}))
