from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, start_combat
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


def test_kobold_sunlight_sensitivity_disadvantage_for_attacks_and_perception_checks() -> None:
    session_id = "test_kobold_sunlight_sensitivity_disadvantage_for_attacks_and_perception_checks"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Kobold",
        side="pc",
        hp_current=18,
        hp_max=18,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        stats={"str": 40, "dex": 60, "con": 50},
        race_features={
            "features": {
                "sunlight_sensitivity": ["attack_rolls", "perception_checks_relying_on_sight"],
            },
            "runtime": {"sunlight_bright": True},
        },
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
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    import app.combat.live_actions as live_actions

    seq = iter([19, 2, 4])
    old_randint = live_actions.random.randint
    live_actions.random.randint = lambda _a, _b: next(seq)
    try:
        attack_patch, attack_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_err is None
        assert attack_patch is not None
        assert any("d20(19,2) -> 2" in t for t in _line_texts(attack_patch))

        rf = {
            "features": {"sunlight_sensitivity": ["attack_rolls", "perception_checks_relying_on_sight"]},
        }
        assert ws_handlers._mode_with_sunlight_disadvantage(
            "normal",
            rf,
            sunlight_bright=True,
            check_name="perception",
        ) == "disadvantage"
        assert ws_handlers._mode_with_sunlight_disadvantage(
            "normal",
            rf,
            sunlight_bright=True,
            check_name="stealth",
        ) == "normal"
    finally:
        live_actions.random.randint = old_randint
        end_combat(session_id)
