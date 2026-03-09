from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, advance_turn, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    return [item["text"] for item in lines if isinstance(item, dict) and isinstance(item.get("text"), str)]


def test_orc_aggressive_spends_bonus_action_moves_and_returns_next_turn() -> None:
    session_id = "test_orc_aggressive_spends_bonus_action_moves_and_returns_next_turn"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Orc",
        side="pc",
        hp_current=22,
        hp_max=22,
        ac=13,
        initiative=20,
        action_available=True,
        bonus_action_available=True,
        speed_ft=30,
        move_speed_ft=30,
        move_remaining_ft=40,
        move_remaining=40,
        stats={"str": 60, "dex": 50, "con": 55, "int": 40, "wis": 50, "cha": 50},
        race_features={"features": {"aggressive": {"type": "bonus_action_move_toward_enemy"}}, "runtime": {}},
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=18,
        hp_max=18,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_aggressive", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Агрессивный" in text or "рывком" in text for text in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        runtime = ((pc.race_features or {}).get("runtime") or {})
        assert pc.bonus_action_available is False
        assert pc.move_remaining_ft < 40 or pc.moved_this_turn_ft > 0
        assert "aggressive_used_turn_id" in runtime

        patch_repeat, err_repeat = handle_live_combat_action("combat_aggressive", session_id)
        assert err_repeat is None
        assert patch_repeat is not None
        assert any("бонусное действие уже потрачено" in text.lower() for text in _line_texts(patch_repeat))

        advanced = advance_turn(session_id)
        assert advanced is not None
        advanced = advance_turn(session_id)
        assert advanced is not None

        state_next = get_combat(session_id)
        assert state_next is not None
        pc_next = state_next.combatants["pc_1"]
        assert pc_next.bonus_action_available is True
        runtime_next = ((pc_next.race_features or {}).get("runtime") or {})
        assert "aggressive_used_turn_id" not in runtime_next

        patch_next, err_next = handle_live_combat_action("combat_aggressive", session_id)
        assert err_next is None
        assert patch_next is not None
        assert any("Агрессивный" in text for text in _line_texts(patch_next))
    finally:
        end_combat(session_id)


def test_orc_aggressive_blocked_when_speed_zero() -> None:
    session_id = "test_orc_aggressive_blocked_when_speed_zero"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Orc",
        side="pc",
        hp_current=22,
        hp_max=22,
        ac=13,
        initiative=20,
        action_available=True,
        bonus_action_available=True,
        speed_ft=0,
        move_speed_ft=0,
        move_remaining_ft=0,
        move_remaining=0,
        race_features={"features": {"aggressive": {"type": "bonus_action_move_toward_enemy"}}, "runtime": {}},
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=18,
        hp_max=18,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_aggressive", session_id)
        assert patch is None
        assert err is not None
        assert "скорость" in err.lower()
    finally:
        end_combat(session_id)
