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
        "uid": 314,
        "name": "Reborn Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "reborn",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {
            "size": "small",
            "flex_asi": {"variant": "2_1", "stats": ["con", "wis"]},
            "languages": ["elvish"],
            "skills": ["arcana", "stealth"],
        },
    }


def test_reborn_create_requires_all_choices_and_persists_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("con") or 0) == 60
    assert int(stats.get("wis") or 0) == 55

    assert str(race_features.get("creature_type") or "").strip().lower() == "humanoid"
    assert str(race_features.get("size") or "").strip().lower() == "small"
    assert [str(x).strip().lower() for x in (race_features.get("languages") or [])] == ["common", "elvish"]

    prof = race_features.get("proficiencies") or {}
    prof_skills = {str(x).strip().lower() for x in (prof.get("skills") or [])}
    assert {"arcana", "stealth"} <= prof_skills

    saves = race_features.get("saves") or {}
    adv_conditions = {str(x).strip().lower() for x in (saves.get("advantage_conditions") or [])}
    assert {"disease", "poisoned", "death_saves"} <= adv_conditions

    resistances = {str(x).strip().lower() for x in (race_features.get("resistances") or [])}
    assert "poison" in resistances

    needs = race_features.get("needs") or {}
    assert {str(x).strip().lower() for x in (needs.get("no_need") or [])} == {"eat", "drink", "breathe", "sleep"}

    immunities = race_features.get("immunities") or {}
    assert "magic_sleep" in {str(x).strip().lower() for x in (immunities.get("conditions") or [])}

    features = race_features.get("features") or {}
    deathless = features.get("deathless_nature") or {}
    assert int(deathless.get("long_rest_hours") or 0) == 4
    assert bool(deathless.get("remain_conscious")) is True
    assert isinstance(features.get("knowledge_from_a_past_life"), dict)

    runtime = race_features.get("runtime") or {}
    assert int(runtime.get("knowledge_past_life_uses_used") or 0) == 0
    assert bool(runtime.get("knowledge_past_life_armed")) is False

    choices = race_features.get("choices") or {}
    assert choices.get("size") == "small"
    assert (choices.get("languages") or []) == ["elvish"]
    assert (choices.get("skills") or []) == ["arcana", "stealth"]
    assert (choices.get("flex_asi") or {}) == {"variant": "2_1", "stats": ["con", "wis"]}


def test_reborn_create_rejects_missing_or_invalid_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    cases = []

    payload_no_size = _base_payload()
    payload_no_size["race_choices"] = dict(payload_no_size["race_choices"])
    payload_no_size["race_choices"].pop("size", None)
    cases.append((payload_no_size, "size"))

    payload_no_flex = _base_payload()
    payload_no_flex["race_choices"] = dict(payload_no_flex["race_choices"])
    payload_no_flex["race_choices"].pop("flex_asi", None)
    cases.append((payload_no_flex, "flex"))

    payload_common = _base_payload()
    payload_common["race_choices"] = dict(payload_common["race_choices"])
    payload_common["race_choices"]["languages"] = ["common"]
    cases.append((payload_common, "common"))

    payload_one_skill = _base_payload()
    payload_one_skill["race_choices"] = dict(payload_one_skill["race_choices"])
    payload_one_skill["race_choices"]["skills"] = ["arcana"]
    cases.append((payload_one_skill, "skill"))

    payload_dupe_skills = _base_payload()
    payload_dupe_skills["race_choices"] = dict(payload_dupe_skills["race_choices"])
    payload_dupe_skills["race_choices"]["skills"] = ["arcana", "arcana"]
    cases.append((payload_dupe_skills, "skill"))

    for payload, expected in cases:
        try:
            asyncio.run(http_routes.api_character_create(payload))
            assert False, "Expected HTTPException"
        except Exception as exc:  # noqa: BLE001
            detail = str(getattr(exc, "detail", exc)).lower()
            assert expected in detail


def test_reborn_ui_texts_present_in_templates() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    create_template = (Path(__file__).resolve().parents[0] / "templates" / "character_create.html").read_text(encoding="utf-8")

    assert "Бессмертная природа:" in session_template
    assert "Знания из прошлой жизни: после броска d20 к проверке навыка можно добавить 1к6" in session_template
    assert 'const isReborn = raceKey === "reborn";' in create_template
    assert "const needsSize = isCustomLineage || isDhampir || isHarengon || isHexblood || isOwlin || isReborn;" in create_template
