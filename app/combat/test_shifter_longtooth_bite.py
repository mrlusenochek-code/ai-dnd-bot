from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.combat.turns import advance_turn_in_state


def test_longtooth_bite_while_shifted(monkeypatch) -> None:
    session_id = "test_longtooth_bite_while_shifted"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Longtooth",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        stats={"str": 60, "dex": 55},
        race_features={
            "race_key": "shifter",
            "subrace": {"key": "longtooth"},
            "features": {
                "shifting": {"uses_max": 1, "uses": "per_short_or_long_rest"},
                "shifting_bonus_action_attack": {"damage_dice": "1d6", "damage_type": "piercing", "ability": "str"},
            },
            "runtime": {"shifted_active": False, "shifting_uses_used": 0},
        },
        movement_speeds={"walk": 30},
        move_speed_ft=30,
        move_remaining_ft=30,
    )
    state.combatants["enemy_1"] = Combatant(key="enemy_1", name="Bandit", side="enemy", hp_current=15, hp_max=15, ac=10, initiative=5)
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0
    rolls = iter([18, 4])  # bite d20, bite damage
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))
    try:
        patch_shift, err_shift = handle_live_combat_action("combat_shift", session_id)
        assert err_shift is None and patch_shift is not None
        advance_turn_in_state(state)
        advance_turn_in_state(state)
        patch_bite, err_bite = handle_live_combat_action("combat_longtooth_bite", session_id)
        assert err_bite is None and patch_bite is not None
        texts = [item.get("text", "") for item in (patch_bite.get("lines") or []) if isinstance(item, dict)]
        assert any("Укус длиннозуба" in t for t in texts)
        assert any("= 5 piercing" in t for t in texts)
        enemy = get_combat(session_id).combatants["enemy_1"]  # type: ignore[union-attr]
        assert int(enemy.hp_current or 0) == 10
    finally:
        end_combat(session_id)
