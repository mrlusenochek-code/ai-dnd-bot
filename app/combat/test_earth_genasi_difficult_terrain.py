from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def test_earth_genasi_trait_does_not_change_normal_move_without_terrain_context() -> None:
    session_id = "test_earth_genasi_trait_does_not_change_normal_move_without_terrain_context"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Earth Genasi",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        speed_ft=30,
        movement_speeds={"walk": 30},
        movement_mode="walk",
        move_speed_ft=30,
        move_remaining_ft=30,
        move_remaining=30,
        race_features={"movement": {"ignore_difficult_terrain": ["earth", "stone"]}},
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_move", session_id, distance_ft=10)
        assert err is None
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        assert pc.move_remaining_ft == 20
        assert pc.moved_this_turn_ft == 10
    finally:
        end_combat(session_id)


def test_non_earth_genasi_normal_move_same_without_terrain_context() -> None:
    session_id = "test_non_earth_genasi_normal_move_same_without_terrain_context"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Adventurer",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        speed_ft=30,
        movement_speeds={"walk": 30},
        movement_mode="walk",
        move_speed_ft=30,
        move_remaining_ft=30,
        move_remaining=30,
        race_features={},
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_move", session_id, distance_ft=10)
        assert err is None
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        assert pc.move_remaining_ft == 20
        assert pc.moved_this_turn_ft == 10
    finally:
        end_combat(session_id)
