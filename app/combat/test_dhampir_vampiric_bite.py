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
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            out.append(text)
    return out


def _build_dhampir_state(session_id: str, *, hp_current: int = 20, level: int = 5) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Dhampir",
        side="pc",
        hp_current=hp_current,
        hp_max=20,
        ac=13,
        initiative=20,
        level=level,
        stats={"con": 60, "str": 50},
        race_features={
            "creature_type": "humanoid",
            "features": {
                "vampiric_bite": {
                    "weapon": {"damage_dice": "1d4", "damage_type": "piercing", "ability": "con"},
                    "advantage_when_hp_below_half": True,
                    "uses": "per_long_rest",
                    "uses_formula": "proficiency_bonus",
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
        race_features={"creature_type": "humanoid"},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def test_dhampir_bite_has_advantage_when_hp_is_half_or_lower(monkeypatch) -> None:
    session_id = "test_dhampir_bite_has_advantage_when_hp_is_half_or_lower"
    _build_dhampir_state(session_id, hp_current=10, level=5)
    modes: list[str] = []
    monkeypatch.setattr("app.combat.live_actions.roll_check", lambda mode, **_kwargs: (modes.append(mode) or (3, 17, 17)))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)

    try:
        patch, err = handle_live_combat_action("combat_vampiric_bite", session_id)
        assert err is None
        assert patch is not None
        assert modes and modes[0] == "advantage"
        texts = _line_texts(patch)
        assert any("Укус вампира" in t for t in texts)
    finally:
        end_combat(session_id)


def test_dhampir_bite_empower_heal_restores_hp_and_spends_use(monkeypatch) -> None:
    session_id = "test_dhampir_bite_empower_heal_restores_hp_and_spends_use"
    _build_dhampir_state(session_id, hp_current=8, level=5)
    monkeypatch.setattr("app.combat.live_actions.roll_check", lambda _mode, **_kwargs: (18, None, 18))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)

    try:
        patch, err = handle_live_combat_action("combat_vampiric_bite", session_id, empower="heal")
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("восстановлено" in t for t in texts)
        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        assert actor.hp_current > 8
        runtime = ((actor.race_features or {}).get("runtime") or {})
        assert int(runtime.get("vampiric_bite_uses_used") or 0) == 1
    finally:
        end_combat(session_id)


def test_dhampir_bite_empower_bonus_applies_to_next_attack_and_is_cleared(monkeypatch) -> None:
    session_id = "test_dhampir_bite_empower_bonus_applies_to_next_attack_and_is_cleared"
    _build_dhampir_state(session_id, hp_current=20, level=5)
    monkeypatch.setattr("app.combat.live_actions.roll_check", lambda _mode, **_kwargs: (18, None, 18))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)

    try:
        bite_patch, bite_err = handle_live_combat_action("combat_vampiric_bite", session_id, empower="bonus")
        assert bite_err is None
        assert bite_patch is not None
        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        runtime = ((actor.race_features or {}).get("runtime") or {})
        assert bool(runtime.get("vampiric_bite_bonus_armed")) is True
        assert int(runtime.get("vampiric_bite_bonus_value") or 0) > 0

        # Return turn to actor to make next attack.
        state_now.turn_index = 0
        actor.action_available = True
        attack_patch, attack_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_err is None
        assert attack_patch is not None
        texts = _line_texts(attack_patch)
        assert any("бонус к следующему d20" in t.lower() for t in texts)
        runtime_after = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert bool(runtime_after.get("vampiric_bite_bonus_armed")) is False
        assert int(runtime_after.get("vampiric_bite_bonus_value") or 0) == 0
    finally:
        end_combat(session_id)


def test_dhampir_bite_uses_are_limited_by_pb_and_reset_on_long_rest(monkeypatch) -> None:
    session_id = "test_dhampir_bite_uses_are_limited_by_pb_and_reset_on_long_rest"
    _build_dhampir_state(session_id, hp_current=20, level=1)  # PB = 2
    monkeypatch.setattr("app.combat.live_actions.roll_check", lambda _mode, **_kwargs: (18, None, 18))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)

    try:
        state_now = get_combat(session_id)
        assert state_now is not None
        for _ in range(2):
            state_now.turn_index = 0
            state_now.combatants["pc_1"].action_available = True
            patch, err = handle_live_combat_action("combat_vampiric_bite", session_id, empower="bonus")
            assert err is None
            assert patch is not None

        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        patch, err = handle_live_combat_action("combat_vampiric_bite", session_id, empower="bonus")
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("лимит БМ/дл отдых исчерпан" in t for t in texts)

        reset_changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1")
        assert reset_changed is True
        runtime_after_reset = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert "vampiric_bite_uses_used" not in runtime_after_reset
        assert "vampiric_bite_bonus_armed" not in runtime_after_reset
        assert "vampiric_bite_bonus_value" not in runtime_after_reset
    finally:
        end_combat(session_id)
