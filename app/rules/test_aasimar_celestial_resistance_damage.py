from __future__ import annotations

from app.combat.state import Combatant, apply_damage, end_combat, get_combat, start_combat


def test_aasimar_celestial_resistance_halves_radiant_and_necrotic_damage() -> None:
    session_id = "test_aasimar_celestial_resistance_halves_radiant_and_necrotic_damage"
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
                    "damage": ["radiant", "necrotic"],
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
    finally:
        end_combat(session_id)


def test_character_without_celestial_resistance_takes_full_radiant_and_other_damage() -> None:
    session_id = "test_character_without_celestial_resistance_takes_full_radiant_and_other_damage"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Commoner",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=10,
        initiative=10,
        race_features={},
    )
    try:
        apply_damage(session_id, "pc_1", 7, damage_type="radiant", source="test")
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].hp_current == 13

        apply_damage(session_id, "pc_1", 7, damage_type="slashing", source="test")
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].hp_current == 6
    finally:
        end_combat(session_id)
