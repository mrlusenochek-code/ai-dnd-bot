from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.combat.turns import advance_turn_in_state
from app.web import ws_handlers


def test_tabaxi_feline_agility_doubles_speed_and_recovers_after_no_move_turn() -> None:
    session_id = "test_tabaxi_feline_agility_doubles_speed"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Tabaxi",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        stats={"str": 50, "dex": 60},
        race_features={
            "race_key": "tabaxi",
            "features": {
                "feline_agility": {
                    "type": "feline_agility",
                    "double_speed": True,
                    "reset_if_zero_movement_turn": True,
                }
            },
            "runtime": {
                "feline_agility_available": True,
                "feline_agility_active": False,
                "feline_agility_used_turn": "",
            },
        },
        movement_speeds={"walk": 30, "climb": 20},
        move_speed_ft=30,
        move_remaining_ft=30,
    )
    state.combatants["enemy_1"] = Combatant(key="enemy_1", name="Guard", side="enemy", hp_current=15, hp_max=15, ac=10, initiative=10)
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_feline_agility", session_id)
        assert err is None and patch is not None
        pc = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        assert pc.action_available is True
        assert pc.bonus_action_available is True
        assert pc.move_speed_ft == 60
        assert pc.move_remaining_ft == 60
        runtime = (pc.race_features or {}).get("runtime") or {}
        assert runtime.get("feline_agility_active") is True

        patch_2, err_2 = handle_live_combat_action("combat_feline_agility", session_id)
        assert patch_2 is None
        assert err_2 is not None and "уже активирована" in err_2

        move_patch, move_err = handle_live_combat_action("combat_move", session_id, distance_ft=10)
        assert move_err is None and move_patch is not None
        assert pc.moved_this_turn_ft == 10
        assert pc.move_remaining_ft == 50

        advance_turn_in_state(state)
        runtime_after_end = (pc.race_features or {}).get("runtime") or {}
        assert runtime_after_end.get("feline_agility_active") is False
        assert runtime_after_end.get("feline_agility_available") is False

        advance_turn_in_state(state)
        advance_turn_in_state(state)
        runtime_after_rest_turn = (pc.race_features or {}).get("runtime") or {}
        assert runtime_after_rest_turn.get("feline_agility_available") is True

        runtime_after_rest_turn["feline_agility_available"] = False
        runtime_after_rest_turn["feline_agility_active"] = True
        pc.race_features["runtime"] = runtime_after_rest_turn
        assert ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=True) is True
        runtime_after_reset = (pc.race_features or {}).get("runtime") or {}
        assert runtime_after_reset.get("feline_agility_available") is True
        assert runtime_after_reset.get("feline_agility_active") is False
    finally:
        end_combat(session_id)
