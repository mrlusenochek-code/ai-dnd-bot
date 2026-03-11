from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace
from typing import Any

from app.web import http_routes


class _FakeScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _FakeDb:
    def __init__(self, session_player: Any) -> None:
        self._session_player = session_player

    async def execute(self, _query: Any) -> _FakeScalarResult:
        return _FakeScalarResult(self._session_player)


class _FakeSessionCtx:
    def __init__(self, db: _FakeDb) -> None:
        self._db = db

    async def __aenter__(self) -> _FakeDb:
        return self._db

    async def __aexit__(self, _exc_type, _exc, _tb) -> bool:
        return False


def _setup_create_mocks(monkeypatch) -> None:
    sess = SimpleNamespace(id=uuid.uuid4(), title="Test Session", settings={}, is_active=False)
    player = SimpleNamespace(id=uuid.uuid4())
    session_player = SimpleNamespace(is_active=True, is_admin=False, join_order=1)
    fake_db = _FakeDb(session_player=session_player)

    monkeypatch.setattr(http_routes, "AsyncSessionLocal", lambda: _FakeSessionCtx(fake_db))

    async def _fake_get_session(_db, _session_id):
        return sess

    async def _fake_get_or_create_player_web(_db, _uid, _name):
        return player

    async def _fake_get_character(_db, _sid, _pid):
        return None

    async def _fake_create_character(_db, _sid, _pid, **kwargs):
        return SimpleNamespace(
            name=str(kwargs.get("name") or ""),
            stats=dict(kwargs.get("stats") or {}),
            race_features=dict(kwargs.get("race_features") or {}),
        )

    async def _noop(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(http_routes, "get_session", _fake_get_session)
    monkeypatch.setattr(http_routes, "get_or_create_player_web", _fake_get_or_create_player_web)
    monkeypatch.setattr(http_routes, "get_character", _fake_get_character)
    monkeypatch.setattr(http_routes, "create_character", _fake_create_character)
    monkeypatch.setattr(http_routes, "_upsert_starter_skills", _noop)
    monkeypatch.setattr(http_routes, "add_system_event", _noop)
    monkeypatch.setattr(
        http_routes,
        "_char_to_payload",
        lambda ch: {
            "stats": dict(getattr(ch, "stats", {}) or {}),
            "race_features": dict(getattr(ch, "race_features", {}) or {}),
        },
    )


def _payload() -> dict[str, Any]:
    return {
        "session_id": "test-session",
        "uid": 1919,
        "name": "Pureblood",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "yuan_ti_pureblood",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }


def test_yuanti_create_without_extra_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("cha") or 0) == 60
    assert int(stats.get("int") or 0) == 55

    langs = [str(x).strip().lower() for x in (race_features.get("languages") or [])]
    assert langs == ["common", "draconic", "abyssal"]

    senses = race_features.get("senses") or {}
    assert int(senses.get("darkvision_ft") or 0) == 60

    immunities = race_features.get("immunities") or {}
    assert "poison" in {str(x).strip().lower() for x in (immunities.get("damage") or [])}
    assert "poisoned" in {str(x).strip().lower() for x in (immunities.get("conditions") or [])}

    features = race_features.get("features") or {}
    poison_immunity = features.get("poison_immunity") or {}
    magic_resistance = features.get("magic_resistance") or {}
    innate_spellcasting = features.get("innate_spellcasting") or {}
    assert poison_immunity.get("type") == "damage_and_condition_immunity"
    assert magic_resistance.get("type") == "magic_resistance"
    assert magic_resistance.get("advantage_on_saves_vs") == ["spells", "magical_effects"]
    assert innate_spellcasting.get("type") == "innate_spellcasting"

    innate_spells = race_features.get("innate_spells") or []
    innate_names = [str((x or {}).get("name") or "").strip().lower() for x in innate_spells if isinstance(x, dict)]
    assert innate_names == ["poison_spray", "animal_friendship", "suggestion"]

    runtime = race_features.get("runtime") or {}
    assert runtime.get("yuanti_suggestion_used") is False
    assert runtime.get("yuanti_last_innate_spell") is None


def test_yuanti_create_does_not_require_subrace_or_race_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    response = asyncio.run(http_routes.api_character_create(_payload()))
    assert response.status_code == 200
