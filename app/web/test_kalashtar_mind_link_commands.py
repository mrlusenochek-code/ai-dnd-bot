from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.web import ws_handlers


class _FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def _kalashtar_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        player_id=player_id,
        race_features={
            "features": {
                "mind_link": {
                    "range_formula": "level*10",
                    "allow_reply_duration": "1_hour",
                    "one_target_reply": True,
                }
            },
            "runtime": {},
        },
    )


def _non_kalashtar_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name, player_id=player_id, race_features={"features": {}, "runtime": {}})


def test_mindlink_open_status_send_close_and_replace(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    target_a_pid = uuid.uuid4()
    target_b_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="Owner")
    player_target_a = SimpleNamespace(id=target_a_pid, display_name="AllyOnePlayer")
    player_target_b = SimpleNamespace(id=target_b_pid, display_name="AllyTwoPlayer")
    owner_ch = _kalashtar_character(owner_pid, "Калаштар")
    target_a = SimpleNamespace(name="Лира", player_id=target_a_pid, race_features={"runtime": {}})
    target_b = SimpleNamespace(name="Брен", player_id=target_b_pid, race_features={"runtime": {}})

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        if pid == target_a_pid:
            return target_a
        if pid == target_b_pid:
            return target_b
        return None

    async def _fake_load_actor_context(_db, _sess):
        uid_map = {
            101: (SimpleNamespace(player_id=owner_pid), player_owner),
            202: (SimpleNamespace(player_id=target_a_pid), player_target_a),
            303: (SimpleNamespace(player_id=target_b_pid), player_target_b),
        }
        chars_by_uid = {
            101: owner_ch,
            202: target_a,
            303: target_b,
        }
        return uid_map, chars_by_uid, {}

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)
    monkeypatch.setattr(ws_handlers, "_load_actor_context", _fake_load_actor_context)

    assert ws_handlers._parse_mind_link_command("mindlink open Лира") == ("mind_link_set", "Лира")
    assert ws_handlers._parse_mind_link_command("mindlink status") == ("mind_link_status", None)
    assert ws_handlers._parse_mind_link_command("mindlink send держимся вместе") == ("mind_link_say", "держимся вместе")
    assert ws_handlers._parse_mind_link_command("mindlink close") == ("mind_link_clear", None)

    fake_db = _FakeDb()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_set",
            raw_text="mind link Лира",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "установлена" in msg.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_status",
            raw_text="mindlink status",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "активна с лира" in msg.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_set",
            raw_text="mind link Брен",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "переключена" in msg.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_clear",
            raw_text="mind link off",
        )
    )
    assert handled is True
    assert err is None
    assert msg == "Связь разумов: разорвана."

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_status",
            raw_text="mindlink status",
        )
    )
    assert handled is True
    assert err is None
    assert msg == "[RACE] Связь разумов: не активна."


def test_mindlink_rejects_non_kalashtar_and_unknown_target(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="Owner")
    owner_ch = _non_kalashtar_character(owner_pid, "Human")

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    async def _fake_load_actor_context(_db, _sess):
        return {101: (SimpleNamespace(player_id=owner_pid), player_owner)}, {101: owner_ch}, {}

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)
    monkeypatch.setattr(ws_handlers, "_load_actor_context", _fake_load_actor_context)

    fake_db = _FakeDb()
    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_set",
            raw_text="mind link Лира",
        )
    )
    assert handled is True
    assert err == "Связь разумов недоступна вашей расе."
    assert msg is None


def test_mindlink_reports_unknown_target(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="Owner")
    owner_ch = _kalashtar_character(owner_pid, "Калаштар")

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    async def _fake_load_actor_context(_db, _sess):
        return {101: (SimpleNamespace(player_id=owner_pid), player_owner)}, {101: owner_ch}, {}

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)
    monkeypatch.setattr(ws_handlers, "_load_actor_context", _fake_load_actor_context)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            _FakeDb(),
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_set",
            raw_text="mind link Неизвестный",
        )
    )
    assert handled is True
    assert err is not None
    assert "не нашёл цель" in err.lower()
    assert msg is None
