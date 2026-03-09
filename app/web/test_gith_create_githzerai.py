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
        "uid": 9711,
        "name": "Githzerai Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "gith",
        "subrace_id": "githzerai",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }


def test_githzerai_create_applies_asi_and_race_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    rf = character.get("race_features") or {}

    assert int(stats.get("int") or 0) == 55
    assert int(stats.get("wis") or 0) == 60

    choices = rf.get("choices") or {}
    assert choices.get("subrace_id") == "githzerai"

    languages = {str(x).strip().lower() for x in (rf.get("languages") or [])}
    assert languages == {"common", "gith"}

    saves = rf.get("saves") or {}
    save_conditions = {str(x).strip().lower() for x in (saves.get("advantage_conditions") or [])}
    assert {"charmed", "frightened"}.issubset(save_conditions)

    spells = [item for item in (rf.get("innate_spells") or []) if isinstance(item, dict)]
    by_name = {str(item.get("name") or "").strip().lower(): item for item in spells}

    assert "mage_hand" in by_name
    assert "shield" in by_name
    assert "detect_thoughts" in by_name

    mage_hand = by_name["mage_hand"]
    assert str(mage_hand.get("frequency") or "").strip().lower() == "at_will"
    assert str(mage_hand.get("note") or "").strip().lower() == "invisible"
    assert mage_hand.get("ability") == "wis"
    assert mage_hand.get("no_material_components") is True

    shield = by_name["shield"]
    assert shield.get("ability") == "wis"
    assert int(shield.get("min_level") or 0) == 3
    assert str(shield.get("frequency") or "").strip().lower() == "1_per_long_rest"
    assert shield.get("no_material_components") is True

    detect_thoughts = by_name["detect_thoughts"]
    assert detect_thoughts.get("ability") == "wis"
    assert int(detect_thoughts.get("min_level") or 0) == 5
    assert str(detect_thoughts.get("frequency") or "").strip().lower() == "1_per_long_rest"
    assert detect_thoughts.get("no_material_components") is True
