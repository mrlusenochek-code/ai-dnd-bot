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


def _setup_create_mocks(monkeypatch, *, captured: dict[str, Any]) -> None:
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

    monkeypatch.setattr(http_routes, "get_session", _fake_get_session)
    monkeypatch.setattr(http_routes, "get_or_create_player_web", _fake_get_or_create_player_web)
    monkeypatch.setattr(http_routes, "get_character", _fake_get_character)

    async def _fake_create_character(_db, _sid, _pid, **kwargs):
        stats = dict(kwargs.get("stats") or {})
        race_features = dict(kwargs.get("race_features") or {})
        captured["stats"] = stats
        captured["race_features"] = race_features
        return SimpleNamespace(name=str(kwargs.get("name") or ""), stats=stats, race_features=race_features)

    async def _noop(*_args, **_kwargs) -> None:
        return None

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


def test_character_create_applies_race_asi_aarakocra(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1001,
                "name": "ASI Hero",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "aarakocra",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
                "gender": "",
                "race": "",
                "description": "",
            }
        )
    )

    assert response.status_code == 200
    payload = json.loads(response.body)
    stats = ((payload.get("character") or {}).get("stats") or {})
    assert stats.get("dex") == 60
    assert stats.get("wis") == 55
    assert (captured.get("stats") or {}).get("dex") == 60
    assert (captured.get("stats") or {}).get("wis") == 55


def test_character_create_applies_race_and_subrace_asi_genasi(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1002,
                "name": "ASI Hero 2",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "genasi",
                "subrace_id": "air_genasi",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
                "gender": "",
                "race": "",
                "description": "",
            }
        )
    )

    assert response.status_code == 200
    payload = json.loads(response.body)
    stats = ((payload.get("character") or {}).get("stats") or {})
    assert stats.get("con") == 60
    assert stats.get("dex") == 55
    assert (captured.get("stats") or {}).get("con") == 60
    assert (captured.get("stats") or {}).get("dex") == 55


def test_air_genasi_persists_unlimited_hold_breath(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1003,
                "name": "Air Genasi",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "genasi",
                "subrace_id": "air_genasi",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    breath = race_features.get("breath") or {}
    assert breath.get("hold") == "unlimited"


def test_water_genasi_persists_amphibious_and_swim_speed(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1004,
                "name": "Water Genasi",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "genasi",
                "subrace_id": "water_genasi",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    breath = race_features.get("breath") or {}
    speeds = race_features.get("speeds") or {}
    assert breath.get("amphibious") is True
    assert int(speeds.get("swim_ft") or 0) == 30


def test_earth_genasi_persists_ignore_difficult_terrain(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1005,
                "name": "Earth Genasi",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "genasi",
                "subrace_id": "earth_genasi",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    movement = race_features.get("movement") or {}
    assert movement.get("ignore_difficult_terrain") == ["earth", "stone"]


def test_fire_genasi_persists_innate_spells(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _setup_create_mocks(monkeypatch, captured=captured)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1006,
                "name": "Fire Genasi",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "genasi",
                "subrace_id": "fire_genasi",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200
    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    innate_spells = race_features.get("innate_spells") or []
    names = [str(item.get("name") or "") for item in innate_spells if isinstance(item, dict)]
    assert "produce_flame" in names
    assert "burning_hands" in names
