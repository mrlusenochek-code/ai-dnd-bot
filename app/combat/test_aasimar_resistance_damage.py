from __future__ import annotations

from app.combat.state import Combatant, apply_damage, end_combat, get_combat, start_combat


def test_aasimar_celestial_resistance_reduces_radiant_and_necrotic_but_not_other_damage() -> None:
    session_id = "test_aasimar_celestial_resistance_reduces_radiant_and_necrotic_but_not_other_damage"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Aasimar",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=15,
        initiative=10,
        race_features={
            "resistances": ["radiant", "necrotic"],
            "features": {
                "celestial_resistance": {
                    "type": "damage_resistance",
                    "damage": ["necrotic", "radiant"],
                }
            },
        },
    )
    try:
        apply_damage(session_id, "pc_1", 7, damage_type="radiant", source="test")
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].hp_current == 17

        apply_damage(session_id, "pc_1", 7, damage_type="necrotic", source="test")
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].hp_current == 14

        apply_damage(session_id, "pc_1", 7, damage_type="slashing", source="test")
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].hp_current == 7
    finally:
        end_combat(session_id)


def test_kalashtar_psychic_resistance_regression_still_works() -> None:
    session_id = "test_kalashtar_psychic_resistance_regression_still_works"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Kalashtar",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=15,
        initiative=10,
        race_features={
            "resistances": ["psychic"],
            "features": {
                "mental_discipline": {
                    "type": "damage_resistance",
                    "damage": ["psychic"],
                }
            },
        },
    )
    try:
        apply_damage(session_id, "pc_1", 7, damage_type="psychic", source="test")
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].hp_current == 17
    finally:
        end_combat(session_id)
