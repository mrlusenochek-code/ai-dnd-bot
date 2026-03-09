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


def test_grung_contact_poison_and_end_of_turn_save_cycle(monkeypatch) -> None:
    session_id = "test_grung_contact_poison_and_end_of_turn_save_cycle"
    state = start_combat(session_id)
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=28,
        hp_max=28,
        ac=12,
        initiative=20,
        level=2,
        stats={"str": 50, "dex": 55, "con": 40},
        action_available=True,
        bonus_action_available=True,
        inventory=[{"id": "w1", "def": "dagger", "name": "Кинжал", "qty": 1}],
        equip={"main_hand": "w1"},
        race_features={"size": "medium", "runtime": {}},
    )
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Grung",
        side="pc",
        hp_current=24,
        hp_max=24,
        ac=13,
        initiative=10,
        level=3,
        stats={"dex": 60, "con": 55},
        race_features={
            "size": "small",
            "features": {
                "poisonous_skin": {
                    "contact_save_dc": 12,
                    "contact_condition": {"condition": "poisoned", "duration": "1_minute", "repeat_save": "end_of_turn"},
                }
            },
            "immunities": {"damage": ["poison"], "conditions": ["poisoned"]},
            "runtime": {},
        },
    )
    state.order = ["enemy_1", "pc_1"]
    state.turn_index = 0

    # 1st enemy attack: d20 hit, d4 damage, contact save fail, end-turn save fail
    # 2nd enemy attack while poisoned: disadvantage d20,d20, damage roll, end-turn save success
    rolls = iter([18, 3, 2, 3, 17, 4, 2, 19])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))
    monkeypatch.setattr("app.combat.turns.random.randint", lambda _a, _b: next(rolls))

    try:
        first_patch, first_err = handle_live_combat_action("combat_attack", session_id)
        assert first_err is None
        assert first_patch is not None
        first_lines = _line_texts(first_patch)
        assert any("ядовитая кожа (контакт)" in t.lower() for t in first_lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        enemy_runtime = ((state_now.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        conditions = enemy_runtime.get("conditions") or {}
        poisoned = conditions.get("poisoned") or {}
        assert poisoned.get("active") is True
        assert int(poisoned.get("remaining_rounds") or 0) >= 9

        # Pass PC turn quickly to enemy turn.
        pass_patch, pass_err = handle_live_combat_action("combat_end_turn", session_id)
        assert pass_err is None
        assert pass_patch is not None

        second_patch, second_err = handle_live_combat_action("combat_attack", session_id)
        assert second_err is None
        assert second_patch is not None
        second_lines = _line_texts(second_patch)
        assert any("d20(17,4) -> 4" in t for t in second_lines)

        state_after = get_combat(session_id)
        assert state_after is not None
        enemy_runtime_after = ((state_after.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        conditions_after = enemy_runtime_after.get("conditions") or {}
        assert "poisoned" not in conditions_after

        # poisoned imposes disadvantage for checks/toolchecks in ws layer
        rf = {"runtime": {"conditions": {"poisoned": {"active": True, "remaining_rounds": 5}}}}
        assert ws_handlers._mode_with_poisoned_disadvantage("normal", rf) == "disadvantage"
        assert ws_handlers._mode_with_poisoned_disadvantage("advantage", rf) == "normal"
    finally:
        end_combat(session_id)
