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


def _base_pc(
    *,
    key: str,
    name: str,
    initiative: int,
    race_features: dict | None = None,
    stats: dict | None = None,
) -> Combatant:
    return Combatant(
        key=key,
        name=name,
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=initiative,
        level=1,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats=stats or {"str": 50, "dex": 50, "con": 50, "wis": 50},
        race_features=race_features or {},
    )


def _base_enemy(*, key: str = "enemy_1", initiative: int = 10, runtime: dict | None = None) -> Combatant:
    race_features = {"runtime": dict(runtime or {})} if runtime is not None else {}
    return Combatant(
        key=key,
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=initiative,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 50, "dex": 50, "con": 50, "wis": 50},
        race_features=race_features,
    )


def test_shared_condition_runtime_boundary_groveled_action_write_and_turn_cleanup(monkeypatch) -> None:
    session_id = "test_shared_condition_runtime_boundary_groveled_action_write_and_turn_cleanup"
    state = start_combat(session_id)
    state.combatants["pc_1"] = _base_pc(
        key="pc_1",
        name="Kobold",
        initiative=20,
        race_features={
            "features": {
                "grovel_cower_beg": {
                    "range_ft": 10,
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                    "duration": "until_start_of_next_turn",
                }
            },
            "runtime": {"sentinel_owner": "keep-owner"},
        },
        stats={"str": 40, "dex": 60, "con": 50},
    )
    state.combatants["pc_2"] = _base_pc(key="pc_2", name="Ally", initiative=18)
    state.combatants["enemy_1"] = _base_enemy(runtime={"sentinel_enemy": "keep-enemy"})
    state.order = ["pc_1", "pc_2", "enemy_1"]
    state.turn_index = 0

    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 10)

    try:
        patch, err = handle_live_combat_action("combat_grovel_cower_beg", session_id)
        assert err is None
        assert patch is not None
        assert any("отвлекает врагов" in text.lower() for text in _line_texts(patch))

        state_now = get_combat(session_id)
        assert state_now is not None
        owner_runtime = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        enemy_runtime = ((state_now.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        assert owner_runtime.get("sentinel_owner") == "keep-owner"
        assert int(owner_runtime.get("grovel_uses_used") or 0) == 1
        assert str(owner_runtime.get("grovel_active_until_turn_start_of_actor_id") or "") == "pc_1"
        assert enemy_runtime.get("sentinel_enemy") == "keep-enemy"
        assert ((enemy_runtime.get("groveled") or {}).get("active")) is True

        state_now.turn_index = 2
        advanced = advance_turn(session_id)
        assert advanced is not None

        state_after = get_combat(session_id)
        assert state_after is not None
        owner_runtime_after = ((state_after.combatants["pc_1"].race_features or {}).get("runtime") or {})
        enemy_runtime_after = ((state_after.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        assert owner_runtime_after.get("sentinel_owner") == "keep-owner"
        assert int(owner_runtime_after.get("grovel_uses_used") or 0) == 1
        assert "grovel_active_until_turn_start_of_actor_id" not in owner_runtime_after
        assert enemy_runtime_after.get("sentinel_enemy") == "keep-enemy"
        assert "groveled" not in enemy_runtime_after
    finally:
        end_combat(session_id)


def test_shared_condition_runtime_boundary_taunted_turn_cleanup_is_idempotent_for_unrelated_runtime(monkeypatch) -> None:
    session_id = "test_shared_condition_runtime_boundary_taunted_turn_cleanup_is_idempotent_for_unrelated_runtime"
    state = start_combat(session_id)
    state.combatants["pc_1"] = _base_pc(
        key="pc_1",
        name="Kender",
        initiative=20,
        race_features={
            "features": {
                "taunt": {
                    "activation": "bonus_action",
                    "range_ft": 60,
                    "save": {"ability": "wis", "dc_formula": "8 + prof + chosen_int_wis_cha_mod"},
                    "duration": "until_start_of_your_next_turn",
                    "effect": "disadvantage_attacks_vs_others",
                    "chosen_ability": "wis",
                }
            }
        },
        stats={"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 60, "cha": 50},
    )
    state.combatants["pc_2"] = _base_pc(key="pc_2", name="Ally", initiative=19)
    state.combatants["enemy_1"] = _base_enemy(runtime={"sentinel_enemy": "keep-enemy"})
    state.order = ["pc_1", "pc_2", "enemy_1"]
    state.turn_index = 0

    rolls = iter([5, 13, 12, 11])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_taunt", session_id, raw_text="насмешка bandit")
        assert err is None
        assert patch is not None
        assert any("провал" in text.lower() for text in _line_texts(patch))

        state_now = get_combat(session_id)
        assert state_now is not None
        enemy_runtime = ((state_now.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        taunted = enemy_runtime.get("taunted") or {}
        assert enemy_runtime.get("sentinel_enemy") == "keep-enemy"
        assert taunted.get("active") is True
        assert str(taunted.get("expires_on_turn_start_of_actor_id") or "") == "pc_1"

        state_now.turn_index = 2
        state_now.order = ["pc_1", "pc_2", "enemy_1"]
        advanced = advance_turn(session_id)
        assert advanced is not None

        state_after = get_combat(session_id)
        assert state_after is not None
        enemy_runtime_after = ((state_after.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        assert enemy_runtime_after == {"sentinel_enemy": "keep-enemy"}

        # Repeat the same turn-start boundary after the condition is already gone:
        # unrelated runtime must stay identical and cleanup must not reintroduce drift.
        state_after.turn_index = 2
        state_after.order = ["pc_1", "pc_2", "enemy_1"]
        advanced_again = advance_turn(session_id)
        assert advanced_again is not None

        state_final = get_combat(session_id)
        assert state_final is not None
        enemy_runtime_final = ((state_final.combatants["enemy_1"].race_features or {}).get("runtime") or {})
        assert enemy_runtime_final == enemy_runtime_after
    finally:
        end_combat(session_id)
