from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.combat.turns import advance_turn_in_state


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    return [str(item.get("text") or "") for item in lines if isinstance(item, dict)]


def _rogue_class_features() -> dict:
    return {
        "features": [
            {
                "key": "sneak_attack",
                "mechanics": {
                    "type": "sneak_attack",
                    "frequency": "once_per_turn",
                    "requires_weapon": True,
                    "requires_finesse_or_ranged": True,
                    "condition": "advantage_or_adjacent_ally_and_no_disadvantage",
                    "damage_progression": [
                        {"level_from": 1, "dice": "1d6"},
                        {"level_from": 3, "dice": "2d6"},
                        {"level_from": 5, "dice": "3d6"},
                    ],
                },
            }
        ],
        "runtime": {},
    }


def _build_rogue_state(session_id: str, *, enemy_dodge: bool = False, with_feature: bool = True) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Rogue",
        side="pc",
        hp_current=24,
        hp_max=24,
        ac=14,
        initiative=20,
        level=5,
        stats={"str": 50, "dex": 90},
        inventory=[{"id": "w1", "def": "dagger", "name": "Кинжал", "qty": 1}],
        equip={"main_hand": "w1"},
        class_features=_rogue_class_features() if with_feature else {"features": [], "runtime": {}},
        help_attack_advantage=True,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=40,
        hp_max=40,
        ac=12,
        initiative=10,
        dodge_active=enemy_dodge,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def _set_positions(*, state, ally_position: dict | None, target_position: dict | None) -> None:
    if ally_position is not None:
        ally = Combatant(
            key="pc_2",
            name="Ally",
            side="pc",
            hp_current=20,
            hp_max=20,
            ac=12,
            initiative=15,
        )
        ally.position = ally_position
        state.combatants["pc_2"] = ally
    state.combatants["enemy_1"].position = target_position


def test_sneak_attack_triggers_with_adjacent_ally_same_node_and_coordinates(monkeypatch) -> None:
    session_id = "test_sneak_attack_triggers_with_adjacent_ally_same_node_and_coordinates"
    _build_rogue_state(session_id)
    state = get_combat(session_id)
    assert state is not None
    state.combatants["pc_1"].help_attack_advantage = False
    _set_positions(
        state=state,
        ally_position={"node_id": "room_a", "x_ft": 5, "y_ft": 0},
        target_position={"node_id": "room_a", "x_ft": 0, "y_ft": 0},
    )
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else (3 if _b == 4 else 2))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Скрытая атака: +6 (3d6)." in text for text in texts)
    finally:
        end_combat(session_id)


def test_sneak_attack_triggers_with_adjacent_ally_without_node_id_when_coordinates_exist(monkeypatch) -> None:
    session_id = "test_sneak_attack_triggers_with_adjacent_ally_without_node_id_when_coordinates_exist"
    _build_rogue_state(session_id)
    state = get_combat(session_id)
    assert state is not None
    state.combatants["pc_1"].help_attack_advantage = False
    _set_positions(
        state=state,
        ally_position={"x_ft": 4, "y_ft": 0},
        target_position={"x_ft": 0, "y_ft": 0},
    )
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else (3 if _b == 4 else 2))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Скрытая атака: +6 (3d6)." in text for text in texts)
    finally:
        end_combat(session_id)


def test_sneak_attack_does_not_trigger_when_adjacent_coordinates_but_different_nodes() -> None:
    session_id = "test_sneak_attack_does_not_trigger_when_adjacent_coordinates_but_different_nodes"
    _build_rogue_state(session_id)
    state = get_combat(session_id)
    assert state is not None
    state.combatants["pc_1"].help_attack_advantage = False
    _set_positions(
        state=state,
        ally_position={"node_id": "room_a", "x_ft": 4, "y_ft": 0},
        target_position={"node_id": "room_b", "x_ft": 0, "y_ft": 0},
    )

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert all("Скрытая атака:" not in text for text in texts)
    finally:
        end_combat(session_id)


def test_sneak_attack_does_not_trigger_when_same_node_but_no_coordinates() -> None:
    session_id = "test_sneak_attack_does_not_trigger_when_same_node_but_no_coordinates"
    _build_rogue_state(session_id)
    state = get_combat(session_id)
    assert state is not None
    state.combatants["pc_1"].help_attack_advantage = False
    _set_positions(
        state=state,
        ally_position={"node_id": "room_a"},
        target_position={"node_id": "room_a"},
    )

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert all("Скрытая атака:" not in text for text in texts)
    finally:
        end_combat(session_id)


def test_rogue_sneak_attack_adds_damage_with_advantage(monkeypatch) -> None:
    session_id = "test_rogue_sneak_attack_adds_damage_with_advantage"
    _build_rogue_state(session_id)
    rolls = iter([15, 7, 3, 5, 6, 1])  # adv d20s, dagger d4, sneak 3d6
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Скрытая атака: +12 (3d6)." in text for text in texts)
        assert any("Урон: 3 + 4 = 19" in text for text in texts)
    finally:
        end_combat(session_id)


def test_sneak_attack_does_not_trigger_twice_in_same_turn() -> None:
    session_id = "test_sneak_attack_does_not_trigger_twice_in_same_turn"
    _build_rogue_state(session_id)
    state = get_combat(session_id)
    assert state is not None
    actor = state.combatants["pc_1"]
    actor.class_features["runtime"] = {"sneak_attack_last_turn_id": "round:1:turn:0:actor:pc_1"}

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert all("Скрытая атака:" not in text for text in texts)
    finally:
        end_combat(session_id)


def test_sneak_attack_can_trigger_again_on_later_turn(monkeypatch) -> None:
    session_id = "test_sneak_attack_can_trigger_again_on_later_turn"
    _build_rogue_state(session_id)
    state = get_combat(session_id)
    assert state is not None
    actor = state.combatants["pc_1"]
    actor.class_features["runtime"] = {"sneak_attack_last_turn_id": "round:1:turn:0:actor:pc_1"}
    advance_turn_in_state(state)
    advance_turn_in_state(state)
    actor.help_attack_advantage = True
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else (3 if _b == 4 else 2))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Скрытая атака:" in text for text in texts)
    finally:
        end_combat(session_id)


def test_sneak_attack_does_not_trigger_with_disadvantage() -> None:
    session_id = "test_sneak_attack_does_not_trigger_with_disadvantage"
    _build_rogue_state(session_id, enemy_dodge=True)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert all("Скрытая атака:" not in text for text in texts)
    finally:
        end_combat(session_id)


def test_sneak_attack_crit_doubles_sneak_dice(monkeypatch) -> None:
    session_id = "test_sneak_attack_crit_doubles_sneak_dice"
    _build_rogue_state(session_id)
    rolls = iter([20, 5, 2, 1, 2, 3, 4, 5, 6])  # adv d20s, dagger d4, sneak 6d6
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Скрытая атака (крит): +21 (6d6)." in text for text in texts)
        assert any("Урон: 4 + 4 = 29" in text for text in texts)
    finally:
        end_combat(session_id)


def test_non_rogue_does_not_get_sneak_attack() -> None:
    session_id = "test_non_rogue_does_not_get_sneak_attack"
    _build_rogue_state(session_id, with_feature=False)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert all("Скрытая атака:" not in text for text in texts)
    finally:
        end_combat(session_id)
