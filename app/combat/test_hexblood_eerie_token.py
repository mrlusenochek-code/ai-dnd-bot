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


def test_hexblood_eerie_token_create_message_view_and_long_rest_reset() -> None:
    session_id = "test_hexblood_eerie_token_create_message_view_and_long_rest_reset"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Hexblood",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        speed_ft=30,
        move_speed_ft=30,
        race_features={
            "features": {
                "eerie_token": {
                    "create_activation": "bonus_action",
                    "range_miles": 10,
                    "message_words_max": 25,
                    "remote_view_duration": "1_minute",
                    "consumes_token_on_view": True,
                    "uses": "per_long_rest",
                    "uses_max": 1,
                }
            },
            "runtime": {
                "eerie_token_uses_used": 0,
                "eerie_token_active": False,
                "eerie_token_consumed": False,
                "eerie_token_created_at": "",
                "eerie_token_expires_on_next_long_rest": True,
            },
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

    try:
        create_patch, create_err = handle_live_combat_action("combat_eerie_token_create", session_id)
        assert create_err is None
        assert create_patch is not None
        assert any("жуткий сувенир" in t.lower() for t in _line_texts(create_patch))

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        runtime = (pc.race_features or {}).get("runtime") or {}
        assert runtime.get("eerie_token_active") is True
        assert runtime.get("eerie_token_consumed") is False
        assert int(runtime.get("eerie_token_uses_used") or 0) == 1
        assert pc.bonus_action_available is False

        first_id = str(runtime.get("eerie_token_id") or "")
        pc.bonus_action_available = True
        create_again_patch, create_again_err = handle_live_combat_action("combat_eerie_token_create", session_id)
        assert create_again_err is None
        assert create_again_patch is not None
        runtime_after_replace = ((pc.race_features or {}).get("runtime") or {})
        assert str(runtime_after_replace.get("eerie_token_id") or "").startswith("et_")
        assert str(runtime_after_replace.get("eerie_token_id") or "") != first_id
        assert int(runtime_after_replace.get("eerie_token_uses_used") or 0) == 1

        long_message = " ".join([f"слово{i}" for i in range(1, 27)])
        msg_fail_patch, msg_fail_err = handle_live_combat_action(
            "combat_eerie_token_message",
            session_id,
            raw_text=f"передаю сообщение сувениром {long_message}",
        )
        assert msg_fail_patch is None
        assert msg_fail_err is not None and "25" in msg_fail_err
        assert pc.action_available is True

        msg_ok_patch, msg_ok_err = handle_live_combat_action(
            "combat_eerie_token_message",
            session_id,
            raw_text="передаю сообщение сувениром Это короткое сообщение для проверки лимита слов",
        )
        assert msg_ok_err is None
        assert msg_ok_patch is not None
        assert any("сообщение" in t.lower() for t in _line_texts(msg_ok_patch))
        assert pc.action_available is False

        pc.action_available = True
        view_patch, view_err = handle_live_combat_action("combat_eerie_token_view", session_id)
        assert view_err is None
        assert view_patch is not None
        assert any("уничтожен" in t.lower() for t in _line_texts(view_patch))

        runtime_after_view = (pc.race_features or {}).get("runtime") or {}
        assert runtime_after_view.get("eerie_token_active") is False
        assert runtime_after_view.get("eerie_token_consumed") is True
        assert runtime_after_view.get("eerie_token_sense_active") is True
        assert int(runtime_after_view.get("eerie_token_remote_view_rounds_left") or 0) == 10

        pc.bonus_action_available = True
        create_after_view_patch, create_after_view_err = handle_live_combat_action("combat_eerie_token_create", session_id)
        assert create_after_view_patch is None
        assert create_after_view_err is not None and "долгого" in create_after_view_err.lower()

        reset_changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=True)
        assert reset_changed is True
        runtime_after_reset = (pc.race_features or {}).get("runtime") or {}
        assert "eerie_token_uses_used" not in runtime_after_reset
        assert "eerie_token_active" not in runtime_after_reset
        assert "eerie_token_consumed" not in runtime_after_reset
    finally:
        end_combat(session_id)
