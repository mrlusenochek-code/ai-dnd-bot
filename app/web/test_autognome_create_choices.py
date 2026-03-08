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
        "uid": 9511,
        "name": "Autognome Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "autognome",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }


def test_autognome_create_choices_persist_and_apply(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload = _base_payload()
    payload["uid"] = 9512
    payload["race_choices"] = {
        "flex_asi": {"variant": "2_1", "stats": ["str", "dex"]},
        "tools": ["tinkers_tools", "smith_tools"],
        "languages": ["elvish"],
    }
    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("str") or 0) == 60
    assert int(stats.get("dex") or 0) == 55

    choices = race_features.get("choices") or {}
    assert (choices.get("flex_asi") or {}).get("variant") == "2_1"
    assert (choices.get("flex_asi") or {}).get("stats") == ["str", "dex"]
    assert choices.get("tools") == ["tinkers_tools", "smith_tools"]
    assert choices.get("languages") == ["elvish"]

    prof = race_features.get("proficiencies") or {}
    tools = set(prof.get("tools") or [])
    assert "tinkers_tools" in tools
    assert "smith_tools" in tools

    languages = set(race_features.get("languages") or [])
    assert "elvish" in languages

    assert str(race_features.get("creature_type") or "") == "construct"
    resistances = set(race_features.get("resistances") or [])
    assert "poison" in resistances
    immunities = race_features.get("immunities") or {}
    assert "diseased" in (immunities.get("conditions") or [])
    saves = race_features.get("saves") or {}
    advantage_conditions = set(saves.get("advantage_conditions") or [])
    assert "poisoned" in advantage_conditions
    assert "paralyzed" in advantage_conditions
    needs = race_features.get("needs") or {}
    no_need = set(needs.get("no_need") or [])
    assert {"eat", "drink", "breathe"}.issubset(no_need)

    nat_armor = race_features.get("natural_armor") or {}
    assert str(nat_armor.get("ac_formula") or "") == "13 + dex_mod"
    assert bool(nat_armor.get("no_armor_stack")) is True

    features = race_features.get("features") or {}
    assert isinstance(features.get("sentry_rest"), dict)
    assert isinstance(features.get("built_for_success"), dict)
    assert isinstance(features.get("mending_heal"), dict)
    assert features.get("healing_spells_affect_construct") is True
