from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _build_state(session_id: str, *, reaction_available: bool) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Герой",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=20,
        reaction_available=reaction_available,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Гоблин",
        side="enemy",
        hp_current=12,
        hp_max=12,
        ac=30,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def test_combat_opportunity_attack_blocked_when_reaction_spent() -> None:
    session_id = "test_combat_opportunity_attack_blocked_when_reaction_spent"
    _build_state(session_id, reaction_available=False)

    try:
        patch, err = handle_live_combat_action("combat_opportunity_attack", session_id)
        assert err is None
        assert patch is not None

        texts = [line.get("text") for line in patch.get("lines", []) if isinstance(line, dict)]
        assert any("реакция уже потрачена" in text.lower() for text in texts if isinstance(text, str))

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.turn_index == 0
    finally:
        end_combat(session_id)


def test_combat_opportunity_attack_spends_reaction_without_advancing_turn(monkeypatch) -> None:
    session_id = "test_combat_opportunity_attack_spends_reaction_without_advancing_turn"
    _build_state(session_id, reaction_available=True)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 1)

    try:
        patch, err = handle_live_combat_action("combat_opportunity_attack", session_id)
        assert err is None
        assert patch is not None

        texts = [line.get("text") for line in patch.get("lines", []) if isinstance(line, dict)]
        assert any("атака возможности" in text.lower() for text in texts if isinstance(text, str))

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].reaction_available is False
        assert state_now.turn_index == 0
    finally:
        end_combat(session_id)
