from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_loxodon_create import _base_payload, _setup_create_mocks


def test_loxodon_trunk_feature_persists_on_create(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    race_features = character.get("race_features") or {}
    features = race_features.get("features") or {}
    trunk = features.get("trunk") or {}

    assert trunk.get("type") == "trunk"
    assert int(trunk.get("reach_ft") or 0) == 5
    assert str(trunk.get("lift_lb_formula") or "").strip().lower() == "5*str"
    assert trunk.get("cannot") == ["wield_weapons", "wield_shield", "fine_manipulation", "somatic_components"]
    assert isinstance(features.get("keen_smell"), dict)


def test_non_loxodon_does_not_gain_trunk(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = {
        "session_id": "non-loxodon-trunk-session",
        "uid": 99102,
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

    assert "trunk" not in features
