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


def _base_payload() -> dict[str, Any]:
    return {
        "session_id": "test-session",
        "uid": 551,
        "name": "Hare Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "harengon",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {
            "size": "small",
            "languages": ["elvish"],
            "flex_asi": {"variant": "2_1", "stats": ["dex", "wis"]},
        },
    }


def test_harengon_create_requires_choices_and_persists_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("dex") or 0) == 60
    assert int(stats.get("wis") or 0) == 55

    assert str(race_features.get("size") or "").strip().lower() == "small"
    assert (race_features.get("languages") or []) == ["common", "elvish"]

    prof = race_features.get("proficiencies") or {}
    assert "perception" in (prof.get("skills") or [])

    features = race_features.get("features") or {}
    assert isinstance(features.get("hare_trigger"), dict)
    assert isinstance(features.get("lucky_footwork"), dict)
    assert isinstance(features.get("rabbit_hop"), dict)
    runtime = race_features.get("runtime") or {}
    assert int(runtime.get("rabbit_hop_uses_used") or 0) == 0

    choices = race_features.get("choices") or {}
    assert str(choices.get("size") or "").strip().lower() == "small"
    assert (choices.get("languages") or []) == ["elvish"]
    flex = choices.get("flex_asi") or {}
    assert str(flex.get("variant") or "").strip().lower() == "2_1"


def test_harengon_create_rejects_missing_size(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    (payload.get("race_choices") or {}).pop("size", None)

    try:
        asyncio.run(http_routes.api_character_create(payload))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc))
        assert "size" in detail.lower()


def test_harengon_create_rejects_missing_flex_asi(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    (payload.get("race_choices") or {}).pop("flex_asi", None)

    try:
        asyncio.run(http_routes.api_character_create(payload))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc))
        assert "flex" in detail.lower() or "asi" in detail.lower()


def test_harengon_create_rejects_common_or_invalid_language(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload_common = _base_payload()
    payload_common["race_choices"]["languages"] = ["common"]
    try:
        asyncio.run(http_routes.api_character_create(payload_common))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc))
        assert "common" in detail.lower()

    payload_many = _base_payload()
    payload_many["race_choices"]["languages"] = ["elvish", "elvish"]
    try:
        asyncio.run(http_routes.api_character_create(payload_many))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc))
        assert "language" in detail.lower() or "exactly 1" in detail.lower()


def test_harengon_combat_action_detection() -> None:
    assert _detect_chat_combat_action("кроличий прыжок") == "combat_rabbit_hop"
    assert _detect_chat_combat_action("rabbit hop") == "combat_rabbit_hop"
    assert _detect_chat_combat_action("сильные ноги") == "combat_lucky_footwork"
    assert _detect_chat_combat_action("lucky footwork") == "combat_lucky_footwork"


def test_harengon_ui_texts_present_in_session_template() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Заячье сердце: +БМ к инициативе" in template
    assert "Сильные ноги: реакцией после провала спасброска Ловкости" in template
    assert "Кроличий прыжок: статус" in template
