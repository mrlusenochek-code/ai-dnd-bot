from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


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


def test_kalashtar_mind_link_runtime_set_say_clear(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    target_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="Owner")
    player_target = SimpleNamespace(id=target_pid, display_name="TargetPlayer")
    owner_ch = _kalashtar_character(owner_pid, "Калаштар")
    target_ch = SimpleNamespace(name="Союзник", player_id=target_pid, race_features={"runtime": {}})

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        if pid == target_pid:
            return target_ch
        return None

    async def _fake_load_actor_context(_db, _sess):
        sp_owner = SimpleNamespace(player_id=owner_pid)
        sp_target = SimpleNamespace(player_id=target_pid)
        uid_map = {
            101: (sp_owner, player_owner),
            202: (sp_target, player_target),
        }
        chars_by_uid = {
            101: owner_ch,
            202: target_ch,
        }
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
            raw_text="телепатия: привет",
        )
    )
    assert handled is True
    assert err is not None
    assert "сначала установите связь" in err.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_set",
            raw_text="связь разумов с союзник",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "установлена" in msg.lower()
    runtime = (owner_ch.race_features or {}).get("runtime") or {}
    assert str(runtime.get("mind_link_target_id") or "").strip() == "pc_202"
    assert str(runtime.get("mind_link_reply_until") or "").strip()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_say",
            raw_text="мысленно: держим строй",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "(телепатия" in msg.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_kalashtar_mind_link_action(
            fake_db,
            sess,
            player=player_owner,
            session_id="kal-session",
            combat_action="mind_link_clear",
            raw_text="разорвать связь",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "разорвана" in msg.lower()
    runtime_after = (owner_ch.race_features or {}).get("runtime") or {}
    assert not str(runtime_after.get("mind_link_target_id") or "").strip()


def test_kalashtar_mind_link_regex_actions_detected() -> None:
    assert _detect_chat_combat_action("связь разумов с Лира") == "mind_link_set"
    assert _detect_chat_combat_action("mind link off") == "mind_link_clear"
    assert _detect_chat_combat_action("телепатия: привет") == "mind_link_say"
    assert _detect_chat_combat_action("telepathy reply: понял") == "mind_link_reply"
