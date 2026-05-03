from __future__ import annotations

from types import SimpleNamespace

from app.rules.character_catalog import CLASS_CATALOG
from app.rules.class_feature_runtime import (
    apply_reliable_talent_to_d20,
    apply_action_surge_usage,
    apply_indomitable_usage,
    apply_second_wind_usage,
    blindsense_range_ft,
    can_use_uncanny_dodge,
    can_use_sneak_attack_this_turn,
    class_feature_saving_throw_proficient,
    get_expertise_targets,
    get_blindsense_mechanics,
    get_cunning_action_mechanics,
    get_evasion_mechanics,
    get_reliable_talent_mechanics,
    get_slippery_mind_mechanics,
    get_sneak_attack_mechanics,
    get_uncanny_dodge_mechanics,
    has_blindsense,
    has_evasion,
    has_reliable_talent,
    has_slippery_mind,
    has_expertise,
    mark_uncanny_dodge_used_for_damage,
    mark_sneak_attack_used,
    mark_failed_save_for_indomitable,
    reset_class_rest_uses,
    sneak_attack_dice_for_level,
)
from app.rules.class_progression import sync_class_features_for_level


class _FixedRng:
    def __init__(self, *values: int):
        self._values = list(values)

    def randint(self, _start: int, _end: int) -> int:
        if not self._values:
            raise AssertionError("No more fixed RNG values")
        return self._values.pop(0)


def _fighter_catalog_entry() -> dict:
    fighter = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "fighter"), None)
    assert fighter is not None
    return fighter


def _rogue_catalog_entry() -> dict:
    rogue = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "rogue"), None)
    assert rogue is not None
    return rogue


