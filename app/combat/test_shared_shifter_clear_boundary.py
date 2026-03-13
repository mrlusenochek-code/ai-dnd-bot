from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.combat.turns import advance_turn_in_state


def _make_shifter(*, session_id: str, subrace: str, features: dict[str, object]) -> Combatant:
    return Combatant(
        key="pc_1",
        name=f"{subrace.title()} Shifter",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        stats={"con": 60, "dex": 60, "cha": 55, "str": 55},
        race_features={
            "race_key": "shifter",
            "subrace": {"key": subrace},
            "features": {"shifting": {"uses_max": 1, "uses": "per_short_or_long_rest"}, **features},
            "runtime": {
                "shifted_active": False,
                "shifting_uses_used": 0,
                "sentinel_top": "keep",
                "conditions": {"sentinel": {"active": True}},
            },
        },
        movement_speeds={"walk": 30},
        move_speed_ft=30,
        move_remaining_ft=30,
    )


def _start_shifter_combat(*, session_id: str, subrace: str, features: dict[str, object]) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = _make_shifter(session_id=session_id, subrace=subrace, features=features)
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=5,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def _runtime(session_id: str) -> dict[str, object]:
    state = get_combat(session_id)
    assert state is not None
    return ((state.combatants["pc_1"].race_features or {}).get("runtime") or {})


def _activate_and_manual_end_shift(session_id: str) -> Combatant:
    patch_shift, err_shift = handle_live_combat_action("combat_shift", session_id)
    assert err_shift is None and patch_shift is not None
    state = get_combat(session_id)
    assert state is not None
    advance_turn_in_state(state)
    advance_turn_in_state(state)
    patch_end, err_end = handle_live_combat_action("combat_shift_end", session_id)
    assert err_end is None and patch_end is not None
    actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
    return actor


def _activate_and_expire_shift(session_id: str) -> Combatant:
    patch_shift, err_shift = handle_live_combat_action("combat_shift", session_id)
    assert err_shift is None and patch_shift is not None
    state = get_combat(session_id)
    assert state is not None
    for _ in range(19):
        advance_turn_in_state(state)
    actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
    return actor


def test_shifter_manual_clear_path_clears_shared_runtime_subset_and_preserves_unrelated_state(monkeypatch) -> None:
    session_id = "test_shifter_manual_clear_boundary_beasthide"
    _start_shifter_combat(
        session_id=session_id,
        subrace="beasthide",
        features={"shifting_bonus": {"temp_hp_extra": "1d6", "ac_bonus": 1}},
    )
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)
    try:
        actor = _activate_and_manual_end_shift(session_id)
        runtime = _runtime(session_id)
        assert bool(runtime.get("shifted_active")) is False
        assert int(runtime.get("shifted_rounds_left") or 0) == 0
        assert int(runtime.get("shifting_ac_bonus_active") or 0) == 0
        assert int(runtime.get("shifting_uses_used") or 0) == 1
        assert int(runtime.get("shifting_temp_hp_granted") or 0) == 8
        assert bool(runtime.get("shifting_longtooth_bite_available")) is False
        assert bool(runtime.get("shifting_swiftstride_reaction_available")) is False
        assert str(runtime.get("sentinel_top") or "") == "keep"
        assert ((runtime.get("conditions") or {}).get("sentinel") or {}).get("active") is True
        assert int(actor.ac or 0) == 13
    finally:
        end_combat(session_id)


def test_shifter_turn_expiry_clears_shared_runtime_subset_and_preserves_unrelated_state(monkeypatch) -> None:
    session_id = "test_shifter_expiry_boundary_beasthide"
    _start_shifter_combat(
        session_id=session_id,
        subrace="beasthide",
        features={"shifting_bonus": {"temp_hp_extra": "1d6", "ac_bonus": 1}},
    )
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)
    try:
        actor = _activate_and_expire_shift(session_id)
        runtime = _runtime(session_id)
        assert bool(runtime.get("shifted_active")) is False
        assert int(runtime.get("shifted_rounds_left") or 0) == 0
        assert int(runtime.get("shifting_ac_bonus_active") or 0) == 0
        assert int(runtime.get("shifting_uses_used") or 0) == 1
        assert int(runtime.get("shifting_temp_hp_granted") or 0) == 8
        assert bool(runtime.get("shifting_longtooth_bite_available")) is False
        assert bool(runtime.get("shifting_swiftstride_reaction_available")) is False
        assert str(runtime.get("sentinel_top") or "") == "keep"
        assert ((runtime.get("conditions") or {}).get("sentinel") or {}).get("active") is True
        assert int(actor.ac or 0) == 13
    finally:
        end_combat(session_id)


def test_shifter_manual_clear_and_zero_expiry_match_on_runtime_subset_but_keep_current_swiftstride_speed_difference() -> None:
    manual_session_id = "test_shifter_manual_clear_swiftstride_runtime_subset"
    expiry_session_id = "test_shifter_expiry_swiftstride_runtime_subset"
    features = {"shifting_mobility": {"walk_speed_bonus_ft": 10, "reaction_move_ft": 10, "no_opportunity_attacks": True}}
    _start_shifter_combat(session_id=manual_session_id, subrace="swiftstride", features=features)
    _start_shifter_combat(session_id=expiry_session_id, subrace="swiftstride", features=features)
    try:
        manual_actor = _activate_and_manual_end_shift(manual_session_id)
        manual_runtime = _runtime(manual_session_id)
        expiry_actor = _activate_and_expire_shift(expiry_session_id)
        expiry_runtime = _runtime(expiry_session_id)

        shared_keys = {
            "shifted_active",
            "shifted_rounds_left",
            "shifting_speed_bonus_active_ft",
            "shifting_uses_used",
            "shifting_temp_hp_granted",
            "shifting_longtooth_bite_available",
            "shifting_swiftstride_reaction_available",
            "sentinel_top",
            "conditions",
        }
        manual_subset = {key: manual_runtime.get(key) for key in shared_keys}
        expiry_subset = {key: expiry_runtime.get(key) for key in shared_keys}
        assert manual_subset == expiry_subset
        assert int((manual_actor.movement_speeds or {}).get("walk") or 0) == 30
        assert int((expiry_actor.movement_speeds or {}).get("walk") or 0) == 30
        assert int(manual_actor.move_speed_ft or 0) == 30
        assert int(manual_actor.move_remaining_ft or 0) == 30
        assert int(expiry_actor.move_speed_ft or 0) == 40
        assert int(expiry_actor.move_remaining_ft or 0) == 40

        state = get_combat(expiry_session_id)
        assert state is not None
        before_runtime = dict(expiry_runtime)
        advance_turn_in_state(state)
        assert _runtime(expiry_session_id) == before_runtime
    finally:
        end_combat(manual_session_id)
        end_combat(expiry_session_id)
