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
                    "implemented_styles": [
                        "archery",
                        "defense",
                        "dueling",
                        "great_weapon_fighting",
                        "protection",
                        "two_weapon_fighting",
                    ],
                    "choice_key": "fighting_style",
                },
            }
        ],
        "choices": {"fighting_style": style_key},
        "runtime": {},
    }


def _fighter_style_and_sneak_features(style_key: str) -> dict:
    out = _fighter_style_features(style_key)
    out["features"].append(
        {
            "key": "sneak_attack",
            "mechanics": {
                "type": "sneak_attack",
                "frequency": "once_per_turn",
                "requires_weapon": True,
                "requires_finesse_or_ranged": True,
                "damage_progression": [{"level": 1, "dice": "1d6"}],
                "condition": "advantage_or_ally_and_no_disadvantage",
            },
        }
    )
    return out


def _build_state(
    session_id: str,
    *,
    stats: dict | None = None,
    main_def: str = "dagger",
    off_def: str | None = "dagger",
    class_features: dict | None = None,
    add_pc_ally: bool = False,
) -> None:
    state = start_combat(session_id)
    inventory = [{"id": "w1", "def": main_def, "name": main_def, "qty": 1}]
    equip = {"main_hand": "w1"}
    if off_def is not None:
        inventory.append({"id": "w2", "def": off_def, "name": off_def, "qty": 1})
        equip["off_hand"] = "w2"
    fighter = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=30,
        hp_max=30,
        ac=15,
        initiative=20,
        level=5,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats=dict(stats or {"str": 90, "dex": 50, "con": 50}),
        inventory=inventory,
        equip=equip,
        class_features=class_features or _fighter_style_features("defense"),
    )
    fighter.combat_position = {"node_id": "room_a", "x_ft": 0, "y_ft": 0}
    state.combatants["pc_1"] = fighter
    enemy = Combatant(
        key="enemy_1",
        name="Target Dummy",
        side="enemy",
        hp_current=30,
        hp_max=30,
        ac=10,
        initiative=10,
        stats={"con": 40},
    )
    enemy.combat_position = {"node_id": "room_a", "x_ft": 5, "y_ft": 0}
    state.combatants["enemy_1"] = enemy
    if add_pc_ally:
        ally = Combatant(
            key="pc_ally",
            name="Ally",
            side="pc",
            hp_current=20,
            hp_max=20,
            ac=12,
            initiative=5,
            stats={"str": 50, "dex": 50},
        )
        ally.combat_position = {"node_id": "room_a", "x_ft": 5, "y_ft": 0}
        state.combatants["pc_ally"] = ally
        state.order = ["pc_1", "enemy_1", "pc_ally"]
    else:
        state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0
    state.round_no = 1


def _capture_rolls(monkeypatch, sequence: list[tuple[int, int | None, int]], *, damage_rolls: list[int]) -> None:
    rolls = iter(sequence)

    def _fake_roll(mode: str, rng=None, reroll_ones: bool = False):
        _ = mode
        _ = rng
        _ = reroll_ones
        return next(rolls)

    damage_iter = iter(damage_rolls)
    monkeypatch.setattr("app.combat.live_actions._roll_check_compat", _fake_roll)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(damage_iter))


def test_two_weapon_attack_main_attack_sets_marker_and_bonus_attack_uses_bonus_action(monkeypatch) -> None:
    session_id = "test_two_weapon_attack_main_attack_sets_marker_and_bonus_attack_uses_bonus_action"
    _build_state(session_id, class_features=_fighter_style_features("two_weapon_fighting"))
    _capture_rolls(monkeypatch, [(15, None, 15), (14, None, 14)], damage_rolls=[3, 4])

    try:
        patch_main, err_main = handle_live_combat_action("combat_attack", session_id)
        assert err_main is None
        assert any("Бой двумя оружиями: можно бонусным действием атаковать второй рукой." in t for t in _line_texts(patch_main))
        state = get_combat(session_id)
        assert state is not None
        fighter = state.combatants["pc_1"]
        marker = ((fighter.class_features or {}).get("runtime") or {}).get("two_weapon_bonus_attack") or {}
        assert marker.get("available") is True
        assert fighter.action_available is False
        assert fighter.bonus_action_available is True
        assert state.turn_index == 0

        patch_off, err_off = handle_live_combat_action("combat_two_weapon_attack", session_id)
        assert err_off is None
        texts = _line_texts(patch_off)
        assert any("Бонусная атака второй рукой:" in t for t in texts)
        state = get_combat(session_id)
        assert state is not None
        fighter = state.combatants["pc_1"]
        assert fighter.action_available is False
        assert fighter.bonus_action_available is False
        assert state.turn_index == 0
        marker = ((fighter.class_features or {}).get("runtime") or {}).get("two_weapon_bonus_attack") or {}
        assert marker.get("available") is False
    finally:
        end_combat(session_id)


