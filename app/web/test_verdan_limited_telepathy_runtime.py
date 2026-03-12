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


def _verdan_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        player_id=player_id,
        race_features={
            "features": {
                "limited_telepathy": {
                    "range_ft": 30,
                    "requires_target_language": True,
                    "bandwidth": "simple_ideas",
                }
            },
            "senses": {
                "telepathy": {
                    "range_ft": 30,
                    "requires_target_language": True,
                    "bandwidth": "simple_ideas",
                }
            },
            "runtime": {},
        },
    )


def _non_verdan_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name, player_id=player_id, race_features={"features": {}, "runtime": {}})


def test_verdan_limited_telepathy_send_and_status(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    target_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="VerdanPlayer")
    player_target = SimpleNamespace(id=target_pid, display_name="ScoutPlayer")
    owner_ch = _verdan_character(owner_pid, "Вердан")
    target_ch = SimpleNamespace(name="Лира", player_id=target_pid, race_features={"runtime": {}})

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        if pid == target_pid:
            return target_ch
        return None

    async def _fake_load_actor_context(_db, _sess):
        uid_map = {
            101: (SimpleNamespace(player_id=owner_pid), player_owner),
            202: (SimpleNamespace(player_id=target_pid), player_target),
        }
        chars_by_uid = {101: owner_ch, 202: target_ch}
        return uid_map, chars_by_uid, {}

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)
    monkeypatch.setattr(ws_handlers, "_load_actor_context", _fake_load_actor_context)

    assert ws_handlers._parse_verdan_telepathy_command("telepathy status") == ("verdan_telepathy_status", None, None)
    assert ws_handlers._parse_verdan_telepathy_command("telepathy send Лира: держимся вместе") == (
        "verdan_telepathy_send",
        "Лира",
        "держимся вместе",
    )

    fake_db = _FakeDb()
    handled, err, msg = asyncio.run(
        ws_handlers._handle_verdan_limited_telepathy_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="verdan-session",
            action="verdan_telepathy_send",
            target_name="Лира",
            message_text="держимся вместе",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "ограниченная телепатия" in msg.lower()
    runtime = (owner_ch.race_features or {}).get("runtime") or {}
    assert str(runtime.get("verdan_telepathy_last_target") or "") == "Лира"
    assert fake_db.commits == 1

    handled, err, msg = asyncio.run(
        ws_handlers._handle_verdan_limited_telepathy_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="verdan-session",
            action="verdan_telepathy_status",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "последняя цель" in msg.lower()


def test_verdan_limited_telepathy_rejects_non_verdan_and_unknown_target(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="Owner")
    owner_ch = _non_verdan_character(owner_pid, "Human")

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    async def _fake_load_actor_context(_db, _sess):
        return {101: (SimpleNamespace(player_id=owner_pid), player_owner)}, {101: owner_ch}, {}

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)
    monkeypatch.setattr(ws_handlers, "_load_actor_context", _fake_load_actor_context)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_verdan_limited_telepathy_action(
            _FakeDb(),
            sess,
            player=player_owner,
            session_id="verdan-session",
            action="verdan_telepathy_send",
            target_name="Лира",
            message_text="привет",
        )
    )
    assert handled is True
    assert err == "Ограниченная телепатия недоступна вашей расе."
    assert msg is None

    owner_ch = _verdan_character(owner_pid, "Вердан")

    async def _fake_get_character_verdan(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character_verdan)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_verdan_limited_telepathy_action(
            _FakeDb(),
            sess,
            player=player_owner,
            session_id="verdan-session",
            action="verdan_telepathy_send",
            target_name="Неизвестный",
            message_text="привет",
        )
    )
    assert handled is True
    assert err is not None and "не нашёл цель" in err.lower()
    assert msg is None
