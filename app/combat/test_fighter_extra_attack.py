from __future__ import annotations

from types import SimpleNamespace

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.rules.character_catalog import CLASS_CATALOG
from app.web.ws_class_features import apply_combat_class_feature_action


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    return [str(item.get("text") or "") for item in lines if isinstance(item, dict)]


def _fighter_features_for_level(level: int, *, with_action_surge: bool = False) -> dict:
    fighter = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "fighter"), None)
    assert fighter is not None
    features_by_level = fighter.get("features_by_level") or {}
    features: list[dict] = []
    for lvl, entries in features_by_level.items():
        if int(lvl) > int(level):
            continue
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            key = str(entry.get("key") or "")
            if key.startswith("extra_attack"):
                features.append({"key": key, "mechanics": dict(entry.get("mechanics") or {})})
            if with_action_surge and key in {"action_surge", "action_surge_2"}:
                features.append({"key": key, "mechanics": dict(entry.get("mechanics") or {})})
    return {"features": features, "runtime": {}}


def _build_state(
    session_id: str,
    *,
    level: int,
    with_action_surge: bool = False,
    with_extra_attack: bool = True,
    enemy_hp: int = 200,
    enemy_ac: int = 10,
) -> None:
    state = start_combat(session_id)
    class_features = _fighter_features_for_level(level, with_action_surge=with_action_surge) if with_extra_attack else {"features": [], "runtime": {}}
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=40,
        hp_max=40,
        ac=16,
        initiative=20,
        level=level,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 60, "dex": 40, "con": 50},
        inventory=[{"id": "w1", "def": "longsword", "name": "Длинный меч", "qty": 1}],
        equip={"main_hand": "w1"},
        class_features=class_features,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Target Dummy",
        side="enemy",
        hp_current=enemy_hp,
        hp_max=enemy_hp,
        ac=enemy_ac,
        initiative=10,
        stats={"con": 40},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0
    state.round_no = 1


def test_fighter_level_4_has_single_attack_per_action(monkeypatch) -> None:
    session_id = "test_fighter_level_4_has_single_attack_per_action"
    _build_state(session_id, level=4)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else 4)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        state = get_combat(session_id)
        assert state is not None
        fighter = state.combatants["pc_1"]
        assert fighter.action_available is False
        assert state.turn_index == 1
        assert any("Ход автоматически передан" in text for text in _line_texts(patch))
    finally:
        end_combat(session_id)


def test_fighter_level_5_has_two_attacks(monkeypatch) -> None:
    session_id = "test_fighter_level_5_has_two_attacks"
    _build_state(session_id, level=5)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else 4)

    try:
        patch_1, err_1 = handle_live_combat_action("combat_attack", session_id)
        assert err_1 is None
        assert patch_1 is not None
        state_mid = get_combat(session_id)
        assert state_mid is not None
        fighter_mid = state_mid.combatants["pc_1"]
        assert fighter_mid.action_available is True
        assert state_mid.turn_index == 0
        assert any("Ход остаётся за вами: можно атаковать ещё раз." in text for text in _line_texts(patch_1))
        assert all("Ход автоматически передан" not in text for text in _line_texts(patch_1))

        patch_2, err_2 = handle_live_combat_action("combat_attack", session_id)
        assert err_2 is None
        assert patch_2 is not None
        assert all("Ход остаётся за вами: можно атаковать ещё раз." not in text for text in _line_texts(patch_2))
        state_after = get_combat(session_id)
        assert state_after is not None
        assert state_after.combatants["pc_1"].action_available is False
        assert state_after.turn_index == 1
    finally:
        end_combat(session_id)


def test_fighter_level_11_has_three_attacks(monkeypatch) -> None:
    session_id = "test_fighter_level_11_has_three_attacks"
    _build_state(session_id, level=11)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else 4)

    try:
        for expected_turn_index in (0, 0, 1):
            patch, err = handle_live_combat_action("combat_attack", session_id)
            assert err is None
            assert patch is not None
            state_now = get_combat(session_id)
            assert state_now is not None
            assert state_now.turn_index == expected_turn_index
    finally:
        end_combat(session_id)


def test_fighter_level_20_has_four_attacks(monkeypatch) -> None:
    session_id = "test_fighter_level_20_has_four_attacks"
    _build_state(session_id, level=20)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else 4)

    try:
        for expected_turn_index in (0, 0, 0, 1):
            patch, err = handle_live_combat_action("combat_attack", session_id)
            assert err is None
            assert patch is not None
            state_now = get_combat(session_id)
            assert state_now is not None
            assert state_now.turn_index == expected_turn_index
    finally:
        end_combat(session_id)


def test_action_surge_grants_new_attack_set_after_attacks_are_spent(monkeypatch) -> None:
    session_id = "test_action_surge_grants_new_attack_set_after_attacks_are_spent"
    _build_state(session_id, level=5, with_action_surge=True)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else 4)
    ch = SimpleNamespace(name="Fighter", class_features=_fighter_features_for_level(5, with_action_surge=True))

    try:
        patch_1, err_1 = handle_live_combat_action("combat_attack", session_id)
        assert err_1 is None
        assert patch_1 is not None

        surge_patch, surge_err, surge_changed = apply_combat_class_feature_action(
            "combat_action_surge",
            session_id,
            "pc_1",
            ch,
        )
        assert surge_err is None
        assert surge_patch is not None
        assert surge_changed is True

        for expected_turn_index in (0, 0, 1):
            patch, err = handle_live_combat_action("combat_attack", session_id)
            assert err is None
            assert patch is not None
            state_now = get_combat(session_id)
            assert state_now is not None
            assert state_now.turn_index == expected_turn_index
    finally:
        end_combat(session_id)


