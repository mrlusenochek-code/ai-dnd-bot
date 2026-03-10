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


def test_high_elf_selected_cantrip_is_persisted_as_innate_spell(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 7011,
                "name": "High Elf",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "elf",
                "subrace_id": "high_elf",
                "race_choices": {"languages": ["draconic"], "cantrips": ["fire_bolt"]},
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    choices = race_features.get("choices") or {}
    assert choices.get("cantrips") == ["fire_bolt"]

    features = race_features.get("features") or {}
    high_elf_cantrip = features.get("high_elf_cantrip") or {}
    innate_spellcasting = features.get("innate_spellcasting") or {}
    assert high_elf_cantrip.get("type") == "innate_spellcasting"
    assert high_elf_cantrip.get("ability") == "int"
    assert ((high_elf_cantrip.get("spell") or {}).get("name") or "") == "fire_bolt"

    innate_spells = race_features.get("innate_spells") or []
    fire_bolt = next(
        item for item in innate_spells
        if isinstance(item, dict) and str(item.get("name") or "").strip().lower() == "fire_bolt"
    )
    assert fire_bolt.get("ability") == "int"
    assert fire_bolt.get("frequency") == "at_will"
    assert int(fire_bolt.get("min_level") or 0) == 1
    assert innate_spellcasting.get("ability") == "int"
