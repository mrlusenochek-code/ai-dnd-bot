from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
            class_features=dict(kwargs.get("class_features") or {}),
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
            "class_features": dict(getattr(ch, "class_features", {}) or {}),
        },
    )


def _base_payload(*, class_id: str = "fighter") -> dict[str, Any]:
    return {
        "session_id": "test-session",
        "uid": 2205,
        "name": "Style Hero",
        "class_id": class_id,
        "custom_class": "",
        "race_id": "yuan_ti_pureblood",
        "subrace_id": "",
        "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
    }


def test_fighter_create_persists_selected_fighting_style(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload(class_id="fighter")
    payload["class_choices"] = {"fighting_style": "defense"}

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    class_features = character.get("class_features") or {}
    choices = class_features.get("choices") or {}

    assert choices.get("fighting_style") == "defense"


def test_fighter_create_rejects_invalid_fighting_style(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload(class_id="fighter")
    payload["class_choices"] = {"fighting_style": "unknown_style"}

    try:
        asyncio.run(http_routes.api_character_create(payload))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        assert "invalid fighting style" in str(getattr(exc, "detail", exc)).lower()


def test_non_fighter_ignores_fighting_style_choice(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload(class_id="rogue")
    payload["class_choices"] = {"fighting_style": "protection"}

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    class_features = character.get("class_features") or {}
    choices = class_features.get("choices") or {}

    assert choices.get("fighting_style") is None


def test_fighter_create_persists_great_weapon_fighting(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload(class_id="fighter")
    payload["class_choices"] = {"fighting_style": "great_weapon_fighting"}

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    class_features = character.get("class_features") or {}
    choices = class_features.get("choices") or {}

    assert choices.get("fighting_style") == "great_weapon_fighting"


def test_fighter_create_persists_protection(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload(class_id="fighter")
    payload["class_choices"] = {"fighting_style": "protection"}

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    class_features = character.get("class_features") or {}
    choices = class_features.get("choices") or {}

    assert choices.get("fighting_style") == "protection"


def test_fighter_create_persists_two_weapon_fighting(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    payload = _base_payload(class_id="fighter")
    payload["class_choices"] = {"fighting_style": "two_weapon_fighting"}

    response = asyncio.run(http_routes.api_character_create(payload))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    class_features = character.get("class_features") or {}
    choices = class_features.get("choices") or {}

    assert choices.get("fighting_style") == "two_weapon_fighting"


def test_char_payload_exposes_inventory_and_equip_from_stats() -> None:
    character = SimpleNamespace(
        name="Inventory Hero",
        class_kit="fighter",
        class_skin="Fighter",
        race_kit="aarakocra",
        race_skin="Aarakocra",
        level=5,
        xp_total=0,
        hp=20,
        hp_max=20,
        sta=10,
        sta_max=10,
        stats={
            "str": 50,
            "dex": 70,
            "con": 50,
            "int": 50,
            "wis": 50,
            "cha": 50,
            "_inv": [
                {"id": "dagger_main", "name": "Кинжал", "qty": 1, "def": "dagger"},
                {"id": "dagger_off", "name": "Кинжал", "qty": 1, "def": "dagger"},
            ],
            "_equip": {"main_hand": "dagger_main", "off_hand": "dagger_off"},
        },
        race_features={},
        class_features={},
    )

    payload = _char_to_payload(character)

    assert payload is not None
    assert payload.get("inventory") == character.stats["_inv"]
    assert payload.get("equip") == character.stats["_equip"]


def test_fighting_style_ui_texts_present_in_templates() -> None:
    templates_dir = Path(__file__).resolve().parents[0] / "templates"
    create_template = (templates_dir / "character_create.html").read_text(encoding="utf-8")
    session_template = (templates_dir / "session.html").read_text(encoding="utf-8")

    assert 'id="choiceFightingStyle"' in create_template
    assert "Оборона: +1 AC, если надет доспех" in create_template
    assert "Стрельба: +2 к атаке дальнобойным оружием" in create_template
    assert "Дуэлянт: +2 к урону одноручным ближним оружием, если нет второго оружия" in create_template
    assert "Сражение большим оружием: переброс 1–2 на костях урона melee weapon, когда оружие используется двумя руками" in create_template
    assert "Защита: реакцией со щитом даёт помеху атаке по союзнику рядом" in create_template
    assert "Сражение двумя оружиями: добавляет модификатор характеристики к урону бонусной атаки второй рукой" in create_template
    assert "Боевой стиль:" in session_template
    assert "Сражение большим оружием" in session_template
    assert "Защита" in session_template
    assert "Сражение двумя оружиями" in session_template
    assert "Доступно улучшение характеристик" in session_template
    assert "Выберите вариант для уровня" in session_template
    assert "+2 к одной характеристике" in session_template
    assert "+1 к двум характеристикам" in session_template
    assert "Применить улучшение" in session_template
    assert "Сила" in session_template
    assert "Ловкость" in session_template
    assert "Телосложение" in session_template
    assert "Интеллект" in session_template
    assert "Мудрость" in session_template
    assert "Харизма" in session_template
    assert "/api/character/asi" in session_template
    assert "pending_asi_levels" in session_template
    assert "if(!pendingLevels.length){" in session_template
    assert 'if(box) box.style.display = "none";' in session_template
    assert "renderInventoryHtml(invList)" in session_template
    assert "getInventoryText(invList)" in session_template
    assert 'card.addEventListener("click", openCharacterModal);' not in session_template
    assert 'card.addEventListener("click", () => openCharacterModal());' in session_template
    assert '&& !("type" in targetPlayer)' in session_template
    assert '&& ("uid" in targetPlayer || "char" in targetPlayer)' in session_template
    fly_block_decl = session_template.index("const flyBlockedByArmor")
    fly_block_use = session_template.index("flyBlockedByArmor ?")
    assert fly_block_decl < fly_block_use
    fly_speed_decl = session_template.index("const flySpeedEqualsWalk")
    fly_speed_use = session_template.index("flySpeedEqualsWalk ?")
    assert fly_speed_decl < fly_speed_use
    assert 'uiCtx.phase === "gm_pending"' in session_template
    assert 'uiCtx.gmPendingContext === "post_victory"' in session_template
    assert "🧙 Мастер описывает последствия победы..." in session_template
    assert "Подождите, Мастер описывает сцену..." in session_template
    assert 'uiCtx.gmPendingContext === "combat_start"' in session_template
    assert "⚔ Мастер подготавливает бой..." in session_template
    assert "Подождите, бой загружается..." in session_template
