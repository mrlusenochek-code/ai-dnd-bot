from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, advance_turn, end_combat, get_combat, start_combat


def _build_eerie_token_state(session_id: str) -> None:
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
                "sentinel_top": "keep-top",
                "conditions": {"custom_marker": {"active": True, "tag": "keep-condition"}},
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


def test_shared_eerie_token_boundary_active_state_first_decrement_and_expiry() -> None:
    session_id = "test_shared_eerie_token_boundary_active_state_first_decrement_and_expiry"
    _build_eerie_token_state(session_id)

    try:
        create_patch, create_err = handle_live_combat_action("combat_eerie_token_create", session_id)
        assert create_err is None
        assert create_patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        actor.action_available = True

        sense_patch, sense_err = handle_live_combat_action("combat_eerie_token_view", session_id)
        assert sense_err is None
        assert sense_patch is not None

        runtime = ((actor.race_features or {}).get("runtime") or {})
        conditions = runtime.get("conditions") or {}
        assert runtime.get("sentinel_top") == "keep-top"
        assert (conditions.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert runtime.get("eerie_token_active") is False
        assert runtime.get("eerie_token_consumed") is True
        assert str(runtime.get("eerie_token_id") or "").startswith("et_")
        assert runtime.get("eerie_token_last_message") == ""
        assert runtime.get("eerie_token_sense_active") is True
        assert int(runtime.get("eerie_token_remote_view_rounds_left") or 0) == 10

        assert advance_turn(session_id) is not None
        state_after_first = get_combat(session_id)
        assert state_after_first is not None
        runtime_after_first = ((state_after_first.combatants["pc_1"].race_features or {}).get("runtime") or {})
        conditions_after_first = runtime_after_first.get("conditions") or {}
        assert runtime_after_first.get("sentinel_top") == "keep-top"
        assert (conditions_after_first.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert runtime_after_first.get("eerie_token_sense_active") is True
        assert int(runtime_after_first.get("eerie_token_remote_view_rounds_left") or 0) == 9

        for _ in range(18):
            assert advance_turn(session_id) is not None

        state_after_expiry = get_combat(session_id)
        assert state_after_expiry is not None
        runtime_after_expiry = ((state_after_expiry.combatants["pc_1"].race_features or {}).get("runtime") or {})
        conditions_after_expiry = runtime_after_expiry.get("conditions") or {}
        assert runtime_after_expiry.get("sentinel_top") == "keep-top"
        assert (conditions_after_expiry.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert runtime_after_expiry.get("eerie_token_sense_active") is False
        assert int(runtime_after_expiry.get("eerie_token_remote_view_rounds_left") or 0) == 0
    finally:
        end_combat(session_id)


def test_shared_eerie_token_boundary_no_drift_after_expiry() -> None:
    session_id = "test_shared_eerie_token_boundary_no_drift_after_expiry"
    _build_eerie_token_state(session_id)

    try:
        create_patch, create_err = handle_live_combat_action("combat_eerie_token_create", session_id)
        assert create_err is None
        assert create_patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        actor.action_available = True

        sense_patch, sense_err = handle_live_combat_action("combat_eerie_token_view", session_id)
        assert sense_err is None
        assert sense_patch is not None

        for _ in range(19):
            assert advance_turn(session_id) is not None

        state_after_expiry = get_combat(session_id)
        assert state_after_expiry is not None
        runtime_after_expiry = dict(((state_after_expiry.combatants["pc_1"].race_features or {}).get("runtime") or {}))

        assert advance_turn(session_id) is not None
        assert advance_turn(session_id) is not None

        state_after_more = get_combat(session_id)
        assert state_after_more is not None
        runtime_after_more = ((state_after_more.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert runtime_after_more == runtime_after_expiry
    finally:
        end_combat(session_id)
