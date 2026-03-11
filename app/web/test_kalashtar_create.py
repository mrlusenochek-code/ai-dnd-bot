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
        "uid": 712,
        "name": "Kal Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "kalashtar",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {
            "languages": ["elvish"],
        },
    }


def test_kalashtar_create_requires_language_and_persists_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("wis") or 0) == 60
    assert int(stats.get("cha") or 0) == 55

    langs = [str(x).strip().lower() for x in (race_features.get("languages") or [])]
    assert langs == ["common", "quori", "elvish"]

    resist = [str(x).strip().lower() for x in (race_features.get("resistances") or [])]
    assert "psychic" in resist

    saves = race_features.get("saves") or {}
    advantage = [str(x).strip().lower() for x in (saves.get("advantage") or [])]
    assert advantage == ["wis"]

    features = race_features.get("features") or {}
    dual_mind = features.get("dual_mind") or {}
    assert dual_mind.get("type") == "save_advantage"
    assert dual_mind.get("abilities") == ["wis"]
    mental_discipline = features.get("mental_discipline") or {}
    assert mental_discipline.get("type") == "damage_resistance"
    assert mental_discipline.get("damage") == ["psychic"]
    mind_link = features.get("mind_link") or {}
    assert str(mind_link.get("range_formula") or "").strip().lower() == "level*10"
    assert str(mind_link.get("allow_reply_duration") or "").strip().lower() == "1_hour"
    assert bool(mind_link.get("one_target_reply")) is True

    dream = features.get("dream_immunity") or {}
    assert bool(dream.get("not_sleep_immunity")) is True

    choices = race_features.get("choices") or {}
    assert (choices.get("languages") or []) == ["elvish"]


def test_kalashtar_create_rejects_missing_or_duplicate_extra_language(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload_no_lang = _base_payload()
    payload_no_lang["race_choices"]["languages"] = []
    try:
        asyncio.run(http_routes.api_character_create(payload_no_lang))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        assert "language" in str(getattr(exc, "detail", exc)).lower()

    payload_common = _base_payload()
    payload_common["race_choices"]["languages"] = ["common"]
    try:
        asyncio.run(http_routes.api_character_create(payload_common))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "common" in detail or "quori" in detail or "language" in detail

    payload_quori = _base_payload()
    payload_quori["race_choices"]["languages"] = ["quori"]
    try:
        asyncio.run(http_routes.api_character_create(payload_quori))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "quori" in detail or "language" in detail


def test_kalashtar_ui_texts_present_in_session_template() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Двойственность разума" in template
    assert "Связь разумов" in template
    assert "Отделённый от снов" in template
