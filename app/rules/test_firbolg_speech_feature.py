from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_firbolg_create import _setup_create_mocks


def test_firbolg_speech_feature_persists_on_create(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = {
        "session_id": "firbolg-speech-session",
        "uid": 88001,
        "name": "Firbolg Speaker",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "firbolg",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    race_features = character.get("race_features") or {}
    features = race_features.get("features") or {}
    speech = features.get("speech_of_beast_and_leaf") or {}

    assert speech.get("type") == "limited_beast_plant_speech"
    assert speech.get("advantage_on") == ["cha_checks_to_influence_beasts_plants"]
    assert isinstance(features.get("firbolg_magic"), dict)
    assert race_features.get("race_key") == "firbolg"


def test_non_firbolg_does_not_gain_speech_feature(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = {
        "session_id": "non-firbolg-speech-session",
        "uid": 88002,
        "name": "Human Speaker",
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

    assert "speech_of_beast_and_leaf" not in features
