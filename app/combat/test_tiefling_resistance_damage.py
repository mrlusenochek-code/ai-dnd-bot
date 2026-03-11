from __future__ import annotations

from app.combat.state import Combatant, apply_damage, end_combat, get_combat, start_combat


def test_tiefling_hellish_resistance_reduces_fire_but_not_other_damage() -> None:
    session_id = "test_tiefling_hellish_resistance_reduces_fire_but_not_other_damage"
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


def test_resistance_regressions_for_kalashtar_and_aasimar_still_work() -> None:
    session_id = "test_resistance_regressions_for_kalashtar_and_aasimar_still_work"
    state = start_combat(session_id)
    state.combatants["pc_kal"] = Combatant(
        key="pc_kal",
        name="Kalashtar",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=12,
        race_features={
            "resistances": ["psychic"],
            "features": {"mental_discipline": {"type": "damage_resistance", "damage": ["psychic"]}},
        },
    )
    state.combatants["pc_aas"] = Combatant(
        key="pc_aas",
        name="Aasimar",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=11,
        race_features={
            "resistances": ["radiant", "necrotic"],
            "features": {"celestial_resistance": {"type": "damage_resistance", "damage": ["necrotic", "radiant"]}},
        },
    )
    try:
        apply_damage(session_id, "pc_kal", 7, damage_type="psychic", source="test")
        apply_damage(session_id, "pc_aas", 7, damage_type="radiant", source="test")

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_kal"].hp_current == 17
        assert state_now.combatants["pc_aas"].hp_current == 17
    finally:
        end_combat(session_id)
