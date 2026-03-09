from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.combat.turns import advance_turn_in_state
from app.web import ws_handlers


def test_wildhunt_mark_and_defense(monkeypatch) -> None:
    session_id = "test_wildhunt_mark_and_defense"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Wildhunt",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        stats={"wis": 60, "dex": 55, "con": 50},
        race_features={
            "race_key": "shifter",
            "subrace": {"key": "wildhunt"},
            "features": {
                "shifting": {"uses_max": 1, "uses": "per_short_or_long_rest"},
                "marked_target": {"uses_max": 1, "locate_range_ft": 60},
                "shifting_defense": {"advantage_on": ["wis_checks"], "deny_enemy_advantage_range_ft": 30, "while_conscious": True},
            },
            "runtime": {"shifted_active": False, "marked_uses_used": 0},
        },
        movement_speeds={"walk": 30},
        move_speed_ft=30,
        move_remaining_ft=30,
    )
    state.combatants["enemy_1"] = Combatant(key="enemy_1", name="Bandit", side="enemy", hp_current=12, hp_max=12, ac=11, initiative=5, help_attack_advantage=True)
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0
    try:
        patch_mark, err_mark = handle_live_combat_action("combat_mark_target", session_id, raw_text="mark Bandit")
        assert err_mark is None and patch_mark is not None
        runtime_after_mark = ((get_combat(session_id).combatants["pc_1"].race_features or {}).get("runtime") or {})  # type: ignore[union-attr]
        assert str(runtime_after_mark.get("wildhunt_marked_target_id") or "") == "enemy_1"
        assert int(runtime_after_mark.get("marked_uses_used") or 0) == 1

        advance_turn_in_state(state)
        advance_turn_in_state(state)
        patch_shift, err_shift = handle_live_combat_action("combat_shift", session_id)
        assert err_shift is None and patch_shift is not None

        ch_rf = (get_combat(session_id).combatants["pc_1"].race_features or {})  # type: ignore[union-attr]
        assert ws_handlers._mode_with_shifter_wildhunt_advantage("normal", ch_rf, check_name="survival", kind="skill") == "advantage"

        advance_turn_in_state(state)
        modes: list[str] = []
        monkeypatch.setattr(
            "app.combat.live_actions.roll_check",
            lambda mode, **_kwargs: (modes.append(mode) or True) and (12, None, 12),
        )
        patch_attack, err_attack = handle_live_combat_action("combat_attack", session_id)
        assert err_attack is None and patch_attack is not None
        assert modes and modes[0] == "normal"
    finally:
        end_combat(session_id)
