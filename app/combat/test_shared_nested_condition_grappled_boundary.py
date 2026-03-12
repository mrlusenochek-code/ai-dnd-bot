from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, _cleanup_battle_runtime, advance_turn, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def _simic_actor() -> Combatant:
    return Combatant(
        key="pc_1",
        name="Simic",
        side="pc",
        hp_current=24,
        hp_max=24,
        ac=13,
        initiative=20,
        level=5,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 60, "dex": 50, "con": 50},
        race_features={
            "race_key": "simic_hybrid",
            "features": {"grappling_appendages": {"activation": "action"}},
            "runtime": {"sentinel_owner": "keep-owner"},
        },
    )


def _enemy_with_grapple_runtime() -> Combatant:
    return Combatant(
        key="enemy_1",
        name="Guard",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 40, "dex": 40, "con": 50},
        race_features={
            "runtime": {
                "sentinel_top": "keep-top",
                "conditions": {"custom_marker": {"active": True, "tag": "keep-condition"}},
            }
        },
    )


def test_shared_nested_grappled_boundary_action_write_and_turn_progression_stability(monkeypatch) -> None:
    session_id = "test_shared_nested_grappled_boundary_action_write_and_turn_progression_stability"
    state = start_combat(session_id)
    state.combatants["pc_1"] = _simic_actor()
    state.combatants["enemy_1"] = _enemy_with_grapple_runtime()
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([18, 3])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_grapple_appendages", session_id, raw_text="Guard")
        assert err is None
        assert patch is not None
        assert any("цель схвачена" in text.lower() for text in _line_texts(patch))

        state_now = get_combat(session_id)
        assert state_now is not None
        owner_runtime = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        target_runtime = ((state_now.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        target_conditions = target_runtime.get("conditions") or {}
        grappled = target_conditions.get("grappled") or {}

        assert owner_runtime.get("sentinel_owner") == "keep-owner"
        assert str(owner_runtime.get("simic_appendages_last_target_id") or "") == "enemy_1"
        assert target_runtime.get("sentinel_top") == "keep-top"
        assert (target_conditions.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert str(grappled.get("by_actor_id") or "") == "pc_1"
        assert str(grappled.get("source") or "") == "simic_appendages"

        assert advance_turn(session_id) is not None
        state_after = get_combat(session_id)
        assert state_after is not None
        target_runtime_after = ((state_after.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        target_conditions_after = target_runtime_after.get("conditions") or {}
        grappled_after = target_conditions_after.get("grappled") or {}
        assert target_runtime_after.get("sentinel_top") == "keep-top"
        assert (target_conditions_after.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert str(grappled_after.get("by_actor_id") or "") == "pc_1"
        assert str(grappled_after.get("source") or "") == "simic_appendages"
    finally:
        end_combat(session_id)


def test_shared_nested_grappled_boundary_no_drift_after_repeated_turn_progression(monkeypatch) -> None:
    session_id = "test_shared_nested_grappled_boundary_no_drift_after_repeated_turn_progression"
    state = start_combat(session_id)
    state.combatants["pc_1"] = _simic_actor()
    state.combatants["enemy_1"] = _enemy_with_grapple_runtime()
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([18, 3])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_grapple_appendages", session_id, raw_text="Guard")
        assert err is None
        assert patch is not None

        assert advance_turn(session_id) is not None
        state_after_first = get_combat(session_id)
        assert state_after_first is not None
        enemy_runtime_after_first = ((state_after_first.combatants["enemy_1"].race_features or {}).get("runtime") or {})

        assert advance_turn(session_id) is not None
        assert advance_turn(session_id) is not None
        state_after_more = get_combat(session_id)
        assert state_after_more is not None
        enemy_runtime_after_more = ((state_after_more.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        assert enemy_runtime_after_more == enemy_runtime_after_first
    finally:
        end_combat(session_id)


def test_shared_nested_grappled_boundary_battle_cleanup_clears_only_matching_simic_markers() -> None:
    session_id = "test_shared_nested_grappled_boundary_battle_cleanup_clears_only_matching_simic_markers"
    state = start_combat(session_id)
    state.combatants["pc_1"] = _simic_actor()
    state.combatants["enemy_match"] = Combatant(
        key="enemy_match",
        name="Match",
        side="enemy",
        hp_current=18,
        hp_max=18,
        ac=12,
        initiative=11,
        race_features={
            "runtime": {
                "sentinel_top": "keep-top",
                "conditions": {
                    "grappled": {"by_actor_id": "pc_1", "source": "simic_appendages"},
                    "custom_marker": {"active": True, "tag": "keep-condition"},
                },
            }
        },
    )
    state.combatants["enemy_other"] = Combatant(
        key="enemy_other",
        name="Other",
        side="enemy",
        hp_current=18,
        hp_max=18,
        ac=12,
        initiative=9,
        race_features={
            "runtime": {
                "sentinel_top": "keep-other-top",
                "conditions": {
                    "grappled": {"by_actor_id": "pc_x", "source": "other_source"},
                    "custom_marker": {"active": True, "tag": "keep-other-condition"},
                },
            }
        },
    )

    try:
        changed_first = _cleanup_battle_runtime(state)
        assert changed_first is True

        match_runtime = ((state.combatants["enemy_match"].race_features or {}).get("runtime") or {})
        match_conditions = match_runtime.get("conditions") or {}
        assert match_runtime.get("sentinel_top") == "keep-top"
        assert "grappled" not in match_conditions
        assert (match_conditions.get("custom_marker") or {}).get("tag") == "keep-condition"

        other_runtime = ((state.combatants["enemy_other"].race_features or {}).get("runtime") or {})
        other_conditions = other_runtime.get("conditions") or {}
        other_grappled = other_conditions.get("grappled") or {}
        assert other_runtime.get("sentinel_top") == "keep-other-top"
        assert str(other_grappled.get("by_actor_id") or "") == "pc_x"
        assert str(other_grappled.get("source") or "") == "other_source"
        assert (other_conditions.get("custom_marker") or {}).get("tag") == "keep-other-condition"

        changed_second = _cleanup_battle_runtime(state)
        assert changed_second is False
        assert ((state.combatants["enemy_match"].race_features or {}).get("runtime") or {}) == match_runtime
        assert ((state.combatants["enemy_other"].race_features or {}).get("runtime") or {}) == other_runtime
    finally:
        end_combat(session_id)
