from __future__ import annotations

from app.combat.state import Combatant, apply_damage, end_combat, get_combat, start_combat


def test_tiefling_hellish_resistance_halves_fire_damage_only() -> None:
    session_id = "test_tiefling_hellish_resistance_halves_fire_damage_only"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Tiefling Hero",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        race_features={
            "resistances": ["fire"],
            "features": {
                "hellish_resistance": {
                    "type": "damage_resistance",
                    "damage": ["fire"],
                }
            },
        },
    )
    try:
        apply_damage(session_id, "pc_1", 7, damage_type="fire", source="test")
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].hp_current == 17

        apply_damage(session_id, "pc_1", 7, damage_type="cold", source="test")
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].hp_current == 10
    finally:
        end_combat(session_id)


def test_character_without_hellish_resistance_takes_full_fire_damage() -> None:
    session_id = "test_character_without_hellish_resistance_takes_full_fire_damage"
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
        apply_damage(session_id, "pc_1", 7, damage_type="fire", source="test")
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].hp_current == 13
    finally:
        end_combat(session_id)
