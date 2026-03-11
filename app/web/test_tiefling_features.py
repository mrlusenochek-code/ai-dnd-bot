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
    sess = SimpleNamespace(
        id=uuid.uuid4(),
        title="Test Session",
        settings={},
        is_active=False,
    )
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


def _create_payload(**kwargs) -> dict[str, Any]:
    payload = {
        "session_id": "test-session",
        "uid": 9111,
        "name": "Tiefling Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "tiefling",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }
    payload.update(kwargs)
    return payload


def test_tiefling_persists_infernal_legacy_and_fire_resistance(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_create_payload(uid=9112)))
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    resistances = [str(x).strip().lower() for x in (race_features.get("resistances") or [])]
    assert "fire" in resistances
    features = race_features.get("features") or {}
    hellish_resistance = features.get("hellish_resistance") or {}
    assert hellish_resistance.get("type") == "damage_resistance"
    assert hellish_resistance.get("damage") == ["fire"]

    innate_spells = race_features.get("innate_spells") or []
    spell_map = {
        str(item.get("name") or "").strip().lower(): item
        for item in innate_spells
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }

    thaumaturgy = spell_map.get("thaumaturgy") or {}
    assert str(thaumaturgy.get("frequency") or "").strip().lower() == "at_will"
    assert int(thaumaturgy.get("min_level") or 0) == 1
    assert str(thaumaturgy.get("ability") or "").strip().lower() == "cha"

    hellish_rebuke = spell_map.get("hellish_rebuke") or {}
    assert str(hellish_rebuke.get("frequency") or "").strip().lower() == "1_per_long_rest"
    assert int(hellish_rebuke.get("min_level") or 0) == 3

    darkness = spell_map.get("darkness") or {}
    assert str(darkness.get("frequency") or "").strip().lower() == "1_per_long_rest"
    assert int(darkness.get("min_level") or 0) == 5
