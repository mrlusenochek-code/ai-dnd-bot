from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_verdan_race_features import _setup_create_mocks


def test_verdan_limited_telepathy_persists_as_sense_and_feature(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 3012,
                "name": "Verdan Sage",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "verdan",
                "race_choices": {"languages": ["dwarvish"]},
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )

    assert response.status_code == 200
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})

    senses = race_features.get("senses") or {}
    telepathy = senses.get("telepathy") or {}
    assert int(telepathy.get("range_ft") or 0) == 30
    assert telepathy.get("requires_target_language") is True
    assert str(telepathy.get("bandwidth") or "").strip().lower() == "simple_ideas"

    features = race_features.get("features") or {}
    limited_telepathy = features.get("limited_telepathy") or {}
    assert int(limited_telepathy.get("range_ft") or 0) == 30
    assert limited_telepathy.get("requires_target_language") is True
    assert str(limited_telepathy.get("bandwidth") or "").strip().lower() == "simple_ideas"

    assert isinstance(features.get("hit_dice_reroll"), dict)
    growth_spurt = features.get("size_change") or {}
    assert int(growth_spurt.get("at_level") or 0) == 5
