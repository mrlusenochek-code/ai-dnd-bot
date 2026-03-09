from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.combat.turns import advance_turn_in_state
from app.web import ws_handlers


def test_beasthide_shift_temp_hp_duration_and_reset(monkeypatch) -> None:
    session_id = "test_beasthide_shift_temp_hp_duration"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Beasthide",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        stats={"con": 60, "str": 55},
        race_features={
            "race_key": "shifter",
            "subrace": {"key": "beasthide"},
            "features": {
                "shifting": {"uses_max": 1, "uses": "per_short_or_long_rest"},
                "shifting_bonus": {"temp_hp_extra": "1d6", "ac_bonus": 1},
            },
            "runtime": {"shifted_active": False, "shifting_uses_used": 0},
        },
        movement_speeds={"walk": 30},
        move_speed_ft=30,
        move_remaining_ft=30,
    )
    state.combatants["enemy_1"] = Combatant(key="enemy_1", name="Bandit", side="enemy", hp_current=10, hp_max=10, ac=12, initiative=5)
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)
    try:
        patch, err = handle_live_combat_action("combat_shift", session_id)
        assert err is None and patch is not None
        actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        runtime = (actor.race_features or {}).get("runtime") or {}
        assert bool(runtime.get("shifted_active")) is True
        assert int(runtime.get("shifted_rounds_left") or 0) == 10
        assert int(runtime.get("shifting_uses_used") or 0) == 1
        assert int(runtime.get("shifting_temp_hp_granted") or 0) == 8
        assert int(runtime.get("shifting_ac_bonus_active") or 0) == 1
        assert int(actor.temp_hp or 0) == 8
        assert int(actor.ac or 0) == 14

        patch_again, err_again = handle_live_combat_action("combat_shift", session_id)
        assert patch_again is None
        assert err_again is not None and "использована" in err_again

        for _ in range(19):
            advance_turn_in_state(state)
        actor_after = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        runtime_after = (actor_after.race_features or {}).get("runtime") or {}
        assert bool(runtime_after.get("shifted_active")) is False
        assert int(runtime_after.get("shifted_rounds_left") or 0) == 0

        reset_changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=False)
        assert reset_changed is True
        runtime_after_reset = ((get_combat(session_id).combatants["pc_1"].race_features or {}).get("runtime") or {})  # type: ignore[union-attr]
        assert int(runtime_after_reset.get("shifting_uses_used") or 0) == 0

        actor_after_reset = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        state.turn_index = 0
        actor_after_reset.bonus_action_available = True
        patch_end, err_end = handle_live_combat_action("combat_shift", session_id)
        assert err_end is None and patch_end is not None
        actor_after_reset.bonus_action_available = True
        patch_stop, err_stop = handle_live_combat_action("combat_shift_end", session_id)
        assert err_stop is None and patch_stop is not None
        runtime_stopped = ((get_combat(session_id).combatants["pc_1"].race_features or {}).get("runtime") or {})  # type: ignore[union-attr]
        assert bool(runtime_stopped.get("shifted_active")) is False
    finally:
        end_combat(session_id)
