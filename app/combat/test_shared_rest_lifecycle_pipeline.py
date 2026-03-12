from __future__ import annotations

from types import SimpleNamespace

from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.web import ws_handlers


def _combatant_with_runtime(
    *,
    key: str,
    name: str,
    runtime: dict[str, object],
    features: dict[str, object],
) -> Combatant:
    return Combatant(
        key=key,
        name=name,
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        level=3,
        race_features={"features": dict(features), "runtime": dict(runtime)},
    )


def _assert_short_rest_active_runtime_cleanup(runtime: dict[str, object], *, adrenaline_uses_used: int) -> None:
    assert "aasimar_transformation" not in runtime
    assert "breath_weapon_used" not in runtime
    assert bool(runtime.get("shifted_active")) is False
    assert int(runtime.get("shifted_rounds_left") or 0) == 0
    assert int(runtime.get("shifting_uses_used") or 0) == 0
    assert int(runtime.get("adrenaline_rush_uses_used") or 0) == adrenaline_uses_used


def test_shared_rest_lifecycle_short_rest_distinguishes_resources_and_keeps_unrelated_actor() -> None:
    session_id = "test_shared_rest_lifecycle_short_rest_distinguishes_resources_and_keeps_unrelated_actor"
    state = start_combat(session_id)
    state.combatants["pc_owner"] = _combatant_with_runtime(
        key="pc_owner",
        name="Owner",
        runtime={
            "aasimar_transform_used": True,
            "aasimar_transformation": {"active": True, "kind": "protector", "rounds_left": 7},
            "fly_speed_ft": 30,
            "breath_weapon_used": True,
            "shifted_active": True,
            "shifted_rounds_left": 4,
            "shifting_uses_used": 1,
            "adrenaline_rush_uses_used": 2,
        },
        features={
            "aasimar_transformation": {"uses": "per_long_rest", "uses_max": 1},
            "breath_weapon": {"recharge": "short_or_long_rest"},
            "shifting": {"uses": "per_short_or_long_rest", "uses_max": 1},
            "adrenaline_rush": {"recharge": "per_long_rest"},
        },
    )
    state.combatants["pc_other"] = _combatant_with_runtime(
        key="pc_other",
        name="Other",
        runtime={"breath_weapon_used": True, "adrenaline_rush_uses_used": 1},
        features={
            "breath_weapon": {"recharge": "short_or_long_rest"},
            "adrenaline_rush": {"recharge": "per_long_rest"},
        },
    )
    try:
        changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_owner", long_rest=False)
        assert changed is True

        state_now = get_combat(session_id)
        assert state_now is not None
        owner_runtime = (state_now.combatants["pc_owner"].race_features or {}).get("runtime") or {}
        assert owner_runtime.get("aasimar_transform_used") is True
        _assert_short_rest_active_runtime_cleanup(owner_runtime, adrenaline_uses_used=2)
        assert "fly_speed_ft" not in owner_runtime

        other_runtime = (state_now.combatants["pc_other"].race_features or {}).get("runtime") or {}
        assert other_runtime.get("breath_weapon_used") is True
        assert int(other_runtime.get("adrenaline_rush_uses_used") or 0) == 1
    finally:
        end_combat(session_id)


