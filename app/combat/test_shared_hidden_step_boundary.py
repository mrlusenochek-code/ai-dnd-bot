from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, advance_turn, end_combat, get_combat, start_combat


def _build_hidden_step_state(session_id: str) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Firbolg",
        side="pc",
        hp_current=24,
        hp_max=24,
        ac=14,
        initiative=20,
        level=5,
        stats={"str": 55, "wis": 60},
        race_features={
            "features": {
                "hidden_step": {
                    "activation": "bonus_action",
                    "duration": "until_start_of_next_turn_or_break",
                    "breaks_on": ["attack", "deal_damage_roll", "force_saving_throw"],
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                }
            },
            "runtime": {
                "sentinel_top": "keep-top",
                "conditions": {"custom_marker": {"active": True, "tag": "keep-condition"}},
            },
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=40,
        hp_max=40,
        ac=11,
        initiative=10,
        stats={"dex": 50},
        race_features={},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def test_shared_hidden_step_boundary_activation_and_owner_turn_start_expiry() -> None:
    session_id = "test_shared_hidden_step_boundary_activation_and_owner_turn_start_expiry"
    _build_hidden_step_state(session_id)

    try:
        patch, err = handle_live_combat_action("combat_hidden_step", session_id)
        assert err is None
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.turn_index == 1

        actor_runtime = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        actor_conditions = actor_runtime.get("conditions") or {}
        hidden_step = actor_runtime.get("hidden_step") or {}

        assert actor_runtime.get("sentinel_top") == "keep-top"
        assert (actor_conditions.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert hidden_step.get("active") is True
        assert int(hidden_step.get("used") or 0) == 1
        assert str(hidden_step.get("source") or "") == "hidden_step"
        assert hidden_step.get("expires_on_owner_turn_start") is True

        assert advance_turn(session_id) is not None
        state_after = get_combat(session_id)
        assert state_after is not None
        assert state_after.turn_index == 0

        actor_runtime_after = ((state_after.combatants["pc_1"].race_features or {}).get("runtime") or {})
        actor_conditions_after = actor_runtime_after.get("conditions") or {}
        hidden_after = actor_runtime_after.get("hidden_step") or {}

        assert actor_runtime_after.get("sentinel_top") == "keep-top"
        assert (actor_conditions_after.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert hidden_after.get("active") is False
        assert int(hidden_after.get("used") or 0) == 1
        assert str(hidden_after.get("source") or "") == "hidden_step"
        assert hidden_after.get("expires_on_owner_turn_start") is True
    finally:
        end_combat(session_id)


def test_shared_hidden_step_boundary_no_drift_after_expiry_progression() -> None:
    session_id = "test_shared_hidden_step_boundary_no_drift_after_expiry_progression"
    _build_hidden_step_state(session_id)

    try:
        patch, err = handle_live_combat_action("combat_hidden_step", session_id)
        assert err is None
        assert patch is not None

        assert advance_turn(session_id) is not None
        state_after_expiry = get_combat(session_id)
        assert state_after_expiry is not None
        actor_runtime_after_expiry = ((state_after_expiry.combatants["pc_1"].race_features or {}).get("runtime") or {})

        assert advance_turn(session_id) is not None
        assert advance_turn(session_id) is not None
        state_after_more = get_combat(session_id)
        assert state_after_more is not None
        actor_runtime_after_more = ((state_after_more.combatants["pc_1"].race_features or {}).get("runtime") or {})

        assert actor_runtime_after_more == actor_runtime_after_expiry
    finally:
        end_combat(session_id)
