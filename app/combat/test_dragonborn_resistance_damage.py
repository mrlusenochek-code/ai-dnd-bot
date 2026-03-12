from __future__ import annotations

from app.combat.state import Combatant, apply_damage, end_combat, get_combat, start_combat


def test_dragonborn_resistance_depends_on_selected_ancestry_damage_type() -> None:
    session_id = "test_dragonborn_resistance_depends_on_selected_ancestry_damage_type"
    state = start_combat(session_id)
    state.combatants["pc_blue"] = Combatant(
        key="pc_blue",
        name="Dragonborn Blue",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=12,
        race_features={
            "choices": {"draconic_ancestry": {"key": "blue", "damage_type": "lightning"}},
            "resistances": ["lightning"],
            "features": {"draconic_resistance": {"type": "damage_resistance", "damage": ["lightning"]}},
        },
    )
    state.combatants["pc_red"] = Combatant(
        key="pc_red",
        name="Dragonborn Red",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        race_features={
            "choices": {"draconic_ancestry": {"key": "red", "damage_type": "fire"}},
            "resistances": ["fire"],
            "features": {"draconic_resistance": {"type": "damage_resistance", "damage": ["fire"]}},
        },
    )
    try:
        apply_damage(session_id, "pc_blue", 7, damage_type="lightning", source="test")
        apply_damage(session_id, "pc_blue", 7, damage_type="fire", source="test")
        apply_damage(session_id, "pc_red", 7, damage_type="fire", source="test")
        apply_damage(session_id, "pc_red", 7, damage_type="cold", source="test")

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_blue"].hp_current == 10
        assert state_now.combatants["pc_red"].hp_current == 10
    finally:
        end_combat(session_id)


def test_dragonborn_resistance_regressions_for_other_races_still_work() -> None:
    session_id = "test_dragonborn_resistance_regressions_for_other_races_still_work"
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
    state.combatants["pc_tie"] = Combatant(
        key="pc_tie",
        name="Tiefling",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        race_features={
            "resistances": ["fire"],
            "features": {"hellish_resistance": {"type": "damage_resistance", "damage": ["fire"]}},
        },
    )
    try:
        apply_damage(session_id, "pc_kal", 7, damage_type="psychic", source="test")
        apply_damage(session_id, "pc_aas", 7, damage_type="radiant", source="test")
        apply_damage(session_id, "pc_tie", 7, damage_type="fire", source="test")

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_kal"].hp_current == 17
        assert state_now.combatants["pc_aas"].hp_current == 17
        assert state_now.combatants["pc_tie"].hp_current == 17
    finally:
        end_combat(session_id)
