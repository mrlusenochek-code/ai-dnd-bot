from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            out.append(text)
    return out


def test_autognome_built_for_success_applies_on_attack_and_spends_charge(monkeypatch) -> None:
    session_id = "test_autognome_built_for_success_applies_on_attack_and_spends_charge"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Autognome",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=1,
        stats={"str": 50},
        race_features={
            "features": {"built_for_success": {"dice": "1d4", "uses_formula": "proficiency_bonus", "uses": "per_long_rest"}},
            "runtime": {"built_for_success_used": 0, "built_for_success_armed": True},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=10,
        stats={"dex": 50},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([15, 4, 6])  # d20 attack, built_for_success d4, weapon damage d6
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Создан для успеха: +4 (1d4)." in t for t in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert int(runtime.get("built_for_success_used") or 0) == 1
        assert bool(runtime.get("built_for_success_armed")) is False
    finally:
        end_combat(session_id)


def test_autognome_built_for_success_applies_on_opportunity_attack(monkeypatch) -> None:
    session_id = "test_autognome_built_for_success_applies_on_opportunity_attack"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Autognome",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=1,
        stats={"str": 50},
        race_features={
            "features": {"built_for_success": {"dice": "1d4", "uses_formula": "proficiency_bonus", "uses": "per_long_rest"}},
            "runtime": {"built_for_success_used": 0, "built_for_success_armed": True},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=10,
        stats={"dex": 50},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([15, 4, 6])  # d20 attack, built_for_success d4, weapon damage d6
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_opportunity_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Создан для успеха: +4 (1d4)." in t for t in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert int(runtime.get("built_for_success_used") or 0) == 1
        assert bool(runtime.get("built_for_success_armed")) is False
    finally:
        end_combat(session_id)


def test_autognome_built_for_success_applies_on_death_save(monkeypatch) -> None:
    session_id = "test_autognome_built_for_success_applies_on_death_save"
    state = start_combat(session_id)
    state.combatants["pc_downed"] = Combatant(
        key="pc_downed",
        name="Downed Autognome",
        side="pc",
        hp_current=0,
        hp_max=12,
        ac=13,
        initiative=20,
        level=1,
        stats={"con": 50},
        race_features={
            "features": {"built_for_success": {"dice": "1d4", "uses_formula": "proficiency_bonus", "uses": "per_long_rest"}},
            "runtime": {"built_for_success_used": 0, "built_for_success_armed": True},
        },
    )
    state.combatants["pc_alive"] = Combatant(
        key="pc_alive",
        name="Ally",
        side="pc",
        hp_current=12,
        hp_max=12,
        ac=12,
        initiative=10,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=8,
        hp_max=8,
        ac=11,
        initiative=5,
    )
    state.order = ["pc_downed", "pc_alive", "enemy_1"]
    state.turn_index = 0
    monkeypatch.setattr("app.combat.live_actions.roll_check", lambda _mode: (10, None, 10))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)

    try:
        patch, err = handle_live_combat_action("combat_end_turn", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Создан для успеха: +4 (1d4)." in t for t in texts)
        assert any("Спасбросок смерти: d20(14)" in t for t in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime = ((state_now.combatants["pc_downed"].race_features or {}).get("runtime") or {})
        assert int(runtime.get("built_for_success_used") or 0) == 1
        assert bool(runtime.get("built_for_success_armed")) is False
    finally:
        end_combat(session_id)
