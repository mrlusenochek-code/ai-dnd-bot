from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def test_combat_attack_blocked_when_action_already_spent() -> None:
    session_id = "test_combat_attack_blocked_when_action_already_spent"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Герой",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=20,
        action_available=False,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Гоблин",
        side="enemy",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None

        texts = [line.get("text") for line in patch.get("lines", []) if isinstance(line, dict)]
        assert any("действие уже потрачено" in text.lower() for text in texts if isinstance(text, str))

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.turn_index == 0
    finally:
        end_combat(session_id)


def test_combat_help_blocked_when_bonus_action_already_spent() -> None:
    session_id = "test_combat_help_blocked_when_bonus_action_already_spent"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Герой",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=20,
        bonus_action_available=False,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Гоблин",
        side="enemy",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_help", session_id)
        assert err is None
        assert patch is not None

        texts = [line.get("text") for line in patch.get("lines", []) if isinstance(line, dict)]
        assert any("бонусное действие уже потрачено" in text.lower() for text in texts if isinstance(text, str))

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.turn_index == 0
    finally:
        end_combat(session_id)


def test_combat_help_spends_bonus_action() -> None:
    session_id = "test_combat_help_spends_bonus_action"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Герой",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=20,
        bonus_action_available=True,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Гоблин",
        side="enemy",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_help", session_id)
        assert err is None
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].bonus_action_available is False
    finally:
        end_combat(session_id)


def test_combat_dash_grants_extra_movement() -> None:
    session_id = "test_combat_dash_grants_extra_movement"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Герой",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=20,
        move_remaining=30,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Гоблин",
        side="enemy",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_dash", session_id)
        assert err is None
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].move_remaining == 60
    finally:
        end_combat(session_id)
