from __future__ import annotations

from app.combat.live_actions import _apply_evasion_to_save_damage, handle_live_combat_action
from app.combat.state import Combatant, end_combat, start_combat


def _rogue_evasion_features() -> dict:
    return {
        "features": [
            {
                "key": "evasion",
                "name_ru": "Увёртливость",
                "mechanics": {
                    "type": "evasion",
                    "trigger": "dex_save_for_half_damage",
                    "success_damage": "none",
                    "failure_damage": "half",
                },
            }
        ],
        "runtime": {},
    }


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


def test_evasion_success_on_dex_save_reduces_damage_to_zero() -> None:
    actor = Combatant(
        key="pc_1",
        name="Плут",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=15,
        initiative=10,
        class_features=_rogue_evasion_features(),
        level=7,
    )
    damage, lines = _apply_evasion_to_save_damage(
        actor,
        ability="dex",
        save_success=True,
        incoming_damage=20,
        half_damage_on_success=True,
    )
    assert damage == 0
    assert any("отменяет урон" in str(item.get("text") or "") for item in lines)


def test_evasion_failure_on_dex_save_halves_damage() -> None:
    actor = Combatant(
        key="pc_1",
        name="Плут",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=15,
        initiative=10,
        class_features=_rogue_evasion_features(),
        level=7,
    )
    damage, lines = _apply_evasion_to_save_damage(
        actor,
        ability="dex",
        save_success=False,
        incoming_damage=21,
        half_damage_on_success=True,
    )
    assert damage == 10
    assert any("уменьшает урон вдвое" in str(item.get("text") or "") for item in lines)


def test_evasion_missing_feature_does_not_change_damage() -> None:
    actor = Combatant(
        key="pc_1",
        name="Неопытный плут",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=15,
        initiative=10,
        class_features={"features": [], "runtime": {}},
        level=6,
    )
    damage, lines = _apply_evasion_to_save_damage(
        actor,
        ability="dex",
        save_success=True,
        incoming_damage=20,
        half_damage_on_success=True,
    )
    assert damage == 20
    assert lines == []


def test_evasion_non_dex_save_does_not_change_damage() -> None:
    actor = Combatant(
        key="pc_1",
        name="Плут",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=15,
        initiative=10,
        class_features=_rogue_evasion_features(),
        level=7,
    )
    damage, lines = _apply_evasion_to_save_damage(
        actor,
        ability="con",
        save_success=True,
        incoming_damage=20,
        half_damage_on_success=True,
    )
    assert damage == 20
    assert lines == []


def test_evasion_requires_half_damage_on_success_effect() -> None:
    actor = Combatant(
        key="pc_1",
        name="Плут",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=15,
        initiative=10,
        class_features=_rogue_evasion_features(),
        level=7,
    )
    damage, lines = _apply_evasion_to_save_damage(
        actor,
        ability="dex",
        save_success=True,
        incoming_damage=20,
        half_damage_on_success=False,
    )
    assert damage == 20
    assert lines == []


def test_evasion_non_rogue_side_does_not_change_damage() -> None:
    actor = Combatant(
        key="enemy_1",
        name="Враг",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=15,
        initiative=10,
        class_features=_rogue_evasion_features(),
        level=7,
    )
    damage, lines = _apply_evasion_to_save_damage(
        actor,
        ability="dex",
        save_success=True,
        incoming_damage=20,
        half_damage_on_success=True,
    )
    assert damage == 20
    assert lines == []


def test_breath_weapon_pipeline_applies_evasion_on_success(monkeypatch) -> None:
    session_id = "test_breath_weapon_pipeline_applies_evasion_on_success"
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
            "features": {
                "breath_weapon": {
                    "dc_formula": "8 + con_mod + proficiency_bonus",
                    "damage_progression": [{"level_from": 1, "dice": "2d6"}],
                    "recharge": "short_or_long_rest",
                    "damage_type": "lightning",
                    "area": {"shape": "line", "line_ft": 30, "line_width_ft": 5},
                    "save_ability": "dex",
                }
            },
            "runtime": {},
        },
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Плут",
        side="pc",
        hp_current=30,
        hp_max=30,
        ac=15,
        initiative=10,
        level=7,
        stats={"dex": 70},
        class_features=_rogue_evasion_features(),
    )
    state.order = ["pc_1", "pc_2"]
    state.turn_index = 0

    rolls = iter([6, 4, 18])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))
    monkeypatch.setattr(
        "app.combat.live_actions._first_living_opponent",
        lambda _state, _side: _state.combatants["pc_2"],
    )

    try:
        patch, err = handle_live_combat_action("combat_breath_weapon", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("SUCCESS" in t for t in texts)
        assert any("Увёртливость: успешный спасбросок Ловкости отменяет урон." in t for t in texts)
        assert any("Фактически получено урона: 0" in t for t in texts)

    finally:
        end_combat(session_id)
