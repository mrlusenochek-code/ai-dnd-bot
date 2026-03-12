from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_kenku_create import _base_payload, _setup_create_mocks


def test_kenku_mimicry_feature_persists_on_create(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    race_features = character.get("race_features") or {}
    features = race_features.get("features") or {}
    mimicry = features.get("mimicry") or {}

    assert mimicry.get("type") == "mimicry"
    counter = mimicry.get("counter_check") or {}
    assert str(counter.get("ability") or "").strip().lower() == "wis"
    assert str(counter.get("skill") or "").strip().lower() == "insight"
    assert isinstance(features.get("expert_forgery"), dict)


def test_non_kenku_does_not_gain_mimicry(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = {
        "session_id": "non-kenku-mimicry-session",
        "uid": 99101,
        "name": "Human Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "human",
        "subrace_id": "",
        "race_choices": {"languages": ["elvish"]},
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    race_features = character.get("race_features") or {}
    features = race_features.get("features") or {}

    assert "mimicry" not in features
