from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.combat.turns import advance_turn_in_state


def test_hexblood_eerie_token_sense_sets_marker_and_expires() -> None:
    session_id = "test_hexblood_eerie_token_sense_sets_marker_and_expires"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Hexblood",
        side="pc",
        hp_current=18,
        hp_max=18,
        ac=13,
        initiative=18,
        level=3,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        speed_ft=30,
        move_speed_ft=30,
        race_features={
            "features": {
                "eerie_token": {
                    "create_activation": "bonus_action",
                    "range_miles": 10,
                    "message_words_max": 25,
                    "remote_view_duration": "1_minute",
                    "consumes_token_on_view": True,
                    "uses": "per_long_rest",
                    "uses_max": 1,
                }
            },
            "runtime": {
                "eerie_token_uses_used": 0,
                "eerie_token_active": False,
                "eerie_token_consumed": False,
                "eerie_token_id": "",
                "eerie_token_created_at": "",
                "eerie_token_last_message": "",
                "eerie_token_sense_active": False,
                "eerie_token_remote_view_rounds_left": 0,
            },
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=12,
        hp_max=12,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        create_patch, create_err = handle_live_combat_action("combat_eerie_token_create", session_id)
        assert create_err is None
        assert create_patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        pc.action_available = True

        sense_patch, sense_err = handle_live_combat_action("combat_eerie_token_view", session_id)
        assert sense_err is None
        assert sense_patch is not None
        runtime = ((pc.race_features or {}).get("runtime") or {})
        assert runtime.get("eerie_token_active") is False
        assert runtime.get("eerie_token_consumed") is True
        assert runtime.get("eerie_token_sense_active") is True
        assert int(runtime.get("eerie_token_remote_view_rounds_left") or 0) == 10

        for _ in range(20):
            advance_turn_in_state(state_now)

        runtime_after = ((pc.race_features or {}).get("runtime") or {})
        assert runtime_after.get("eerie_token_sense_active") is False
        assert int(runtime_after.get("eerie_token_remote_view_rounds_left") or 0) == 0
    finally:
        end_combat(session_id)