def _fighter_second_wind_mechanics() -> dict:
    fighter = _fighter_catalog_entry()
    features = (fighter.get("features_by_level") or {}).get(1) or []
    second_wind = next((item for item in features if str((item or {}).get("key") or "") == "second_wind"), None)
    assert isinstance(second_wind, dict)
    mechanics = second_wind.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_action_surge_mechanics() -> dict:
    fighter = _fighter_catalog_entry()
    features = (fighter.get("features_by_level") or {}).get(2) or []
    action_surge = next((item for item in features if str((item or {}).get("key") or "") == "action_surge"), None)
    assert isinstance(action_surge, dict)
    mechanics = action_surge.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_action_surge_improvement_mechanics() -> dict:
    fighter = _fighter_catalog_entry()
    features = (fighter.get("features_by_level") or {}).get(17) or []
    action_surge_2 = next((item for item in features if str((item or {}).get("key") or "") == "action_surge_2"), None)
    assert isinstance(action_surge_2, dict)
    mechanics = action_surge_2.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_indomitable_mechanics() -> dict:
    fighter = _fighter_catalog_entry()
    features = (fighter.get("features_by_level") or {}).get(9) or []
    indomitable = next((item for item in features if str((item or {}).get("key") or "") == "indomitable_1"), None)
    assert isinstance(indomitable, dict)
    mechanics = indomitable.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_indomitable_improvement_2_mechanics() -> dict:
    fighter = _fighter_catalog_entry()
    features = (fighter.get("features_by_level") or {}).get(13) or []
    indomitable = next((item for item in features if str((item or {}).get("key") or "") == "indomitable_2"), None)
    assert isinstance(indomitable, dict)
    mechanics = indomitable.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_indomitable_improvement_3_mechanics() -> dict:
    fighter = _fighter_catalog_entry()
    features = (fighter.get("features_by_level") or {}).get(17) or []
    indomitable = next((item for item in features if str((item or {}).get("key") or "") == "indomitable_3"), None)
    assert isinstance(indomitable, dict)
    mechanics = indomitable.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _rogue_cunning_action_mechanics() -> dict:
    rogue = _rogue_catalog_entry()
    features = (rogue.get("features_by_level") or {}).get(2) or []
    cunning_action = next((item for item in features if str((item or {}).get("key") or "") == "cunning_action"), None)
    assert isinstance(cunning_action, dict)
    mechanics = cunning_action.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _rogue_sneak_attack_mechanics() -> dict:
    rogue = _rogue_catalog_entry()
    features = (rogue.get("features_by_level") or {}).get(1) or []
    sneak_attack = next((item for item in features if str((item or {}).get("key") or "") == "sneak_attack"), None)
    assert isinstance(sneak_attack, dict)
    mechanics = sneak_attack.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _rogue_expertise_mechanics() -> dict:
    rogue = _rogue_catalog_entry()
    features = (rogue.get("features_by_level") or {}).get(1) or []
    expertise = next((item for item in features if str((item or {}).get("key") or "") == "expertise"), None)
    assert isinstance(expertise, dict)
    mechanics = expertise.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _rogue_expertise_2_mechanics() -> dict:
    rogue = _rogue_catalog_entry()
    features = (rogue.get("features_by_level") or {}).get(6) or []
    expertise = next((item for item in features if str((item or {}).get("key") or "") == "expertise_2"), None)
    assert isinstance(expertise, dict)
    mechanics = expertise.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _rogue_uncanny_dodge_mechanics() -> dict:
    rogue = _rogue_catalog_entry()
    features = (rogue.get("features_by_level") or {}).get(5) or []
    uncanny_dodge = next((item for item in features if str((item or {}).get("key") or "") == "uncanny_dodge"), None)
    assert isinstance(uncanny_dodge, dict)
    mechanics = uncanny_dodge.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _rogue_evasion_mechanics() -> dict:
    rogue = _rogue_catalog_entry()
    features = (rogue.get("features_by_level") or {}).get(7) or []
    evasion = next((item for item in features if str((item or {}).get("key") or "") == "evasion"), None)
    assert isinstance(evasion, dict)
    mechanics = evasion.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _rogue_reliable_talent_mechanics() -> dict:
    rogue = _rogue_catalog_entry()
    features = (rogue.get("features_by_level") or {}).get(11) or []
    reliable_talent = next((item for item in features if str((item or {}).get("key") or "") == "reliable_talent"), None)
    assert isinstance(reliable_talent, dict)
    mechanics = reliable_talent.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _rogue_blindsense_mechanics() -> dict:
    rogue = _rogue_catalog_entry()
    features = (rogue.get("features_by_level") or {}).get(14) or []
    blindsense = next((item for item in features if str((item or {}).get("key") or "") == "blindsense"), None)
    assert isinstance(blindsense, dict)
    mechanics = blindsense.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _rogue_slippery_mind_mechanics() -> dict:
    rogue = _rogue_catalog_entry()
    features = (rogue.get("features_by_level") or {}).get(15) or []
    slippery_mind = next((item for item in features if str((item or {}).get("key") or "") == "slippery_mind"), None)
    assert isinstance(slippery_mind, dict)
    mechanics = slippery_mind.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def test_fighter_second_wind_catalog_has_runtime_mechanics() -> None:
    mechanics = _fighter_second_wind_mechanics()
    assert mechanics == {
        "type": "second_wind",
        "uses": "per_short_or_long_rest",
        "heal_dice": "1d10",
        "heal_bonus": "level",
        "action_cost": "bonus_action",
    }


def test_rogue_cunning_action_catalog_has_runtime_mechanics() -> None:
    mechanics = _rogue_cunning_action_mechanics()
    assert mechanics == {
        "type": "cunning_action",
        "action_cost": "bonus_action",
        "allowed_actions": ["combat_dash", "combat_disengage", "combat_hide"],
    }


def test_rogue_expertise_catalog_has_runtime_mechanics() -> None:
    assert _rogue_expertise_mechanics() == {
        "type": "expertise",
        "count": 2,
        "allowed_kinds": ["skill", "tool"],
        "default_choices": ["stealth", "tool:thieves_tools"],
    }
    assert _rogue_expertise_2_mechanics() == {
        "type": "expertise",
        "count": 2,
        "allowed_kinds": ["skill", "tool"],
        "default_choices": ["perception", "sleight_of_hand"],
    }