def test_two_weapon_attack_without_style_omits_positive_damage_mod(monkeypatch) -> None:
    session_id = "test_two_weapon_attack_without_style_omits_positive_damage_mod"
    _build_state(session_id, class_features=_fighter_style_features("defense"))
    _capture_rolls(monkeypatch, [(15, None, 15), (14, None, 14)], damage_rolls=[3, 3])

    try:
        handle_live_combat_action("combat_attack", session_id)
        patch, err = handle_live_combat_action("combat_two_weapon_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("урон второй руки без положительного модификатора" in t for t in texts)
        assert any("Урон: 3 + 0 = 3" in t for t in texts)
    finally:
        end_combat(session_id)


def test_two_weapon_attack_with_style_adds_positive_damage_mod(monkeypatch) -> None:
    session_id = "test_two_weapon_attack_with_style_adds_positive_damage_mod"
    _build_state(session_id, class_features=_fighter_style_features("two_weapon_fighting"))
    _capture_rolls(monkeypatch, [(15, None, 15), (14, None, 14)], damage_rolls=[3, 3])

    try:
        handle_live_combat_action("combat_attack", session_id)
        patch, err = handle_live_combat_action("combat_two_weapon_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("модификатор характеристики добавлен к урону второй руки" in t for t in texts)
        assert any("Урон: 3 + 4 = 7" in t for t in texts)
    finally:
        end_combat(session_id)


def test_two_weapon_attack_negative_mod_applies_without_style(monkeypatch) -> None:
    session_id = "test_two_weapon_attack_negative_mod_applies_without_style"
    _build_state(
        session_id,
        stats={"str": 30, "dex": 30, "con": 50},
        class_features=_fighter_style_features("defense"),
    )
    _capture_rolls(monkeypatch, [(20, None, 20), (15, None, 15)], damage_rolls=[2, 3])

    try:
        handle_live_combat_action("combat_attack", session_id)
        patch, err = handle_live_combat_action("combat_two_weapon_attack", session_id)
        assert err is None
        assert any("Урон: 3 + -2 = 1" in t for t in _line_texts(patch))
    finally:
        end_combat(session_id)


def test_two_weapon_attack_requires_offhand_and_light_weapons(monkeypatch) -> None:
    for session_id, main_def, off_def in [
        ("test_twf_no_offhand", "dagger", None),
        ("test_twf_offhand_shield", "dagger", "shield"),
        ("test_twf_offhand_longsword", "dagger", "longsword"),
        ("test_twf_mainhand_longsword", "longsword", "dagger"),
    ]:
        _build_state(session_id, main_def=main_def, off_def=off_def, class_features=_fighter_style_features("two_weapon_fighting"))
        _capture_rolls(monkeypatch, [(15, None, 15)], damage_rolls=[3])
        try:
            patch_main, err_main = handle_live_combat_action("combat_attack", session_id)
            assert err_main is None
            assert all("Бой двумя оружиями: можно бонусным действием атаковать второй рукой." not in t for t in _line_texts(patch_main))
            patch, err = handle_live_combat_action("combat_two_weapon_attack", session_id)
            assert patch is None
            assert "сначала нужна подходящая атака действием" in str(err or "").lower()
        finally:
            end_combat(session_id)


def test_two_weapon_attack_requires_bonus_action_and_prior_main_attack(monkeypatch) -> None:
    session_id = "test_twf_requires_prior_main_attack"
    _build_state(session_id, class_features=_fighter_style_features("two_weapon_fighting"))
    _capture_rolls(monkeypatch, [(15, None, 15)], damage_rolls=[3])
    try:
        patch, err = handle_live_combat_action("combat_two_weapon_attack", session_id)
        assert patch is None
        assert "сначала нужна подходящая атака действием" in str(err or "").lower()
    finally:
        end_combat(session_id)

    session_id = "test_twf_requires_bonus_action_available"
    _build_state(session_id, class_features=_fighter_style_features("two_weapon_fighting"))
    _capture_rolls(monkeypatch, [(15, None, 15), (14, None, 14)], damage_rolls=[3, 3])
    try:
        handle_live_combat_action("combat_attack", session_id)
        state = get_combat(session_id)
        assert state is not None
        state.combatants["pc_1"].bonus_action_available = False
        patch, err = handle_live_combat_action("combat_two_weapon_attack", session_id)
        assert err is None
        assert any("бонусное действие уже потрачено" in t.lower() for t in _line_texts(patch))
    finally:
        end_combat(session_id)


def test_two_weapon_attack_does_not_duplicate_sneak_attack_same_turn(monkeypatch) -> None:
    session_id = "test_twf_does_not_duplicate_sneak_attack_same_turn"
    _build_state(
        session_id,
        class_features=_fighter_style_and_sneak_features("two_weapon_fighting"),
        add_pc_ally=True,
    )
    _capture_rolls(monkeypatch, [(15, None, 15), (14, None, 14)], damage_rolls=[3, 6, 4])
    try:
        patch_main, err_main = handle_live_combat_action("combat_attack", session_id)
        assert err_main is None
        assert any("Скрытая атака: +6 (1d6)." in t for t in _line_texts(patch_main))
        patch_off, err_off = handle_live_combat_action("combat_two_weapon_attack", session_id)
        assert err_off is None
        texts = _line_texts(patch_off)
        assert all("Скрытая атака:" not in t for t in texts)
    finally:
        end_combat(session_id)


def test_two_weapon_attack_crit_doubles_offhand_weapon_dice(monkeypatch) -> None:
    session_id = "test_twf_crit_doubles_offhand_weapon_dice"
    _build_state(session_id, class_features=_fighter_style_features("defense"))
    _capture_rolls(monkeypatch, [(15, None, 15), (20, None, 20)], damage_rolls=[3, 3])
    try:
        handle_live_combat_action("combat_attack", session_id)
        patch, err = handle_live_combat_action("combat_two_weapon_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("Результат: критическое попадание" in t for t in texts)
        assert any("Урон: 6 + 0 = 6" in t for t in texts)
    finally:
        end_combat(session_id)
