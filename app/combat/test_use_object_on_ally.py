from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import add_enemy, end_combat, get_combat, start_combat, upsert_pc


def _texts(patch: dict) -> list[str]:
    return [line.get("text") for line in patch["lines"] if isinstance(line, dict) and isinstance(line.get("text"), str)]


def test_combat_use_object_on_ally_success(monkeypatch) -> None:
    session_id = "test_combat_use_object_on_ally_success"
    start_combat(session_id)
    upsert_pc(
        session_id,
        pc_key="pc_1",
        name="Клирик",
        hp=10,
        hp_max=10,
        ac=12,
        initiative=20,
        inventory=[{"id": "pot_1", "name": "Зелье лечения", "qty": 2, "def": "healing_potion"}],
    )
    upsert_pc(
        session_id,
        pc_key="pc_2",
        name="Воин",
        hp=0,
        hp_max=14,
        ac=14,
        initiative=15,
    )
    add_enemy(session_id, name="Гоблин", hp=8, ac=11)

    state = get_combat(session_id)
    assert state is not None
    state.turn_index = 0
    state.order = ["pc_1", "pc_2", "enemy_1"]

    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 2)

    try:
        patch, err = handle_live_combat_action("combat_use_object_on_ally", session_id)
        assert err is None
        assert patch is not None

        texts = _texts(patch)
        assert any("Предмет:" in text and "→ Воин" in text for text in texts)

        state = get_combat(session_id)
        assert state is not None
        target = state.combatants["pc_2"]
        assert target.hp_current == 6

        actor = state.combatants["pc_1"]
        inv = actor.inventory if isinstance(actor.inventory, list) else []
        assert inv
        first = inv[0] if isinstance(inv[0], dict) else {}
        assert first.get("qty") == 1
    finally:
        end_combat(session_id)


def test_combat_use_object_on_ally_no_potion() -> None:
    session_id = "test_combat_use_object_on_ally_no_potion"
    start_combat(session_id)
    upsert_pc(
        session_id,
        pc_key="pc_1",
        name="Клирик",
        hp=10,
        hp_max=10,
        ac=12,
        initiative=20,
        inventory=[],
    )
    upsert_pc(
        session_id,
        pc_key="pc_2",
        name="Воин",
        hp=0,
        hp_max=14,
        ac=14,
        initiative=15,
    )
    add_enemy(session_id, name="Гоблин", hp=8, ac=11)

    state = get_combat(session_id)
    assert state is not None
    state.turn_index = 0
    state.order = ["pc_1", "pc_2", "enemy_1"]

    try:
        patch, err = handle_live_combat_action("combat_use_object_on_ally", session_id)
        assert err is None
        assert patch is not None
        assert any("нет лечащего предмета." in text for text in _texts(patch))
    finally:
        end_combat(session_id)


def test_combat_use_object_on_ally_no_downed_ally() -> None:
    session_id = "test_combat_use_object_on_ally_no_downed_ally"
    start_combat(session_id)
    upsert_pc(
        session_id,
        pc_key="pc_1",
        name="Клирик",
        hp=10,
        hp_max=10,
        ac=12,
        initiative=20,
        inventory=[{"id": "pot_1", "name": "Зелье лечения", "qty": 1, "def": "healing_potion"}],
    )
    upsert_pc(
        session_id,
        pc_key="pc_2",
        name="Воин",
        hp=7,
        hp_max=14,
        ac=14,
        initiative=15,
    )
    add_enemy(session_id, name="Гоблин", hp=8, ac=11)

    state = get_combat(session_id)
    assert state is not None
    state.turn_index = 0
    state.order = ["pc_1", "pc_2", "enemy_1"]

    try:
        patch, err = handle_live_combat_action("combat_use_object_on_ally", session_id)
        assert err is None
        assert patch is not None
        assert any("нет цели для лечения." in text for text in _texts(patch))
    finally:
        end_combat(session_id)
