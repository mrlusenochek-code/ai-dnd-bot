from __future__ import annotations

from types import SimpleNamespace

from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.web import ws_handlers


def _satyr_character():
    return SimpleNamespace(
        race_features={
            "features": {
                "mirthful_leaps": {
                    "bonus_dice": "1d8",
                    "applies_to": ["long_jump", "high_jump"],
                }
            },
            "runtime": {},
        }
    )


def test_satyr_mirthful_leaps_jump_logs_bonus_out_of_combat(monkeypatch) -> None:
    ch = _satyr_character()
    monkeypatch.setattr(ws_handlers.random, "randint", lambda _a, _b: 6)

    err, msg, changed = ws_handlers._apply_satyr_mirthful_leaps_jump(
        session_id="satyr_jump_ooc",
        player_uid=None,
        ch=ch,
        jump_kind="long_jump",
    )

    assert err is None
    assert changed is True
    assert msg is not None and "+1d8 (6) фт" in msg
    runtime = (ch.race_features or {}).get("runtime") or {}
    assert int(runtime.get("last_mirthful_leaps_bonus_ft") or 0) == 6
    assert str(runtime.get("last_mirthful_leaps_kind") or "") == "long_jump"


def test_satyr_mirthful_leaps_jump_spends_movement_in_combat(monkeypatch) -> None:
    session_id = "satyr_jump_combat"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Satyr",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        speed_ft=35,
        movement_speeds={"walk": 35},
        move_speed_ft=35,
        move_remaining_ft=20,
        move_remaining=20,
        race_features={
            "features": {
                "mirthful_leaps": {
                    "bonus_dice": "1d8",
                    "applies_to": ["long_jump", "high_jump"],
                }
            },
            "runtime": {},
        },
    )
    state.order = ["pc_1"]
    state.turn_index = 0

    ch = _satyr_character()
    monkeypatch.setattr(ws_handlers.random, "randint", lambda _a, _b: 5)

    try:
        err, msg, changed = ws_handlers._apply_satyr_mirthful_leaps_jump(
            session_id=session_id,
            player_uid=1,
            ch=ch,
            jump_kind="high_jump",
        )
        assert err is None
        assert changed is True
        assert msg is not None and "Потрачено движения: 5 фт" in msg

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        assert int(actor.move_remaining_ft) == 15
    finally:
        end_combat(session_id)
