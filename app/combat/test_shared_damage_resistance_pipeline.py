from __future__ import annotations

from app.combat.state import Combatant, apply_damage, end_combat, get_combat, start_combat


def _pc(
    key: str,
    name: str,
    *,
    resistances: list[str] | None = None,
    features: dict[str, object] | None = None,
) -> Combatant:
    return Combatant(
        key=key,
        name=name,
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        race_features={
            "resistances": list(resistances or []),
            "features": dict(features or {}),
        },
    )


def test_shared_resistance_pipeline_handles_fixed_multi_choice_and_package_cases() -> None:
    session_id = "test_shared_resistance_pipeline_handles_fixed_multi_choice_and_package_cases"
    state = start_combat(session_id)
    state.combatants["pc_tie"] = _pc(
        "pc_tie",
        "Tiefling",
        resistances=["fire"],
        features={"hellish_resistance": {"type": "damage_resistance", "damage": ["fire"]}},
    )
    state.combatants["pc_kal"] = _pc(
        "pc_kal",
        "Kalashtar",
        resistances=["psychic"],
        features={"mental_discipline": {"type": "damage_resistance", "damage": ["psychic"]}},
    )
    state.combatants["pc_aas"] = _pc(
        "pc_aas",
        "Aasimar",
        resistances=["radiant", "necrotic"],
        features={"celestial_resistance": {"type": "damage_resistance", "damage": ["radiant", "necrotic"]}},
    )
    state.combatants["pc_blue"] = _pc(
        "pc_blue",
        "Dragonborn Blue",
        resistances=["lightning"],
        features={"draconic_resistance": {"type": "damage_resistance", "damage": ["lightning"], "from_choice": "draconic_ancestry"}},
    )
    state.combatants["pc_red"] = _pc(
        "pc_red",
        "Dragonborn Red",
        resistances=["fire"],
        features={"draconic_resistance": {"type": "damage_resistance", "damage": ["fire"], "from_choice": "draconic_ancestry"}},
    )
    state.combatants["pc_fire_genasi"] = _pc(
        "pc_fire_genasi",
        "Fire Genasi",
        resistances=["fire"],
        features={"fire_resistance": {"type": "damage_resistance", "damage": ["fire"]}},
    )
    state.combatants["pc_water_genasi"] = _pc(
        "pc_water_genasi",
        "Water Genasi",
        resistances=["acid"],
        features={"acid_resistance": {"type": "damage_resistance", "damage": ["acid"]}},
    )
    state.combatants["pc_plain"] = _pc("pc_plain", "Plain Human")
    try:
        apply_damage(session_id, "pc_tie", 7, damage_type="fire", source="test")
        apply_damage(session_id, "pc_tie", 7, damage_type="cold", source="test")
        apply_damage(session_id, "pc_kal", 7, damage_type="psychic", source="test")
        apply_damage(session_id, "pc_aas", 7, damage_type="radiant", source="test")
        apply_damage(session_id, "pc_aas", 7, damage_type="necrotic", source="test")
        apply_damage(session_id, "pc_blue", 7, damage_type="lightning", source="test")
        apply_damage(session_id, "pc_blue", 7, damage_type="fire", source="test")
        apply_damage(session_id, "pc_red", 7, damage_type="fire", source="test")
        apply_damage(session_id, "pc_red", 7, damage_type="cold", source="test")
        apply_damage(session_id, "pc_fire_genasi", 7, damage_type="fire", source="test")
        apply_damage(session_id, "pc_fire_genasi", 7, damage_type="slashing", source="test")
        apply_damage(session_id, "pc_water_genasi", 7, damage_type="acid", source="test")
        apply_damage(session_id, "pc_water_genasi", 7, damage_type="fire", source="test")
        apply_damage(session_id, "pc_plain", 7, damage_type="fire", source="test")

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_tie"].hp_current == 10
        assert state_now.combatants["pc_kal"].hp_current == 17
        assert state_now.combatants["pc_aas"].hp_current == 14
        assert state_now.combatants["pc_blue"].hp_current == 10
        assert state_now.combatants["pc_red"].hp_current == 10
        assert state_now.combatants["pc_fire_genasi"].hp_current == 10
        assert state_now.combatants["pc_water_genasi"].hp_current == 10
        assert state_now.combatants["pc_plain"].hp_current == 13
    finally:
        end_combat(session_id)


def test_shared_resistance_pipeline_applies_resistance_only_once() -> None:
    session_id = "test_shared_resistance_pipeline_applies_resistance_only_once"
    state = start_combat(session_id)
    state.combatants["pc_1"] = _pc(
        "pc_1",
        "Tiefling Duplicate",
        resistances=["fire", "fire"],
        features={"hellish_resistance": {"type": "damage_resistance", "damage": ["fire"]}},
    )
    try:
        apply_damage(session_id, "pc_1", 9, damage_type="fire", source="test")

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].hp_current == 16
        assert state_now.combatants["pc_1"].last_damage_taken == 4
    finally:
        end_combat(session_id)

