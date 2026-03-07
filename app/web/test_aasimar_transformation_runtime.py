from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.combat.state import add_enemy, end_combat, get_combat, start_combat, upsert_pc
from app.combat.turns import advance_turn_in_state
from app.combat.sync_pcs import sync_pcs_from_chars
from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def _aasimar_protector_char(*, level: int = 3):
    return SimpleNamespace(
        name="Protector",
        level=level,
        hp=10,
        hp_max=20,
        speed_ft=30,
        stats={"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 55, "cha": 60},
        race_features={
            "features": {
                "aasimar_transformation": {
                    "kind": "protector",
                    "min_level": 3,
                    "duration": "1_minute",
                    "fly_speed_ft": 30,
                    "uses": "per_long_rest",
                    "uses_max": 1,
                }
            }
        },
    )


def test_detect_aasimar_transform_phrase_as_action() -> None:
    action = _detect_chat_combat_action("раскрываю крылья")
    assert action == "combat_aasimar_transform"


def test_aasimar_transformation_runtime_cycle_and_sync_fly() -> None:
    ch = _aasimar_protector_char(level=3)

    runtime_1, err_1, changed_1 = ws_handlers._apply_aasimar_transformation_usage(ch)
    assert err_1 is None
    assert changed_1 is True
    assert isinstance(runtime_1, dict)
    assert runtime_1.get("active") is True
    assert runtime_1.get("kind") == "protector"
    assert int(runtime_1.get("rounds_left") or 0) == 10
    runtime = (ch.race_features or {}).get("runtime") or {}
    assert runtime.get("aasimar_transform_used") is True

    session_id = f"test_aasimar_transform_sync_{uuid.uuid4().hex}"
    try:
        start_combat(session_id, reason="test")
        sync_pcs_from_chars(session_id, {1: ch})
        state = get_combat(session_id)
        assert state is not None
        pc = state.combatants.get("pc_1")
        assert pc is not None
        assert int((pc.movement_speeds or {}).get("fly") or 0) == 30

        runtime_2, err_2, changed_2 = ws_handlers._apply_aasimar_transformation_usage(ch)
        assert runtime_2 is None
        assert err_2 is not None
        assert "долгого отдыха" in err_2
        assert changed_2 is False

        reset_changed = ws_handlers._reset_racial_rest_uses(ch)
        assert reset_changed is True
        runtime_after_reset = (ch.race_features or {}).get("runtime") or {}
        assert "aasimar_transform_used" not in runtime_after_reset
        assert "aasimar_transformation" not in runtime_after_reset

        runtime_3, err_3, changed_3 = ws_handlers._apply_aasimar_transformation_usage(ch)
        assert err_3 is None
        assert changed_3 is True
        assert isinstance(runtime_3, dict)
        assert runtime_3.get("active") is True
    finally:
        end_combat(session_id)


def test_aasimar_transformation_turn_tick_on_owner_end_turn() -> None:
    session_id = f"test_aasimar_transform_tick_{uuid.uuid4().hex}"
    try:
        start_combat(session_id, reason="test")
        upsert_pc(
            session_id,
            pc_key="pc_1",
            name="Protector",
            hp=10,
            hp_max=20,
            ac=12,
            initiative=10,
            level=3,
            race_features={
                "runtime": {
                    "aasimar_transform_used": True,
                    "fly_speed_ft": 30,
                    "aasimar_transformation": {"active": True, "kind": "protector", "rounds_left": 2},
                }
            },
            movement_speeds={"walk": 30, "fly": 30},
        )
        add_enemy(session_id, name="Bandit", hp=10, ac=12, enemy_id="enemy_1")
        state = get_combat(session_id)
        assert state is not None
        state.order = ["pc_1", "enemy_1"]
        state.turn_index = 0

        advance_turn_in_state(state)
        pc_runtime_1 = ((state.combatants["pc_1"].race_features or {}).get("runtime") or {}).get("aasimar_transformation") or {}
        assert int(pc_runtime_1.get("rounds_left") or 0) == 1
        assert pc_runtime_1.get("active") is True

        advance_turn_in_state(state)
        pc_runtime_2 = ((state.combatants["pc_1"].race_features or {}).get("runtime") or {}).get("aasimar_transformation") or {}
        assert int(pc_runtime_2.get("rounds_left") or 0) == 1

        advance_turn_in_state(state)
        runtime_after_end = (state.combatants["pc_1"].race_features or {}).get("runtime") or {}
        transform_after_end = runtime_after_end.get("aasimar_transformation") or {}
        assert int(transform_after_end.get("rounds_left") or 0) == 0
        assert transform_after_end.get("active") is False
        assert "fly_speed_ft" not in runtime_after_end
    finally:
        end_combat(session_id)
