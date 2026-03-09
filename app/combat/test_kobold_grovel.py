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


def test_kobold_grovel_grants_advantage_and_resets() -> None:
    session_id = "test_kobold_grovel_grants_advantage_and_resets"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Kobold",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        stats={"str": 40, "dex": 60, "con": 50},
        race_features={
            "features": {
                "grovel_cower_beg": {
                    "range_ft": 10,
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                    "duration": "until_start_of_next_turn",
                }
            },
            "runtime": {},
        },
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Ally",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=18,
        action_available=True,
        stats={"str": 50, "dex": 55, "con": 50},
        inventory=[{"id": "w1", "def": "dagger", "name": "Кинжал", "qty": 1}],
        equip={"main_hand": "w1"},
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
    state.order = ["pc_1", "pc_2", "enemy_1"]
    state.turn_index = 0

    import app.combat.live_actions as live_actions

    seq = iter([4, 17, 4, 13, 4])
    old_randint = live_actions.random.randint
    live_actions.random.randint = lambda _a, _b: next(seq)
    try:
        grovel_patch, grovel_err = handle_live_combat_action("combat_grovel_cower_beg", session_id)
        assert grovel_err is None
        assert grovel_patch is not None
        assert any("отвлекает врагов" in t.lower() for t in _line_texts(grovel_patch))

        st = get_combat(session_id)
        assert st is not None
        kobold_runtime = ((st.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert int(kobold_runtime.get("grovel_uses_used") or 0) == 1

        st.turn_index = 1
        st.combatants["pc_2"].action_available = True
        attack_with_adv_patch, attack_with_adv_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_with_adv_err is None
        assert attack_with_adv_patch is not None
        assert any("d20(4,17) -> 17" in t for t in _line_texts(attack_with_adv_patch))

        st = get_combat(session_id)
        assert st is not None
        st.turn_index = 2
        advanced = advance_turn(session_id)
        assert advanced is not None

        st = get_combat(session_id)
        assert st is not None
        enemy_runtime = ((st.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        assert "groveled" not in enemy_runtime

        st.turn_index = 0
        st.combatants["pc_1"].action_available = True
        grovel_again_patch, grovel_again_err = handle_live_combat_action("combat_grovel_cower_beg", session_id)
        assert grovel_again_patch is None
        assert grovel_again_err is not None
        assert "использовано" in grovel_again_err.lower()

        assert ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=False) is True
        st.combatants["pc_1"].action_available = True
        grovel_after_rest_patch, grovel_after_rest_err = handle_live_combat_action("combat_grovel_cower_beg", session_id)
        assert grovel_after_rest_err is None
        assert grovel_after_rest_patch is not None
    finally:
        live_actions.random.randint = old_randint
        end_combat(session_id)
