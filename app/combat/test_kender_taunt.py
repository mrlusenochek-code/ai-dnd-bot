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


def test_kender_taunt_applies_disadvantage_vs_others_and_expires_on_next_turn_start(monkeypatch) -> None:
    session_id = "test_kender_taunt_applies_disadvantage_vs_others_and_expires_on_next_turn_start"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Kender",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 60, "cha": 50},
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
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Ally",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=19,
    )
    state.combatants["enemy_1"] = Combatant(
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
    )
    state.order = ["pc_1", "pc_2", "enemy_1"]
    state.turn_index = 0

    # Taunt WIS save: 5 (fail vs DC 11); enemy attack disadvantage rolls: 19/2; then normal roll 13.
    rolls = iter([5, 19, 2, 14, 13, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        taunt_patch, taunt_err = handle_live_combat_action("combat_taunt", session_id, raw_text="насмешка bandit")
        assert taunt_err is None
        assert taunt_patch is not None
        taunt_lines = _line_texts(taunt_patch)
        assert any("провал" in t.lower() for t in taunt_lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        enemy = state_now.combatants["enemy_1"]
        taunted_runtime = ((enemy.race_features or {}).get("runtime") or {}).get("taunted") or {}
        assert taunted_runtime.get("active") is True
        assert str(taunted_runtime.get("by_actor_id") or "") == "pc_1"

        # Enemy attacks ally (pc_2): must have disadvantage from taunt.
        state_now.turn_index = 2
        enemy.action_available = True
        state_now.order = ["pc_2", "pc_1", "enemy_1"]
        dis_patch, dis_err = handle_live_combat_action("combat_attack", session_id)
        assert dis_err is None
        assert dis_patch is not None
        dis_lines = _line_texts(dis_patch)
        assert any("d20(19,2)" in t for t in dis_lines)

        # Enemy attacks kender (pc_1): taunt disadvantage must not apply.
        state_now = get_combat(session_id)
        assert state_now is not None
        state_now.turn_index = 2
        state_now.order = ["pc_1", "pc_2", "enemy_1"]
        state_now.combatants["enemy_1"].action_available = True
        normal_patch, normal_err = handle_live_combat_action("combat_attack", session_id)
        assert normal_err is None
        assert normal_patch is not None
        normal_lines = _line_texts(normal_patch)
        assert any("d20(13)" in t for t in normal_lines)

        # At start of kender's next turn taunt expires.
        state_now = get_combat(session_id)
        assert state_now is not None
        state_now.order = ["pc_1", "pc_2", "enemy_1"]
        state_now.turn_index = 2
        advanced = advance_turn(session_id)
        assert advanced is not None
        enemy_after = advanced.combatants["enemy_1"]
        runtime_after = (enemy_after.race_features or {}).get("runtime") or {}
        assert "taunted" not in runtime_after
    finally:
        end_combat(session_id)
