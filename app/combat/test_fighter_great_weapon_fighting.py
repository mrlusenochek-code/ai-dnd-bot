from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.rules.item_catalog import ITEMS
from app.rules.items import EquipSpec, ItemDef, ItemKind, WeaponStats


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
                    "implemented_styles": ["archery", "defense", "dueling", "great_weapon_fighting"],
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
    item_def_key: str,
    class_features: dict,
    inventory_entry: dict | None = None,
) -> None:
    state = start_combat(session_id)
    entry = {"id": "w1", "def": item_def_key, "name": item_def_key, "qty": 1}
    if isinstance(inventory_entry, dict):
        entry.update(inventory_entry)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=40,
        hp_max=40,
        ac=16,
        initiative=20,
        level=5,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 50, "dex": 50, "con": 50},
        inventory=[entry],
        equip={"main_hand": "w1", "ranged": "w1"},
        class_features=class_features,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Target Dummy",
        side="enemy",
        hp_current=50,
        hp_max=50,
        ac=10,
        initiative=10,
        stats={"con": 40},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0
    state.round_no = 1


def _patch_test_weapon(monkeypatch, *, key: str, damage_dice: str, properties: tuple[str, ...], two_handed: bool) -> None:
    monkeypatch.setitem(
        ITEMS,
        key,
        ItemDef(
            key=key,
            name_ru=key,
            kind=ItemKind.weapon,
            equip=EquipSpec(
                allowed_slots=tuple(),
                two_handed=two_handed,
                wear_group="weapon",
                weapon=WeaponStats(
                    damage_dice=damage_dice,
                    damage_type="slashing",
                    properties=properties,
                ),
            ),
        ),
    )


def _sequence_randint(seq: list[int]):
    values = iter(seq)

    def _randint(_low: int, _high: int) -> int:
        try:
            return next(values)
        except StopIteration as exc:  # pragma: no cover - guard for accidental extra rerolls
            raise AssertionError("Unexpected extra randint call") from exc

    return _randint


def test_great_weapon_fighting_rerolls_melee_two_handed_damage_die(monkeypatch) -> None:
    session_id = "test_great_weapon_fighting_rerolls_melee_two_handed_damage_die"
    _patch_test_weapon(monkeypatch, key="test_greataxe", damage_dice="1d12", properties=("two-handed",), two_handed=True)
    _build_state(session_id, item_def_key="test_greataxe", class_features=_fighter_style_features("great_weapon_fighting"))
    monkeypatch.setattr("app.combat.live_actions.random.randint", _sequence_randint([15, 1, 5]))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("Сражение большим оружием: переброс кости урона 1→5." in text for text in texts)
        assert any("Урон: 5 + 0 = 5" in text for text in texts)
    finally:
        end_combat(session_id)


def test_great_weapon_fighting_rerolls_two_and_keeps_one_on_reroll(monkeypatch) -> None:
    session_id = "test_great_weapon_fighting_rerolls_two_and_keeps_one_on_reroll"
    _patch_test_weapon(monkeypatch, key="test_greataxe_two", damage_dice="1d12", properties=("two-handed",), two_handed=True)
    _build_state(session_id, item_def_key="test_greataxe_two", class_features=_fighter_style_features("great_weapon_fighting"))
    monkeypatch.setattr("app.combat.live_actions.random.randint", _sequence_randint([15, 2, 1]))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert any("Сражение большим оружием: переброс кости урона 2→1." in text for text in texts)
        assert any("Урон: 1 + 0 = 1" in text for text in texts)
    finally:
        end_combat(session_id)


def test_great_weapon_fighting_crit_rerolls_each_weapon_die_once(monkeypatch) -> None:
    session_id = "test_great_weapon_fighting_crit_rerolls_each_weapon_die_once"
    _patch_test_weapon(monkeypatch, key="test_greataxe_crit", damage_dice="1d12", properties=("two-handed",), two_handed=True)
    _build_state(session_id, item_def_key="test_greataxe_crit", class_features=_fighter_style_features("great_weapon_fighting"))
    monkeypatch.setattr("app.combat.live_actions.random.randint", _sequence_randint([20, 1, 5, 2, 6]))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert sum(1 for text in texts if "Сражение большим оружием:" in text) == 2
        assert any("Результат: критическое попадание" in text for text in texts)
        assert any("Урон: 11 + 0 = 11" in text for text in texts)
    finally:
        end_combat(session_id)


def test_great_weapon_fighting_does_not_reroll_ranged_or_one_handed_weapon(monkeypatch) -> None:
    ranged_session = "test_great_weapon_fighting_does_not_reroll_ranged"
    _build_state(ranged_session, item_def_key="shortbow", class_features=_fighter_style_features("great_weapon_fighting"))
    monkeypatch.setattr("app.combat.live_actions.random.randint", _sequence_randint([15, 1]))

    try:
        patch, err = handle_live_combat_action("combat_attack", ranged_session)
        assert err is None
        texts = _line_texts(patch)
        assert all("Сражение большим оружием:" not in text for text in texts)
        assert any("Урон: 1 + 0 = 1" in text for text in texts)
    finally:
        end_combat(ranged_session)

    melee_session = "test_great_weapon_fighting_does_not_reroll_one_handed"
    _build_state(melee_session, item_def_key="longsword", class_features=_fighter_style_features("great_weapon_fighting"))
    monkeypatch.setattr("app.combat.live_actions.random.randint", _sequence_randint([15, 1]))

    try:
        patch, err = handle_live_combat_action("combat_attack", melee_session)
        assert err is None
        texts = _line_texts(patch)
        assert all("Сражение большим оружием:" not in text for text in texts)
        assert any("Урон: 1 + 0 = 1" in text for text in texts)
    finally:
        end_combat(melee_session)


def test_great_weapon_fighting_does_not_reroll_sneak_attack_extra_dice(monkeypatch) -> None:
    session_id = "test_great_weapon_fighting_does_not_reroll_sneak_attack_extra_dice"
    _patch_test_weapon(
        monkeypatch,
        key="test_finesse_greatblade",
        damage_dice="1d12",
        properties=("finesse", "two-handed"),
        two_handed=True,
    )
    _build_state(
        session_id,
        item_def_key="test_finesse_greatblade",
        class_features=_fighter_style_and_sneak_features("great_weapon_fighting"),
    )
    state = get_combat(session_id)
    assert state is not None
    state.combatants["pc_1"].help_attack_advantage = True
    monkeypatch.setattr("app.combat.live_actions.random.randint", _sequence_randint([15, 1, 1, 5, 2]))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        texts = _line_texts(patch)
        assert sum(1 for text in texts if "Сражение большим оружием:" in text) == 1
        assert any("Скрытая атака: +2 (1d6)." in text for text in texts)
        assert any("Урон: 5 + 0 = 7" in text for text in texts)
    finally:
        end_combat(session_id)
