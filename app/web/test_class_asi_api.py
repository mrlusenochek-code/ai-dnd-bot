from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException

from app.rules.character_catalog import CLASS_CATALOG
from app.rules.class_feature_runtime import apply_class_asi_choice
from app.rules.class_progression import sync_class_features_for_level
from app.web import http_routes
from app.web.gameplay_helpers import _char_to_payload


class _FakeScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _FakeDb:
    def __init__(self, session_player: Any) -> None:
        self._session_player = session_player
        self.commits = 0

    async def execute(self, _query: Any) -> _FakeScalarResult:
        return _FakeScalarResult(self._session_player)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _obj: Any) -> None:
        return None


class _FakeSessionCtx:
    def __init__(self, db: _FakeDb) -> None:
        self._db = db

    async def __aenter__(self) -> _FakeDb:
        return self._db

    async def __aexit__(self, _exc_type, _exc, _tb) -> bool:
        return False


def _fighter_catalog_entry() -> dict[str, Any]:
    fighter = next((item for item in CLASS_CATALOG if str(item.get("key") or "").strip().lower() == "fighter"), None)
    assert isinstance(fighter, dict)
    return fighter


def _fighter_character(*, level: int = 4, stats: dict[str, int] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="ASI Hero",
        class_kit="fighter",
        class_skin="Fighter",
        race_kit="human",
        race_skin="Human",
        level=level,
        xp_total=0,
        hp=24,
        hp_max=24,
        sta=12,
        sta_max=12,
        stats=stats or {"str": 65, "dex": 65, "con": 50, "int": 50, "wis": 50, "cha": 50},
        race_features={},
        class_features=sync_class_features_for_level(_fighter_catalog_entry(), level),
    )


def _legacy_fighter_character(*, level: int = 4, stats: dict[str, int] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="Legacy ASI Hero",
        class_kit="fighter",
        class_skin="Fighter",
        race_kit="human",
        race_skin="Human",
        level=level,
        xp_total=0,
        hp=24,
        hp_max=24,
        sta=12,
        sta_max=12,
        stats=stats or {"str": 65, "dex": 65, "con": 50, "int": 50, "wis": 50, "cha": 50},
        race_features={},
        class_features={
            "class_key": "fighter",
            "name_ru": "Воин",
            "name": "Fighter",
            "features": [
                {
                    "key": "asi",
                    "level": 4,
                    "name_ru": "Увеличение характеристик",
                    "summary_ru": "Улучшение характеристик или выбор таланта.",
                    "mechanics": {},
                }
            ],
        },
    )


