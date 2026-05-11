from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    return [str(item.get("text") or "") for item in lines if isinstance(item, dict)]


def _fighter_style_features(style_key: str) -> dict:
    return {
        "features": [
            {
                "key": "fighting_style",
                "mechanics": {
                    "type": "fighting_style",
                    "allowed_styles": [
                        "archery",
                        "defense",
                        "dueling",
                        "great_weapon_fighting",
                        "protection",
                        "two_weapon_fighting",
                    ],
                    "implemented_styles": ["archery", "defense", "dueling", "great_weapon_fighting", "protection"],
                    "choice_key": "fighting_style",
                },
            }
        ],
        "choices": {"fighting_style": style_key},
        "runtime": {},
    }


def _build_state(
    session_id: str,
    *,
    target_first: bool = True,
    protector_has_shield: bool = True,
    protector_reaction: bool = True,
    protector_position: dict | None = None,
    protector_conditions: dict | None = None,
    attacker_has_advantage: bool = False,
) -> None:
    state = start_combat(session_id)
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Goblin",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        level=5,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 50, "dex": 50, "con": 50},
        inventory=[{"id": "b1", "def": "shortbow", "name": "shortbow", "qty": 1}],
        equip={"ranged": "b1"},
        help_attack_advantage=attacker_has_advantage,
    )
    target = Combatant(
        key="pc_target",
        name="Wizard",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=10,
        level=5,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 40, "dex": 50, "con": 40},
    )
    protector_inventory = [{"id": "w1", "def": "longsword", "name": "longsword", "qty": 1}]
    protector_equip = {"main_hand": "w1"}
    if protector_has_shield:
        protector_inventory.append({"id": "s1", "def": "shield", "name": "shield", "qty": 1})
        protector_equip["off_hand"] = "s1"
    protector = Combatant(
        key="pc_guard",
        name="Guardian",
        side="pc",
        hp_current=30,
        hp_max=30,
        ac=18,
        initiative=5,
        level=5,
        action_available=True,
        bonus_action_available=True,
        reaction_available=protector_reaction,
        stats={"str": 60, "dex": 40, "con": 60},
        inventory=protector_inventory,
        equip=protector_equip,
        class_features=_fighter_style_features("protection"),
        race_features={"runtime": {"conditions": dict(protector_conditions or {})}},
    )
    target.combat_position = {"node_id": "room_a", "x_ft": 0, "y_ft": 0}
    protector.combat_position = dict(protector_position or {"node_id": "room_a", "x_ft": 5, "y_ft": 0})
    state.combatants["pc_target"] = target
    state.combatants["pc_guard"] = protector
    state.order = ["enemy_1", "pc_target", "pc_guard"] if target_first else ["enemy_1", "pc_guard", "pc_target"]
    state.turn_index = 0
    state.round_no = 1


def _capture_roll_modes(monkeypatch) -> list[str]:
    modes: list[str] = []

    def _fake_roll(mode: str, rng=None, reroll_ones: bool = False):
        _ = rng
        _ = reroll_ones
        modes.append(mode)
        if mode == "disadvantage":
            return 18, 3, 3
        if mode == "advantage":
            return 18, 3, 18
        return 18, None, 18

    monkeypatch.setattr("app.combat.live_actions._roll_check_compat", _fake_roll)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 4)
    return modes


def test_protection_applies_disadvantage_and_spends_reaction(monkeypatch) -> None:
    session_id = "test_protection_applies_disadvantage_and_spends_reaction"
    _build_state(session_id)
    modes = _capture_roll_modes(monkeypatch)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert modes == ["disadvantage"]
        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_guard"].reaction_available is False
        texts = _line_texts(patch)
        assert any("Защита:" in text and "помеху" in text for text in texts)
    finally:
        end_combat(session_id)


def test_protection_does_not_apply_without_shield(monkeypatch) -> None:
    session_id = "test_protection_does_not_apply_without_shield"
    _build_state(session_id, protector_has_shield=False)
    modes = _capture_roll_modes(monkeypatch)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert modes == ["normal"]
        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_guard"].reaction_available is True
        assert all("Защита:" not in text for text in _line_texts(patch))
    finally:
        end_combat(session_id)


def test_protection_does_not_apply_without_reaction(monkeypatch) -> None:
    session_id = "test_protection_does_not_apply_without_reaction"
    _build_state(session_id, protector_reaction=False)
    modes = _capture_roll_modes(monkeypatch)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert modes == ["normal"]
        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_guard"].reaction_available is False
        assert all("Защита:" not in text for text in _line_texts(patch))
    finally:
        end_combat(session_id)


def test_protection_does_not_apply_when_target_is_guardian(monkeypatch) -> None:
    session_id = "test_protection_does_not_apply_when_target_is_guardian"
    _build_state(session_id, target_first=False)
    modes = _capture_roll_modes(monkeypatch)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert modes == ["normal"]
        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_guard"].reaction_available is True
        assert all("Защита:" not in text for text in _line_texts(patch))
    finally:
        end_combat(session_id)


def test_protection_does_not_apply_when_guardian_too_far_or_in_other_node(monkeypatch) -> None:
    for suffix, position in (
        ("far", {"node_id": "room_a", "x_ft": 15, "y_ft": 0}),
        ("other_node", {"node_id": "room_b", "x_ft": 5, "y_ft": 0}),
    ):
        session_id = f"test_protection_does_not_apply_{suffix}"
        _build_state(session_id, protector_position=position)
        modes = _capture_roll_modes(monkeypatch)
        try:
            patch, err = handle_live_combat_action("combat_attack", session_id)
            assert err is None
            assert modes == ["normal"]
            state = get_combat(session_id)
            assert state is not None
            assert state.combatants["pc_guard"].reaction_available is True
            assert all("Защита:" not in text for text in _line_texts(patch))
        finally:
            end_combat(session_id)


def test_protection_does_not_apply_when_guardian_incapacitated(monkeypatch) -> None:
    session_id = "test_protection_does_not_apply_when_guardian_incapacitated"
    _build_state(session_id, protector_conditions={"incapacitated": {"active": True}})
    modes = _capture_roll_modes(monkeypatch)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert modes == ["normal"]
        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_guard"].reaction_available is True
        assert all("Защита:" not in text for text in _line_texts(patch))
    finally:
        end_combat(session_id)


def test_protection_cancels_attacker_advantage_to_normal(monkeypatch) -> None:
    session_id = "test_protection_cancels_attacker_advantage_to_normal"
    _build_state(session_id, attacker_has_advantage=True)
    modes = _capture_roll_modes(monkeypatch)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert modes == ["normal"]
        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_guard"].reaction_available is False
        assert any("Защита:" in text for text in _line_texts(patch))
    finally:
        end_combat(session_id)
