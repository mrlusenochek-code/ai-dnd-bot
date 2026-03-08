from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace
from typing import Any

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
        stats = dict(kwargs.get("stats") or {})
        race_features = dict(kwargs.get("race_features") or {})
        return SimpleNamespace(name=str(kwargs.get("name") or ""), stats=stats, race_features=race_features)

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
        "uid": 7011,
        "name": "Half-Elf Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "half_elf",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }


def _expect_400(payload: dict[str, Any]) -> None:
    try:
        asyncio.run(http_routes.api_character_create(payload))
        raise AssertionError("Expected HTTPException 400")
    except HTTPException as exc:
        assert exc.status_code == 400


def test_half_elf_create_persists_choices_and_applies_bonuses(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = _base_payload()
    payload["uid"] = 7012
    payload["race_choices"] = {
        "asi": [{"stat": "str", "bonus": 1}, {"stat": "dex", "delta": 1}],
        "skills": ["perception", "stealth"],
        "languages": ["dwarvish"],
    }

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert stats.get("cha") == 60
    assert stats.get("str") == 55
    assert stats.get("dex") == 55

    choices = race_features.get("choices") or {}
    assert choices.get("languages") == ["dwarvish"]
    assert choices.get("skills") == ["perception", "stealth"]
    asi_choices = choices.get("asi") or []
    asi_by_stat = {str(item.get("stat") or ""): int(item.get("bonus") or 0) for item in asi_choices if isinstance(item, dict)}
    assert asi_by_stat.get("str") == 1
    assert asi_by_stat.get("dex") == 1

    prof = race_features.get("proficiencies") or {}
    prof_skills = set(prof.get("skills") or [])
    assert {"perception", "stealth"}.issubset(prof_skills)

    languages = set(race_features.get("languages") or [])
    assert "dwarvish" in languages

    saves = race_features.get("saves") or {}
    immunities = race_features.get("immunities") or {}
    assert "charmed" in (saves.get("advantage_conditions") or [])
    assert "magic_sleep" in (immunities.get("conditions") or [])


def test_half_elf_create_rejects_cha_asi_choice(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = _base_payload()
    payload["uid"] = 7013
    payload["race_choices"] = {
        "asi": [{"stat": "cha", "bonus": 1}, {"stat": "dex", "bonus": 1}],
        "skills": ["perception", "stealth"],
        "languages": ["dwarvish"],
    }

    _expect_400(payload)


def test_half_elf_create_rejects_duplicate_skills(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = _base_payload()
    payload["uid"] = 7014
    payload["race_choices"] = {
        "asi": [{"stat": "str", "bonus": 1}, {"stat": "dex", "bonus": 1}],
        "skills": ["perception", "perception"],
        "languages": ["dwarvish"],
    }

    _expect_400(payload)


def test_half_elf_create_requires_two_asi_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = _base_payload()
    payload["uid"] = 7015
    payload["race_choices"] = {
        "asi": [{"stat": "str", "bonus": 1}],
        "skills": ["perception", "stealth"],
        "languages": ["dwarvish"],
    }

    _expect_400(payload)


def test_half_elf_create_requires_two_skill_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = _base_payload()
    payload["uid"] = 7016
    payload["race_choices"] = {
        "asi": [{"stat": "str", "bonus": 1}, {"stat": "dex", "bonus": 1}],
        "skills": ["perception"],
        "languages": ["dwarvish"],
    }

    _expect_400(payload)


def test_half_elf_create_requires_language_choice(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = _base_payload()
    payload["uid"] = 7017
    payload["race_choices"] = {
        "asi": [{"stat": "str", "bonus": 1}, {"stat": "dex", "bonus": 1}],
        "skills": ["perception", "stealth"],
    }

    _expect_400(payload)
