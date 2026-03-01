from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _build_state(session_id: str, *, actor_wis: int) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Лекарь",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=20,
        stats={"wis": actor_wis},
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Раненый",
        side="pc",
        hp_current=0,
        hp_max=12,
        ac=12,
        initiative=10,
        is_stable=False,
        is_dead=False,
    )
    state.order = ["pc_1", "pc_2"]
    state.turn_index = 0


def test_combat_stabilize_success(monkeypatch) -> None:
    session_id = "test_combat_stabilize_success"
    _build_state(session_id, actor_wis=90)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 10)

    try:
        patch, err = handle_live_combat_action("combat_stabilize", session_id)
        assert err is None
        assert patch is not None

        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_2"].is_stable is True

        texts = [line.get("text") for line in patch["lines"] if isinstance(line, dict)]
        assert any("Результат: успех" in text for text in texts if isinstance(text, str))
    finally:
        end_combat(session_id)


def test_combat_stabilize_failure(monkeypatch) -> None:
    session_id = "test_combat_stabilize_failure"
    _build_state(session_id, actor_wis=50)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 1)

    try:
        patch, err = handle_live_combat_action("combat_stabilize", session_id)
        assert err is None
        assert patch is not None

        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_2"].is_stable is False

        texts = [line.get("text") for line in patch["lines"] if isinstance(line, dict)]
        assert any("провал" in text for text in texts if isinstance(text, str))
    finally:
        end_combat(session_id)
