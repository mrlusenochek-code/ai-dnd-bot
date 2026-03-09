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


def _base_payload() -> dict[str, Any]:
    return {
        "session_id": "test-session",
        "uid": 777,
        "name": "Hob Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "hobgoblin",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {
            "martial_weapons": ["longsword", "longbow"],
        },
    }


def test_hobgoblin_create_requires_two_martial_weapons_and_persists(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("con") or 0) == 60
    assert int(stats.get("int") or 0) == 55

    assert (race_features.get("languages") or []) == ["common", "goblin"]
    senses = race_features.get("senses") or {}
    assert int(senses.get("darkvision_ft") or 0) == 60

    prof = race_features.get("proficiencies") or {}
    armor = [str(x).strip().lower() for x in (prof.get("armor") or [])]
    weapons = [str(x).strip().lower() for x in (prof.get("weapons") or [])]
    assert "light" in armor
    assert "longsword" in weapons
    assert "longbow" in weapons

    features = race_features.get("features") or {}
    assert isinstance(features.get("saving_face"), dict)

    choices = race_features.get("choices") or {}
    assert (choices.get("martial_weapons") or []) == ["longsword", "longbow"]


def test_hobgoblin_create_rejects_missing_or_invalid_martial_weapon_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload_missing = _base_payload()
    payload_missing["race_choices"].pop("martial_weapons", None)
    try:
        asyncio.run(http_routes.api_character_create(payload_missing))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "martial" in detail or "weapon" in detail

    payload_one = _base_payload()
    payload_one["race_choices"]["martial_weapons"] = ["longsword"]
    try:
        asyncio.run(http_routes.api_character_create(payload_one))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "exactly 2" in detail or "martial" in detail

    payload_dupes = _base_payload()
    payload_dupes["race_choices"]["martial_weapons"] = ["longsword", "longsword"]
    try:
        asyncio.run(http_routes.api_character_create(payload_dupes))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "distinct" in detail or "martial" in detail
