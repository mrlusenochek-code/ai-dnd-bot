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


def _build_firbolg_state(session_id: str) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Firbolg",
        side="pc",
        hp_current=24,
        hp_max=24,
        ac=14,
        initiative=20,
        level=5,
        stats={"str": 55, "wis": 60},
        race_features={
            "features": {
                "hidden_step": {
                    "activation": "bonus_action",
                    "duration": "until_start_of_next_turn_or_break",
                    "breaks_on": ["attack", "deal_damage_roll", "force_saving_throw"],
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
        hp_current=40,
        hp_max=40,
        ac=11,
        initiative=10,
        stats={"dex": 50},
        race_features={},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def _build_firbolg_breath_state(session_id: str) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Firbolg",
        side="pc",
        hp_current=24,
        hp_max=24,
        ac=14,
        initiative=20,
        level=5,
        stats={"str": 55, "wis": 60, "con": 60},
        race_features={
            "features": {
                "hidden_step": {
                    "activation": "bonus_action",
                    "duration": "until_start_of_next_turn_or_break",
                    "breaks_on": ["attack", "deal_damage_roll", "force_saving_throw"],
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                },
                "breath_weapon": {
                    "dc_formula": "8 + con_mod + proficiency_bonus",
                    "damage_progression": [{"level_from": 1, "dice": "2d6"}],
                    "recharge": "short_or_long_rest",
                    "damage_type": "force",
                    "area": {"shape": "line", "line_ft": 30, "line_width_ft": 5},
                    "save_ability": "dex",
                },
            },
            "runtime": {},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=40,
        hp_max=40,
        ac=11,
        initiative=10,
        stats={"dex": 50},
        race_features={},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def test_firbolg_hidden_step_advantage_break_and_rest_reset(monkeypatch) -> None:
    session_id = "test_firbolg_hidden_step_advantage_break_and_rest_reset"
    _build_firbolg_state(session_id)
    modes: list[str] = []
    monkeypatch.setattr("app.combat.live_actions.roll_check", lambda mode, **_kwargs: (modes.append(mode) or (18, None, 18)))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)

    try:
        patch, err = handle_live_combat_action("combat_hidden_step", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Незримая поступь" in t for t in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        hidden_step = (((actor.race_features or {}).get("runtime") or {}).get("hidden_step") or {})
        assert hidden_step.get("active") is True
        assert int(hidden_step.get("used") or 0) == 1

        state_now.turn_index = 0
        actor.action_available = True
        attack_patch, attack_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_err is None
        assert attack_patch is not None
        assert modes and modes[0] == "advantage"
        attack_texts = _line_texts(attack_patch)
        assert any("Незримая поступь прерывается" in t for t in attack_texts)
        hidden_step_after_attack = (((actor.race_features or {}).get("runtime") or {}).get("hidden_step") or {})
        assert hidden_step_after_attack.get("active") is False

        state_now.turn_index = 0
        actor.bonus_action_available = True
        second_patch, second_err = handle_live_combat_action("combat_hidden_step", session_id)
        assert second_patch is None
        assert second_err is not None and "использована" in second_err.lower()

        reset_changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1")
        assert reset_changed is True
        runtime_after_reset = ((actor.race_features or {}).get("runtime") or {})
        assert "hidden_step" not in runtime_after_reset

        state_now.turn_index = 0
        actor.bonus_action_available = True
        third_patch, third_err = handle_live_combat_action("combat_hidden_step", session_id)
        assert third_err is None
        assert third_patch is not None
    finally:
        end_combat(session_id)


def test_firbolg_hidden_step_expires_at_start_of_next_turn() -> None:
    session_id = "test_firbolg_hidden_step_expires_at_start_of_next_turn"
    _build_firbolg_state(session_id)

    try:
        patch, err = handle_live_combat_action("combat_hidden_step", session_id)
        assert err is None
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        hidden_step = (((actor.race_features or {}).get("runtime") or {}).get("hidden_step") or {})
        assert hidden_step.get("active") is True
        assert state_now.turn_index == 1

        enemy = state_now.combatants["enemy_1"]
        enemy.action_available = True
        enemy.bonus_action_available = True
        enemy.reaction_available = True
        pass_patch, pass_err = handle_live_combat_action("combat_end_turn", session_id)
        assert pass_err is None
        assert pass_patch is not None

        state_after = get_combat(session_id)
        assert state_after is not None
        assert state_after.turn_index == 0
        hidden_after = ((((state_after.combatants["pc_1"].race_features or {}).get("runtime") or {}).get("hidden_step")) or {})
        assert hidden_after.get("active") is False
    finally:
        end_combat(session_id)


def test_firbolg_hidden_step_breaks_on_save_forcing_action(monkeypatch) -> None:
    session_id = "test_firbolg_hidden_step_breaks_on_save_forcing_action"
    _build_firbolg_breath_state(session_id)
    rolls = iter([4, 5, 3])  # 2d6 damage, enemy dex save fail
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_hidden_step", session_id)
        assert err is None
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        state_now.turn_index = 0
        actor = state_now.combatants["pc_1"]
        actor.action_available = True

        breath_patch, breath_err = handle_live_combat_action("combat_breath_weapon", session_id)
        assert breath_err is None
        assert breath_patch is not None
        texts = _line_texts(breath_patch)
        assert any("Спасбросок врага" in t for t in texts)
        assert any("Незримая поступь прерывается" in t for t in texts)

        hidden_after = ((((actor.race_features or {}).get("runtime") or {}).get("hidden_step")) or {})
        assert hidden_after.get("active") is False
    finally:
        end_combat(session_id)
