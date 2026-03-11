from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def test_minotaur_goring_rush_requires_dash_and_20ft_move_and_spends_bonus_action(monkeypatch) -> None:
    session_id = "test_minotaur_goring_rush_requires_dash_and_20ft_move_and_spends_bonus_action"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Minotaur",
        side="pc",
        hp_current=24,
        hp_max=24,
        ac=14,
        initiative=20,
        level=1,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        speed_ft=30,
        move_speed_ft=30,
        move_remaining_ft=30,
        move_remaining=30,
        moved_this_turn_ft=0,
        stats={"str": 60, "dex": 50, "con": 55, "int": 50, "wis": 50, "cha": 50},
        race_features={
            "features": {
                "goring_rush": {"requires": {"dash": True, "move_ft": 20}, "activation": "bonus_action", "attack": "horns"},
            },
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
        stats={"str": 50, "dex": 50, "con": 50},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    # goring attack roll + damage
    rolls = iter([15, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        dash_patch, dash_err = handle_live_combat_action("combat_dash", session_id)
        assert dash_err is None
        assert dash_patch is not None

        move_patch, move_err = handle_live_combat_action("combat_move", session_id, distance_ft=20)
        assert move_err is None
        assert move_patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert bool(runtime.get("goring_rush_available")) is True

        rush_patch, rush_err = handle_live_combat_action("combat_goring_rush", session_id)
        assert rush_err is None
        assert rush_patch is not None
        lines = [item.get("text", "") for item in (rush_patch.get("lines") or []) if isinstance(item, dict)]
        assert any("Пронзающий натиск" in t for t in lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.turn_index == 1  # passed to enemy
        pc = state_now.combatants["pc_1"]
        assert pc.bonus_action_available is False
        runtime_after = ((pc.race_features or {}).get("runtime") or {})
        assert bool(runtime_after.get("goring_rush_available")) is False
    finally:
        end_combat(session_id)


def test_minotaur_goring_rush_blocks_without_dash_or_without_20ft_move() -> None:
    session_id = "test_minotaur_goring_rush_blocks_without_dash_or_without_20ft_move"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Minotaur",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=14,
        initiative=20,
        action_available=True,
        bonus_action_available=True,
        speed_ft=30,
        move_speed_ft=30,
        move_remaining_ft=30,
        move_remaining=30,
        stats={"str": 60, "dex": 50, "con": 55, "int": 50, "wis": 50, "cha": 50},
        race_features={"features": {"goring_rush": {"requires": {"dash": True, "move_ft": 20}}}, "runtime": {}},
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
        patch_no_dash, err_no_dash = handle_live_combat_action("combat_goring_rush", session_id)
        assert patch_no_dash is None
        assert err_no_dash is not None
        assert "рывок" in err_no_dash.lower()

        dash_patch, dash_err = handle_live_combat_action("combat_dash", session_id)
        assert dash_err is None
        assert dash_patch is not None
        move_patch, move_err = handle_live_combat_action("combat_move", session_id, distance_ft=10)
        assert move_err is None
        assert move_patch is not None

        patch_short_move, err_short_move = handle_live_combat_action("combat_goring_rush", session_id)
        assert patch_short_move is None
        assert err_short_move is not None
        assert "20" in err_short_move
    finally:
        end_combat(session_id)


def test_minotaur_goring_rush_expires_on_next_turn_if_unused() -> None:
    session_id = "test_minotaur_goring_rush_expires_on_next_turn_if_unused"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Minotaur",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=14,
        initiative=20,
        action_available=True,
        bonus_action_available=True,
        speed_ft=30,
        move_speed_ft=30,
        move_remaining_ft=30,
        move_remaining=30,
        stats={"str": 60, "dex": 50, "con": 55},
        race_features={"features": {"goring_rush": {"requires": {"dash": True, "move_ft": 20}}}, "runtime": {}},
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
        dash_patch, dash_err = handle_live_combat_action("combat_dash", session_id)
        assert dash_err is None
        assert dash_patch is not None
        move_patch, move_err = handle_live_combat_action("combat_move", session_id, distance_ft=20)
        assert move_err is None
        assert move_patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert bool(runtime.get("goring_rush_available")) is True

        end_turn_patch, end_turn_err = handle_live_combat_action("combat_end_turn", session_id)
        assert end_turn_err is None
        assert end_turn_patch is not None

        state_after = get_combat(session_id)
        assert state_after is not None
        runtime_after = ((state_after.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert bool(runtime_after.get("goring_rush_available")) is False
    finally:
        end_combat(session_id)


def test_minotaur_goring_rush_does_not_leak_between_battles() -> None:
    session_id = "test_minotaur_goring_rush_does_not_leak_between_battles"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Minotaur",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=14,
        initiative=20,
        race_features={
            "features": {"goring_rush": {"requires": {"dash": True, "move_ft": 20}}},
            "runtime": {"goring_rush_available": True, "hammering_horns_available": True, "hammering_horns_target_id": "enemy_1"},
        },
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

    end_combat(session_id)

    assert get_combat(session_id) is None
    runtime = ((state.combatants["pc_1"].race_features or {}).get("runtime") or {})
    assert bool(runtime.get("goring_rush_available")) is False
    assert bool(runtime.get("hammering_horns_available")) is False
    assert str(runtime.get("hammering_horns_target_id") or "") == ""