def test_shared_rest_lifecycle_long_rest_resets_long_rest_resources_and_is_idempotent() -> None:
    session_id = "test_shared_rest_lifecycle_long_rest_resets_long_rest_resources_and_is_idempotent"
    state = start_combat(session_id)
    state.combatants["pc_1"] = _combatant_with_runtime(
        key="pc_1",
        name="Lifecycle",
        runtime={
            "healing_hands_used": True,
            "aasimar_transform_used": True,
            "relentless_endurance_used": True,
            "adrenaline_rush_uses_used": 2,
            "shifted_active": False,
            "shifted_rounds_left": 0,
            "shifting_uses_used": 0,
        },
        features={
            "healing_hands": {"uses": "per_long_rest"},
            "aasimar_transformation": {"uses": "per_long_rest"},
            "relentless_endurance": {"uses": "per_long_rest"},
            "adrenaline_rush": {"recharge": "per_long_rest"},
            "shifting": {"uses": "per_short_or_long_rest"},
        },
    )
    try:
        changed_first = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=True)
        assert changed_first is True

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime_after_first = (state_now.combatants["pc_1"].race_features or {}).get("runtime") or {}
        assert "healing_hands_used" not in runtime_after_first
        assert "aasimar_transform_used" not in runtime_after_first
        assert "relentless_endurance_used" not in runtime_after_first
        assert int(runtime_after_first.get("adrenaline_rush_uses_used") or 0) == 0
        assert bool(runtime_after_first.get("shifted_active")) is False
        assert int(runtime_after_first.get("shifted_rounds_left") or 0) == 0
        assert int(runtime_after_first.get("shifting_uses_used") or 0) == 0

        changed_second = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=True)
        assert changed_second is False
        runtime_after_second = (state_now.combatants["pc_1"].race_features or {}).get("runtime") or {}
        assert runtime_after_second == runtime_after_first
    finally:
        end_combat(session_id)


def test_shared_rest_lifecycle_character_reset_matches_combat_reset_behavior() -> None:
    ch = SimpleNamespace(
        race_features={
            "features": {
                "aasimar_transformation": {"uses": "per_long_rest"},
                "shifting": {"uses": "per_short_or_long_rest"},
                "adrenaline_rush": {"recharge": "per_long_rest"},
                "breath_weapon": {"recharge": "short_or_long_rest"},
            },
            "runtime": {
                "aasimar_transform_used": True,
                "aasimar_transformation": {"active": True, "kind": "scourge", "rounds_left": 10},
                "breath_weapon_used": True,
                "shifted_active": True,
                "shifted_rounds_left": 6,
                "shifting_uses_used": 1,
                "adrenaline_rush_uses_used": 2,
            },
        }
    )

    changed_short = ws_handlers._reset_racial_rest_uses(ch, long_rest=False)
    assert changed_short is True
    runtime_after_short = (ch.race_features or {}).get("runtime") or {}
    assert runtime_after_short.get("aasimar_transform_used") is True
    _assert_short_rest_active_runtime_cleanup(runtime_after_short, adrenaline_uses_used=2)

    changed_long = ws_handlers._reset_racial_rest_uses(ch, long_rest=True)
    assert changed_long is True
    runtime_after_long = (ch.race_features or {}).get("runtime") or {}
    assert "aasimar_transform_used" not in runtime_after_long
    assert int(runtime_after_long.get("adrenaline_rush_uses_used") or 0) == 0

    changed_long_again = ws_handlers._reset_racial_rest_uses(ch, long_rest=True)
    assert changed_long_again is False


def test_shared_combat_cleanup_end_combat_clears_stale_battle_flags() -> None:
    session_id = "test_shared_combat_cleanup_end_combat_clears_stale_battle_flags"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Cleanup",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        turns_taken=2,
        surprise_attack_used=True,
        charge_hooves_available=True,
        race_features={
            "runtime": {
                "goring_rush_available": True,
                "hammering_horns_available": True,
                "hammering_horns_target_id": "enemy_1",
                "fury_of_small_armed": True,
            }
        },
    )

    end_combat(session_id)

    assert get_combat(session_id) is None
    actor = state.combatants["pc_1"]
    runtime_after = (actor.race_features or {}).get("runtime") or {}
    assert actor.turns_taken == 0
    assert actor.surprise_attack_used is False
    assert actor.charge_hooves_available is False
    assert runtime_after.get("goring_rush_available") is False
    assert runtime_after.get("hammering_horns_available") is False
    assert str(runtime_after.get("hammering_horns_target_id") or "") == ""
    assert runtime_after.get("fury_of_small_armed") is False