def test_rogue_sneak_attack_catalog_has_runtime_mechanics() -> None:
    mechanics = _rogue_sneak_attack_mechanics()
    assert mechanics == {
        "type": "sneak_attack",
        "frequency": "once_per_turn",
        "requires_weapon": True,
        "requires_finesse_or_ranged": True,
        "condition": "advantage_or_adjacent_ally_and_no_disadvantage",
        "damage_progression": [
            {"level_from": 1, "dice": "1d6"},
            {"level_from": 3, "dice": "2d6"},
            {"level_from": 5, "dice": "3d6"},
            {"level_from": 7, "dice": "4d6"},
            {"level_from": 9, "dice": "5d6"},
            {"level_from": 11, "dice": "6d6"},
            {"level_from": 13, "dice": "7d6"},
            {"level_from": 15, "dice": "8d6"},
            {"level_from": 17, "dice": "9d6"},
            {"level_from": 19, "dice": "10d6"},
        ],
    }


def test_rogue_uncanny_dodge_catalog_has_runtime_mechanics() -> None:
    assert _rogue_uncanny_dodge_mechanics() == {
        "type": "uncanny_dodge",
        "trigger": "after_hit_by_attack",
        "cost": "reaction",
        "damage_reduction": "half",
    }


def test_rogue_evasion_catalog_has_runtime_mechanics() -> None:
    assert _rogue_evasion_mechanics() == {
        "type": "evasion",
        "trigger": "dex_save_for_half_damage",
        "success_damage": "none",
        "failure_damage": "half",
    }


def test_rogue_reliable_talent_catalog_has_runtime_mechanics() -> None:
    assert _rogue_reliable_talent_mechanics() == {
        "type": "reliable_talent",
        "min_d20": 10,
        "requires_proficiency": True,
        "applies_to": ["ability_check"],
    }


def test_rogue_blindsense_catalog_has_runtime_mechanics() -> None:
    assert _rogue_blindsense_mechanics() == {
        "type": "blindsense",
        "range_ft": 10,
        "detects": ["hidden", "invisible"],
        "requires_hearing": True,
    }


def test_rogue_slippery_mind_catalog_has_runtime_mechanics() -> None:
    assert _rogue_slippery_mind_mechanics() == {
        "type": "saving_throw_proficiency",
        "ability": "wis",
        "source": "slippery_mind",
    }


def test_sneak_attack_damage_progression_matches_rogue_levels() -> None:
    mechanics = _rogue_sneak_attack_mechanics()
    assert [sneak_attack_dice_for_level(level, mechanics) for level in (1, 3, 5, 7, 9, 11, 13, 15, 17, 19)] == [
        "1d6",
        "2d6",
        "3d6",
        "4d6",
        "5d6",
        "6d6",
        "7d6",
        "8d6",
        "9d6",
        "10d6",
    ]


def test_slippery_mind_runtime_reports_wis_save_proficiency_only() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "slippery_mind",
                    "mechanics": _rogue_slippery_mind_mechanics(),
                }
            ],
            "runtime": {},
        }
    )

    mechanics, err = get_slippery_mind_mechanics(ch)
    assert err is None
    assert mechanics == _rogue_slippery_mind_mechanics()
    assert has_slippery_mind(ch) is True
    assert class_feature_saving_throw_proficient(ch, "wis") is True
    assert class_feature_saving_throw_proficient(ch, "dex") is False
    assert class_feature_saving_throw_proficient(ch, "int") is False
    assert class_feature_saving_throw_proficient(ch, "cha") is False


def test_sync_class_features_for_level_preserves_second_wind_mechanics() -> None:
    fighter = _fighter_catalog_entry()
    class_features = {
        "class_key": "fighter",
        "features_by_level": dict(fighter.get("features_by_level") or {}),
    }

    synced = sync_class_features_for_level(class_features, 1)
    second_wind = next((item for item in synced["features"] if item.get("key") == "second_wind"), None)

    assert isinstance(second_wind, dict)
    assert second_wind.get("mechanics") == _fighter_second_wind_mechanics()


def test_sync_class_features_for_level_preserves_action_surge_mechanics() -> None:
    fighter = _fighter_catalog_entry()
    class_features = {
        "class_key": "fighter",
        "features_by_level": dict(fighter.get("features_by_level") or {}),
    }

    synced = sync_class_features_for_level(class_features, 17)
    action_surge = next((item for item in synced["features"] if item.get("key") == "action_surge"), None)
    action_surge_2 = next((item for item in synced["features"] if item.get("key") == "action_surge_2"), None)

    assert isinstance(action_surge, dict)
    assert action_surge.get("mechanics") == _fighter_action_surge_mechanics()
    assert isinstance(action_surge_2, dict)
    assert action_surge_2.get("mechanics") == _fighter_action_surge_improvement_mechanics()


