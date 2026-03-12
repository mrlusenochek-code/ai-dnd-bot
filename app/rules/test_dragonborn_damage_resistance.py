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


def _create_dragonborn(monkeypatch, ancestry: str) -> dict[str, Any]:
    _setup_create_mocks(monkeypatch)
    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 4013,
                "name": f"Dragonborn {ancestry}",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "dragonborn",
                "race_choices": {"draconic_ancestry": ancestry},
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200
    character = json.loads(response.body).get("character") or {}
    return character.get("race_features") or {}


def test_dragonborn_ancestry_persists_correct_resistance_mapping(monkeypatch) -> None:
    blue_features = _create_dragonborn(monkeypatch, "blue")
    blue_resistances = {str(x).strip().lower() for x in (blue_features.get("resistances") or [])}
    assert "lightning" in blue_resistances
    blue_structured = ((blue_features.get("features") or {}).get("draconic_resistance") or {})
    assert blue_structured.get("type") == "damage_resistance"
    assert blue_structured.get("damage") == ["lightning"]
    assert blue_structured.get("from_choice") == "draconic_ancestry"

    red_features = _create_dragonborn(monkeypatch, "red")
    red_resistances = {str(x).strip().lower() for x in (red_features.get("resistances") or [])}
    assert "fire" in red_resistances
    red_structured = ((red_features.get("features") or {}).get("draconic_resistance") or {})
    assert red_structured.get("type") == "damage_resistance"
    assert red_structured.get("damage") == ["fire"]
    assert red_structured.get("from_choice") == "draconic_ancestry"


def test_non_dragonborn_does_not_gain_draconic_resistance_feature() -> None:
    race = next((item for item in http_routes.RACE_CATALOG if str(item.get("key") or "") == "human"), None)
    assert race is not None
    race_features = http_routes._build_race_features({"details": race})
    resistances = {str(x).strip().lower() for x in (race_features.get("resistances") or [])}
    assert "fire" not in resistances
    assert "lightning" not in resistances
    assert "draconic_resistance" not in ((race_features.get("features") or {}))
