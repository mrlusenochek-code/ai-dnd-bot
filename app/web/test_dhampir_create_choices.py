from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

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


def _base_payload() -> dict[str, Any]:
    return {
        "session_id": "test-session",
        "uid": 9911,
        "name": "Dhampir Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "dhampir",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {
            "size": "small",
            "flex_asi": {"variant": "2_1", "stats": ["con", "dex"]},
            "skills": ["stealth", "perception"],
            "languages": ["elvish"],
        },
    }


def test_dhampir_create_choices_persist_and_apply(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["uid"] = 9912

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200
    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    rf = character.get("race_features") or {}
    choices = rf.get("choices") or {}
    senses = rf.get("senses") or {}
    needs = rf.get("needs") or {}
    prof = rf.get("proficiencies") or {}
    features = rf.get("features") or {}
    speeds = rf.get("speeds") or {}

    assert int(stats.get("con") or 0) == 60
    assert int(stats.get("dex") or 0) == 55
    assert int(speeds.get("walk_ft") or 0) == 35
    assert int(speeds.get("climb_ft") or 0) == 35
    assert int(senses.get("darkvision_ft") or 0) == 60
    assert "breathe" in set(needs.get("no_need") or [])
    assert str(rf.get("creature_type") or "").strip().lower() == "humanoid"
    assert isinstance(features.get("ancestral_legacy"), dict)
    assert isinstance(features.get("spider_climb"), dict)
    assert isinstance(features.get("vampiric_bite"), dict)
    assert choices.get("size") == "small"
    assert (choices.get("flex_asi") or {}).get("variant") == "2_1"
    assert choices.get("skills") == ["stealth", "perception"]
    assert choices.get("languages") == ["elvish"]
    assert "elvish" in set(rf.get("languages") or [])
    assert {"stealth", "perception"}.issubset(set(prof.get("skills") or []))


def test_dhampir_create_requires_size(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["race_choices"].pop("size", None)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))
    assert exc.value.status_code == 400


def test_dhampir_create_requires_flex_asi(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["race_choices"].pop("flex_asi", None)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))
    assert exc.value.status_code == 400


def test_dhampir_create_requires_two_skills(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["race_choices"]["skills"] = ["stealth"]
    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))
    assert exc.value.status_code == 400


def test_dhampir_create_rejects_common_language(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["race_choices"]["languages"] = ["common"]
    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))
    assert exc.value.status_code == 400


def test_dhampir_create_rejects_duplicate_skill_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["race_choices"]["skills"] = ["stealth", "stealth"]
    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))
    assert exc.value.status_code == 400
