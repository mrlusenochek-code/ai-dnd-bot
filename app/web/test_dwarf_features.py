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
            hp_max=int(kwargs.get("hp_max") or 0),
            hp=int(kwargs.get("hp_max") or 0),
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
            "hp_max": int(getattr(ch, "hp_max", 0) or 0),
            "hp": int(getattr(ch, "hp", 0) or 0),
        },
    )


def _create_payload(**kwargs) -> dict[str, Any]:
    payload = {
        "session_id": "test-session",
        "uid": 5011,
        "name": "Dwarf Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "dwarf",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {"tools": ["smith_tools"]},
    }
    payload.update(kwargs)
    return payload


def test_dwarf_persists_darkvision_poison_resilience_and_stonecunning(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_create_payload()))
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    senses = race_features.get("senses") or {}
    resistances = race_features.get("resistances") or []
    saves = race_features.get("saves") or {}
    movement = race_features.get("movement") or {}
    features = race_features.get("features") or {}

    assert int(senses.get("darkvision_ft") or 0) == 60
    dwarven_resilience = features.get("dwarven_resilience") or {}
    assert dwarven_resilience.get("type") == "poison_resilience"
    assert "poison" in resistances
    assert "poison" in (saves.get("advantage_conditions") or [])
    assert movement.get("ignore_heavy_armor_speed_penalty") is True
    assert isinstance(features.get("stonecunning"), dict)


def test_dwarf_tool_choice_persists_in_choices_and_proficiencies(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_create_payload()))
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    choices = race_features.get("choices") or {}
    proficiencies = race_features.get("proficiencies") or {}
    assert choices.get("tools") == ["smith_tools"]
    assert "smith_tools" in (proficiencies.get("tools") or [])


def test_hill_dwarf_gets_plus_one_hp_max_on_create(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            _create_payload(
                uid=5012,
                class_id="fighter",
                custom_class="",
                subrace_id="hill_dwarf",
            )
        )
    )
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    expected_hp_max = int((http_routes.CLASS_PRESETS.get("fighter") or {}).get("hp_max") or 0) + 1
    assert int(character.get("hp_max") or 0) == expected_hp_max
    assert int(character.get("hp") or 0) == expected_hp_max


def test_mountain_dwarf_persists_armor_proficiencies(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            _create_payload(
                uid=5013,
                subrace_id="mountain_dwarf",
            )
        )
    )
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    armor = ((race_features.get("proficiencies") or {}).get("armor") or [])
    assert "light" in armor
    assert "medium" in armor
