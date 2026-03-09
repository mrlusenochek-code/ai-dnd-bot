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
        "uid": 777,
        "name": "Grung Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "grung",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }


def test_grung_create_persists_json_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("dex") or 0) == 60
    assert int(stats.get("con") or 0) == 55

    languages = [str(x).strip().lower() for x in (race_features.get("languages") or [])]
    assert languages == ["grung"]

    speeds = race_features.get("speeds") or {}
    assert int(speeds.get("walk_ft") or 0) == 25
    assert int(speeds.get("climb_ft") or 0) == 25

    immunities = race_features.get("immunities") or {}
    assert "poison" in (immunities.get("damage") or [])
    assert "poisoned" in (immunities.get("conditions") or [])

    prof = race_features.get("proficiencies") or {}
    assert "perception" in (prof.get("skills") or [])

    features = race_features.get("features") or {}
    assert features.get("amphibious") is True

    poisonous_skin = features.get("poisonous_skin") or {}
    assert int(poisonous_skin.get("contact_save_dc") or 0) == 12
    contact = poisonous_skin.get("contact_condition") or {}
    assert str(contact.get("condition") or "").strip().lower() == "poisoned"
    assert str(contact.get("duration") or "").strip().lower() == "1_minute"

    weapon_poison = poisonous_skin.get("weapon_poison") or {}
    assert str(weapon_poison.get("requires") or "").strip().lower() == "piercing_weapon"
    assert int(weapon_poison.get("save_dc") or 0) == 12
    assert str(weapon_poison.get("damage") or "").strip().lower() == "2d4"

    standing_leap = features.get("standing_leap") or {}
    assert int(standing_leap.get("long_jump_ft") or 0) == 25
    assert int(standing_leap.get("high_jump_ft") or 0) == 15

    water_dependency = features.get("water_dependency") or {}
    assert str(water_dependency.get("required_immersion_per_day") or "").strip().lower() == "1_hour"
    assert str(water_dependency.get("penalty") or "").strip().lower() == "exhaustion_1"

    runtime = race_features.get("runtime") or {}
    assert runtime.get("grung_weapon_poison_armed") is False
    assert str(runtime.get("water_last_immersion_at") or "") == ""
    assert int(runtime.get("water_dependency_exhaustion_level") or 0) == 0
