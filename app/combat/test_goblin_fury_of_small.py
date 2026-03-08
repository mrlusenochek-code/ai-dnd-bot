from __future__ import annotations

from types import SimpleNamespace

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.web import ws_handlers


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


def test_goblin_fury_of_small_arm_hit_and_short_rest_reset(monkeypatch) -> None:
    session_id = "test_goblin_fury_of_small_arm_hit_and_short_rest_reset"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Goblin",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        stats={"str": 50},
        race_features={
            "features": {
                "fury_of_the_small": {
                    "amount": "level",
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                }
            },
            "runtime": {},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=30,
        hp_max=30,
        ac=12,
        initiative=10,
        stats={"dex": 50},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    goblin = state.combatants["pc_1"]
    ch = SimpleNamespace(level=3, race_features=dict(goblin.race_features or {}))
    arm_err, changed = ws_handlers._apply_fury_of_small_arm(ch)
    assert arm_err is None
    assert changed is True
    goblin.race_features = ch.race_features

    rolls = iter([15, 6, 14, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch_1, err_1 = handle_live_combat_action("combat_attack", session_id)
        assert err_1 is None
        assert patch_1 is not None
        texts_1 = _line_texts(patch_1)
        assert any("Ярость малого: +3 урона (уровень)." in t for t in texts_1)

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime_now = (state_now.combatants["pc_1"].race_features or {}).get("runtime") or {}
        assert runtime_now.get("fury_of_small_used") is True
        assert runtime_now.get("fury_of_small_armed") is False
        assert state_now.combatants["enemy_1"].hp_current == 21

        ch_after = SimpleNamespace(level=3, race_features=dict(state_now.combatants["pc_1"].race_features or {}))
        arm_err_2, changed_2 = ws_handlers._apply_fury_of_small_arm(ch_after)
        assert changed_2 is False
        assert arm_err_2 is not None
        assert "использована" in arm_err_2

        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        patch_2, err_2 = handle_live_combat_action("combat_attack", session_id)
        assert err_2 is None
        assert patch_2 is not None
        texts_2 = _line_texts(patch_2)
        assert not any("Ярость малого:" in t for t in texts_2)
        assert state_now.combatants["enemy_1"].hp_current == 17

        reset_changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1")
        assert reset_changed is True
        runtime_after_reset = (state_now.combatants["pc_1"].race_features or {}).get("runtime") or {}
        assert "fury_of_small_used" not in runtime_after_reset
        assert "fury_of_small_armed" not in runtime_after_reset

        ch_reset = SimpleNamespace(level=3, race_features=dict(state_now.combatants["pc_1"].race_features or {}))
        arm_err_3, changed_3 = ws_handlers._apply_fury_of_small_arm(ch_reset)
        assert arm_err_3 is None
        assert changed_3 is True
    finally:
        end_combat(session_id)