def test_fighter_level_4_action_surge_before_attack_keeps_turn_until_second_attack(monkeypatch) -> None:
    session_id = "test_fighter_level_4_action_surge_before_attack_keeps_turn_until_second_attack"
    _build_state(session_id, level=4, with_action_surge=True)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else 4)
    ch = SimpleNamespace(name="Fighter", class_features=_fighter_features_for_level(4, with_action_surge=True))

    try:
        surge_patch, surge_err, surge_changed = apply_combat_class_feature_action(
            "combat_action_surge",
            session_id,
            "pc_1",
            ch,
        )
        assert surge_err is None
        assert surge_patch is not None
        assert surge_changed is True

        patch_1, err_1 = handle_live_combat_action("combat_attack", session_id)
        assert err_1 is None
        assert patch_1 is not None
        texts_1 = _line_texts(patch_1)
        assert any("Ход остаётся за вами: доступно дополнительное действие." in text for text in texts_1)
        assert all("Ход автоматически передан" not in text for text in texts_1)
        state_mid = get_combat(session_id)
        assert state_mid is not None
        assert state_mid.turn_index == 0

        patch_2, err_2 = handle_live_combat_action("combat_attack", session_id)
        assert err_2 is None
        assert patch_2 is not None
        texts_2 = _line_texts(patch_2)
        assert any("Ход автоматически передан" in text for text in texts_2)
        state_after = get_combat(session_id)
        assert state_after is not None
        assert state_after.turn_index == 1
    finally:
        end_combat(session_id)


def test_fighter_level_4_action_surge_after_first_attack_grants_second_attack_same_round(monkeypatch) -> None:
    session_id = "test_fighter_level_4_action_surge_after_first_attack_grants_second_attack_same_round"
    _build_state(session_id, level=4, with_action_surge=True)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else 4)
    ch = SimpleNamespace(name="Fighter", class_features=_fighter_features_for_level(4, with_action_surge=True))

    try:
        state = get_combat(session_id)
        assert state is not None
        fighter = state.combatants["pc_1"]
        fighter.action_available = False

        surge_patch, surge_err, surge_changed = apply_combat_class_feature_action(
            "combat_action_surge",
            session_id,
            "pc_1",
            ch,
        )
        assert surge_err is None
        assert surge_patch is not None
        assert surge_changed is True
        assert fighter.bonus_action_available is True

        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        assert any("Ход автоматически передан" in text for text in _line_texts(patch))
        state_after = get_combat(session_id)
        assert state_after is not None
        assert state_after.turn_index == 1
    finally:
        end_combat(session_id)


def test_character_without_extra_attack_gets_no_additional_attacks(monkeypatch) -> None:
    session_id = "test_character_without_extra_attack_gets_no_additional_attacks"
    _build_state(session_id, level=5, with_extra_attack=False)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else 4)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        state = get_combat(session_id)
        assert state is not None
        assert state.turn_index == 1
        assert state.combatants["pc_1"].action_available is False
    finally:
        end_combat(session_id)


def test_fighter_level_5_miss_first_attack_keeps_followup_and_hint(monkeypatch) -> None:
    session_id = "test_fighter_level_5_miss_first_attack_keeps_followup_and_hint"
    _build_state(session_id, level=5, enemy_ac=30)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 5 if _b == 20 else 4)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Результат: промах" in text for text in texts)
        assert any("Ход остаётся за вами: можно атаковать ещё раз." in text for text in texts)
        assert all("Ход автоматически передан" not in text for text in texts)
        state = get_combat(session_id)
        assert state is not None
        assert state.turn_index == 0
        assert state.combatants["pc_1"].action_available is True
    finally:
        end_combat(session_id)


def test_fighter_level_5_killing_first_attack_ends_combat_without_followup_hint(monkeypatch) -> None:
    session_id = "test_fighter_level_5_killing_first_attack_ends_combat_without_followup_hint"
    _build_state(session_id, level=5, enemy_hp=5)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 15 if _b == 20 else 4)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert patch.get("open") is False
        assert patch.get("status") == "Бой завершён"
        assert any("Target Dummy повержен." in text for text in texts)
        assert all("Ход остаётся за вами: можно атаковать ещё раз." not in text for text in texts)
        assert all("Ход автоматически передан" not in text for text in texts)
    finally:
        end_combat(session_id)


def test_dash_and_dodge_do_not_create_extra_attack_followup_hint() -> None:
    session_id_dash = "test_dash_does_not_create_extra_attack_followup_hint"
    _build_state(session_id_dash, level=5)
    try:
        patch_dash, err_dash = handle_live_combat_action("combat_dash", session_id_dash)
        assert err_dash is None
        assert patch_dash is not None
        assert all("можно атаковать ещё раз" not in text for text in _line_texts(patch_dash))
    finally:
        end_combat(session_id_dash)

    session_id_dodge = "test_dodge_does_not_create_extra_attack_followup_hint"
    _build_state(session_id_dodge, level=5)
    try:
        patch_dodge, err_dodge = handle_live_combat_action("combat_dodge", session_id_dodge)
        assert err_dodge is None
        assert patch_dodge is not None
        assert all("можно атаковать ещё раз" not in text for text in _line_texts(patch_dodge))
    finally:
        end_combat(session_id_dodge)
