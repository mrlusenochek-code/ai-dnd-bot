from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.web import ws_handlers


def test_tortle_shell_defense_activation_exit_and_reset() -> None:
    session_id = "test_tortle_shell_defense"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Tortle",
        side="pc",
        hp_current=22,
        hp_max=22,
        ac=17,
        initiative=20,
        level=3,
        stats={"str": 60, "con": 60, "dex": 50, "wis": 55},
        race_features={
            "race_key": "tortle",
            "natural_armor": {"ac": 17, "no_armor_stack": True},
            "features": {
                "shell_defense": {
                    "type": "shell_defense",
                    "ac_bonus": 4,
                    "adv_saves": ["str", "con"],
                    "disadv_saves": ["dex"],
                    "speed_override_ft": 0,
                }
            },
            "runtime": {
                "shell_defense_active": False,
                "shell_defense_entered_turn": "",
            },
        },
        movement_speeds={"walk": 30},
        speed_ft=30,
        move_speed_ft=30,
        move_remaining_ft=30,
    )
    state.combatants["enemy_1"] = Combatant(key="enemy_1", name="Guard", side="enemy", hp_current=14, hp_max=14, ac=12, initiative=5)
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_shell_defense", session_id)
        assert err is None and patch is not None
        actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        runtime = (actor.race_features or {}).get("runtime") or {}
        assert actor.action_available is False
        assert int(actor.ac or 0) == 21
        assert int(actor.move_speed_ft or 0) == 0
        assert int(actor.move_remaining_ft or 0) == 0
        assert runtime.get("shell_defense_active") is True
        assert ws_handlers._effective_save_mode("normal", actor.race_features, "str") == "advantage"
        assert ws_handlers._effective_save_mode("normal", actor.race_features, "con") == "advantage"
        assert ws_handlers._effective_save_mode("normal", actor.race_features, "dex") == "disadvantage"

        actor.action_available = True
        patch_again, err_again = handle_live_combat_action("combat_shell_defense", session_id)
        assert patch_again is None
        assert err_again is not None and "уже активна" in err_again

        actor.action_available = True
        patch_exit, err_exit = handle_live_combat_action("combat_shell_defense_exit", session_id)
        assert err_exit is None and patch_exit is not None
        runtime_after = (actor.race_features or {}).get("runtime") or {}
        assert runtime_after.get("shell_defense_active") is False
        assert int(actor.ac or 0) == 17
        assert int(actor.move_speed_ft or 0) == 30
        assert int(actor.move_remaining_ft or 0) == 30
        assert ws_handlers._effective_save_mode("normal", actor.race_features, "str") == "normal"
        assert ws_handlers._effective_save_mode("normal", actor.race_features, "dex") == "normal"

        runtime_after["shell_defense_active"] = True
        runtime_after["ac_bonus"] = 4
        runtime_after["speed_override_ft"] = 0
        actor.race_features["runtime"] = runtime_after
        assert ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=True) is True
        runtime_reset = (actor.race_features or {}).get("runtime") or {}
        assert runtime_reset.get("shell_defense_active") is False
        assert "ac_bonus" not in runtime_reset
        assert "speed_override_ft" not in runtime_reset
    finally:
        end_combat(session_id)
