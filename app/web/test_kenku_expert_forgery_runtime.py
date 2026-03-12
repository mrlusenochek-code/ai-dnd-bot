from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.web import ws_handlers


class _FakeDb:
    async def commit(self) -> None:  # pragma: no cover - handler should not need commits here
        raise AssertionError("commit should not be called for kenku expert forgery utility path")


def _kenku_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        player_id=player_id,
        race_features={
            "features": {
                "expert_forgery": {
                    "type": "expert_forgery",
                }
            }
        },
    )


def _non_kenku_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name, player_id=player_id, race_features={"features": {}})


def test_kenku_expert_forgery_status_and_narrative_copy(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="KenkuPlayer")
    owner_ch = _kenku_character(owner_pid, "Кенку")

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)

    assert ws_handlers._parse_kenku_expert_forgery_command("forgery status") == ("kenku_forgery_status", None)
    assert ws_handlers._parse_kenku_expert_forgery_command("forgery copy: королевскую подпись") == (
        "kenku_forgery_copy",
        "королевскую подпись",
    )

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kenku_expert_forgery_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="kenku_forgery_status",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "искусный подлог готов" in msg.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kenku_expert_forgery_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="kenku_forgery_copy",
            message_text="королевскую подпись",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "тщательно воспроизводите" in msg.lower()


def test_kenku_expert_forgery_rejects_non_kenku_and_empty_copy(monkeypatch) -> None:
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
        ws_handlers._handle_kenku_expert_forgery_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="kenku_forgery_status",
        )
    )
    assert handled is True
    assert err == "Искусный подлог недоступен вашей расе."
    assert msg is None

    owner_ch = _kenku_character(owner_pid, "Кенку")

    async def _fake_get_character_kenku(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character_kenku)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kenku_expert_forgery_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="kenku_forgery_copy",
            message_text="",
        )
    )
    assert handled is True
    assert err == "Укажите, что именно вы хотите воспроизвести после двоеточия."
    assert msg is None

