from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_gith_create_githyanki import _base_payload, _setup_create_mocks
from app.web.test_gith_create_githzerai import _payload


def test_githyanki_innate_spellcasting_is_persisted_in_common_format(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    features = race_features.get("features") or {}
    innate_spellcasting = features.get("innate_spellcasting") or {}
    runtime = race_features.get("runtime") or {}

    assert innate_spellcasting.get("type") == "innate_spellcasting"
    assert innate_spellcasting.get("ability") == "int"
    spells = innate_spellcasting.get("spells") or []
    spell_map = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in spells
        if isinstance(item, dict)
    }
    assert (spell_map.get("mage_hand") or {}).get("frequency") == "at_will"
    assert (spell_map.get("jump") or {}).get("frequency") == "1_per_long_rest"
    assert int((spell_map.get("jump") or {}).get("min_level") or 0) == 3
    assert (spell_map.get("misty_step") or {}).get("frequency") == "1_per_long_rest"
    assert int((spell_map.get("misty_step") or {}).get("min_level") or 0) == 5
    assert runtime.get("githyanki_jump_used") is False
    assert runtime.get("githyanki_misty_step_used") is False


def test_githzerai_innate_spellcasting_is_persisted_in_common_format(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_payload()))
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    features = race_features.get("features") or {}
    innate_spellcasting = features.get("innate_spellcasting") or {}
    runtime = race_features.get("runtime") or {}

    assert innate_spellcasting.get("type") == "innate_spellcasting"
    assert innate_spellcasting.get("ability") == "wis"
    spells = innate_spellcasting.get("spells") or []
    spell_map = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in spells
        if isinstance(item, dict)
    }
    assert (spell_map.get("mage_hand") or {}).get("frequency") == "at_will"
    assert (spell_map.get("shield") or {}).get("frequency") == "1_per_long_rest"
    assert int((spell_map.get("shield") or {}).get("min_level") or 0) == 3
    assert (spell_map.get("detect_thoughts") or {}).get("frequency") == "1_per_long_rest"
    assert int((spell_map.get("detect_thoughts") or {}).get("min_level") or 0) == 5
    assert runtime.get("githzerai_shield_used") is False
    assert runtime.get("githzerai_detect_thoughts_used") is False
