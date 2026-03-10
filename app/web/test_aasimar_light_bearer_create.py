from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_race_asi_applied import _setup_create_mocks


def test_aasimar_light_bearer_is_persisted_in_common_innate_format(monkeypatch) -> None:
    captured: dict[str, object] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 3101,
                "name": "Protector Aasimar",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "aasimar",
                "subrace_id": "aasimar_protector",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    features = race_features.get("features") or {}
    innate_spellcasting = features.get("innate_spellcasting") or {}
    light_bearer = features.get("light_bearer") or {}

    assert innate_spellcasting.get("type") == "innate_spellcasting"
    assert innate_spellcasting.get("ability") == "cha"

    spells = innate_spellcasting.get("spells") or []
    spell_map = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in spells
        if isinstance(item, dict)
    }
    assert (spell_map.get("light") or {}).get("frequency") == "at_will"
    assert int((spell_map.get("light") or {}).get("min_level") or 0) == 1

    assert light_bearer.get("type") == "innate_spellcasting"
    assert light_bearer.get("ability") == "cha"
    assert ((light_bearer.get("spell") or {}).get("name") or "") == "light"

    innate_spells = race_features.get("innate_spells") or []
    innate_names = {
        str((item or {}).get("name") or "").strip().lower()
        for item in innate_spells
        if isinstance(item, dict)
    }
    assert "light" in innate_names

