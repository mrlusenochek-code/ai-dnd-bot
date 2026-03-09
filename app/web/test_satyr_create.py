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
        "uid": 605,
        "name": "Satyr Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "satyr",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {"tools": ["lute"]},
    }


def test_satyr_create_requires_instrument_and_persists_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("cha") or 0) == 60
    assert int(stats.get("dex") or 0) == 55
    assert str(race_features.get("creature_type") or "").strip().lower() == "fey"

    speeds = race_features.get("speeds") or {}
    assert int(speeds.get("walk_ft") or 0) == 35

    langs = [str(x).strip().lower() for x in (race_features.get("languages") or [])]
    assert langs == ["common", "sylvan"]

    prof = race_features.get("proficiencies") or {}
    prof_skills = {str(x).strip().lower() for x in (prof.get("skills") or [])}
    prof_tools = {str(x).strip().lower() for x in (prof.get("tools") or [])}
    assert {"performance", "persuasion"} <= prof_skills
    assert "lute" in prof_tools

    natural_weapons = race_features.get("natural_weapons") or []
    ram = next((x for x in natural_weapons if str((x or {}).get("key") or "").strip().lower() == "ram"), {})
    assert str(ram.get("damage_dice") or "").strip().lower() == "1d4"
    assert str(ram.get("damage_type") or "").strip().lower() == "bludgeoning"
    assert str(ram.get("ability") or "").strip().lower() == "str"

    features = race_features.get("features") or {}
    assert isinstance(features.get("magic_resistance"), dict)
    assert isinstance(features.get("mirthful_leaps"), dict)
    assert isinstance(features.get("reveler"), dict)

    choices = race_features.get("choices") or {}
    assert (choices.get("tools") or []) == ["lute"]


def test_satyr_create_rejects_missing_or_invalid_instrument(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload_missing = _base_payload()
    payload_missing["race_choices"] = {}
    try:
        asyncio.run(http_routes.api_character_create(payload_missing))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        assert "tool" in str(getattr(exc, "detail", exc)).lower() or "instrument" in str(getattr(exc, "detail", exc)).lower()

    payload_bad = _base_payload()
    payload_bad["race_choices"] = {"tools": ["thieves_tools"]}
    try:
        asyncio.run(http_routes.api_character_create(payload_bad))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        assert "invalid race tool choice" in str(getattr(exc, "detail", exc)).lower()


def test_satyr_ui_texts_present_in_templates() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    create_template = (Path(__file__).resolve().parents[0] / "templates" / "character_create.html").read_text(encoding="utf-8")

    assert "Таран: рога 1к4 + СИЛ дробящий (природное оружие)" in session_template
    assert "Сопротивление магии: преимущество на спасброски от заклинаний и прочих магических эффектов" in session_template
    assert "Зрелищные прыжки: +1к8 футов к прыжку в длину/высоту" in session_template
    assert "Гуляка: владение Выступление, Убеждение; музыкальный инструмент:" in session_template
    assert '"lute": "Лютня"' in create_template
    assert '"bagpipes": "Волынка"' in create_template


def test_satyr_jump_action_detection() -> None:
    assert _detect_chat_combat_action("jump long") == "combat_jump"
    assert _detect_chat_combat_action("jump high") == "combat_jump"
    assert _detect_chat_combat_action("прыгаю в длину") == "combat_jump"
    assert _detect_chat_combat_action("прыгаю в высоту") == "combat_jump"
