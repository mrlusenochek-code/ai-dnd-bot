from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.web import ws_handlers


class _FakeDb:
    async def commit(self) -> None:  # pragma: no cover - handler should not need commits here
        raise AssertionError("commit should not be called for kenku mimicry utility path")


def _kenku_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        player_id=player_id,
        race_features={
            "features": {
                "mimicry": {
                    "type": "mimicry",
                    "counter_check": {"ability": "wis", "skill": "insight"},
                }
            }
        },
    )


def _non_kenku_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name, player_id=player_id, race_features={"features": {}})


def test_kenku_mimicry_status_and_narrative_send(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="KenkuPlayer")
    owner_ch = _kenku_character(owner_pid, "Кенку")

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)

    assert ws_handlers._parse_kenku_mimicry_command("mimicry status") == ("kenku_mimicry_status", None)
    assert ws_handlers._parse_kenku_mimicry_command("mimicry voice: уходите отсюда") == ("kenku_mimicry_voice", "уходите отсюда")
    assert ws_handlers._parse_kenku_mimicry_command("mimicry sound: скрип старой двери") == ("kenku_mimicry_sound", "скрип старой двери")

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kenku_mimicry_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="kenku_mimicry_status",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "подражание готово" in msg.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kenku_mimicry_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="kenku_mimicry_voice",
            message_text="уходите отсюда",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "имитируете голос" in msg.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kenku_mimicry_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="kenku_mimicry_sound",
            message_text="скрип старой двери",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "имитируете звук" in msg.lower()


def test_kenku_mimicry_rejects_non_kenku_and_empty_message(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="Owner")
    owner_ch = _non_kenku_character(owner_pid, "Human")

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kenku_mimicry_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="kenku_mimicry_status",
        )
    )
    assert handled is True
    assert err == "Подражание недоступно вашей расе."
    assert msg is None

    owner_ch = _kenku_character(owner_pid, "Кенку")

    async def _fake_get_character_kenku(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character_kenku)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kenku_mimicry_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="kenku_mimicry_sound",
            message_text="",
        )
    )
    assert handled is True
    assert err == "Укажите звук или фразу после двоеточия."
    assert msg is None
