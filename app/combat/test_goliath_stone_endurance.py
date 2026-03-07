from __future__ import annotations

from app.combat.live_actions import handle_live_combat_reaction
from app.combat.state import Combatant, apply_damage, end_combat, get_combat, start_combat


def test_goliath_stone_endurance_reduces_fresh_damage_once_per_rest(monkeypatch) -> None:
    session_id = "test_goliath_stone_endurance_reduces_fresh_damage_once_per_rest"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Голиаф",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=15,
        initiative=10,
        reaction_available=True,
        stats={"con": 70},
        race_features={
            "features": {
                "stone_endurance": {
                    "type": "stone_endurance",
                    "roll": "1d12",
                    "add": "con_mod",
                    "trigger": "reaction_on_damage",
                    "uses": "per_short_or_long_rest",
                    "reduce_damage": True,
                }
            }
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Орк",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=12,
    )
    state.order = ["enemy_1", "pc_1"]
    state.turn_index = 0
    state.round_no = 1

    try:
        applied_state = apply_damage(session_id, "pc_1", 10)
        assert applied_state is not None
        actor = applied_state.combatants["pc_1"]
        assert actor.hp_current == 10
        assert actor.last_damage_taken == 10
        assert actor.last_damage_taken_round == 1

        monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 7)
        patch, err = handle_live_combat_reaction("combat_stone_endurance", session_id, "pc_1")
        assert err is None
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        assert actor.hp_current == 19
        assert actor.reaction_available is False
        runtime = ((actor.race_features or {}).get("runtime") or {})
        assert runtime.get("stone_endurance_used") is True

        actor.reaction_available = True
        second_patch, second_err = handle_live_combat_reaction("combat_stone_endurance", session_id, "pc_1")
        assert second_patch is None
        assert second_err is not None
    finally:
        end_combat(session_id)


def test_goliath_stone_endurance_requires_fresh_damage() -> None:
    session_id = "test_goliath_stone_endurance_requires_fresh_damage"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Голиаф",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=15,
        initiative=10,
        reaction_available=True,
        stats={"con": 70},
        race_features={"features": {"stone_endurance": {"type": "stone_endurance"}}},
        last_damage_taken=5,
        last_damage_taken_round=0,
    )
    state.order = ["pc_1"]
    state.turn_index = 0
    state.round_no = 1

    try:
        patch, err = handle_live_combat_reaction("combat_stone_endurance", session_id, "pc_1")
        assert patch is None
        assert err is not None
    finally:
        end_combat(session_id)
