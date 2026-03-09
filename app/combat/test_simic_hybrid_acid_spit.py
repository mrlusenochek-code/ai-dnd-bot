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
            out.append(str(item.get("text")))
    return out


def test_simic_acid_spit_uses_damage_and_long_rest_reset(monkeypatch) -> None:
    session_id = "test_simic_acid_spit_uses_damage_and_long_rest_reset"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Simic",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        level=5,
        stats={"con": 60},
        race_features={
            "race_key": "simic_hybrid",
            "features": {"acid_spit": {"range_ft": 30, "damage": "2d10", "damage_type": "acid", "uses_formula": "max(con_mod,1)"}},
            "runtime": {"acid_spit_uses_used": 0},
        },
    )
    state.combatants["enemy_1"] = Combatant(key="enemy_1", name="Guard", side="enemy", hp_current=30, hp_max=30, ac=12, initiative=10, stats={"dex": 50})
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([5, 7, 8, 18, 4, 6])  # fail save, dmg 15; success save, dmg 10 => half 5
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch_1, err_1 = handle_live_combat_action("combat_acid_spit", session_id)
        assert err_1 is None and patch_1 is not None
        texts_1 = _line_texts(patch_1)
        assert any("Кислотный плевок" in t for t in texts_1)
        assert any("FAIL" in t for t in texts_1)
        assert any("full = 15" in t for t in texts_1)
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["enemy_1"].hp_current == 15
        assert int(((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {}).get("acid_spit_uses_used") or 0) == 1

        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        patch_2, err_2 = handle_live_combat_action("combat_acid_spit", session_id)
        assert patch_2 is None
        assert err_2 is not None and "исчерпан" in err_2

        assert ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=True) is True
        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        patch_3, err_3 = handle_live_combat_action("combat_acid_spit", session_id)
        assert err_3 is None and patch_3 is not None
        texts_3 = _line_texts(patch_3)
        assert any("SUCCESS" in t for t in texts_3)
        assert any("half = 5" in t for t in texts_3)
    finally:
        end_combat(session_id)


def test_simic_acid_spit_scales_at_level_11(monkeypatch) -> None:
    session_id = "test_simic_acid_spit_scales_at_level_11"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Simic",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        level=11,
        stats={"con": 60},
        race_features={
            "race_key": "simic_hybrid",
            "features": {"acid_spit": {"range_ft": 30, "damage": "2d10", "damage_type": "acid", "uses_formula": "max(con_mod,1)"}},
            "runtime": {"acid_spit_uses_used": 0},
        },
    )
    state.combatants["enemy_1"] = Combatant(key="enemy_1", name="Guard", side="enemy", hp_current=30, hp_max=30, ac=12, initiative=10, stats={"dex": 50})
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([4, 3, 4, 5])  # fail save, 3d10 damage = 12
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))
    try:
        patch, err = handle_live_combat_action("combat_acid_spit", session_id)
        assert err is None and patch is not None
        texts = _line_texts(patch)
        assert any("3+4+5 acid => full = 12" in t for t in texts)
    finally:
        end_combat(session_id)
