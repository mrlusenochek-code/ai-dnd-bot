from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_race_asi_applied import _setup_create_mocks


def test_fairy_innate_spellcasting_is_persisted_in_common_format(monkeypatch) -> None:
    captured: dict[str, object] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 9101,
                "name": "Fairy Hero",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "fairy",
                "subrace_id": "",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
                "race_choice_innate_ability": "wis",
                "race_choices": {
                    "languages": ["elvish"],
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
    fairy_magic = features.get("fairy_magic") or {}

    assert str(choices.get("innate_spellcasting_ability") or "").strip().lower() == "wis"
    assert (choices.get("languages") or []) == ["elvish"]

    assert innate_spellcasting.get("type") == "innate_spellcasting"
    assert innate_spellcasting.get("ability") == "wis"
    assert fairy_magic.get("type") == "innate_spellcasting"
    assert fairy_magic.get("ability") == "wis"

    spells = innate_spellcasting.get("spells") or []
    spell_map = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in spells
        if isinstance(item, dict)
    }
    assert (spell_map.get("druidcraft") or {}).get("frequency") == "at_will"
    assert (spell_map.get("faerie_fire") or {}).get("frequency") == "1_per_long_rest"
    assert int((spell_map.get("faerie_fire") or {}).get("min_level") or 0) == 3
    assert (spell_map.get("enlarge_reduce") or {}).get("frequency") == "1_per_long_rest"
    assert int((spell_map.get("enlarge_reduce") or {}).get("min_level") or 0) == 5

    innate_spells = race_features.get("innate_spells") or []
    by_name = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in innate_spells
        if isinstance(item, dict)
    }
    assert str((by_name.get("druidcraft") or {}).get("ability") or "").strip().lower() == "wis"
    assert str((by_name.get("faerie_fire") or {}).get("ability") or "").strip().lower() == "wis"
    assert str((by_name.get("enlarge_reduce") or {}).get("ability") or "").strip().lower() == "wis"


def test_fairy_create_requires_innate_spellcasting_ability_choice(monkeypatch) -> None:
    captured: dict[str, object] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    try:
        asyncio.run(
            http_routes.api_character_create(
                {
                    "session_id": "test-session",
                    "uid": 9102,
                    "name": "Fairy Hero",
                    "class_id": "",
                    "custom_class": "Adventurer",
                    "race_id": "fairy",
                    "subrace_id": "",
                    "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
                    "race_choice_innate_ability": "",
                    "race_choices": {
                        "languages": ["elvish"],
                        "flex_asi": {"variant": "2_1", "stats": ["dex", "wis"]},
                    },
                }
            )
        )
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "ability" in detail or "int/wis/cha" in detail
