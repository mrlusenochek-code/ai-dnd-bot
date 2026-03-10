from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_elf_features import _create_payload, _setup_create_mocks


def test_drow_innate_spellcasting_is_persisted_in_common_format(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            _create_payload(
                uid=6125,
                subrace_id="drow",
            )
        )
    )
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    features = race_features.get("features") or {}
    innate_spellcasting = features.get("innate_spellcasting") or {}
    runtime = race_features.get("runtime") or {}

    assert innate_spellcasting.get("type") == "innate_spellcasting"
    assert innate_spellcasting.get("ability") == "cha"

    spells = innate_spellcasting.get("spells") or []
    spell_map = {
        str((item or {}).get("name") or "").strip().lower(): item
        for item in spells
        if isinstance(item, dict)
    }
    assert (spell_map.get("dancing_lights") or {}).get("frequency") == "at_will"
    assert int((spell_map.get("dancing_lights") or {}).get("min_level") or 0) == 1
    assert (spell_map.get("faerie_fire") or {}).get("frequency") == "1_per_long_rest"
    assert int((spell_map.get("faerie_fire") or {}).get("min_level") or 0) == 3
    assert (spell_map.get("darkness") or {}).get("frequency") == "1_per_long_rest"
    assert int((spell_map.get("darkness") or {}).get("min_level") or 0) == 5

    innate_spells = race_features.get("innate_spells") or []
    innate_names = {
        str((item or {}).get("name") or "").strip().lower()
        for item in innate_spells
        if isinstance(item, dict)
    }
    assert {"dancing_lights", "faerie_fire", "darkness"} <= innate_names

    assert runtime.get("drow_faerie_fire_used") is False
    assert runtime.get("drow_darkness_used") is False
