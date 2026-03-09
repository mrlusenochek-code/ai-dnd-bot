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
        lambda ch: {"stats": dict(getattr(ch, "stats", {}) or {}), "race_features": dict(getattr(ch, "race_features", {}) or {})},
    )


def _payload(subrace_id: str = "") -> dict[str, Any]:
    return {
        "session_id": "test-session",
        "uid": 321,
        "name": "Shifter Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "shifter",
        "subrace_id": subrace_id,
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }


def test_shifter_create_requires_subrace(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    try:
        asyncio.run(http_routes.api_character_create(_payload()))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        assert "subrace" in str(getattr(exc, "detail", exc)).lower()


def test_shifter_subrace_asi_only_from_subrace(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    cases = {
        "beasthide": {"con": 60, "str": 55, "dex": 50, "cha": 50, "skill": "athletics"},
        "longtooth": {"str": 60, "dex": 55, "con": 50, "wis": 50, "skill": "intimidation"},
        "swiftstride": {"dex": 60, "cha": 55, "str": 50, "wis": 50, "skill": "acrobatics"},
        "wildhunt": {"wis": 60, "dex": 55, "str": 50, "cha": 50, "skill": "survival"},
    }
    for subrace_id, expected in cases.items():
        response = asyncio.run(http_routes.api_character_create(_payload(subrace_id=subrace_id)))
        assert response.status_code == 200
        character = json.loads(response.body).get("character") or {}
        stats = character.get("stats") or {}
        race_features = character.get("race_features") or {}
        for stat_key, stat_value in expected.items():
            if stat_key == "skill":
                continue
            assert int(stats.get(stat_key) or 0) == stat_value
        assert [str(x).strip().lower() for x in (race_features.get("languages") or [])] == ["common"]
        assert str((race_features.get("choices") or {}).get("subrace_id") or "").strip().lower() == subrace_id
        prof_skills = {str(x).strip().lower() for x in ((race_features.get("proficiencies") or {}).get("skills") or [])}
        assert expected["skill"] in prof_skills
        features = race_features.get("features") or {}
        assert isinstance(features.get("shifting"), dict)


def test_shifter_ui_texts_present() -> None:
    create_template = (Path(__file__).resolve().parents[0] / "templates" / "character_create.html").read_text(encoding="utf-8")
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Для расы «Шифтер» обязательно выбери подрасу." in create_template
    assert "Смена формы: бонусным действием, 1 мин" in session_template
    assert "Зверошкура: +1 КД в форме" in session_template
    assert "Длиннозуб: бонусным действием укус 1к6+СИЛ" in session_template
    assert "Быстроног: +10 скорость в форме" in session_template
    assert "Дикий охотник: «Помеченная цель» 1/к/д" in session_template
