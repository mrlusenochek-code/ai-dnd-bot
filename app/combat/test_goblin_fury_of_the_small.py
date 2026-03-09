from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            out.append(text)
    return out


def _build_state(session_id: str) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Goblin",
        side="pc",
        hp_current=24,
        hp_max=24,
        ac=14,
        initiative=20,
        level=3,
        stats={"str": 50, "dex": 60, "con": 55},
        race_features={
            "size": "small",
            "features": {
                "fury_of_the_small": {
                    "amount": "level",
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                    "condition": "target_size_larger_than_you",
                    "trigger": "deal_damage_with_attack_or_spell",
                }
            },
            "runtime": {},
        },
    )
    state.combatants["enemy_large"] = Combatant(
        key="enemy_large",
        name="Ogre",
        side="enemy",
        hp_current=40,
        hp_max=40,
        ac=11,
        initiative=11,
        stats={"dex": 45},
        race_features={"size": "large"},
    )
    state.combatants["enemy_small"] = Combatant(
        key="enemy_small",
        name="Goblin Scout",
        side="enemy",
        hp_current=40,
        hp_max=40,
        ac=11,
        initiative=10,
        stats={"dex": 50},
        race_features={"size": "small"},
    )
    state.order = ["pc_1", "enemy_large", "enemy_small"]
    state.turn_index = 0


def test_goblin_fury_of_the_small_end_to_end(monkeypatch) -> None:
    session_id = "test_goblin_fury_of_the_small_end_to_end"
    _build_state(session_id)
    action = _detect_chat_combat_action("разъярённая мелкота")
    assert action == "combat_fury_of_small"

    rolls = iter([15, 6, 15, 6, 15, 6])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        arm_patch, arm_err = handle_live_combat_action(action, session_id)
        assert arm_err is None
        assert arm_patch is not None
        arm_lines = _line_texts(arm_patch)
        assert any("Разъярённая мелкота подготовлена" in t for t in arm_lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert runtime.get("fury_of_small_armed") is True
        assert runtime.get("fury_of_small_used") is not True

        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        hit_large_patch, hit_large_err = handle_live_combat_action("combat_attack", session_id)
        assert hit_large_err is None
        assert hit_large_patch is not None
        hit_large_lines = _line_texts(hit_large_patch)
        assert any("Разъярённая мелкота: +3 урона." in t for t in hit_large_lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime_after_large = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert runtime_after_large.get("fury_of_small_used") is True
        assert runtime_after_large.get("fury_of_small_armed") is False

        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        second_arm_patch, second_arm_err = handle_live_combat_action(action, session_id)
        assert second_arm_patch is None
        assert second_arm_err is not None and "использована" in second_arm_err.lower()

        reset_changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1")
        assert reset_changed is True

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime_after_reset = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert "fury_of_small_used" not in runtime_after_reset
        assert "fury_of_small_armed" not in runtime_after_reset

        state_now.turn_index = 0
        rearm_patch, rearm_err = handle_live_combat_action(action, session_id)
        assert rearm_err is None
        assert rearm_patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        state_now.order = ["pc_1", "enemy_small", "enemy_large"]
        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        hit_medium_patch, hit_medium_err = handle_live_combat_action("combat_attack", session_id)
        assert hit_medium_err is None
        assert hit_medium_patch is not None
        hit_medium_lines = _line_texts(hit_medium_patch)
        assert not any("Разъярённая мелкота:" in t for t in hit_medium_lines)

        runtime_after_small = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert runtime_after_small.get("fury_of_small_armed") is True
        assert runtime_after_small.get("fury_of_small_used") is not True

        state_now.order = ["pc_1", "enemy_large", "enemy_small"]
        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        hit_large_second_patch, hit_large_second_err = handle_live_combat_action("combat_attack", session_id)
        assert hit_large_second_err is None
        assert hit_large_second_patch is not None
        hit_large_second_lines = _line_texts(hit_large_second_patch)
        assert any("Разъярённая мелкота: +3 урона." in t for t in hit_large_second_lines)

        runtime_after_second_large = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert runtime_after_second_large.get("fury_of_small_used") is True
        assert runtime_after_second_large.get("fury_of_small_armed") is False
    finally:
        end_combat(session_id)
