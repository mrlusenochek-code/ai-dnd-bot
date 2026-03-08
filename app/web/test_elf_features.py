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
            speed_ft=int(kwargs.get("speed_ft") or 0),
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
            "speed_ft": int(getattr(ch, "speed_ft", 0) or 0),
        },
    )


def _create_payload(**kwargs) -> dict[str, Any]:
    payload = {
        "session_id": "test-session",
        "uid": 6011,
        "name": "Elf Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "elf",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }
    payload.update(kwargs)
    return payload


def test_base_elf_persists_core_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_create_payload(uid=6012)))
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    senses = race_features.get("senses") or {}
    prof = race_features.get("proficiencies") or {}
    saves = race_features.get("saves") or {}
    immunities = race_features.get("immunities") or {}

    assert int(senses.get("darkvision_ft") or 0) == 60
    assert "perception" in (prof.get("skills") or [])
    assert "charmed" in (saves.get("advantage_conditions") or [])
    assert "magic_sleep" in (immunities.get("conditions") or [])


def test_high_elf_persists_language_and_cantrip_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            _create_payload(
                uid=6013,
                subrace_id="high_elf",
                race_choices={"languages": ["draconic"], "cantrips": ["fire_bolt"]},
            )
        )
    )
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    choices = race_features.get("choices") or {}
    assert choices.get("languages") == ["draconic"]
    assert choices.get("cantrips") == ["fire_bolt"]


def test_wood_elf_has_walk_speed_35(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            _create_payload(
                uid=6014,
                subrace_id="wood_elf",
            )
        )
    )
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    race_features = character.get("race_features") or {}
    speeds = race_features.get("speeds") or {}

    assert int(speeds.get("walk_ft") or 0) == 35
    assert int(character.get("speed_ft") or 0) == 35


def test_drow_persists_darkvision_sunlight_marker_and_magic(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            _create_payload(
                uid=6015,
                subrace_id="drow",
            )
        )
    )
    assert response.status_code == 200

    race_features = ((json.loads(response.body).get("character") or {}).get("race_features") or {})
    senses = race_features.get("senses") or {}
    features = race_features.get("features") or {}
    innate_spells = race_features.get("innate_spells") or []
    innate_spell_names = {str(item.get("name") or "").strip().lower() for item in innate_spells if isinstance(item, dict)}

    assert int(senses.get("darkvision_ft") or 0) == 120
    assert isinstance(features.get("sunlight_sensitivity"), list)
    assert "dancing_lights" in innate_spell_names
    assert "faerie_fire" in innate_spell_names
    assert "darkness" in innate_spell_names
