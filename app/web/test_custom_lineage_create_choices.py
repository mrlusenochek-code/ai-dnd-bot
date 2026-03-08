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
    feat_key = str((http_routes.FEATS_CATALOG[0] or {}).get("key") or "alert").strip().lower()
    return {
        "session_id": "test-session",
        "uid": 9811,
        "name": "Custom Lineage Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "custom_lineage",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {
            "size": "small",
            "asi": [{"stat": "dex", "bonus": 2}],
            "feats": [feat_key],
            "variable_trait": "darkvision_60",
            "languages": ["elvish"],
        },
    }


def test_custom_lineage_darkvision_choice_persists_and_applies(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["uid"] = 9812

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200
    character = json.loads(response.body).get("character") or {}

    stats = character.get("stats") or {}
    rf = character.get("race_features") or {}
    choices = rf.get("choices") or {}
    senses = rf.get("senses") or {}

    assert int(stats.get("dex") or 0) == 60
    assert str(rf.get("size") or "").strip().lower() == "small"
    assert int(senses.get("darkvision_ft") or 0) == 60
    assert choices.get("size") == "small"
    assert choices.get("asi") == [{"stat": "dex", "bonus": 2}]
    assert choices.get("feats") == payload["race_choices"]["feats"]
    assert choices.get("variable_trait") == "darkvision_60"
    assert choices.get("languages") == ["elvish"]


def test_custom_lineage_skill_choice_adds_skill_and_has_no_darkvision(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["uid"] = 9813
    payload["race_choices"]["variable_trait"] = "skill_proficiency_choice_1"
    payload["race_choices"]["skills"] = ["stealth"]

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200
    character = json.loads(response.body).get("character") or {}

    rf = character.get("race_features") or {}
    choices = rf.get("choices") or {}
    prof = rf.get("proficiencies") or {}
    senses = rf.get("senses") or {}

    assert choices.get("variable_trait") == "skill_proficiency_choice_1"
    assert choices.get("skills") == ["stealth"]
    assert "stealth" in (prof.get("skills") or [])
    assert senses.get("darkvision_ft") in (None, 0)


def test_custom_lineage_create_requires_size(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    del payload["race_choices"]["size"]

    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))
    assert exc.value.status_code == 400


def test_custom_lineage_create_requires_feat(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    del payload["race_choices"]["feats"]

    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))
    assert exc.value.status_code == 400


def test_custom_lineage_create_requires_variable_trait(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    del payload["race_choices"]["variable_trait"]

    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))
    assert exc.value.status_code == 400


def test_custom_lineage_create_requires_language(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    del payload["race_choices"]["languages"]

    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))
    assert exc.value.status_code == 400


def test_custom_lineage_skill_trait_requires_skill_choice(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["race_choices"]["variable_trait"] = "skill_proficiency_choice_1"
    payload["race_choices"].pop("skills", None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))
    assert exc.value.status_code == 400
