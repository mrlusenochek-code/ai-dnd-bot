from __future__ import annotations

from app.combat.live_actions import handle_live_combat_reaction
from app.combat.state import Combatant, apply_damage, end_combat, get_combat, start_combat


def _rogue_uncanny_dodge_features() -> dict:
    return {
        "features": [
            {
                "key": "uncanny_dodge",
                "name_ru": "Невероятное уклонение",
                "mechanics": {
                    "type": "uncanny_dodge",
                    "trigger": "after_hit_by_attack",
                    "cost": "reaction",
                    "damage_reduction": "half",
                },
            }
        ],
        "runtime": {},
    }


def test_rogue_uncanny_dodge_restores_half_damage_and_spends_reaction() -> None:
    session_id = "test_rogue_uncanny_dodge_restores_half_damage_and_spends_reaction"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Плут",
        side="pc",
        hp_current=20,
        hp_max=30,
        ac=15,
        initiative=12,
        reaction_available=True,
        class_features=_rogue_uncanny_dodge_features(),
        level=5,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Орк",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=10,
    )
    state.order = ["enemy_1", "pc_1"]
    state.turn_index = 0
    state.round_no = 1

    try:
        applied_state = apply_damage(session_id, "pc_1", 9, source="orc_attack")
        assert applied_state is not None

        patch, err = handle_live_combat_reaction("combat_uncanny_dodge", session_id, "pc_1")
        assert err is None
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        assert actor.hp_current == 15
        assert actor.reaction_available is False
        runtime = ((actor.class_features or {}).get("runtime") or {})
        assert runtime.get("uncanny_dodge_used_damage_keys") == ["round:1|source:orc_attack|damage:9"]
    finally:
        end_combat(session_id)


def test_rogue_uncanny_dodge_cannot_repeat_same_damage_key() -> None:
    session_id = "test_rogue_uncanny_dodge_cannot_repeat_same_damage_key"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Плут",
        side="pc",
        hp_current=20,
        hp_max=30,
        ac=15,
        initiative=12,
        reaction_available=True,
        class_features=_rogue_uncanny_dodge_features(),
        level=5,
        last_damage_taken=9,
        last_damage_taken_round=1,
        last_damage_taken_source="orc_attack",
    )
    state.order = ["pc_1"]
    state.turn_index = 0
    state.round_no = 1

    try:
        first_patch, first_err = handle_live_combat_reaction("combat_uncanny_dodge", session_id, "pc_1")
        assert first_err is None
        assert first_patch is not None

        state.combatants["pc_1"].reaction_available = True
        second_patch, second_err = handle_live_combat_reaction("combat_uncanny_dodge", session_id, "pc_1")
        assert second_patch is None
        assert second_err == "Невероятное уклонение уже применено к этому урону."
    finally:
        end_combat(session_id)


def test_rogue_uncanny_dodge_requires_reaction() -> None:
    session_id = "test_rogue_uncanny_dodge_requires_reaction"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Плут",
        side="pc",
        hp_current=20,
        hp_max=30,
        ac=15,
        initiative=12,
        reaction_available=False,
        class_features=_rogue_uncanny_dodge_features(),
        level=5,
        last_damage_taken=9,
        last_damage_taken_round=1,
        last_damage_taken_source="orc_attack",
    )
    state.order = ["pc_1"]
    state.turn_index = 0
    state.round_no = 1

    try:
        patch, err = handle_live_combat_reaction("combat_uncanny_dodge", session_id, "pc_1")
        assert patch is None
        assert err == "Реакция недоступна: реакция уже потрачена."
    finally:
        end_combat(session_id)


def test_rogue_uncanny_dodge_requires_feature_and_level() -> None:
    session_id = "test_rogue_uncanny_dodge_requires_feature_and_level"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Плут-ученик",
        side="pc",
        hp_current=20,
        hp_max=30,
        ac=15,
        initiative=12,
        reaction_available=True,
        class_features={"features": [], "runtime": {}},
        level=4,
        last_damage_taken=9,
        last_damage_taken_round=1,
        last_damage_taken_source="orc_attack",
    )
    state.order = ["pc_1"]
    state.turn_index = 0
    state.round_no = 1

    try:
        patch, err = handle_live_combat_reaction("combat_uncanny_dodge", session_id, "pc_1")
        assert patch is None
        assert err == "Невероятное уклонение недоступно вашему классу."
    finally:
        end_combat(session_id)


def test_non_rogue_without_feature_cannot_use_uncanny_dodge() -> None:
    session_id = "test_non_rogue_without_feature_cannot_use_uncanny_dodge"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Воин",
        side="pc",
        hp_current=20,
        hp_max=30,
        ac=17,
        initiative=10,
        reaction_available=True,
        class_features={"features": [], "runtime": {}},
        level=5,
        last_damage_taken=9,
        last_damage_taken_round=1,
        last_damage_taken_source="orc_attack",
    )
    state.order = ["pc_1"]
    state.turn_index = 0
    state.round_no = 1

    try:
        patch, err = handle_live_combat_reaction("combat_uncanny_dodge", session_id, "pc_1")
        assert patch is None
        assert err == "Невероятное уклонение недоступно вашему классу."
    finally:
        end_combat(session_id)


def test_rogue_uncanny_dodge_requires_positive_last_damage() -> None:
    session_id = "test_rogue_uncanny_dodge_requires_positive_last_damage"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Плут",
        side="pc",
        hp_current=20,
        hp_max=30,
        ac=15,
        initiative=12,
        reaction_available=True,
        class_features=_rogue_uncanny_dodge_features(),
        level=5,
        last_damage_taken=0,
        last_damage_taken_round=1,
        last_damage_taken_source="orc_attack",
    )
    state.order = ["pc_1"]
    state.turn_index = 0
    state.round_no = 1

    try:
        patch, err = handle_live_combat_reaction("combat_uncanny_dodge", session_id, "pc_1")
        assert patch is None
        assert err == "Нет подходящего полученного урона для Невероятного уклонения."
    finally:
        end_combat(session_id)
