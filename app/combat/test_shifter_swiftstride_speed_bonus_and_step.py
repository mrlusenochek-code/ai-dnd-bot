from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def test_swiftstride_speed_bonus_and_reaction_step() -> None:
    session_id = "test_swiftstride_speed_bonus_and_reaction_step"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Swiftstride",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        stats={"dex": 60, "cha": 55},
        race_features={
            "race_key": "shifter",
            "subrace": {"key": "swiftstride"},
            "features": {
                "shifting": {"uses_max": 1, "uses": "per_short_or_long_rest"},
                "shifting_mobility": {"walk_speed_bonus_ft": 10, "reaction_move_ft": 10, "no_opportunity_attacks": True},
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
    try:
        patch_shift, err_shift = handle_live_combat_action("combat_shift", session_id)
        assert err_shift is None and patch_shift is not None
        actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        assert int((actor.movement_speeds or {}).get("walk") or 0) == 40

        patch_step, err_step = handle_live_combat_action("combat_swiftstride_step", session_id)
        assert err_step is None and patch_step is not None
        texts = [item.get("text", "") for item in (patch_step.get("lines") or []) if isinstance(item, dict)]
        assert any("реакцией смещается на 10 фт" in t for t in texts)
        actor_after = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        assert bool(actor_after.reaction_available) is False
    finally:
        end_combat(session_id)
