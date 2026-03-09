from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.web import ws_handlers


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def test_hobgoblin_saving_face_turns_miss_into_hit_and_resets_on_short_rest(monkeypatch) -> None:
    session_id = "test_hobgoblin_saving_face_turns_miss_into_hit_and_resets_on_short_rest"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Hobgoblin",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 50, "dex": 50, "con": 60, "int": 55},
        inventory=[{"id": "w1", "def": "longsword", "name": "Длинный меч", "qty": 1}],
        equip={"main_hand": "w1"},
        race_features={
            "features": {
                "saving_face": {
                    "range_ft": 30,
                    "uses_max": 1,
                    "uses": "per_short_or_long_rest",
                    "bonus_formula": "min(allies_within_30ft, 5)",
                }
            },
            "runtime": {"saving_face_uses_used": 0},
        },
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Ally 1",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=18,
    )
    state.combatants["pc_3"] = Combatant(
        key="pc_3",
        name="Ally 2",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=17,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        stats={"con": 50},
    )
    state.order = ["pc_1", "enemy_1", "pc_2", "pc_3"]
    state.turn_index = 0

    # attack d20=9 (total 11 vs AC 12 -> miss), damage d8=4
    rolls = iter([9, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        miss_patch, miss_err = handle_live_combat_action("combat_attack", session_id)
        assert miss_err is None
        assert miss_patch is not None
        miss_lines = _line_texts(miss_patch)
        assert any("промах" in t.lower() for t in miss_lines)
        assert any("сохранить лицо" in t.lower() for t in miss_lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        runtime = (pc.race_features or {}).get("runtime") or {}
        assert isinstance(runtime.get("saving_face_pending"), dict)

        enemy_before = state_now.combatants["enemy_1"].hp_current

        sf_patch, sf_err = handle_live_combat_action("combat_saving_face", session_id)
        assert sf_err is None
        assert sf_patch is not None
        sf_lines = _line_texts(sf_patch)
        assert any("попадание" in t.lower() for t in sf_lines)

        state_after = get_combat(session_id)
        assert state_after is not None
        pc_after = state_after.combatants["pc_1"]
        enemy_after = state_after.combatants["enemy_1"]
        runtime_after = (pc_after.race_features or {}).get("runtime") or {}

        assert pc_after.reaction_available is False
        assert int(runtime_after.get("saving_face_uses_used") or 0) == 1
        assert "saving_face_pending" not in runtime_after
        assert enemy_after.hp_current < enemy_before

        sf_again_patch, sf_again_err = handle_live_combat_action("combat_saving_face", session_id)
        assert sf_again_patch is None
        assert sf_again_err is not None

        reset_changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=False)
        assert reset_changed is True
        runtime_reset = (pc_after.race_features or {}).get("runtime") or {}
        assert "saving_face_uses_used" not in runtime_reset

        pc_after.reaction_available = True
        runtime_reset["saving_face_pending"] = {"kind": "check", "dc": 12, "total": 10}
        pc_after.race_features["runtime"] = runtime_reset
        sf_after_rest_patch, sf_after_rest_err = handle_live_combat_action("combat_saving_face", session_id)
        assert sf_after_rest_err is None
        assert sf_after_rest_patch is not None
    finally:
        end_combat(session_id)
