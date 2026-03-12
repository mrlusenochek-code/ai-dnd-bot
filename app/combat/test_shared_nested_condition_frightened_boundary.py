from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, advance_turn, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def _leonin_actor() -> Combatant:
    return Combatant(
        key="pc_1",
        name="Leonin",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 55, "dex": 50, "con": 60, "int": 50, "wis": 50, "cha": 50},
        race_features={
            "features": {
                "daunting_roar": {
                    "activation": "bonus_action",
                    "range_ft": 10,
                    "save": {"ability": "wis", "dc_formula": "8 + prof + con_mod"},
                    "duration": "until_end_of_your_next_turn",
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                }
            },
            "runtime": {},
        },
    )


def _enemy_with_fright_runtime() -> Combatant:
    return Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 50, "dex": 50, "con": 50, "wis": 50},
        race_features={
            "runtime": {
                "sentinel_top": "keep-top",
                "conditions": {"custom_marker": {"active": True, "tag": "keep-condition"}},
            }
        },
    )


def test_shared_nested_frightened_boundary_action_write_and_source_turn_decrement(monkeypatch) -> None:
    session_id = "test_shared_nested_frightened_boundary_action_write_and_source_turn_decrement"
    state = start_combat(session_id)
    state.combatants["pc_1"] = _leonin_actor()
    state.combatants["enemy_1"] = _enemy_with_fright_runtime()
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 5)

    try:
        patch, err = handle_live_combat_action("combat_daunting_roar", session_id)
        assert err is None
        assert patch is not None
        assert any("испуган" in t.lower() for t in _line_texts(patch))

        state_now = get_combat(session_id)
        assert state_now is not None
        enemy_runtime = ((state_now.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        conditions = enemy_runtime.get("conditions") or {}
        frightened = conditions.get("frightened") or {}
        assert enemy_runtime.get("sentinel_top") == "keep-top"
        assert (conditions.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert frightened.get("active") is True
        assert str(frightened.get("source") or "") == "leonin_daunting_roar"
        assert str(frightened.get("expires_on_end_of_source_next_turn") or "") == "pc_1"
        assert int(frightened.get("source_turns_remaining") or 0) == 2

        assert advance_turn(session_id) is not None
        state_after = get_combat(session_id)
        assert state_after is not None
        enemy_runtime_after = ((state_after.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        conditions_after = enemy_runtime_after.get("conditions") or {}
        frightened_after = conditions_after.get("frightened") or {}
        assert enemy_runtime_after.get("sentinel_top") == "keep-top"
        assert (conditions_after.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert frightened_after.get("active") is True
        assert int(frightened_after.get("source_turns_remaining") or 0) == 1
    finally:
        end_combat(session_id)


def test_shared_nested_frightened_boundary_source_turn_cleanup_and_no_runtime_drift(monkeypatch) -> None:
    session_id = "test_shared_nested_frightened_boundary_source_turn_cleanup_and_no_runtime_drift"
    state = start_combat(session_id)
    state.combatants["pc_1"] = _leonin_actor()
    state.combatants["enemy_1"] = _enemy_with_fright_runtime()
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 5)

    try:
        patch, err = handle_live_combat_action("combat_daunting_roar", session_id)
        assert err is None
        assert patch is not None

        assert advance_turn(session_id) is not None
        assert advance_turn(session_id) is not None
        assert advance_turn(session_id) is not None

        state_after = get_combat(session_id)
        assert state_after is not None
        enemy_runtime_after = ((state_after.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        conditions_after = enemy_runtime_after.get("conditions") or {}
        assert enemy_runtime_after.get("sentinel_top") == "keep-top"
        assert "frightened" not in conditions_after
        assert (conditions_after.get("custom_marker") or {}).get("tag") == "keep-condition"

        assert advance_turn(session_id) is not None
        state_final = get_combat(session_id)
        assert state_final is not None
        enemy_runtime_final = ((state_final.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        assert enemy_runtime_final == enemy_runtime_after
    finally:
        end_combat(session_id)
