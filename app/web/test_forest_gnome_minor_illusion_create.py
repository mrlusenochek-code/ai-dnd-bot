from __future__ import annotations

import asyncio
import json

from app.web import http_routes
from app.web.test_gnome_features import _create_payload, _setup_create_mocks


def test_forest_gnome_minor_illusion_is_persisted_in_innate_spellcasting(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            _create_payload(
                uid=7811,
                subrace_id="forest_gnome",
            )
        )
    )
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    features = race_features.get("features") or {}
    innate_spellcasting = features.get("innate_spellcasting") or {}
    forest_gnome_cantrip = features.get("forest_gnome_cantrip") or {}
    speak_small_beasts = features.get("speak_with_small_beasts") or {}

    assert innate_spellcasting.get("type") == "innate_spellcasting"
    assert innate_spellcasting.get("ability") == "int"
    spells = innate_spellcasting.get("spells") or []
    assert spells == [{"name": "minor_illusion", "frequency": "at_will", "min_level": 1}]

    assert forest_gnome_cantrip.get("type") == "innate_spellcasting"
    assert forest_gnome_cantrip.get("ability") == "int"
    assert ((forest_gnome_cantrip.get("spell") or {}).get("name") or "") == "minor_illusion"

    innate_spells = race_features.get("innate_spells") or []
    minor_illusion = next(
        item for item in innate_spells
        if isinstance(item, dict) and str(item.get("name") or "").strip().lower() == "minor_illusion"
    )
    assert minor_illusion.get("ability") == "int"
    assert minor_illusion.get("frequency") == "at_will"

    assert speak_small_beasts.get("type") == "speak_with_beasts"
    assert speak_small_beasts.get("scope") == "small_or_smaller_beasts"
