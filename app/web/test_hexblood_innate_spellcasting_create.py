from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_race_asi_applied import _setup_create_mocks


def test_hexblood_innate_spellcasting_is_persisted_in_common_format(monkeypatch) -> None:
    captured: dict[str, object] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 9201,
                "name": "Hexblood Hero",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "hexblood",
                "subrace_id": "",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
                "race_choice_innate_ability": "wis",
                "race_choices": {
                    "size": "small",
                    "languages": ["elvish"],
                    "skills": ["arcana", "insight"],
                    "flex_asi": {"variant": "2_1", "stats": ["dex", "wis"]},
                },
            }
        )
    )

    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    choices = race_features.get("choices") or {}
    features = race_features.get("features") or {}
    innate_spellcasting = features.get("innate_spellcasting") or {}
    hex_magic = features.get("hex_magic") or {}

    assert str(choices.get("innate_spellcasting_ability") or "").strip().lower() == "wis"

    assert innate_spellcasting.get("type") == "innate_spellcasting"
    assert innate_spellcasting.get("ability") == "wis"
    assert hex_magic.get("ability") == "wis"
    assert str(hex_magic.get("shared_group") or "").strip().lower() == "hex_magic"
    assert str(hex_magic.get("shared_recharge") or "").strip().lower() == "per_long_rest"

    spells = innate_spellcasting.get("spells") or []
    spell_map = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in spells
        if isinstance(item, dict)
    }
    assert (spell_map.get("disguise_self") or {}).get("frequency") == "shared_1_per_long_rest"
    assert int((spell_map.get("disguise_self") or {}).get("min_level") or 0) == 1
    assert (spell_map.get("hex") or {}).get("frequency") == "shared_1_per_long_rest"
    assert int((spell_map.get("hex") or {}).get("min_level") or 0) == 1

    innate_spells = race_features.get("innate_spells") or []
    by_name = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in innate_spells
        if isinstance(item, dict)
    }
    assert str((by_name.get("disguise_self") or {}).get("ability") or "").strip().lower() == "wis"
    assert str((by_name.get("hex") or {}).get("ability") or "").strip().lower() == "wis"
