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
        "uid": 313,
        "name": "Kender Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "kender",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choice_innate_ability": "wis",
        "race_choices": {
            "languages": ["elvish"],
            "skills": ["stealth"],
            "flex_asi": {"variant": "2_1", "stats": ["dex", "cha"]},
        },
    }


def test_kender_create_requires_choices_and_persists_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    race_features = character.get("race_features") or {}

    assert (race_features.get("languages") or []) == ["common", "elvish"]
    prof = race_features.get("proficiencies") or {}
    assert "stealth" in (prof.get("skills") or [])

    features = race_features.get("features") or {}
    assert isinstance(features.get("fearless_vs_frightened"), dict)
    taunt = features.get("taunt") or {}
    assert str(taunt.get("chosen_ability") or "").strip().lower() == "wis"

    choices = race_features.get("choices") or {}
    assert (choices.get("languages") or []) == ["elvish"]
    assert (choices.get("skills") or []) == ["stealth"]
    assert str(choices.get("taunt_ability") or "").strip().lower() == "wis"


def test_kender_create_rejects_missing_or_invalid_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload_no_flex = _base_payload()
    payload_no_flex["race_choices"].pop("flex_asi", None)
    try:
        asyncio.run(http_routes.api_character_create(payload_no_flex))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "flex" in detail or "asi" in detail

    payload_common = _base_payload()
    payload_common["race_choices"]["languages"] = ["common"]
    try:
        asyncio.run(http_routes.api_character_create(payload_common))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        assert "common" in str(getattr(exc, "detail", exc)).lower()

    payload_no_skill = _base_payload()
    payload_no_skill["race_choices"]["skills"] = []
    try:
        asyncio.run(http_routes.api_character_create(payload_no_skill))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        assert "skill" in str(getattr(exc, "detail", exc)).lower()

    payload_no_ability = _base_payload()
    payload_no_ability["race_choice_innate_ability"] = ""
    try:
        asyncio.run(http_routes.api_character_create(payload_no_ability))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "ability" in detail or "int" in detail or "wis" in detail or "cha" in detail


def test_kender_combat_action_detection() -> None:
    assert _detect_chat_combat_action("насмешка") == "combat_taunt"
    assert _detect_chat_combat_action("taunt") == "combat_taunt"
    assert _detect_chat_combat_action("бесстрашие") == "combat_fearless"
    assert _detect_chat_combat_action("fearless") == "combat_fearless"


def test_kender_ui_texts_present_in_session_template() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Бесстрашие: преимущество на спасброски против «испуганный»" in template
    assert "Любопытство кендеров: владение навыком" in template
    assert "Насмешка: бонусным действием, Сл = 8 + БМ + мод" in template
