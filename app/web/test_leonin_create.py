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
        "uid": 5001,
        "name": "Leonin Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "leonin",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {"skills": ["perception"]},
    }


def test_leonin_create_requires_one_skill_and_persists_roar_and_claws(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("con") or 0) == 60
    assert int(stats.get("str") or 0) == 55

    speeds = race_features.get("speeds") or {}
    assert int(speeds.get("walk_ft") or 0) == 35
    assert (race_features.get("languages") or []) == ["common", "leonin"]

    senses = race_features.get("senses") or {}
    assert int(senses.get("darkvision_ft") or 0) == 60

    natural_weapons = race_features.get("natural_weapons") or []
    claws = next((x for x in natural_weapons if str((x or {}).get("key") or "").strip().lower() == "claws_leonin"), {})
    assert str(claws.get("damage_dice") or "").strip().lower() == "1d4"
    assert str(claws.get("damage_type") or "").strip().lower() == "slashing"
    assert str(claws.get("ability") or "").strip().lower() == "str"

    prof = race_features.get("proficiencies") or {}
    skills = [str(x).strip().lower() for x in (prof.get("skills") or [])]
    assert "perception" in skills

    features = race_features.get("features") or {}
    roar = features.get("daunting_roar") or {}
    assert isinstance(roar, dict)
    assert str(roar.get("activation") or "").strip().lower() == "bonus_action"
    assert int(roar.get("uses_max") or 0) == 1
    assert str(roar.get("uses") or "").strip().lower() == "per_short_or_long_rest"

    choices = race_features.get("choices") or {}
    assert (choices.get("skills") or []) == ["perception"]


def test_leonin_create_rejects_missing_or_invalid_skill(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload_no_skill = _base_payload()
    payload_no_skill["race_choices"]["skills"] = []
    try:
        asyncio.run(http_routes.api_character_create(payload_no_skill))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "skill" in detail

    payload_bad_skill = _base_payload()
    payload_bad_skill["race_choices"]["skills"] = ["arcana"]
    try:
        asyncio.run(http_routes.api_character_create(payload_bad_skill))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "invalid race skill choice" in detail or "skill" in detail


def test_leonin_ui_texts_present_in_session_template() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Когти: природное оружие 1к4 + СИЛ рубящий" in template
    assert "Инстинкты охотника: владение навыком" in template
    assert "Устрашающий рёв: бонусным действием" in template
