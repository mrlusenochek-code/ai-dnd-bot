from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, advance_turn, end_combat, get_combat, start_combat


def test_minotaur_hammering_horns_available_after_melee_hit_and_consumed_on_use(monkeypatch) -> None:
    session_id = "test_minotaur_hammering_horns_available_after_melee_hit_and_consumed_on_use"
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
        stats={"str": 60, "dex": 50, "con": 55, "int": 50, "wis": 50, "cha": 50},
        inventory=[{"id": "w1", "def": "longsword"}],
        equip={"main_hand": "w1"},
        race_features={
            "natural_weapons": [
                {"key": "horns_minotaur", "damage_dice": "1d6", "damage_type": "piercing", "kind": "unarmed", "ability": "str"}
            ],
            "features": {"hammering_horns": {"push_ft": 10, "save": {"ability": "str", "dc_formula": "8 + prof + str_mod"}}},
            "runtime": {},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=35,
        hp_max=35,
        ac=10,
        initiative=10,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 50, "dex": 50, "con": 50, "wis": 50},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    # combat_attack: hit + damage; combat_hammering_horns: STR save fail
    rolls = iter([15, 4, 3])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        attack_patch, attack_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_err is None
        assert attack_patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.turn_index == 0  # can still use bonus action
        runtime = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert bool(runtime.get("hammering_horns_available")) is True
        assert str(runtime.get("hammering_horns_target_id") or "") == "enemy_1"

        horns_patch, horns_err = handle_live_combat_action("combat_hammering_horns", session_id)
        assert horns_err is None
        assert horns_patch is not None
        lines = [item.get("text", "") for item in (horns_patch.get("lines") or []) if isinstance(item, dict)]
        assert any("оттолкнут на 10 фт" in t for t in lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.turn_index == 1
        pc = state_now.combatants["pc_1"]
        assert pc.bonus_action_available is False
        runtime_after = ((pc.race_features or {}).get("runtime") or {})
        assert bool(runtime_after.get("hammering_horns_available")) is False
        assert str(runtime_after.get("hammering_horns_target_id") or "") == ""

        # without new melee hit, ability must stay unavailable
        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        state_now.combatants["pc_1"].bonus_action_available = True
        patch_again, err_again = handle_live_combat_action("combat_hammering_horns", session_id)
        assert patch_again is None
        assert err_again is not None
        assert "сначала попадите" in err_again.lower()

        # next own turn cleanup keeps it unavailable
        state_now = get_combat(session_id)
        assert state_now is not None
        state_now.turn_index = 1
        assert advance_turn(session_id) is not None
        state_now = get_combat(session_id)
        assert state_now is not None
        state_now.combatants["pc_1"].bonus_action_available = True
        patch_next, err_next = handle_live_combat_action("combat_hammering_horns", session_id)
        assert patch_next is None
        assert err_next is not None
    finally:
        end_combat(session_id)
