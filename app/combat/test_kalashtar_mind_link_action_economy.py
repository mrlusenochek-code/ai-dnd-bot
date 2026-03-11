from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.combat.state import Combatant, end_combat, start_combat
from app.web import ws_handlers


class _FakeDb:
    async def commit(self) -> None:
        return None


def test_mind_link_open_in_combat_uses_current_model_without_spending_action(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    target_pid = uuid.uuid4()
    session_id = "test_kalashtar_mind_link_open_in_combat"
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

    state = start_combat(session_id)
    state.combatants["pc_101"] = Combatant(
        key="pc_101",
        name="Калаштар",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=15,
        action_available=False,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Союзник",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_101", "enemy_1"]
    state.turn_index = 0

    try:
        handled, err, msg = asyncio.run(
            ws_handlers._handle_kalashtar_mind_link_action(
                _FakeDb(),
                sess,
                player=player_owner,
                session_id=session_id,
                combat_action="mind_link_set",
                raw_text="mind link Союзник",
            )
        )
        assert handled is True
        assert err is None
        assert msg is not None and "установлена" in msg.lower()
        assert state.combatants["pc_101"].action_available is False
    finally:
        end_combat(session_id)
