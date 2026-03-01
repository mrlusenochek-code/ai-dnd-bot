from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import add_enemy, end_combat, get_combat, start_combat, upsert_pc


def _build_state(session_id: str) -> None:
    start_combat(session_id)
    upsert_pc(
        session_id,
        pc_key="pc_downed",
        name="Павший",
        hp=0,
        hp_max=12,
        ac=12,
        initiative=20,
    )
    upsert_pc(
        session_id,
        pc_key="pc_alive",
        name="Живой",
        hp=12,
        hp_max=12,
        ac=13,
        initiative=10,
    )
    add_enemy(session_id, name="Гоблин", hp=8, ac=11)
    state = get_combat(session_id)
    assert state is not None
    state.turn_index = 0
    state.order = ["pc_downed", "pc_alive", "enemy_1"]


def test_death_save_success_on_10(monkeypatch) -> None:
    session_id = "test_death_save_success_on_10"
    _build_state(session_id)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 10)

    try:
        patch, err = handle_live_combat_action("combat_end_turn", session_id)
        assert err is None
        assert patch is not None
        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_downed"].death_successes == 1
        texts = [line.get("text") for line in patch["lines"] if isinstance(line, dict)]
        assert any("Спасбросок смерти" in text for text in texts if isinstance(text, str))
        assert any("успех" in text for text in texts if isinstance(text, str))
    finally:
        end_combat(session_id)


def test_death_save_double_fail_on_1(monkeypatch) -> None:
    session_id = "test_death_save_double_fail_on_1"
    _build_state(session_id)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 1)

    try:
        patch, err = handle_live_combat_action("combat_end_turn", session_id)
        assert err is None
        assert patch is not None
        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_downed"].death_failures == 2
        texts = [line.get("text") for line in patch["lines"] if isinstance(line, dict)]
        assert any("два провала" in text for text in texts if isinstance(text, str))
    finally:
        end_combat(session_id)


def test_death_save_nat20_returns_to_1_hp(monkeypatch) -> None:
    session_id = "test_death_save_nat20_returns_to_1_hp"
    _build_state(session_id)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 20)

    try:
        patch, err = handle_live_combat_action("combat_end_turn", session_id)
        assert err is None
        assert patch is not None
        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_downed"].hp_current == 1
        texts = [line.get("text") for line in patch["lines"] if isinstance(line, dict)]
        assert any("1 HP" in text for text in texts if isinstance(text, str))
    finally:
        end_combat(session_id)