def test_apply_second_wind_usage_heals_and_blocks_repeat_until_rest() -> None:
    ch = SimpleNamespace(
        name="Fighter",
        level=4,
        hp=5,
        hp_max=20,
        class_features={
            "features": [
                {
                    "key": "second_wind",
                    "name_ru": "Второе дыхание",
                    "mechanics": _fighter_second_wind_mechanics(),
                }
            ],
            "runtime": {},
        },
    )

    healed_1, err_1, changed_1 = apply_second_wind_usage(ch, rng=_FixedRng(6))
    assert err_1 is None
    assert healed_1 == 10
    assert changed_1 is True
    assert ch.hp == 15
    runtime_after_first = (ch.class_features or {}).get("runtime") or {}
    assert runtime_after_first.get("second_wind_used") is True

    healed_2, err_2, changed_2 = apply_second_wind_usage(ch, rng=_FixedRng(3))
    assert healed_2 is None
    assert err_2 is not None
    assert "короткого или долгого отдыха" in err_2
    assert changed_2 is False
    assert ch.hp == 15


def test_reset_class_rest_uses_supports_short_and_long_rest_and_empty_runtime() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "second_wind",
                    "mechanics": _fighter_second_wind_mechanics(),
                }
            ],
            "runtime": {"second_wind_used": True},
        }
    )

    short_changed = reset_class_rest_uses(ch, long_rest=False)
    assert short_changed is True
    runtime_after_short = (ch.class_features or {}).get("runtime") or {}
    assert "second_wind_used" not in runtime_after_short

    ch.class_features["runtime"] = {"second_wind_used": True}
    long_changed = reset_class_rest_uses(ch, long_rest=True)
    assert long_changed is True
    runtime_after_long = (ch.class_features or {}).get("runtime") or {}
    assert "second_wind_used" not in runtime_after_long

    empty_runtime_char = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "second_wind",
                    "mechanics": _fighter_second_wind_mechanics(),
                }
            ],
            "runtime": {},
        }
    )
    assert reset_class_rest_uses(empty_runtime_char, long_rest=False) is False


def test_action_surge_usage_blocks_repeat_until_short_rest() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "action_surge",
                    "mechanics": _fighter_action_surge_mechanics(),
                }
            ],
            "runtime": {},
        }
    )

    ok_1, err_1, changed_1 = apply_action_surge_usage(ch)
    assert ok_1 is True
    assert err_1 is None
    assert changed_1 is True
    runtime_after_first = (ch.class_features or {}).get("runtime") or {}
    assert int(runtime_after_first.get("action_surge_used") or 0) == 1

    ok_2, err_2, changed_2 = apply_action_surge_usage(ch)
    assert ok_2 is None
    assert err_2 is not None
    assert "короткого или долгого отдыха" in err_2
    assert changed_2 is False

    reset_changed = reset_class_rest_uses(ch, long_rest=False)
    assert reset_changed is True
    runtime_after_reset = (ch.class_features or {}).get("runtime") or {}
    assert "action_surge_used" not in runtime_after_reset


def test_action_surge_improvement_allows_two_uses_before_rest() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "action_surge",
                    "mechanics": _fighter_action_surge_mechanics(),
                },
                {
                    "key": "action_surge_2",
                    "mechanics": _fighter_action_surge_improvement_mechanics(),
                },
            ],
            "runtime": {},
        }
    )

    ok_1, err_1, changed_1 = apply_action_surge_usage(ch)
    assert ok_1 is True
    assert err_1 is None
    assert changed_1 is True

    ok_2, err_2, changed_2 = apply_action_surge_usage(ch)
    assert ok_2 is True
    assert err_2 is None
    assert changed_2 is True
    runtime_after_second = (ch.class_features or {}).get("runtime") or {}
    assert int(runtime_after_second.get("action_surge_used") or 0) == 2

    ok_3, err_3, changed_3 = apply_action_surge_usage(ch)
    assert ok_3 is None
    assert err_3 is not None
    assert "короткого или долгого отдыха" in err_3
    assert changed_3 is False


