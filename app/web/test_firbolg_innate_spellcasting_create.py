from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_firbolg_create import _setup_create_mocks


def test_firbolg_innate_spellcasting_is_persisted_in_common_format(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "firbolg-session",
                "uid": 8126,
                "name": "Firbolg Hero",
                "class_id": "",
                "custom_class": "Ranger",
                "race_id": "firbolg",
                "subrace_id": "",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    features = race_features.get("features") or {}
    innate_spellcasting = features.get("innate_spellcasting") or {}

    assert innate_spellcasting.get("type") == "innate_spellcasting"
    assert innate_spellcasting.get("ability") == "wis"
    spells = innate_spellcasting.get("spells") or []
    spell_map = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in spells
        if isinstance(item, dict)
    }
    assert (spell_map.get("detect_magic") or {}).get("frequency") == "shared_1_per_short_or_long_rest"
    assert int((spell_map.get("detect_magic") or {}).get("min_level") or 0) == 1
    assert (spell_map.get("disguise_self") or {}).get("frequency") == "shared_1_per_short_or_long_rest"
    assert int((spell_map.get("disguise_self") or {}).get("min_level") or 0) == 1
