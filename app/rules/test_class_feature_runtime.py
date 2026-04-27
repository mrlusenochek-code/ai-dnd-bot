from __future__ import annotations

from types import SimpleNamespace

from app.rules.character_catalog import CLASS_CATALOG
from app.rules.class_feature_runtime import (
    apply_action_surge_usage,
    apply_indomitable_usage,
    apply_second_wind_usage,
    mark_failed_save_for_indomitable,
    reset_class_rest_uses,
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


def test_fighter_second_wind_catalog_has_runtime_mechanics() -> None:
    mechanics = _fighter_second_wind_mechanics()
    assert mechanics == {
        "type": "second_wind",
        "uses": "per_short_or_long_rest",
        "heal_dice": "1d10",
        "heal_bonus": "level",
        "action_cost": "bonus_action",
    }


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
