from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import add_enemy, end_combat, get_combat, start_combat, upsert_pc


def _texts(patch: dict) -> list[str]:
    return [line.get("text") for line in patch["lines"] if isinstance(line, dict) and isinstance(line.get("text"), str)]


def test_auto_potion_on_zero_hp_uses_healing_consumable_before_death_save(monkeypatch) -> None:
    session_id = "test_auto_potion_on_zero_hp_uses_healing_consumable_before_death_save"
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
    state.combatants["pc_1"].is_dead = False
    state.combatants["pc_1"].is_stable = False

    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 2)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None

        texts = _texts(patch)
        assert any("Авто-предмет:" in text for text in texts)
        assert not any("Спасбросок смерти" in text for text in texts)

        state = get_combat(session_id)
        assert state is not None
        pc = state.combatants["pc_1"]
        assert pc.hp_current == 6

        inv = pc.inventory if isinstance(pc.inventory, list) else []
        assert len(inv) == 0
    finally:
        end_combat(session_id)


def test_auto_potion_on_zero_hp_uses_weakest_consumable(monkeypatch) -> None:
    session_id = "test_auto_potion_on_zero_hp_uses_weakest_consumable"
    start_combat(session_id)
    upsert_pc(
        session_id,
        pc_key="pc_1",
        name="Герой",
        hp=0,
        hp_max=20,
        ac=12,
        initiative=20,
        inventory=[
            {"id": "pot_1", "name": "Зелье лечения", "qty": 1, "def": "healing_potion"},
            {"id": "pot_2", "name": "Большое зелье лечения", "qty": 1, "def": "greater_healing_potion"},
        ],
    )
    add_enemy(session_id, name="Гоблин", hp=8, ac=11)

    state = get_combat(session_id)
    assert state is not None
    state.turn_index = 0
    state.order = ["pc_1", "enemy_1"]

    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 2)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None

        texts = _texts(patch)
        auto_lines = [text for text in texts if "Авто-предмет:" in text]
        assert auto_lines
        assert any("Зелье лечения" in text or "healing_potion" in text for text in auto_lines)

        state = get_combat(session_id)
        assert state is not None
        pc = state.combatants["pc_1"]
        inv = pc.inventory if isinstance(pc.inventory, list) else []
        defs = [entry.get("def") for entry in inv if isinstance(entry, dict)]
        assert "healing_potion" not in defs
        assert "greater_healing_potion" in defs
    finally:
        end_combat(session_id)


def test_auto_potion_on_zero_hp_without_consumables_rolls_death_save(monkeypatch) -> None:
    session_id = "test_auto_potion_on_zero_hp_without_consumables_rolls_death_save"
    start_combat(session_id)
    upsert_pc(
        session_id,
        pc_key="pc_1",
        name="Герой",
        hp=0,
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

    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 10)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        assert any("Спасбросок смерти" in text for text in _texts(patch))
    finally:
        end_combat(session_id)
