from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.web import ws_handlers


class _FakeDb:
    async def commit(self) -> None:
        return None


def test_mind_link_send_requires_active_link_and_logs_message(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    target_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="Owner")
    player_target = SimpleNamespace(id=target_pid, display_name="TargetPlayer")
    owner_ch = SimpleNamespace(
        name="Калаштар",
        player_id=owner_pid,
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
    target_ch = SimpleNamespace(name="Союзник", player_id=target_pid, race_features={"runtime": {}})

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

    fake_db = _FakeDb()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_say",
            raw_text="mind: привет",
        )
    )
    assert handled is True
    assert err is not None
    assert "сначала установите связь" in err.lower()

    asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_set",
            raw_text="mind link Союзник",
        )
    )

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_say",
            raw_text="mindlink send держим строй и идем вправо",
        )
    )
    assert handled is True
    assert err is None
    assert msg == "(Телепатия → Союзник): держим строй и идем вправо"
