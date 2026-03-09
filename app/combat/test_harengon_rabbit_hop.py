from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.web import ws_handlers


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def test_harengon_rabbit_hop_bonus_action_uses_and_long_rest_reset() -> None:
    session_id = "test_harengon_rabbit_hop_bonus_action_uses_and_long_rest_reset"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Harengon",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        bonus_action_available=True,
        speed_ft=30,
        move_speed_ft=30,
        race_features={
            "features": {
                "rabbit_hop": {
                    "activation": "bonus_action",
                    "distance_formula": "5 * proficiency_bonus",
                    "uses": "per_long_rest",
                    "uses_formula": "proficiency_bonus",
                    "requires": {"speed_gt_0": True},
                }
            },
            "runtime": {"rabbit_hop_uses_used": 0},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    try:
        patch_1, err_1 = handle_live_combat_action("combat_rabbit_hop", session_id)
        assert err_1 is None
        assert patch_1 is not None
        texts_1 = _line_texts(patch_1)
        assert any("10 фт" in t for t in texts_1)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        runtime = (pc.race_features or {}).get("runtime") or {}
        assert int(runtime.get("rabbit_hop_uses_used") or 0) == 1
        assert pc.bonus_action_available is False

        # next turn: reset bonus action manually for isolated action test
        pc.bonus_action_available = True
        patch_2, err_2 = handle_live_combat_action("combat_rabbit_hop", session_id)
        assert err_2 is None
        assert patch_2 is not None
        runtime2 = ((pc.race_features or {}).get("runtime") or {})
        assert int(runtime2.get("rabbit_hop_uses_used") or 0) == 2

        pc.bonus_action_available = True
        patch_3, err_3 = handle_live_combat_action("combat_rabbit_hop", session_id)
        assert patch_3 is None
        assert err_3 is not None and "исчерпан" in err_3.lower()

        reset_changed = ws_handlers._reset_combatant_harengon_long_rest(session_id, "pc_1")
        assert reset_changed is True
        runtime_reset = ((pc.race_features or {}).get("runtime") or {})
        assert int(runtime_reset.get("rabbit_hop_uses_used") or 0) == 0

        pc.bonus_action_available = True
        patch_4, err_4 = handle_live_combat_action("combat_rabbit_hop", session_id)
        assert err_4 is None
        assert patch_4 is not None

        pc.move_speed_ft = 0
        pc.speed_ft = 0
        pc.bonus_action_available = True
        patch_5, err_5 = handle_live_combat_action("combat_rabbit_hop", session_id)
        assert patch_5 is None
        assert err_5 is not None and "скорость" in err_5.lower()
    finally:
        end_combat(session_id)
