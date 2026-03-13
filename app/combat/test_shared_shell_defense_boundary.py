from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def test_shared_shell_defense_boundary_preserves_unrelated_runtime_and_no_drift() -> None:
    session_id = "test_shared_shell_defense_boundary"
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
                "unrelated_top_level": "keep-me",
                "conditions": {"poisoned": {"active": True, "save_dc": 12}},
            },
        },
        movement_speeds={"walk": 30},
        speed_ft=30,
        move_speed_ft=30,
        move_remaining_ft=30,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Guard",
        side="enemy",
        hp_current=14,
        hp_max=14,
        ac=12,
        initiative=5,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch, err = handle_live_combat_action("combat_shell_defense", session_id)
        assert err is None and patch is not None
        actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        runtime = (actor.race_features or {}).get("runtime") or {}
        assert runtime.get("shell_defense_active") is True
        assert runtime.get("shell_defense_entered_turn") == "1:pc_1"
        assert int(runtime.get("ac_bonus") or 0) == 4
        assert runtime.get("speed_override_ft") == 0
        assert runtime.get("unrelated_top_level") == "keep-me"
        assert ((runtime.get("conditions") or {}).get("poisoned") or {}).get("active") is True
        assert int(actor.ac or 0) == 21
        assert int(actor.speed_ft or 0) == 0
        assert int(actor.move_speed_ft or 0) == 0
        assert int(actor.move_remaining_ft or 0) == 0

        actor.action_available = True
        patch_exit, err_exit = handle_live_combat_action("combat_shell_defense_exit", session_id)
        assert err_exit is None and patch_exit is not None
        runtime_after = (actor.race_features or {}).get("runtime") or {}
        assert runtime_after.get("shell_defense_active") is False
        assert runtime_after.get("shell_defense_entered_turn") == ""
        assert "ac_bonus" not in runtime_after
        assert "speed_override_ft" not in runtime_after
        assert runtime_after.get("unrelated_top_level") == "keep-me"
        assert ((runtime_after.get("conditions") or {}).get("poisoned") or {}).get("active") is True
        assert int(actor.ac or 0) == 17
        assert int(actor.speed_ft or 0) == 30
        assert int(actor.move_speed_ft or 0) == 30
        assert int(actor.move_remaining_ft or 0) == 30

        actor.action_available = True
        runtime_snapshot = dict(runtime_after)
        nested_conditions_snapshot = dict(runtime_after.get("conditions") or {})
        patch_exit_again, err_exit_again = handle_live_combat_action("combat_shell_defense_exit", session_id)
        assert patch_exit_again is None
        assert err_exit_again is not None and "сейчас не активна" in err_exit_again
        runtime_final = (actor.race_features or {}).get("runtime") or {}
        assert runtime_final == runtime_snapshot
        assert dict(runtime_final.get("conditions") or {}) == nested_conditions_snapshot
    finally:
        end_combat(session_id)
