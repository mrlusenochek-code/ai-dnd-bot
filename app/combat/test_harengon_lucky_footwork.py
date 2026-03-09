from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def _build_state(session_id: str) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Harengon",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        reaction_available=True,
        speed_ft=30,
        move_speed_ft=30,
        race_features={
            "features": {
                "lucky_footwork": {
                    "dice": "1d4",
                    "trigger": "failed_dex_save",
                    "requires": {"not_prone": True, "speed_gt_0": True},
                }
            },
            "runtime": {"last_failed_dex_save": {"dc": 15, "total": 11}},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def test_harengon_lucky_footwork_turns_failed_dex_save_into_success(monkeypatch) -> None:
    session_id = "test_harengon_lucky_footwork_turns_failed_dex_save_into_success"
    _build_state(session_id)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)

    try:
        patch, err = handle_live_combat_action("combat_lucky_footwork", session_id)
        assert err is None
        assert patch is not None
        lines = _line_texts(patch)
        assert any("+4" in t and "успех" in t.lower() for t in lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        assert pc.reaction_available is False
        runtime = (pc.race_features or {}).get("runtime") or {}
        assert "last_failed_dex_save" not in runtime
        result = runtime.get("last_dex_save_result") or {}
        assert result.get("success") is True
        assert int(result.get("new_total") or 0) == 15
    finally:
        end_combat(session_id)


def test_harengon_lucky_footwork_blocked_when_prone_or_speed_zero() -> None:
    session_id_prone = "test_harengon_lucky_footwork_blocked_when_prone"
    _build_state(session_id_prone)
    try:
        state_prone = get_combat(session_id_prone)
        assert state_prone is not None
        pc = state_prone.combatants["pc_1"]
        runtime = (pc.race_features or {}).get("runtime") or {}
        runtime["conditions"] = {"prone": {"active": True}}
        pc.race_features["runtime"] = runtime

        patch, err = handle_live_combat_action("combat_lucky_footwork", session_id_prone)
        assert patch is None
        assert err is not None and "сбиты с ног" in err.lower()
    finally:
        end_combat(session_id_prone)

    session_id_speed = "test_harengon_lucky_footwork_blocked_when_speed_zero"
    _build_state(session_id_speed)
    try:
        state_speed = get_combat(session_id_speed)
        assert state_speed is not None
        pc = state_speed.combatants["pc_1"]
        pc.move_speed_ft = 0
        pc.speed_ft = 0

        patch, err = handle_live_combat_action("combat_lucky_footwork", session_id_speed)
        assert patch is None
        assert err is not None and "скорость" in err.lower()
    finally:
        end_combat(session_id_speed)
