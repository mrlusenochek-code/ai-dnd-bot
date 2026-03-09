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


def _base_payload(enhancement: str = "nimble_climber") -> dict[str, Any]:
    return {
        "session_id": "test-session",
        "uid": 1111,
        "name": "Simic Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "simic_hybrid",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {
            "asi": [{"stat": "dex", "bonus": 1}],
            "languages": ["elvish"],
            "animal_enhancement_lvl1": enhancement,
        },
    }


def test_simic_hybrid_create_requires_choices_and_applies_lvl1_enhancement(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    expected = {
        "nimble_climber": ("climb_ft", 30),
        "underwater_adaptation": ("swim_ft", 30),
        "manta_glide": ("glide", None),
    }
    for enhancement, effect in expected.items():
        response = asyncio.run(http_routes.api_character_create(_base_payload(enhancement)))
        assert response.status_code == 200
        character = json.loads(response.body).get("character") or {}
        stats = character.get("stats") or {}
        race_features = character.get("race_features") or {}

        assert int(stats.get("con") or 0) == 60
        assert int(stats.get("dex") or 0) == 55

        langs = [str(x).strip().lower() for x in (race_features.get("languages") or [])]
        assert langs == ["common", "elvish"]

        senses = race_features.get("senses") or {}
        assert int(senses.get("darkvision_ft") or 0) == 60

        animal = (race_features.get("features") or {}).get("animal_enhancement") or {}
        assert animal.get("chosen_lvl1") == enhancement
        assert animal.get("chosen_lvl5") is None

        speeds = race_features.get("speeds") or {}
        if effect[0] == "climb_ft":
            assert int(speeds.get("climb_ft") or 0) == effect[1]
        elif effect[0] == "swim_ft":
            assert int(speeds.get("swim_ft") or 0) == effect[1]
            assert (race_features.get("features") or {}).get("amphibious") is True
        else:
            glide = (race_features.get("features") or {}).get("glide") or {}
            assert int(glide.get("reduce_fall_ft") or 0) == 100
            assert int(glide.get("horizontal_per_fall_ft") or 0) == 2

        choices = race_features.get("choices") or {}
        assert choices.get("asi_plus1_stat") == "dex"
        assert choices.get("language") == "elvish"
        assert choices.get("animal_enhancement_lvl1") == enhancement


def test_simic_hybrid_create_rejects_missing_or_invalid_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload_no_asi = _base_payload()
    payload_no_asi["race_choices"] = dict(payload_no_asi["race_choices"])
    payload_no_asi["race_choices"].pop("asi", None)
    try:
        asyncio.run(http_routes.api_character_create(payload_no_asi))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        assert "asi" in str(getattr(exc, "detail", exc)).lower()

    payload_no_lang = _base_payload()
    payload_no_lang["race_choices"] = dict(payload_no_lang["race_choices"])
    payload_no_lang["race_choices"]["languages"] = []
    try:
        asyncio.run(http_routes.api_character_create(payload_no_lang))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        assert "language" in str(getattr(exc, "detail", exc)).lower()

    payload_bad_lang = _base_payload()
    payload_bad_lang["race_choices"] = dict(payload_bad_lang["race_choices"])
    payload_bad_lang["race_choices"]["languages"] = ["common"]
    try:
        asyncio.run(http_routes.api_character_create(payload_bad_lang))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "elvish" in detail or "vedalken" in detail or "language" in detail

    payload_bad_enhancement = _base_payload()
    payload_bad_enhancement["race_choices"] = dict(payload_bad_enhancement["race_choices"])
    payload_bad_enhancement["race_choices"]["animal_enhancement_lvl1"] = "acid_spit"
    try:
        asyncio.run(http_routes.api_character_create(payload_bad_enhancement))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        assert "animal enhancement" in str(getattr(exc, "detail", exc)).lower()


def test_simic_hybrid_ui_texts_present_in_templates() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    create_template = (Path(__file__).resolve().parents[0] / "templates" / "character_create.html").read_text(encoding="utf-8")

    assert "Животное усиление: 1 уровень" in session_template
    assert "на 5 уровне выберете ещё одно усиление" in session_template
    assert "Животное усиление (1 уровень, обязательно)" in create_template
    assert 'animal_enhancement_lvl1' in create_template
