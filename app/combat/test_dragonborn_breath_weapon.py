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


def test_dragonborn_breath_weapon_full_half_and_recharge(monkeypatch) -> None:
    session_id = "test_dragonborn_breath_weapon_full_half_and_recharge"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Dragonborn",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        level=1,
        stats={"con": 60},
        race_features={
            "choices": {
                "draconic_ancestry": {
                    "key": "blue",
                    "damage_type": "lightning",
                    "breath": {"shape": "line", "line_ft": 30, "line_width_ft": 5, "save": "dex"},
                }
            },
            "features": {
                "breath_weapon": {
                    "dc_formula": "8 + con_mod + proficiency_bonus",
                    "damage_progression": [
                        {"level_from": 1, "dice": "2d6"},
                        {"level_from": 6, "dice": "3d6"},
                    ],
                    "recharge": "short_or_long_rest",
                    "damage_type": "lightning",
                    "area": {"shape": "line", "line_ft": 30, "line_width_ft": 5},
                    "save_ability": "dex",
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

    rolls = iter([4, 5, 3, 6, 2, 18])  # dmg,dmg,save(fail) then dmg,dmg,save(success)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch_1, err_1 = handle_live_combat_action("combat_breath_weapon", session_id)
        assert err_1 is None
        assert patch_1 is not None
        texts_1 = _line_texts(patch_1)
        assert any("Оружие дыхания: lightning (линия 30x5 фт)" in t for t in texts_1)
        assert any("FAIL" in t for t in texts_1)
        assert any("full = 9" in t for t in texts_1)
        assert any("Фактически получено урона: 9" in t for t in texts_1)

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].action_available is False
        runtime_now = (state_now.combatants["pc_1"].race_features or {}).get("runtime") or {}
        assert runtime_now.get("breath_weapon_used") is True
        assert state_now.combatants["enemy_1"].hp_current == 21

        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        patch_2, err_2 = handle_live_combat_action("combat_breath_weapon", session_id)
        assert patch_2 is None
        assert err_2 is not None
        assert "уже использовано" in err_2

        reset_changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1")
        assert reset_changed is True
        runtime_after_reset = (state_now.combatants["pc_1"].race_features or {}).get("runtime") or {}
        assert "breath_weapon_used" not in runtime_after_reset

        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        patch_3, err_3 = handle_live_combat_action("combat_breath_weapon", session_id)
        assert err_3 is None
        assert patch_3 is not None
        texts_3 = _line_texts(patch_3)
        assert any("SUCCESS" in t for t in texts_3)
        assert any("half = 4" in t for t in texts_3)
        assert any("Фактически получено урона: 4" in t for t in texts_3)

        state_after = get_combat(session_id)
        assert state_after is not None
        assert state_after.combatants["enemy_1"].hp_current == 17
    finally:
        end_combat(session_id)


def test_dragonborn_breath_weapon_uses_ancestry_damage_type_in_damage_pipeline(monkeypatch) -> None:
    session_id = "test_dragonborn_breath_weapon_uses_ancestry_damage_type_in_damage_pipeline"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Dragonborn Green",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        level=1,
        stats={"con": 50},
        race_features={
            "choices": {
                "draconic_ancestry": {
                    "key": "green",
                    "damage_type": "poison",
                    "breath": {"shape": "cone", "cone_ft": 15, "save": "con"},
                }
            },
            "features": {
                "breath_weapon": {
                    "dc_formula": "8 + con_mod + proficiency_bonus",
                    "damage_progression": [{"level_from": 1, "dice": "2d6"}],
                    "recharge": "short_or_long_rest",
                    "damage_type": "poison",
                    "area": {"shape": "cone", "cone_ft": 15},
                    "save_ability": "con",
                }
            },
            "runtime": {},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Resistant Bandit",
        side="enemy",
        hp_current=30,
        hp_max=30,
        ac=12,
        initiative=10,
        stats={"con": 50},
        race_features={"resistances": ["poison"]},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([4, 5, 3])  # damage 9, save fail
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_breath_weapon", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Оружие дыхания: poison (конус 15 фт)" in t for t in texts)
        assert any("FAIL" in t for t in texts)
        assert any("full = 9" in t for t in texts)
        assert any("Фактически получено урона: 4" in t for t in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["enemy_1"].hp_current == 26
    finally:
        end_combat(session_id)