def test_indomitable_unavailable_without_feature() -> None:
    ch = SimpleNamespace(class_features={"features": [], "runtime": {}})
    changed = mark_failed_save_for_indomitable(
        ch,
        ability="wis",
        vs_tag="frightened",
        dc=15,
        total=12,
        mode="normal",
        mod=2,
    )
    assert changed is False

    payload, err, runtime_changed = apply_indomitable_usage(ch, rng=_FixedRng(18))
    assert payload is None
    assert err == "Несгибаемый недоступен вашему классу."
    assert runtime_changed is False


def test_indomitable_level_9_allows_one_use_until_long_rest() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [{"key": "indomitable_1", "mechanics": _fighter_indomitable_mechanics()}],
            "runtime": {},
        }
    )

    marked = mark_failed_save_for_indomitable(
        ch,
        ability="wis",
        vs_tag="frightened",
        dc=15,
        total=12,
        mode="normal",
        mod=2,
    )
    assert marked is True

    payload_1, err_1, changed_1 = apply_indomitable_usage(ch, rng=_FixedRng(17))
    assert isinstance(payload_1, dict)
    assert err_1 is None
    assert changed_1 is True
    runtime_after_first = (ch.class_features or {}).get("runtime") or {}
    assert int(runtime_after_first.get("indomitable_used") or 0) == 1
    assert "indomitable_pending_failed_save" not in runtime_after_first

    mark_failed_save_for_indomitable(
        ch,
        ability="wis",
        vs_tag="frightened",
        dc=15,
        total=12,
        mode="normal",
        mod=2,
    )
    payload_2, err_2, changed_2 = apply_indomitable_usage(ch, rng=_FixedRng(14))
    assert payload_2 is None
    assert err_2 == "Несгибаемый уже использован до долгого отдыха."
    assert changed_2 is False


def test_indomitable_level_13_allows_two_uses_until_long_rest() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {"key": "indomitable_1", "mechanics": _fighter_indomitable_mechanics()},
                {"key": "indomitable_2", "mechanics": _fighter_indomitable_improvement_2_mechanics()},
            ],
            "runtime": {},
        }
    )

    for expected_used, roll in ((1, 16), (2, 15)):
        mark_failed_save_for_indomitable(
            ch,
            ability="con",
            vs_tag="poison",
            dc=14,
            total=11,
            mode="normal",
            mod=3,
        )
        payload, err, changed = apply_indomitable_usage(ch, rng=_FixedRng(roll))
        assert isinstance(payload, dict)
        assert err is None
        assert changed is True
        runtime_now = (ch.class_features or {}).get("runtime") or {}
        assert int(runtime_now.get("indomitable_used") or 0) == expected_used

    mark_failed_save_for_indomitable(
        ch,
        ability="con",
        vs_tag="poison",
        dc=14,
        total=11,
        mode="normal",
        mod=3,
    )
    payload_3, err_3, changed_3 = apply_indomitable_usage(ch, rng=_FixedRng(18))
    assert payload_3 is None
    assert err_3 == "Несгибаемый уже использован до долгого отдыха."
    assert changed_3 is False


def test_indomitable_level_17_allows_three_uses_until_long_rest() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {"key": "indomitable_1", "mechanics": _fighter_indomitable_mechanics()},
                {"key": "indomitable_2", "mechanics": _fighter_indomitable_improvement_2_mechanics()},
                {"key": "indomitable_3", "mechanics": _fighter_indomitable_improvement_3_mechanics()},
            ],
            "runtime": {},
        }
    )

    for expected_used, roll in ((1, 15), (2, 16), (3, 17)):
        mark_failed_save_for_indomitable(
            ch,
            ability="str",
            vs_tag="",
            dc=13,
            total=10,
            mode="normal",
            mod=2,
        )
        payload, err, changed = apply_indomitable_usage(ch, rng=_FixedRng(roll))
        assert isinstance(payload, dict)
        assert err is None
        assert changed is True
        runtime_now = (ch.class_features or {}).get("runtime") or {}
        assert int(runtime_now.get("indomitable_used") or 0) == expected_used

    mark_failed_save_for_indomitable(
        ch,
        ability="str",
        vs_tag="",
        dc=13,
        total=10,
        mode="normal",
        mod=2,
    )
    payload_4, err_4, changed_4 = apply_indomitable_usage(ch, rng=_FixedRng(19))
    assert payload_4 is None
    assert err_4 == "Несгибаемый уже использован до долгого отдыха."
    assert changed_4 is False


