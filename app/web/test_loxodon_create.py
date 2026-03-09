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
        "uid": 711,
        "name": "Loxodon Hero",
        "class_id": "",
        "custom_class": "Adventurer",
        "race_id": "loxodon",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        "race_choices": {},
    }


def test_loxodon_create_persists_expected_race_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("con") or 0) == 60
    assert int(stats.get("wis") or 0) == 55
    assert (race_features.get("languages") or []) == ["common", "loxodon"]

    saves = race_features.get("saves") or {}
    adv_conditions = {str(x).strip().lower() for x in (saves.get("advantage_conditions") or [])}
    assert {"charmed", "frightened"}.issubset(adv_conditions)

    natural_armor = race_features.get("natural_armor") or {}
    assert str(natural_armor.get("ac_formula") or "").strip().lower() == "12 + con_mod"
    assert bool(natural_armor.get("shield_applies")) is True
    assert bool(natural_armor.get("allow_when_armored_if_better")) is True

    carry = race_features.get("carry") or {}
    assert bool(carry.get("powerful_build")) is True

    features = race_features.get("features") or {}
    assert isinstance(features.get("trunk"), dict)
    assert isinstance(features.get("keen_smell"), dict)


def test_loxodon_ui_texts_present_in_session_template() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Спокойствие локсодонов: преимущество на спасброски от очарования/испуга" in template
    assert "Природный доспех: без брони КД = 12 + модиф. ТЕЛ; можно использовать, если броня хуже; щит работает" in template
    assert "Хобот: досягаемость 5 фт, переноска/толкать/тянуть, безоружный удар; нельзя держать оружие/щит, точные действия и соматику" in template
    assert "Обострённый нюх: преимущество на проверки Восприятия/Выживания/Расследования, основанные на запахе" in template
