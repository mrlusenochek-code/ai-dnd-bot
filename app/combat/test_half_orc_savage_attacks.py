from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    out: list[str] = []
    if not isinstance(lines, list):
        return out
    for line in lines:
        if isinstance(line, dict) and isinstance(line.get("text"), str):
            out.append(line["text"])
    return out


def _build_state(session_id: str, *, weapon_def: str, equip: dict[str, str]) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Полуорк",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        stats={"str": 50, "dex": 50},
        inventory=[{"id": "w1", "def": weapon_def}],
        equip=equip,
        race_features={
            "features": {
                "savage_attacks": {
                    "type": "savage_attacks",
                    "extra_weapon_damage_die": 1,
                    "trigger": "melee_weapon_crit",
                }
            }
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Цель",
        side="enemy",
        hp_current=100,
        hp_max=100,
        ac=10,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def test_savage_attacks_adds_extra_die_on_melee_weapon_crit(monkeypatch) -> None:
    session_id = "test_half_orc_savage_attacks_melee_crit"
    _build_state(session_id, weapon_def="longsword", equip={"main_hand": "w1"})

    rolls = iter((20, 5, 7))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None

        texts = _line_texts(patch)
        assert any("Свирепые атаки: +7 (1d8 доп. кость урона оружия)." in t for t in texts)
        assert any("Урон: 10 + 0 = 17" in t for t in texts)

        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["enemy_1"].hp_current == 83
    finally:
        end_combat(session_id)


def test_savage_attacks_not_applied_for_ranged_weapon_crit(monkeypatch) -> None:
    session_id = "test_half_orc_savage_attacks_ranged_crit"
    _build_state(session_id, weapon_def="shortbow", equip={"ranged": "w1"})

    rolls = iter((20, 5))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None

        texts = _line_texts(patch)
        assert not any("Свирепые атаки" in t for t in texts)
        assert any("Урон: 10 + 0 = 10" in t for t in texts)

        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["enemy_1"].hp_current == 90
    finally:
        end_combat(session_id)


def test_savage_attacks_not_applied_for_non_half_orc(monkeypatch) -> None:
    session_id = "test_half_orc_savage_attacks_non_half_orc"
    _build_state(session_id, weapon_def="longsword", equip={"main_hand": "w1"})
    state = get_combat(session_id)
    assert state is not None
    state.combatants["pc_1"].race_features = {"features": {}}

    rolls = iter((20, 5))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None

        texts = _line_texts(patch)
        assert not any("Свирепые атаки" in t for t in texts)
        assert any("Урон: 10 + 0 = 10" in t for t in texts)

        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["enemy_1"].hp_current == 90
    finally:
        end_combat(session_id)


def test_savage_attacks_not_applied_for_natural_weapon_crit_in_current_model(monkeypatch) -> None:
    session_id = "test_half_orc_savage_attacks_natural_weapon_crit"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Полуорк",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        stats={"str": 50, "dex": 50},
        inventory=[],
        equip={},
        race_features={
            "features": {
                "savage_attacks": {
                    "type": "savage_attacks",
                    "extra_weapon_damage_die": 1,
                    "trigger": "melee_weapon_crit",
                }
            },
            "natural_weapons": [{"key": "bite", "kind": "unarmed", "damage_dice": "1d6", "damage_type": "piercing", "ability": "str"}],
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Цель",
        side="enemy",
        hp_current=100,
        hp_max=100,
        ac=10,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter((20, 5))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None

        texts = _line_texts(patch)
        assert not any("Свирепые атаки" in t for t in texts)
        assert any("Урон: 10 + 0 = 10" in t for t in texts)

        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["enemy_1"].hp_current == 90
    finally:
        end_combat(session_id)
