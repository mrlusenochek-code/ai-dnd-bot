from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            out.append(text)
    return out


def test_centaur_climb_mode_applies_x5_movement_cost() -> None:
    session_id = "test_centaur_climb_mode_applies_x5_movement_cost"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Centaur",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        speed_ft=40,
        movement_speeds={"walk": 40},
        movement_mode="climb",
        move_speed_ft=40,
        move_remaining_ft=50,
        move_remaining=50,
        race_features={
            "movement": {
                "climb_extra_cost_ft_per_ft": 4,
                "climb_requires_hands_and_feet": True,
            }
        },
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
        texts = _line_texts(patch)
        assert any("Лошадиное телосложение" in t and "потрачено 50 фт" in t for t in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        assert pc.move_remaining_ft == 0
        assert pc.moved_this_turn_ft == 10
    finally:
        end_combat(session_id)


def test_mode_switch_does_not_reset_movement_budget_mid_turn() -> None:
    session_id = "test_mode_switch_does_not_reset_movement_budget_mid_turn"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Centaur",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        speed_ft=40,
        movement_speeds={"walk": 40, "swim": 30, "climb": 30},
        movement_mode="walk",
        move_speed_ft=40,
        move_remaining_ft=17,
        move_remaining=17,
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
        patch_swim, err_swim = handle_live_combat_action("combat_mode_swim", session_id)
        assert err_swim is None
        assert patch_swim is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        assert pc.movement_mode == "swim"
        assert pc.move_remaining_ft == 17

        patch_climb, err_climb = handle_live_combat_action("combat_mode_climb", session_id)
        assert err_climb is None
        assert patch_climb is not None
        assert pc.movement_mode == "climb"
        assert pc.move_remaining_ft == 17

        patch_walk, err_walk = handle_live_combat_action("combat_mode_walk", session_id)
        assert err_walk is None
        assert patch_walk is not None
        assert pc.movement_mode == "walk"
        assert pc.move_remaining_ft == 17
    finally:
        end_combat(session_id)
