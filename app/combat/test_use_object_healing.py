from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import add_enemy, end_combat, get_combat, start_combat, upsert_pc


def test_combat_use_object_heals_and_revives(monkeypatch) -> None:
    session_id = "test_combat_use_object_heals_and_revives"
    start_combat(session_id)
    upsert_pc(
        session_id,
        pc_key="pc_1",
        name="Герой",
        hp=0,
        hp_max=10,
        ac=12,
        initiative=20,
        inventory=[{"id": "pot_1", "name": "Зелье лечения", "qty": 1, "def": "healing_potion"}],
    )
    add_enemy(session_id, name="Гоблин", hp=8, ac=11)

    state = get_combat(session_id)
    assert state is not None
    state.turn_index = 0
    state.order = ["pc_1", "enemy_1"]
    state.combatants["pc_1"].is_stable = True
    state.combatants["pc_1"].death_successes = 2
    state.combatants["pc_1"].death_failures = 1

    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 2)

    try:
        patch, err = handle_live_combat_action("combat_use_object", session_id)
        assert err is None
        assert patch is not None

        state = get_combat(session_id)
        assert state is not None
        pc = state.combatants["pc_1"]
        assert pc.hp_current == 6
        assert pc.death_successes == 0
        assert pc.death_failures == 0
        assert pc.is_stable is False

        inv = pc.inventory if isinstance(pc.inventory, list) else []
        assert len(inv) == 0

        texts = [line.get("text") for line in patch["lines"] if isinstance(line, dict)]
        assert any(isinstance(text, str) and "Предмет:" in text for text in texts)
    finally:
        end_combat(session_id)


def test_combat_use_object_heal_is_capped_by_hp_max(monkeypatch) -> None:
    session_id = "test_combat_use_object_heal_is_capped_by_hp_max"
    start_combat(session_id)
    upsert_pc(
        session_id,
        pc_key="pc_1",
        name="Герой",
        hp=8,
        hp_max=10,
        ac=12,
        initiative=20,
        inventory=[{"id": "pot_1", "name": "Зелье лечения", "qty": 1, "def": "healing_potion"}],
    )
    add_enemy(session_id, name="Гоблин", hp=8, ac=11)

    state = get_combat(session_id)
    assert state is not None
    state.turn_index = 0
    state.order = ["pc_1", "enemy_1"]

    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 2)

    try:
        patch, err = handle_live_combat_action("combat_use_object", session_id)
        assert err is None
        assert patch is not None

        state = get_combat(session_id)
        assert state is not None
        pc = state.combatants["pc_1"]
        assert pc.hp_current == 10

        inv = pc.inventory if isinstance(pc.inventory, list) else []
        assert len(inv) == 0
    finally:
        end_combat(session_id)


def test_combat_use_object_no_consumables_still_advances_turn() -> None:
    session_id = "test_combat_use_object_no_consumables_still_advances_turn"
    start_combat(session_id)
    upsert_pc(
        session_id,
        pc_key="pc_1",
        name="Герой",
        hp=10,
        hp_max=10,
        ac=12,
        initiative=20,
        inventory=[{"id": "dagger_1", "name": "Кинжал", "qty": 1, "def": "dagger"}],
    )
    add_enemy(session_id, name="Гоблин", hp=8, ac=11)

    state = get_combat(session_id)
    assert state is not None
    state.turn_index = 0
    state.order = ["pc_1", "enemy_1"]

    try:
        patch, err = handle_live_combat_action("combat_use_object", session_id)
        assert err is None
        assert patch is not None

        texts = [line.get("text") for line in patch["lines"] if isinstance(line, dict)]
        assert any(
            isinstance(text, str) and "нет подходящего предмета лечения" in text for text in texts
        )

        state = get_combat(session_id)
        assert state is not None
        assert state.turn_index == 1
    finally:
        end_combat(session_id)
