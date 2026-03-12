from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.web import ws_handlers


class _FakeDb:
    async def commit(self) -> None:  # pragma: no cover - handler should not need commits here
        raise AssertionError("commit should not be called for loxodon trunk utility path")


def _loxodon_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        player_id=player_id,
        race_features={
            "features": {
                "trunk": {
                    "type": "trunk",
                    "reach_ft": 5,
                    "lift_lb_formula": "5*str",
                    "cannot": ["wield_weapons", "wield_shield", "fine_manipulation", "somatic_components"],
                }
            }
        },
    )


def _non_loxodon_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name, player_id=player_id, race_features={"features": {}})


def test_loxodon_trunk_status_and_narrative_use(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="LoxodonPlayer")
    owner_ch = _loxodon_character(owner_pid, "Локсодон")

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)

    assert ws_handlers._parse_loxodon_trunk_command("trunk status") == ("loxodon_trunk_status", None)
    assert ws_handlers._parse_loxodon_trunk_command("trunk use: открыть тяжёлую дверь") == ("loxodon_trunk_use", "открыть тяжёлую дверь")

    handled, err, msg = asyncio.run(
        ws_handlers._handle_loxodon_trunk_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="loxodon_trunk_status",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "хобот готов" in msg.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_loxodon_trunk_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="loxodon_trunk_use",
            message_text="открыть тяжёлую дверь",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "используете хобот" in msg.lower()


def test_loxodon_trunk_rejects_non_loxodon_and_empty_action(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="Owner")
    owner_ch = _non_loxodon_character(owner_pid, "Human")

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_loxodon_trunk_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="loxodon_trunk_status",
        )
    )
    assert handled is True
    assert err == "Хобот недоступен вашей расе."
    assert msg is None

    owner_ch = _loxodon_character(owner_pid, "Локсодон")

    async def _fake_get_character_loxodon(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character_loxodon)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_loxodon_trunk_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="loxodon_trunk_use",
            message_text="",
        )
    )
    assert handled is True
    assert err == "Опишите простое действие после двоеточия."
    assert msg is None