def test_indomitable_long_rest_resets_used_and_pending_but_short_rest_does_not() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [{"key": "indomitable_1", "mechanics": _fighter_indomitable_mechanics()}],
            "runtime": {
                "indomitable_used": 1,
                "indomitable_pending_failed_save": {
                    "ability": "wis",
                    "dc": 15,
                    "old_total": 12,
                    "mode": "normal",
                    "mod": 2,
                    "bonus_total": 0,
                    "bonus_texts": [],
                },
            },
        }
    )

    short_changed = reset_class_rest_uses(ch, long_rest=False)
    assert short_changed is False
    runtime_after_short = (ch.class_features or {}).get("runtime") or {}
    assert int(runtime_after_short.get("indomitable_used") or 0) == 1
    assert "indomitable_pending_failed_save" in runtime_after_short

    long_changed = reset_class_rest_uses(ch, long_rest=True)
    assert long_changed is True
    runtime_after_long = (ch.class_features or {}).get("runtime") or {}
    assert "indomitable_used" not in runtime_after_long
    assert "indomitable_pending_failed_save" not in runtime_after_long


def test_get_cunning_action_mechanics_returns_error_without_feature() -> None:
    mechanics, err = get_cunning_action_mechanics(SimpleNamespace(class_features={"features": [], "runtime": {}}))
    assert mechanics == {}
    assert err == "Хитрое действие недоступно вашему классу."


def test_get_cunning_action_mechanics_finds_rogue_feature() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "cunning_action",
                    "mechanics": _rogue_cunning_action_mechanics(),
                }
            ],
            "runtime": {},
        }
    )
    mechanics, err = get_cunning_action_mechanics(ch)
    assert err is None
    assert mechanics == _rogue_cunning_action_mechanics()


def test_get_sneak_attack_mechanics_returns_error_without_feature() -> None:
    mechanics, err = get_sneak_attack_mechanics(SimpleNamespace(class_features={"features": [], "runtime": {}}))
    assert mechanics == {}
    assert err == "Скрытая атака недоступна вашему классу."


def test_get_uncanny_dodge_mechanics_returns_error_without_feature() -> None:
    mechanics, err = get_uncanny_dodge_mechanics(SimpleNamespace(class_features={"features": [], "runtime": {}}))
    assert mechanics == {}
    assert err == "Невероятное уклонение недоступно вашему классу."


def test_get_evasion_mechanics_returns_error_without_feature() -> None:
    mechanics, err = get_evasion_mechanics(SimpleNamespace(class_features={"features": [], "runtime": {}}))
    assert mechanics == {}
    assert err == "Увёртливость недоступна вашему классу."


def test_get_reliable_talent_mechanics_returns_error_without_feature() -> None:
    mechanics, err = get_reliable_talent_mechanics(SimpleNamespace(class_features={"features": [], "runtime": {}}))
    assert mechanics == {}
    assert err == "Надёжный талант недоступен вашему классу."


def test_get_blindsense_mechanics_returns_error_without_feature() -> None:
    mechanics, err = get_blindsense_mechanics(SimpleNamespace(class_features={"features": [], "runtime": {}}))
    assert mechanics == {}
    assert err == "Слепое чутьё недоступно вашему классу."


def test_has_evasion_detects_rogue_feature() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "evasion",
                    "mechanics": _rogue_evasion_mechanics(),
                }
            ],
            "runtime": {},
        }
    )
    mechanics, err = get_evasion_mechanics(ch)
    assert err is None
    assert mechanics == _rogue_evasion_mechanics()
    assert has_evasion(ch) is True


