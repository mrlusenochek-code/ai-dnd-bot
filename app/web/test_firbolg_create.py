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
        title="Firbolg Session",
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


def test_firbolg_create_has_fixed_asi_and_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = {
        "session_id": "test-session",
        "uid": 77701,
        "name": "Firbolg Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "firbolg",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }
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
