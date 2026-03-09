from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from app.web import http_routes
from app.web.ws_handlers import _detect_innate_spell_key


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
        "uid": 9811,
        "name": "Githyanki Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "gith",
        "subrace_id": "githyanki",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {
            "decadent_mastery": {
                "language": "draconic",
                "skill": "stealth",
                "tool": None,
            }
        },
    }


def test_githyanki_create_requires_and_persists_decadent_mastery(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    rf = character.get("race_features") or {}

    assert int(stats.get("int") or 0) == 55
    assert int(stats.get("str") or 0) == 60

    choices = rf.get("choices") or {}
    assert choices.get("subrace_id") == "githyanki"
    decadent = choices.get("decadent_mastery") or {}
    assert decadent.get("language") == "draconic"
    assert decadent.get("skill") == "stealth"
    assert decadent.get("tool") is None

    languages = {str(x).strip().lower() for x in (rf.get("languages") or [])}
    assert {"common", "gith", "draconic"}.issubset(languages)

    prof = rf.get("proficiencies") or {}
    armor = {str(x).strip().lower() for x in (prof.get("armor") or [])}
    weapons = {str(x).strip().lower() for x in (prof.get("weapons") or [])}
    skills = {str(x).strip().lower() for x in (prof.get("skills") or [])}
    assert {"light", "medium"}.issubset(armor)
    assert {"shortsword", "longsword", "greatsword"}.issubset(weapons)
    assert "stealth" in skills

    spells = [item for item in (rf.get("innate_spells") or []) if isinstance(item, dict)]
    by_name = {str(item.get("name") or "").strip().lower(): item for item in spells}
    assert {"mage_hand", "jump", "misty_step"}.issubset(set(by_name.keys()))
    assert by_name["mage_hand"].get("ability") == "int"
    assert by_name["jump"].get("ability") == "int"
    assert by_name["misty_step"].get("ability") == "int"
    assert by_name["mage_hand"].get("no_material_components") is True
    assert by_name["jump"].get("no_material_components") is True
    assert by_name["misty_step"].get("no_material_components") is True


def test_githyanki_create_supports_tool_instead_of_skill(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["uid"] = 9812
    payload["race_choices"]["decadent_mastery"] = {
        "language": "elvish",
        "skill": None,
        "tool": "smith_tools",
    }

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    rf = (json.loads(response.body).get("character") or {}).get("race_features") or {}
    choices = rf.get("choices") or {}
    decadent = choices.get("decadent_mastery") or {}
    assert decadent.get("language") == "elvish"
    assert decadent.get("skill") is None
    assert decadent.get("tool") == "smith_tools"

    prof = rf.get("proficiencies") or {}
    tools = {str(x).strip().lower() for x in (prof.get("tools") or [])}
    assert "smith_tools" in tools


def test_gith_create_rejects_missing_subrace(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["subrace_id"] = ""

    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))

    assert exc.value.status_code == 400


def test_githyanki_create_rejects_missing_language(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["race_choices"]["decadent_mastery"] = {"language": "", "skill": "stealth", "tool": None}

    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))

    assert exc.value.status_code == 400


@pytest.mark.parametrize("bad_language", ["common", "gith"])
def test_githyanki_create_rejects_disallowed_or_duplicate_language(monkeypatch, bad_language: str) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["uid"] = 9813
    payload["race_choices"]["decadent_mastery"] = {
        "language": bad_language,
        "skill": "stealth",
        "tool": None,
    }

    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))

    assert exc.value.status_code == 400


def test_githyanki_create_rejects_skill_and_tool_together(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["race_choices"]["decadent_mastery"] = {
        "language": "draconic",
        "skill": "stealth",
        "tool": "smith_tools",
    }

    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))

    assert exc.value.status_code == 400


def test_githyanki_create_rejects_when_skill_and_tool_missing(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload()
    payload["race_choices"]["decadent_mastery"] = {
        "language": "draconic",
        "skill": None,
        "tool": None,
    }

    with pytest.raises(HTTPException) as exc:
        asyncio.run(http_routes.api_character_create(payload))

    assert exc.value.status_code == 400


def test_gith_psionics_regex_detection_ru_and_en() -> None:
    assert _detect_innate_spell_key("кастую щит") == "shield"
    assert _detect_innate_spell_key("использую обнаружение мыслей") == "detect_thoughts"
    assert _detect_innate_spell_key("кастую прыжок") == "jump"
    assert _detect_innate_spell_key("cast misty step") == "misty_step"
