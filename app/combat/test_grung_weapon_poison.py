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


def test_grung_weapon_poison_arm_and_apply_on_piercing_hit(monkeypatch) -> None:
    session_id = "test_grung_weapon_poison_arm_and_apply_on_piercing_hit"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Grung",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        action_available=True,
        bonus_action_available=True,
        stats={"str": 50, "dex": 60, "con": 55},
        inventory=[{"id": "w1", "def": "dagger", "name": "Кинжал", "qty": 1}],
        equip={"main_hand": "w1"},
        race_features={
            "size": "small",
            "features": {
                "poisonous_skin": {
                    "contact_save_dc": 12,
                    "contact_condition": {"condition": "poisoned", "duration": "1_minute", "repeat_save": "end_of_turn"},
                    "weapon_poison": {"requires": "piercing_weapon", "save_dc": 12, "damage": "2d4", "damage_type": "poison"},
                }
            },
            "runtime": {"grung_weapon_poison_armed": False},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=30,
        hp_max=30,
        ac=11,
        initiative=10,
        stats={"con": 40},
        race_features={"size": "medium"},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    # attack d20, damage d4, poison save d20, poison 2d4
    rolls = iter([16, 3, 2, 2, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        arm_patch, arm_err = handle_live_combat_action("combat_grung_poison_weapon", session_id)
        assert arm_err is None
        assert arm_patch is not None
        arm_lines = _line_texts(arm_patch)
        assert any("наносит яд грунга" in t.lower() for t in arm_lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        runtime = (pc.race_features or {}).get("runtime") or {}
        assert runtime.get("grung_weapon_poison_armed") is True
        assert pc.bonus_action_available is False

        attack_patch, attack_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_err is None
        assert attack_patch is not None
        attack_lines = _line_texts(attack_patch)
        assert any("яд грунга (оружие): спасбросок" in t.lower() for t in attack_lines)
        assert any("урона ядом" in t.lower() for t in attack_lines)

        state_after = get_combat(session_id)
        assert state_after is not None
        pc_after = state_after.combatants["pc_1"]
        runtime_after = (pc_after.race_features or {}).get("runtime") or {}
        assert runtime_after.get("grung_weapon_poison_armed") is False

        enemy_after = state_after.combatants["enemy_1"]
        assert enemy_after.hp_current <= 21
    finally:
        end_combat(session_id)
