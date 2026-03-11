from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.web import http_routes
from app.web.ws_gameplay import _detect_chat_combat_action


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


def test_orc_create_applies_asi_languages_and_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(
        http_routes.api_character_create(
            {
                "session_id": "test-session",
                "uid": 1011,
                "name": "Orc Hero",
                "class_id": "",
                "custom_class": "Adventurer",
                "race_id": "orc",
                "stats": {"str": 50, "dex": 50, "con": 50, "int": 5, "wis": 50, "cha": 50},
                "race_choices": {},
            }
        )
    )

    assert response.status_code == 200
    character = (json.loads(response.body).get("character") or {})
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("str") or 0) == 60
    assert int(stats.get("con") or 0) == 55
    assert int(stats.get("int") or 0) == 5

    senses = race_features.get("senses") or {}
    assert int(senses.get("darkvision_ft") or 0) == 60

    langs = set(race_features.get("languages") or [])
    assert {"common", "orc"} == langs

    prof = race_features.get("proficiencies") or {}
    assert "intimidation" in set(prof.get("skills") or [])

    features = race_features.get("features") or {}
    runtime = race_features.get("runtime") or {}
    assert isinstance(features.get("adrenaline_rush"), dict)
    assert isinstance(features.get("powerful_build"), dict)
    assert int(runtime.get("adrenaline_rush_uses_used") or 0) == 0


def test_orc_combat_action_detection_and_ui_texts() -> None:
    assert _detect_chat_combat_action("прилив адреналина") == "combat_adrenaline_rush"
    assert _detect_chat_combat_action("adrenaline rush") == "combat_adrenaline_rush"
    assert _detect_chat_combat_action("агрессивный") == "combat_adrenaline_rush"
    assert _detect_chat_combat_action("агрессия") == "combat_adrenaline_rush"

    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Угрожающий: владение Запугивание" in template
    assert "Прилив адреналина: бонусным действием совершаете Рывок и получаете temp HP = PB" in template
    assert "Мощное телосложение: считается на 1 размер больше для переноски/толкания/тяги/подъёма" in template
