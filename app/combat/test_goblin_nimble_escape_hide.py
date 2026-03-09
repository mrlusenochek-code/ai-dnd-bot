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


def test_goblin_nimble_escape_hide_grants_advantage_on_next_attack(monkeypatch) -> None:
    session_id = "test_goblin_nimble_escape_hide_grants_advantage_on_next_attack"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Goblin",
        side="pc",
        hp_current=22,
        hp_max=22,
        ac=14,
        initiative=20,
        level=3,
        action_available=True,
        bonus_action_available=True,
        stats={"str": 40, "dex": 60, "con": 50},
        race_features={
            "size": "small",
            "features": {"nimble_escape": True},
            "runtime": {},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=30,
        hp_max=30,
        ac=12,
        initiative=10,
        stats={"dex": 50},
        race_features={"size": "medium"},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([4, 17, 5])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        hide_patch, hide_err = handle_live_combat_action("combat_hide", session_id)
        assert hide_err is None
        assert hide_patch is not None
        hide_lines = _line_texts(hide_patch)
        assert any("прячется" in t.lower() for t in hide_lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc_now = state_now.combatants["pc_1"]
        runtime_now = (pc_now.race_features or {}).get("runtime") or {}
        hide_runtime = runtime_now.get("nimble_escape_hide") or {}
        assert hide_runtime.get("active") is True
        assert pc_now.bonus_action_available is False

        second_hide_patch, second_hide_err = handle_live_combat_action("combat_hide", session_id)
        assert second_hide_err is None
        assert second_hide_patch is not None
        second_hide_lines = _line_texts(second_hide_patch)
        assert any("бонусное действие уже потрачено" in t.lower() for t in second_hide_lines)

        attack_patch, attack_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_err is None
        assert attack_patch is not None
        attack_lines = _line_texts(attack_patch)
        assert any("d20(4,17) -> 17" in t for t in attack_lines)
        assert any("преимущество на эту атаку" in t.lower() for t in attack_lines)

        state_after = get_combat(session_id)
        assert state_after is not None
        pc_after = state_after.combatants["pc_1"]
        runtime_after = (pc_after.race_features or {}).get("runtime") or {}
        hide_after = runtime_after.get("nimble_escape_hide") or {}
        assert hide_after.get("active") is False
    finally:
        end_combat(session_id)