def test_reliable_talent_applies_only_to_proficient_checks() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "reliable_talent",
                    "mechanics": _rogue_reliable_talent_mechanics(),
                }
            ],
            "runtime": {},
        }
    )
    assert has_reliable_talent(ch) is True
    assert apply_reliable_talent_to_d20(ch, kind="skill", roll=3, proficient=True) == (10, True)
    assert apply_reliable_talent_to_d20(ch, kind="tool", roll=9, proficient=True) == (10, True)
    assert apply_reliable_talent_to_d20(ch, kind="skill", roll=3, proficient=False) == (3, False)
    assert apply_reliable_talent_to_d20(ch, kind="save", roll=3, proficient=True) == (3, False)
    assert apply_reliable_talent_to_d20(ch, kind="attack", roll=3, proficient=True) == (3, False)


def test_blindsense_helpers_detect_feature_and_range() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "blindsense",
                    "mechanics": _rogue_blindsense_mechanics(),
                }
            ],
            "runtime": {},
        }
    )
    mechanics, err = get_blindsense_mechanics(ch)
    assert err is None
    assert mechanics == _rogue_blindsense_mechanics()
    assert has_blindsense(ch) is True
    assert blindsense_range_ft(ch) == 10


def test_uncanny_dodge_runtime_marks_damage_key_once() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "uncanny_dodge",
                    "mechanics": _rogue_uncanny_dodge_mechanics(),
                }
            ],
            "runtime": {},
        }
    )

    mechanics_1, err_1 = can_use_uncanny_dodge(ch, damage_key="round:1|source:orc|damage:9")
    assert err_1 is None
    assert mechanics_1 == _rogue_uncanny_dodge_mechanics()
    assert mark_uncanny_dodge_used_for_damage(ch, "round:1|source:orc|damage:9") is True

    _mechanics_2, err_2 = can_use_uncanny_dodge(ch, damage_key="round:1|source:orc|damage:9")
    assert err_2 == "Невероятное уклонение уже применено к этому урону."

    mechanics_3, err_3 = can_use_uncanny_dodge(ch, damage_key="round:1|source:goblin|damage:4")
    assert err_3 is None
    assert mechanics_3 == _rogue_uncanny_dodge_mechanics()


def test_sneak_attack_once_per_turn_runtime_uses_turn_id() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {
                    "key": "sneak_attack",
                    "mechanics": _rogue_sneak_attack_mechanics(),
                }
            ],
            "runtime": {},
        }
    )

    mechanics_1, err_1 = can_use_sneak_attack_this_turn(ch, turn_id="round:1:turn:0:actor:pc_1")
    assert err_1 is None
    assert mechanics_1 == _rogue_sneak_attack_mechanics()
    assert mark_sneak_attack_used(ch, turn_id="round:1:turn:0:actor:pc_1") is True

    _mechanics_2, err_2 = can_use_sneak_attack_this_turn(ch, turn_id="round:1:turn:0:actor:pc_1")
    assert err_2 == "Скрытая атака уже использована в этот ход."

    mechanics_3, err_3 = can_use_sneak_attack_this_turn(ch, turn_id="round:1:turn:1:actor:enemy_1")
    assert err_3 is None
    assert mechanics_3 == _rogue_sneak_attack_mechanics()


def test_get_expertise_targets_uses_rogue_default_choices() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {"key": "expertise", "mechanics": _rogue_expertise_mechanics()},
                {"key": "expertise_2", "mechanics": _rogue_expertise_2_mechanics()},
            ],
            "runtime": {},
        }
    )

    targets = get_expertise_targets(ch)
    assert targets == {
        "skill": {"stealth", "perception", "sleight_of_hand"},
        "tool": {"thieves_tools"},
    }
    assert has_expertise(ch, "skill", "stealth") is True
    assert has_expertise(ch, "tool", "thieves_tools") is True


def test_get_expertise_targets_prefers_explicit_choices_over_defaults() -> None:
    ch = SimpleNamespace(
        class_features={
            "features": [
                {"key": "expertise", "mechanics": _rogue_expertise_mechanics()},
                {"key": "expertise_2", "mechanics": _rogue_expertise_2_mechanics()},
            ],
            "choices": {
                "expertise": [
                    "stealth",
                    "tool:thieves_tools",
                    {"kind": "skill", "key": "acrobatics"},
                ]
            },
            "runtime": {},
        }
    )

    targets = get_expertise_targets(ch)
    assert targets == {
        "skill": {"stealth", "acrobatics"},
        "tool": {"thieves_tools"},
    }
    assert has_expertise(ch, "skill", "perception") is False
