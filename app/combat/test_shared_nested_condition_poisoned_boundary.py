from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def _enemy_with_poison_runtime() -> Combatant:
    return Combatant(
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
        reaction_available=True,
        inventory=[{"id": "w1", "def": "dagger", "name": "Кинжал", "qty": 1}],
        equip={"main_hand": "w1"},
        race_features={
            "size": "medium",
            "runtime": {
                "sentinel_top": "keep-top",
                "conditions": {"custom_marker": {"active": True, "tag": "keep-condition"}},
            },
        },
    )


def _grung_target() -> Combatant:
    return Combatant(
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
                    "contact_condition": {
                        "condition": "poisoned",
                        "duration": "1_minute",
                        "repeat_save": "end_of_turn",
                    },
                }
            },
            "immunities": {"damage": ["poison"], "conditions": ["poisoned"]},
            "runtime": {},
        },
    )


def test_shared_nested_poisoned_boundary_action_write_and_failed_turn_cleanup(monkeypatch) -> None:
    session_id = "test_shared_nested_poisoned_boundary_action_write_and_failed_turn_cleanup"
    state = start_combat(session_id)
    state.combatants["enemy_1"] = _enemy_with_poison_runtime()
    state.combatants["pc_1"] = _grung_target()
    state.order = ["enemy_1", "pc_1"]
    state.turn_index = 0

    # first attack hit + damage + fail contact save + fail immediate end-turn save
    rolls = iter([18, 3, 2, 3])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))
    monkeypatch.setattr("app.combat.turns.random.randint", lambda _a, _b: next(rolls))

    try:
        first_patch, first_err = handle_live_combat_action("combat_attack", session_id)
        assert first_err is None
        assert first_patch is not None
        assert any("ядовитая кожа (контакт)" in t.lower() for t in _line_texts(first_patch))

        state_now = get_combat(session_id)
        assert state_now is not None
        enemy_runtime = ((state_now.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        conditions = enemy_runtime.get("conditions") or {}
        poisoned = conditions.get("poisoned") or {}
        assert enemy_runtime.get("sentinel_top") == "keep-top"
        assert (conditions.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert poisoned.get("active") is True
        assert int(poisoned.get("save_dc") or 0) == 12
        assert int(poisoned.get("remaining_rounds") or 0) == 9
        assert str(poisoned.get("repeat_save") or "") == "end_of_turn"
        assert str(poisoned.get("source") or "") == "grung_contact_poison"
    finally:
        end_combat(session_id)


def test_shared_nested_poisoned_boundary_success_cleanup_and_no_runtime_drift(monkeypatch) -> None:
    session_id = "test_shared_nested_poisoned_boundary_success_cleanup_and_no_runtime_drift"
    state = start_combat(session_id)
    state.combatants["enemy_1"] = _enemy_with_poison_runtime()
    state.combatants["pc_1"] = _grung_target()
    state.order = ["enemy_1", "pc_1"]
    state.turn_index = 0

    # first attack hit + damage + fail contact save + fail immediate end-turn save
    # second attack while poisoned: disadvantage attack + damage + successful end-turn save
    rolls = iter([18, 3, 2, 3, 17, 4, 2, 19])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))
    monkeypatch.setattr("app.combat.turns.random.randint", lambda _a, _b: next(rolls))

    try:
        first_patch, first_err = handle_live_combat_action("combat_attack", session_id)
        assert first_err is None
        assert first_patch is not None

        pass_patch, pass_err = handle_live_combat_action("combat_end_turn", session_id)
        assert pass_err is None
        assert pass_patch is not None

        second_patch, second_err = handle_live_combat_action("combat_attack", session_id)
        assert second_err is None
        assert second_patch is not None

        state_after = get_combat(session_id)
        assert state_after is not None
        enemy_runtime_after = ((state_after.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        conditions_after = enemy_runtime_after.get("conditions") or {}
        assert enemy_runtime_after.get("sentinel_top") == "keep-top"
        assert "poisoned" not in conditions_after
        assert (conditions_after.get("custom_marker") or {}).get("tag") == "keep-condition"

        # Next round with poison already removed must not drift unrelated runtime.
        pass_again_patch, pass_again_err = handle_live_combat_action("combat_end_turn", session_id)
        assert pass_again_err is None
        assert pass_again_patch is not None

        state_final = get_combat(session_id)
        assert state_final is not None
        enemy_runtime_final = ((state_final.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        assert enemy_runtime_final == enemy_runtime_after
    finally:
        end_combat(session_id)
