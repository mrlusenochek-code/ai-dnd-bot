from __future__ import annotations

import asyncio
import json

from app.test_helpers.race_create_helpers import firbolg_base_payload
from app.test_helpers.race_create_helpers import setup_basic_create_mocks
from app.web import http_routes


def _setup_create_mocks(monkeypatch) -> None:
    setup_basic_create_mocks(monkeypatch, session_title="Firbolg Session")


def test_firbolg_create_has_fixed_asi_and_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = firbolg_base_payload()
    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("wis") or 0) == 60
    assert int(stats.get("str") or 0) == 55

    languages = set(race_features.get("languages") or [])
    assert {"common", "elvish", "giant"} <= languages

    spells = race_features.get("innate_spells") or []
    assert isinstance(spells, list)
    by_name = {
        str(spell.get("name") or "").strip().lower(): spell
        for spell in spells
        if isinstance(spell, dict)
    }
    assert "detect_magic" in by_name
    assert "disguise_self" in by_name
    assert by_name["detect_magic"].get("frequency") == "shared_1_per_short_or_long_rest"
    assert by_name["detect_magic"].get("shared_group") == "firbolg_magic"
    assert by_name["detect_magic"].get("shared_recharge") == "per_short_or_long_rest"
    assert by_name["detect_magic"].get("ability") == "wis"
    assert by_name["disguise_self"].get("frequency") == "shared_1_per_short_or_long_rest"
    assert by_name["disguise_self"].get("shared_group") == "firbolg_magic"
    assert by_name["disguise_self"].get("shared_recharge") == "per_short_or_long_rest"
    assert by_name["disguise_self"].get("ability") == "wis"

    features = race_features.get("features") or {}
    assert isinstance(features.get("hidden_step"), dict)
    assert isinstance(features.get("firbolg_magic"), dict)
    assert isinstance(features.get("powerful_build"), dict)
    assert isinstance(features.get("speech_of_beast_and_leaf"), dict)
    assert ((features.get("firbolg_magic") or {}).get("special") or {}).get("disguise_self_height_delta_ft") == -3
    runtime = race_features.get("runtime") or {}
    hidden_runtime = runtime.get("hidden_step") or {}
    assert hidden_runtime.get("used") == 0
    assert hidden_runtime.get("active") is False

    carry = race_features.get("carry") or {}
    assert carry.get("powerful_build") is True
