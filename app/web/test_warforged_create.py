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
        "uid": 9191,
        "name": "Warforged Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "warforged",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {
            "asi_plus1_stat": "dex",
            "specialized_design_skill": "perception",
            "specialized_design_tool": "tinkers_tools",
            "extra_language": "elvish",
        },
    }


def test_warforged_create_requires_choices_and_persists(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("con") or 0) == 60
    assert int(stats.get("dex") or 0) == 55

    langs = [str(x).strip().lower() for x in (race_features.get("languages") or [])]
    assert langs == ["common", "elvish"]

    prof = race_features.get("proficiencies") or {}
    assert "perception" in {str(x).strip().lower() for x in (prof.get("skills") or [])}
    assert "tinkers_tools" in {str(x).strip().lower() for x in (prof.get("tools") or [])}

    features = race_features.get("features") or {}
    resilience = features.get("constructed_resilience") or {}
    sentry_rest = features.get("sentry_rest") or {}
    integrated = features.get("integrated_protection") or {}
    specialized = features.get("specialized_design") or {}
    extra_lang = features.get("extra_language_choice") or {}

    assert resilience.get("cannot_be_magically_slept") is True
    assert int(sentry_rest.get("long_rest_inert_hours") or 0) == 6
    assert int(integrated.get("ac_bonus") or 0) == 1
    assert specialized.get("chosen_skill") == "perception"
    assert specialized.get("chosen_tool") == "tinkers_tools"
    assert extra_lang.get("chosen") == "elvish"

    choices = race_features.get("choices") or {}
    assert choices.get("asi_plus1_stat") == "dex"
    assert choices.get("specialized_design_skill") == "perception"
    assert choices.get("specialized_design_tool") == "tinkers_tools"
    assert choices.get("extra_language") == "elvish"

    runtime = race_features.get("runtime") or {}
    assert runtime.get("warforged_sentry_rest_active") is False
    assert runtime.get("warforged_integrated_armor_state") is None


def test_warforged_create_rejects_missing_invalid_or_duplicate_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    invalid_payloads = [
        ({}, "required"),
        ({"asi_plus1_stat": "con", "specialized_design_skill": "perception", "specialized_design_tool": "tinkers_tools", "extra_language": "elvish"}, "con"),
        ({"asi_plus1_stat": "dex", "specialized_design_skill": "bad_skill", "specialized_design_tool": "tinkers_tools", "extra_language": "elvish"}, "skill"),
        ({"asi_plus1_stat": "dex", "specialized_design_skill": "perception", "specialized_design_tool": "bad_tool", "extra_language": "elvish"}, "tool"),
        ({"asi_plus1_stat": "dex", "specialized_design_skill": "perception", "specialized_design_tool": "tinkers_tools", "extra_language": "bad_language"}, "language"),
        ({"asi_plus1_stat": "dex", "specialized_design_skill": "perception", "specialized_design_tool": "tinkers_tools", "extra_language": "common"}, "common"),
    ]

    for choices, expected in invalid_payloads:
        payload = _base_payload()
        payload["race_choices"] = choices
        try:
            asyncio.run(http_routes.api_character_create(payload))
            assert False, "Expected HTTPException"
        except Exception as exc:  # noqa: BLE001
            assert expected in str(getattr(exc, "detail", exc)).lower()