def _setup_asi_api_mocks(monkeypatch, ch: SimpleNamespace) -> _FakeDb:
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
        return ch

    async def _noop(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(http_routes, "get_session", _fake_get_session)
    monkeypatch.setattr(http_routes, "get_or_create_player_web", _fake_get_or_create_player_web)
    monkeypatch.setattr(http_routes, "get_character", _fake_get_character)
    monkeypatch.setattr(http_routes, "add_system_event", _noop)
    return fake_db


def test_char_payload_exposes_pending_asi_levels_for_fighter_level_4() -> None:
    ch = _fighter_character(level=4)

    payload = _char_to_payload(ch)

    assert payload is not None
    assert payload.get("pending_asi_levels") == [4]
    assert payload.get("asi_choices") == {}
    asi_options = payload.get("asi_options") or {}
    assert asi_options.get("cap") == 100
    assert asi_options.get("stat_keys") == ["str", "dex", "con", "int", "wis", "cha"]


def test_char_payload_clears_pending_asi_after_choice() -> None:
    ch = _fighter_character(level=4)
    result = apply_class_asi_choice(ch, 4, {"mode": "single", "stat": "str"})
    assert result["applied"] is True

    payload = _char_to_payload(ch)

    assert payload is not None
    assert payload.get("pending_asi_levels") == []
    assert (payload.get("asi_choices") or {}).get("4", {}).get("mode") == "single"


def test_legacy_char_payload_exposes_pending_asi_levels() -> None:
    ch = _legacy_fighter_character(level=4)

    payload = _char_to_payload(ch)

    assert payload is not None
    assert payload.get("pending_asi_levels") == [4]


def test_legacy_char_payload_exposes_default_asi_options() -> None:
    ch = _legacy_fighter_character(level=4)

    payload = _char_to_payload(ch)

    assert payload is not None
    assert payload.get("asi_options") == {
        "type": "ability_score_improvement",
        "options": [
            {"kind": "single", "amount": 10, "count": 1},
            {"kind": "split", "amount": 5, "count": 2},
        ],
        "stat_keys": ["str", "dex", "con", "int", "wis", "cha"],
        "cap": 100,
    }


def test_api_character_asi_single_applies_bonus_and_returns_updated_payload(monkeypatch) -> None:
    ch = _fighter_character(level=4, stats={"str": 65, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50})
    _setup_asi_api_mocks(monkeypatch, ch)

    response = asyncio.run(
        http_routes.api_character_apply_asi(
            {
                "session_id": "test-session",
                "uid": 4401,
                "level": 4,
                "choice": {"mode": "single", "stat": "str"},
            }
        )
    )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["ok"] is True
    assert body["applied"] is True
    assert body["changes"] == [{"stat": "str", "old": 65, "new": 75, "delta": 10}]
    assert body["stats"]["str"] == 75
    assert body["character"]["stats"]["str"] == 75
    assert body["character"]["pending_asi_levels"] == []
    assert body["character"]["asi_choices"]["4"]["stat"] == "str"


def test_api_character_asi_split_applies_bonus_to_two_stats(monkeypatch) -> None:
    ch = _fighter_character(level=4, stats={"str": 65, "dex": 65, "con": 50, "int": 50, "wis": 50, "cha": 50})
    _setup_asi_api_mocks(monkeypatch, ch)

    response = asyncio.run(
        http_routes.api_character_apply_asi(
            {
                "session_id": "test-session",
                "uid": 4402,
                "level": 4,
                "choice": {"mode": "split", "stats": ["str", "dex"]},
            }
        )
    )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["stats"]["str"] == 70
    assert body["stats"]["dex"] == 70
    assert body["character"]["asi_choices"]["4"]["mode"] == "split"


def test_api_character_asi_rejects_repeat_for_same_level(monkeypatch) -> None:
    ch = _fighter_character(level=4)
    apply_class_asi_choice(ch, 4, {"mode": "single", "stat": "str"})
    _setup_asi_api_mocks(monkeypatch, ch)

    try:
        asyncio.run(
            http_routes.api_character_apply_asi(
                {
                    "session_id": "test-session",
                    "uid": 4403,
                    "level": 4,
                    "choice": {"mode": "single", "stat": "dex"},
                }
            )
        )
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "ASI for this level is already chosen"


def test_api_character_asi_rejects_invalid_stat(monkeypatch) -> None:
    ch = _fighter_character(level=4)
    _setup_asi_api_mocks(monkeypatch, ch)

    try:
        asyncio.run(
            http_routes.api_character_apply_asi(
                {
                    "session_id": "test-session",
                    "uid": 4404,
                    "level": 4,
                    "choice": {"mode": "single", "stat": "luck"},
                }
            )
        )
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Некорректная характеристика для ASI."


def test_api_character_asi_rejects_unavailable_level(monkeypatch) -> None:
    ch = _fighter_character(level=3)
    _setup_asi_api_mocks(monkeypatch, ch)

    try:
        asyncio.run(
            http_routes.api_character_apply_asi(
                {
                    "session_id": "test-session",
                    "uid": 4405,
                    "level": 4,
                    "choice": {"mode": "single", "stat": "str"},
                }
            )
        )
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "ASI level is not available for this character"


def test_api_character_asi_payload_reflects_updated_stats_and_choice(monkeypatch) -> None:
    ch = _fighter_character(level=6, stats={"str": 65, "dex": 65, "con": 50, "int": 50, "wis": 50, "cha": 50})
    _setup_asi_api_mocks(monkeypatch, ch)

    response = asyncio.run(
        http_routes.api_character_apply_asi(
            {
                "session_id": "test-session",
                "uid": 4406,
                "level": 4,
                "choice": {"mode": "split", "stats": ["str", "dex"]},
            }
        )
    )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["character"]["stats"]["str"] == 70
    assert body["character"]["stats"]["dex"] == 70
    assert body["character"]["pending_asi_levels"] == [6]
    assert body["character"]["asi_choices"]["4"]["changes"] == [
        {"stat": "str", "old": 65, "new": 70, "delta": 5},
        {"stat": "dex", "old": 65, "new": 70, "delta": 5},
    ]


def test_api_character_asi_supports_legacy_fighter_entry(monkeypatch) -> None:
    ch = _legacy_fighter_character(level=4, stats={"str": 65, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50})
    _setup_asi_api_mocks(monkeypatch, ch)

    response = asyncio.run(
        http_routes.api_character_apply_asi(
            {
                "session_id": "test-session",
                "uid": 4407,
                "level": 4,
                "choice": {"mode": "single", "stat": "str"},
            }
        )
    )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["stats"]["str"] == 75
    assert body["character"]["pending_asi_levels"] == []
    assert body["character"]["asi_choices"]["4"]["stat"] == "str"
