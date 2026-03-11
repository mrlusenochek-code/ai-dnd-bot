from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, advance_turn, end_combat, get_combat, start_combat
from app.web import ws_handlers


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    return [item["text"] for item in lines if isinstance(item, dict) and isinstance(item.get("text"), str)]


def _build_orc_state(session_id: str) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Orc",
        side="pc",
        hp_current=22,
        hp_max=22,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        bonus_action_available=True,
        speed_ft=30,
        move_speed_ft=30,
        move_remaining_ft=30,
        move_remaining=30,
        temp_hp=0,
        stats={"str": 60, "dex": 50, "con": 55, "int": 50, "wis": 50, "cha": 50},
        race_features={
            "features": {
                "adrenaline_rush": {
                    "type": "adrenaline_rush",
                    "activation": "bonus_action",
                    "movement": "dash",
                    "temp_hp_formula": "proficiency_bonus",
                    "uses_formula": "proficiency_bonus",
                    "recharge": "per_long_rest",
                }
            },
            "runtime": {"adrenaline_rush_uses_used": 0},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=18,
        hp_max=18,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def test_orc_adrenaline_rush_spends_bonus_action_grants_dash_and_temp_hp() -> None:
    session_id = "test_orc_adrenaline_rush_spends_bonus_action_grants_dash_and_temp_hp"
    _build_orc_state(session_id)

    try:
        patch, err = handle_live_combat_action("combat_adrenaline_rush", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Прилив адреналина" in text for text in texts)
        assert any("Движение: +30 (итого 60)" in text for text in texts)
        assert any("Временные хиты: +2 (всего 2)." in text for text in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        runtime = ((pc.race_features or {}).get("runtime") or {})
        assert pc.bonus_action_available is False
        assert pc.dash_active is True
        assert pc.move_remaining_ft == 60
        assert int(pc.temp_hp or 0) == 2
        assert int(runtime.get("adrenaline_rush_uses_used") or 0) == 1
    finally:
        end_combat(session_id)


def test_orc_adrenaline_rush_is_pb_limited_and_resets_only_on_long_rest() -> None:
    session_id = "test_orc_adrenaline_rush_is_pb_limited_and_resets_only_on_long_rest"
    _build_orc_state(session_id)

    try:
        patch1, err1 = handle_live_combat_action("combat_adrenaline_rush", session_id)
        assert err1 is None
        assert patch1 is not None

        state = get_combat(session_id)
        assert state is not None
        state.combatants["pc_1"].bonus_action_available = True
        state.combatants["pc_1"].move_remaining_ft = 30
        state.combatants["pc_1"].move_remaining = 30

        patch2, err2 = handle_live_combat_action("combat_adrenaline_rush", session_id)
        assert err2 is None
        assert patch2 is not None

        state = get_combat(session_id)
        assert state is not None
        state.combatants["pc_1"].bonus_action_available = True
        state.combatants["pc_1"].move_remaining_ft = 30
        state.combatants["pc_1"].move_remaining = 30

        patch3, err3 = handle_live_combat_action("combat_adrenaline_rush", session_id)
        assert patch3 is None
        assert err3 is not None
        assert "длительного отдыха" in err3.lower()

        assert ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=False) is False
        state_after_short = get_combat(session_id)
        assert state_after_short is not None
        runtime_after_short = ((state_after_short.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert int(runtime_after_short.get("adrenaline_rush_uses_used") or 0) == 2

        assert ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=True) is True
        state_after_long = get_combat(session_id)
        assert state_after_long is not None
        runtime_after_long = ((state_after_long.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert int(runtime_after_long.get("adrenaline_rush_uses_used") or 0) == 0
    finally:
        end_combat(session_id)


def test_orc_adrenaline_rush_dash_state_does_not_stick_between_turns() -> None:
    session_id = "test_orc_adrenaline_rush_dash_state_does_not_stick_between_turns"
    _build_orc_state(session_id)

    try:
        patch, err = handle_live_combat_action("combat_adrenaline_rush", session_id)
        assert err is None
        assert patch is not None

        advanced = advance_turn(session_id)
        assert advanced is not None
        advanced = advance_turn(session_id)
        assert advanced is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        assert pc.dash_active is False
        assert pc.move_speed_ft == 30
        assert pc.move_remaining_ft == 30
    finally:
        end_combat(session_id)
