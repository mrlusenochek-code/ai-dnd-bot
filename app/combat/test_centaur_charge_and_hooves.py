from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


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


def _build_centaur_state(session_id: str) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Centaur",
        side="pc",
        hp_current=30,
        hp_max=30,
        ac=13,
        initiative=20,
        level=3,
        speed_ft=40,
        movement_speeds={"walk": 40},
        movement_mode="walk",
        move_speed_ft=40,
        move_remaining_ft=40,
        move_remaining=40,
        stats={"str": 60, "dex": 50, "con": 50},
        inventory=[{"id": "w1", "def": "longsword"}],
        equip={"main_hand": "w1"},
        race_features={
            "features": {
                "charge": {"move_ft": 30, "activation": "bonus_action", "bonus_attack": "hooves"},
            },
            "natural_weapons": [
                {
                    "key": "hooves",
                    "name_ru": "Копыта",
                    "damage_dice": "1d4",
                    "damage_type": "bludgeoning",
                    "kind": "unarmed",
                    "ability": "str",
                }
            ],
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
        stats={"dex": 50},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def test_centaur_charge_enables_hooves_and_hooves_spends_bonus_action(monkeypatch) -> None:
    session_id = "test_centaur_charge_enables_hooves_and_hooves_spends_bonus_action"
    _build_centaur_state(session_id)

    rolls = iter([15, 4, 14, 3])  # attack d20, longsword d8, hooves d20, hooves d4
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        move_patch, move_err = handle_live_combat_action("combat_move", session_id, distance_ft=30)
        assert move_err is None
        assert move_patch is not None

        attack_patch, attack_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_err is None
        assert attack_patch is not None
        attack_texts = _line_texts(attack_patch)
        assert any("Разбег: можно бонусным действием ударить копытами" in t for t in attack_texts)

        state_after_attack = get_combat(session_id)
        assert state_after_attack is not None
        pc_after_attack = state_after_attack.combatants["pc_1"]
        enemy_after_attack = state_after_attack.combatants["enemy_1"]
        assert pc_after_attack.charge_hooves_available is True
        assert pc_after_attack.action_available is False
        assert pc_after_attack.bonus_action_available is True
        assert enemy_after_attack.hp_current == 15

        hooves_patch, hooves_err = handle_live_combat_action("combat_hooves_attack", session_id)
        assert hooves_err is None
        assert hooves_patch is not None
        hooves_texts = _line_texts(hooves_patch)
        assert any("Копыта: бонусная атака после Разбега." in t for t in hooves_texts)

        state_after_hooves = get_combat(session_id)
        assert state_after_hooves is not None
        pc_after_hooves = state_after_hooves.combatants["pc_1"]
        enemy_after_hooves = state_after_hooves.combatants["enemy_1"]
        assert pc_after_hooves.charge_hooves_available is False
        assert pc_after_hooves.bonus_action_available is False
        assert enemy_after_hooves.hp_current == 11
    finally:
        end_combat(session_id)


def test_centaur_charge_not_available_below_30ft(monkeypatch) -> None:
    session_id = "test_centaur_charge_not_available_below_30ft"
    _build_centaur_state(session_id)

    rolls = iter([15, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        move_patch, move_err = handle_live_combat_action("combat_move", session_id, distance_ft=20)
        assert move_err is None
        assert move_patch is not None

        attack_patch, attack_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_err is None
        assert attack_patch is not None
        attack_texts = _line_texts(attack_patch)
        assert not any("Разбег: можно бонусным действием ударить копытами" in t for t in attack_texts)

        state_after_attack = get_combat(session_id)
        assert state_after_attack is not None
        assert state_after_attack.combatants["pc_1"].charge_hooves_available is False
        assert state_after_attack.turn_index == 1
    finally:
        end_combat(session_id)


def test_centaur_charge_not_available_without_melee_hit(monkeypatch) -> None:
    session_id = "test_centaur_charge_not_available_without_melee_hit"
    _build_centaur_state(session_id)

    rolls = iter([2, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        move_patch, move_err = handle_live_combat_action("combat_move", session_id, distance_ft=30)
        assert move_err is None
        assert move_patch is not None

        attack_patch, attack_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_err is None
        assert attack_patch is not None
        attack_texts = _line_texts(attack_patch)
        assert not any("Разбег: можно бонусным действием ударить копытами" in t for t in attack_texts)

        state_after_attack = get_combat(session_id)
        assert state_after_attack is not None
        pc_after_attack = state_after_attack.combatants["pc_1"]
        assert pc_after_attack.charge_hooves_available is False
        assert pc_after_attack.bonus_action_available is True
    finally:
        end_combat(session_id)


def test_centaur_charge_expires_on_next_turn_if_unused(monkeypatch) -> None:
    session_id = "test_centaur_charge_expires_on_next_turn_if_unused"
    _build_centaur_state(session_id)

    rolls = iter([15, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        move_patch, move_err = handle_live_combat_action("combat_move", session_id, distance_ft=30)
        assert move_err is None
        assert move_patch is not None

        attack_patch, attack_err = handle_live_combat_action("combat_attack", session_id)
        assert attack_err is None
        assert attack_patch is not None

        state_after_attack = get_combat(session_id)
        assert state_after_attack is not None
        assert state_after_attack.combatants["pc_1"].charge_hooves_available is True

        state_after_enemy = handle_live_combat_action("combat_end_turn", session_id)[0]
        assert state_after_enemy is not None
        next_state = get_combat(session_id)
        assert next_state is not None
        assert next_state.turn_index == 1

        state_after_return = handle_live_combat_action("combat_end_turn", session_id)[0]
        assert state_after_return is not None
        final_state = get_combat(session_id)
        assert final_state is not None
        assert final_state.turn_index == 0
        assert final_state.combatants["pc_1"].charge_hooves_available is False
    finally:
        end_combat(session_id)


def test_centaur_charge_does_not_leak_between_battles() -> None:
    session_id = "test_centaur_charge_does_not_leak_between_battles"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Centaur",
        side="pc",
        hp_current=30,
        hp_max=30,
        ac=13,
        initiative=20,
        charge_hooves_available=True,
        race_features={"features": {"charge": {"move_ft": 30, "activation": "bonus_action", "bonus_attack": "hooves"}}},
    )
    state.order = ["pc_1"]
    state.turn_index = 0

    end_combat(session_id)
    restarted = start_combat(session_id)
    assert restarted.active is True
    assert restarted.combatants == {}
