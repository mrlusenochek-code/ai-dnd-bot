from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.combat.state import add_enemy, end_combat, get_combat, start_combat, upsert_pc
from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def _aasimar_char(*, hp: int = 10, hp_max: int = 20, level: int = 3):
    return SimpleNamespace(
        name="Aasimar",
        level=level,
        hp=hp,
        hp_max=hp_max,
        race_features={
            "features": {
                "healing_hands": {
                    "uses": "per_long_rest",
                    "uses_max": 1,
                    "amount": "level",
                }
            }
        },
    )


def test_detect_healing_hands_phrase_as_action() -> None:
    action = _detect_chat_combat_action("исцеляющие руки")
    assert action == "combat_healing_hands"


def test_healing_hands_long_rest_usage_cycle() -> None:
    ch = _aasimar_char(hp=10, hp_max=20, level=3)

    healed_1, err_1, changed_1 = ws_handlers._apply_healing_hands_usage(ch)
    assert err_1 is None
    assert healed_1 == 3
    assert changed_1 is True
    assert ch.hp == 13

    healed_2, err_2, changed_2 = ws_handlers._apply_healing_hands_usage(ch)
    assert healed_2 is None
    assert err_2 is not None
    assert "долгого отдыха" in err_2
    assert changed_2 is False
    assert ch.hp == 13

    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    assert reset_changed is True
    runtime_after_reset = (ch.race_features or {}).get("runtime") or {}
    assert "healing_hands_used" not in runtime_after_reset

    healed_3, err_3, changed_3 = ws_handlers._apply_healing_hands_usage(ch)
    assert err_3 is None
    assert healed_3 == 3
    assert changed_3 is True
    assert ch.hp == 16


def test_healing_hands_in_combat_requires_turn_and_spends_action() -> None:
    session_id = f"test_aasimar_healing_hands_{uuid.uuid4().hex}"
    ch = _aasimar_char(hp=10, hp_max=20, level=3)
    try:
        start_combat(session_id, reason="test")
        upsert_pc(
            session_id,
            pc_key="pc_1",
            name="Aasimar",
            hp=10,
            hp_max=20,
            ac=12,
            initiative=10,
            race_features=ch.race_features,
            level=3,
        )
        add_enemy(session_id, name="Bandit", hp=8, ac=12, enemy_id="enemy_1")
        state = get_combat(session_id)
        assert state is not None

        state.order = ["enemy_1", "pc_1"]
        state.turn_index = 0
        patch_wrong_turn, err_wrong_turn, changed_wrong_turn = ws_handlers._apply_healing_hands_in_combat(session_id, "pc_1", ch)
        assert patch_wrong_turn is None
        assert err_wrong_turn is not None
        assert "Дождись своего хода" in err_wrong_turn
        assert changed_wrong_turn is False

        state.order = ["pc_1", "enemy_1"]
        state.turn_index = 0
        state.combatants["pc_1"].action_available = False
        patch_no_action, err_no_action, changed_no_action = ws_handlers._apply_healing_hands_in_combat(session_id, "pc_1", ch)
        assert patch_no_action is None
        assert err_no_action is not None
        assert "действие уже потрачено" in err_no_action.lower()
        assert changed_no_action is False

        state.combatants["pc_1"].action_available = True
        patch_ok, err_ok, changed_ok = ws_handlers._apply_healing_hands_in_combat(session_id, "pc_1", ch)
        assert err_ok is None
        assert patch_ok is not None
        assert changed_ok is True
        assert ch.hp == 13
        assert state.combatants["pc_1"].hp_current == 13
        assert state.combatants["pc_1"].action_available is False
        lines = patch_ok.get("lines") if isinstance(patch_ok, dict) else []
        first_text = ""
        if isinstance(lines, list) and lines and isinstance(lines[0], dict):
            first_text = str(lines[0].get("text") or "")
        assert "Исцеляющие руки" in first_text

        state.combatants["pc_1"].race_features = ch.race_features
        reset_combatant = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1")
        assert reset_combatant is True
        combat_runtime = (state.combatants["pc_1"].race_features or {}).get("runtime") or {}
        assert "healing_hands_used" not in combat_runtime
    finally:
        end_combat(session_id)
