from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, advance_turn, end_combat, get_combat, start_combat
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


def test_leonin_daunting_roar_uses_bonus_action_applies_frightened_and_resets() -> None:
    session_id = "test_leonin_daunting_roar_uses_bonus_action_applies_frightened_and_resets"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Leonin",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 55, "dex": 50, "con": 60, "int": 50, "wis": 50, "cha": 50},
        race_features={
            "features": {
                "daunting_roar": {
                    "activation": "bonus_action",
                    "range_ft": 10,
                    "save": {"ability": "wis", "dc_formula": "8 + prof + con_mod"},
                    "duration": "until_end_of_your_next_turn",
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                }
            },
            "runtime": {},
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
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 50, "dex": 50, "con": 50, "wis": 50},
        race_features={"runtime": {}},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    import app.combat.live_actions as live_actions

    old_randint = live_actions.random.randint
    live_actions.random.randint = lambda _a, _b: 5  # WIS save fail vs DC 11
    try:
        patch, err = handle_live_combat_action("combat_daunting_roar", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("сл 11" in t.lower() for t in texts)
        assert any("испуган" in t.lower() for t in texts)

        st = get_combat(session_id)
        assert st is not None
        leonin = st.combatants["pc_1"]
        enemy = st.combatants["enemy_1"]
        assert leonin.bonus_action_available is False
        runtime = ((leonin.race_features or {}).get("runtime") or {})
        assert int(runtime.get("daunting_roar_uses_used") or 0) == 1
        enemy_conditions = ((((enemy.race_features or {}).get("runtime") or {}).get("conditions") or {}))
        frightened = enemy_conditions.get("frightened") or {}
        assert frightened.get("active") is True
        assert str(frightened.get("source") or "") == "leonin_daunting_roar"

        patch_again, err_again = handle_live_combat_action("combat_daunting_roar", session_id)
        assert patch_again is None
        assert err_again is not None
        assert "использован" in err_again.lower()

        # End of the same leonin turn: condition should still remain.
        st.turn_index = 0
        assert advance_turn(session_id) is not None
        st = get_combat(session_id)
        assert st is not None
        enemy_conditions = ((((st.combatants["enemy_1"].race_features or {}).get("runtime") or {}).get("conditions") or {}))
        assert "frightened" in enemy_conditions

        # End of leonin next turn: condition should expire.
        st.turn_index = 0
        assert advance_turn(session_id) is not None
        st = get_combat(session_id)
        assert st is not None
        enemy_conditions = ((((st.combatants["enemy_1"].race_features or {}).get("runtime") or {}).get("conditions") or {}))
        assert "frightened" not in enemy_conditions

        assert ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=False) is True
        st = get_combat(session_id)
        assert st is not None
        reset_runtime = ((st.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert "daunting_roar_uses_used" not in reset_runtime

        st.turn_index = 0
        st.combatants["pc_1"].bonus_action_available = True
        patch_after_rest, err_after_rest = handle_live_combat_action("combat_daunting_roar", session_id)
        assert err_after_rest is None
        assert patch_after_rest is not None
    finally:
        live_actions.random.randint = old_randint
        end_combat(session_id)
