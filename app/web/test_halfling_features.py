from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace
from typing import Any

from app.web import http_routes
from app.web import ws_handlers


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


def _create_halfling(monkeypatch, *, uid: int, subrace_id: str = "") -> dict[str, Any]:
    _setup_create_mocks(monkeypatch)
    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": uid,
                "name": "Halfling Hero",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "halfling",
                "subrace_id": subrace_id,
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
            }
        )
    )
    assert response.status_code == 200
    return (json.loads(response.body).get("character") or {}).get("race_features") or {}


def test_halfling_persists_lucky_brave_and_nimbleness(monkeypatch) -> None:
    race_features = _create_halfling(monkeypatch, uid=9011)

    features = race_features.get("features") or {}
    saves = race_features.get("saves") or {}

    reroll_ones = features.get("reroll_ones") or {}
    scope = set(reroll_ones.get("scope") or [])
    assert {"attack", "check", "save"}.issubset(scope)
    brave = features.get("brave") or {}
    assert brave.get("type") == "save_advantage_vs_condition"
    assert brave.get("conditions") == ["frightened"]
    assert features.get("move_through_larger_creatures") is True
    assert "frightened" in (saves.get("advantage_conditions") or [])


def test_lightfoot_halfling_persists_naturally_stealthy_marker(monkeypatch) -> None:
    race_features = _create_halfling(monkeypatch, uid=9012, subrace_id="lightfoot")

    features = race_features.get("features") or {}
    assert features.get("hide_with_larger_cover") is True


def test_stout_halfling_persists_poison_resilience(monkeypatch) -> None:
    race_features = _create_halfling(monkeypatch, uid=9013, subrace_id="stout")

    saves = race_features.get("saves") or {}
    resistances = race_features.get("resistances") or []
    assert "poison" in (saves.get("advantage_conditions") or [])
    assert "poison" in resistances


def test_effective_save_mode_auto_advantage_vs_frightened_for_halfling() -> None:
    race_features = {
        "saves": {
            "advantage_conditions": ["frightened"],
        }
    }
    mode = ws_handlers._effective_save_mode("normal", race_features, "wis", vs_tag="frightened")
    assert mode == "advantage"


def test_effective_save_mode_keeps_disadvantage_vs_poison() -> None:
    race_features = {
        "saves": {
            "advantage_conditions": ["poison"],
        }
    }
    mode = ws_handlers._effective_save_mode("disadvantage", race_features, "con", vs_tag="poison")
    assert mode == "disadvantage"
