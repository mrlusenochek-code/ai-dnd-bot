from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
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
        "uid": 1212,
        "name": "Tabaxi Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "tabaxi",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }


def test_tabaxi_create_without_extra_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("dex") or 0) == 60
    assert int(stats.get("cha") or 0) == 55

    langs = [str(x).strip().lower() for x in (race_features.get("languages") or [])]
    assert langs == ["common", "tabaxi"]

    senses = race_features.get("senses") or {}
    assert int(senses.get("darkvision_ft") or 0) == 60

    prof = race_features.get("proficiencies") or {}
    skills = {str(x).strip().lower() for x in (prof.get("skills") or [])}
    assert {"perception", "stealth"} <= skills

    speeds = race_features.get("speeds") or {}
    assert int(speeds.get("walk_ft") or 0) == 30
    assert int(speeds.get("climb_ft") or 0) == 20

    features = race_features.get("features") or {}
    feline = features.get("feline_agility") or {}
    claws = features.get("cat_claws") or {}
    assert feline.get("double_speed") is True
    assert claws.get("damage_dice") == "1d4"
    assert claws.get("damage_type") == "slashing"

    runtime = race_features.get("runtime") or {}
    assert runtime.get("feline_agility_available") is True
    assert runtime.get("feline_agility_active") is False


def test_tabaxi_create_does_not_require_subrace_or_race_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200


def test_tabaxi_ui_texts_present_in_templates() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Кошачий талант: Восприятие, Скрытность" in session_template
    assert "Когти кошки: скорость лазания" in session_template
    assert "Кошачья ловкость готова: в свой ход можете удвоить скорость." in session_template
    assert "Кошачья ловкость восстановится, если завершите свой ход без движения." in session_template
