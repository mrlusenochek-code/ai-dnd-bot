from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    return [str(item.get("text") or "") for item in lines if isinstance(item, dict)]


def _champion_features(*, crit_min_roll: int | None = 19, two_weapon: bool = False, legacy: bool = False) -> dict:
    features: list[dict] = []
    if two_weapon:
        features.append(
            {
                "key": "fighting_style",
                "mechanics": {
                    "type": "fighting_style",
                    "allowed_styles": ["two_weapon_fighting"],
                    "implemented_styles": ["two_weapon_fighting"],
                    "choice_key": "fighting_style",
                },
            }
        )
    subclass_features_by_level: dict[int, list[dict]] = {}
    if crit_min_roll is not None:
        subclass_features_by_level[3] = [
            {
                "key": "improved_critical",
                "mechanics": {} if legacy else {"type": "improved_critical", "crit_min_roll": 19, "applies_to": "weapon_attacks"},
            }
        ]
        if crit_min_roll <= 18:
            subclass_features_by_level[15] = [
                {
                    "key": "superior_critical",
                    "mechanics": {} if legacy else {"type": "improved_critical", "crit_min_roll": 18, "applies_to": "weapon_attacks"},
                }
            ]
    return {
        "features": features,
        "subclass": {
            "key": "champion",
            "features_by_level": subclass_features_by_level,
        },
        "runtime": {},
    }


def _build_state(
    session_id: str,
    *,
    level: int = 4,
    class_features: dict | None = None,
    race_features: dict | None = None,
    off_hand: bool = False,
    reaction_available: bool = True,
) -> None:
    state = start_combat(session_id)
    inventory = [{"id": "w1", "def": "dagger", "name": "dagger", "qty": 1}]
    equip = {"main_hand": "w1"}
    if off_hand:
        inventory.append({"id": "w2", "def": "dagger", "name": "dagger", "qty": 1})
        equip["off_hand"] = "w2"
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Champion",
        side="pc",
        hp_current=30,
        hp_max=30,
        ac=15,
        initiative=20,
        level=level,
        action_available=True,
        bonus_action_available=True,
        reaction_available=reaction_available,
        stats={"str": 90, "dex": 50, "con": 50},
        inventory=inventory,
        equip=equip,
        class_features=class_features or {"features": [], "runtime": {}},
        race_features=race_features,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Target Dummy",
        side="enemy",
        hp_current=30,
        hp_max=30,
        ac=10,
        initiative=10,
        stats={"con": 40},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0
    state.round_no = 1


def _capture_attack_rolls(monkeypatch, attack_rolls: list[tuple[int, int | None, int]], *, randint_values: list[int]) -> None:
    attack_iter = iter(attack_rolls)
    randint_iter = iter(randint_values)

    def _fake_roll(mode: str, rng=None, reroll_ones: bool = False):
        _ = mode
        _ = rng
        _ = reroll_ones
        return next(attack_iter)

    monkeypatch.setattr("app.combat.live_actions._roll_check_compat", _fake_roll)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(randint_iter))


def test_champion_fighter_natural_19_main_hand_weapon_attack_is_crit(monkeypatch) -> None:
    session_id = "test_champion_fighter_natural_19_main_hand_weapon_attack_is_crit"
    _build_state(session_id, level=4, class_features=_champion_features())
    _capture_attack_rolls(monkeypatch, [(19, None, 19)], randint_values=[4, 4])

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("Результат: критическое попадание" in text for text in texts)
    finally:
        end_combat(session_id)


def test_non_champion_fighter_natural_19_main_hand_weapon_attack_is_not_crit(monkeypatch) -> None:
    session_id = "test_non_champion_fighter_natural_19_main_hand_weapon_attack_is_not_crit"
    _build_state(session_id, level=4)
    _capture_attack_rolls(monkeypatch, [(19, None, 19)], randint_values=[4])

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("Результат: попадание" in text for text in texts)
        assert all("Результат: критическое попадание" not in text for text in texts)
    finally:
        end_combat(session_id)


def test_non_champion_fighter_natural_20_main_hand_weapon_attack_remains_crit(monkeypatch) -> None:
    session_id = "test_non_champion_fighter_natural_20_main_hand_weapon_attack_remains_crit"
    _build_state(session_id, level=4)
    _capture_attack_rolls(monkeypatch, [(20, None, 20)], randint_values=[5, 6])

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("Результат: критическое попадание" in text for text in texts)
    finally:
        end_combat(session_id)


def test_champion_fighter_natural_19_off_hand_weapon_attack_is_crit(monkeypatch) -> None:
    session_id = "test_champion_fighter_natural_19_off_hand_weapon_attack_is_crit"
    _build_state(session_id, level=4, class_features=_champion_features(two_weapon=True), off_hand=True)
    _capture_attack_rolls(monkeypatch, [(15, None, 15), (19, None, 19)], randint_values=[3, 4, 4])

    try:
        patch_main, err_main = handle_live_combat_action("combat_attack", session_id, raw_text="только основной")
        assert err_main is None
        assert any("можно бонусным действием атаковать второй рукой" in text for text in _line_texts(patch_main))

        patch_offhand, err_offhand = handle_live_combat_action("combat_two_weapon_attack", session_id)
        assert err_offhand is None
        texts = _line_texts(patch_offhand)
        assert any("Бонусная атака второй рукой:" in text for text in texts)
        assert any("Результат: критическое попадание" in text for text in texts)
    finally:
        end_combat(session_id)


def test_champion_fighter_natural_19_opportunity_attack_is_crit(monkeypatch) -> None:
    session_id = "test_champion_fighter_natural_19_opportunity_attack_is_crit"
    _build_state(session_id, level=4, class_features=_champion_features(), reaction_available=True)
    _capture_attack_rolls(monkeypatch, [(19, None, 19)], randint_values=[4, 4])

    try:
        patch, err = handle_live_combat_action("combat_opportunity_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("Атака возможности" in text for text in texts)
        assert any("Результат: критическое попадание" in text for text in texts)
        state = get_combat(session_id)
        assert state is not None
        assert state.combatants["pc_1"].reaction_available is False
    finally:
        end_combat(session_id)


def test_champion_fighter_level_15_natural_18_weapon_attack_is_crit(monkeypatch) -> None:
    session_id = "test_champion_fighter_level_15_natural_18_weapon_attack_is_crit"
    _build_state(session_id, level=15, class_features=_champion_features(crit_min_roll=18))
    _capture_attack_rolls(monkeypatch, [(18, None, 18)], randint_values=[6, 6])

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("Результат: критическое попадание" in text for text in texts)
    finally:
        end_combat(session_id)


def test_champion_fighter_natural_18_plus_bonus_does_not_become_crit(monkeypatch) -> None:
    session_id = "test_champion_fighter_natural_18_plus_bonus_does_not_become_crit"
    _build_state(
        session_id,
        level=4,
        class_features=_champion_features(),
        race_features={
            "features": {"built_for_success": {"dice": "1d4", "uses_formula": "proficiency_bonus", "uses": "per_long_rest"}},
            "runtime": {"built_for_success_used": 0, "built_for_success_armed": True},
        },
    )
    _capture_attack_rolls(monkeypatch, [(18, None, 18)], randint_values=[1, 5])

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("Создан для успеха: +1 (1d4)." in text for text in texts)
        assert any("Результат: попадание" in text for text in texts)
        assert all("Результат: критическое попадание" not in text for text in texts)
    finally:
        end_combat(session_id)
