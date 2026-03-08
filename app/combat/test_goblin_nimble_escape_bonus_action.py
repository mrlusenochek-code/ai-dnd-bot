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


def test_goblin_nimble_escape_spends_bonus_action_on_disengage() -> None:
    session_id = "test_goblin_nimble_escape_spends_bonus_action_on_disengage"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Goblin",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        action_available=True,
        bonus_action_available=True,
        race_features={"features": {"nimble_escape": True}},
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
        patch, err = handle_live_combat_action("combat_disengage", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Ловкое бегство: потрачено бонусное действие." in t for t in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        assert pc.action_available is True
        assert pc.bonus_action_available is False
    finally:
        end_combat(session_id)
