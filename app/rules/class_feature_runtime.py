from __future__ import annotations

import random
import re
from typing import Any


_SECOND_WIND_RUNTIME_KEY = "second_wind_used"
_SECOND_WIND_MECHANIC_TYPE = "second_wind"
_ACTION_SURGE_RUNTIME_KEY = "action_surge_used"
_ACTION_SURGE_MECHANIC_TYPE = "action_surge"
_ACTION_SURGE_IMPROVEMENT_TYPE = "action_surge_improvement"


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _class_features_dict(ch: Any) -> dict[str, Any]:
    class_features_raw = getattr(ch, "class_features", None)
    return dict(class_features_raw) if isinstance(class_features_raw, dict) else {}


def _class_feature_entries(class_features: dict[str, Any]) -> list[dict[str, Any]]:
    features_raw = class_features.get("features")
    if not isinstance(features_raw, list):
        return []
    return [entry for entry in features_raw if isinstance(entry, dict)]


def find_class_feature_entry(
    class_features: dict[str, Any] | Any,
    *,
    feature_key: str = "",
    mechanic_type: str = "",
) -> dict[str, Any] | None:
    src = class_features if isinstance(class_features, dict) else _class_features_dict(class_features)
    expected_key = str(feature_key or "").strip().lower()
    expected_type = str(mechanic_type or "").strip().lower()

    for entry in _class_feature_entries(src):
        key = str(entry.get("key") or "").strip().lower()
        mechanics_raw = entry.get("mechanics")
        mechanics = mechanics_raw if isinstance(mechanics_raw, dict) else {}
        runtime_type = str(mechanics.get("type") or "").strip().lower()
        if expected_key and key == expected_key:
            return entry
        if expected_type and runtime_type == expected_type:
            return entry
    return None


def get_class_feature_mechanics(
    ch: Any,
    *,
    feature_key: str = "",
    mechanic_type: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    class_features = _class_features_dict(ch)
    entry = find_class_feature_entry(
        class_features,
        feature_key=feature_key,
        mechanic_type=mechanic_type,
    )
    mechanics_raw = (entry or {}).get("mechanics")
    mechanics = dict(mechanics_raw) if isinstance(mechanics_raw, dict) else {}
    return class_features, mechanics


def get_class_feature_runtime(ch: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    class_features = _class_features_dict(ch)
    runtime_raw = class_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    return class_features, runtime


def _store_class_feature_runtime(ch: Any, class_features: dict[str, Any], runtime: dict[str, Any]) -> None:
    if runtime:
        class_features["runtime"] = runtime
    else:
        class_features.pop("runtime", None)
    ch.class_features = class_features


def apply_second_wind_usage(ch: Any, *, rng: Any = None) -> tuple[int | None, str | None, bool]:
    class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="second_wind",
        mechanic_type=_SECOND_WIND_MECHANIC_TYPE,
    )
    if not mechanics:
        return None, "Второе дыхание недоступно вашему классу.", False

    runtime_raw = class_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    uses = str(mechanics.get("uses") or "").strip().lower()
    if uses == "per_short_or_long_rest" and bool(runtime.get(_SECOND_WIND_RUNTIME_KEY)):
        return None, "Второе дыхание уже использовано до короткого или долгого отдыха.", False

    heal_dice = str(mechanics.get("heal_dice") or "1d10").strip().lower()
    match = re.fullmatch(r"(\d+)d(\d+)", heal_dice)
    if match:
        dice_count = max(1, _as_int(match.group(1), 1))
        dice_sides = max(1, _as_int(match.group(2), 10))
    else:
        dice_count = 1
        dice_sides = 10

    roller = rng if rng is not None else random
    heal_from_dice = sum(max(1, int(roller.randint(1, dice_sides))) for _ in range(dice_count))
    level = max(1, _as_int(getattr(ch, "level", 1), 1))
    heal_bonus_raw = str(mechanics.get("heal_bonus") or "").strip().lower()
    heal_bonus = level if heal_bonus_raw == "level" else max(0, _as_int(heal_bonus_raw, 0))
    heal = max(0, heal_from_dice + heal_bonus)

    hp_before = max(0, _as_int(getattr(ch, "hp", 0), 0))
    hp_max = max(0, _as_int(getattr(ch, "hp_max", 0), 0))
    hp_after = min(hp_max, hp_before + heal)
    ch.hp = hp_after

    changed = hp_after != hp_before
    if uses == "per_short_or_long_rest":
        if not bool(runtime.get(_SECOND_WIND_RUNTIME_KEY)):
            runtime[_SECOND_WIND_RUNTIME_KEY] = True
            changed = True
        _store_class_feature_runtime(ch, class_features, runtime)

    return max(0, hp_after - hp_before), None, changed


def _action_surge_uses_max(class_features: dict[str, Any], mechanics: dict[str, Any]) -> int:
    uses_max = max(1, _as_int(mechanics.get("uses_max"), 1))
    improvement = find_class_feature_entry(
        class_features,
        feature_key="action_surge_2",
        mechanic_type=_ACTION_SURGE_IMPROVEMENT_TYPE,
    )
    improvement_mechanics_raw = (improvement or {}).get("mechanics")
    improvement_mechanics = dict(improvement_mechanics_raw) if isinstance(improvement_mechanics_raw, dict) else {}
    uses_bonus = max(0, _as_int(improvement_mechanics.get("uses_max_bonus"), 0))
    return uses_max + uses_bonus


def apply_action_surge_usage(ch: Any) -> tuple[bool | None, str | None, bool]:
    class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="action_surge",
        mechanic_type=_ACTION_SURGE_MECHANIC_TYPE,
    )
    if not mechanics:
        return None, "Всплеск действий недоступен вашему классу.", False

    runtime_raw = class_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    uses = str(mechanics.get("uses") or "").strip().lower()
    uses_max = _action_surge_uses_max(class_features, mechanics)
    used = max(0, _as_int(runtime.get(_ACTION_SURGE_RUNTIME_KEY), 0))
    if uses == "per_short_or_long_rest" and used >= uses_max:
        return None, "Всплеск действий уже использован до короткого или долгого отдыха.", False

    runtime[_ACTION_SURGE_RUNTIME_KEY] = used + 1
    _store_class_feature_runtime(ch, class_features, runtime)
    return True, None, True


def reset_class_rest_uses(ch: Any, *, long_rest: bool = True) -> bool:
    class_features, runtime = get_class_feature_runtime(ch)
    if not runtime:
        return False

    changed = False
    second_wind_entry = find_class_feature_entry(
        class_features,
        feature_key="second_wind",
        mechanic_type=_SECOND_WIND_MECHANIC_TYPE,
    )
    second_wind_mechanics_raw = (second_wind_entry or {}).get("mechanics")
    second_wind_mechanics = dict(second_wind_mechanics_raw) if isinstance(second_wind_mechanics_raw, dict) else {}
    second_wind_uses = str(second_wind_mechanics.get("uses") or "").strip().lower()
    should_reset_second_wind = long_rest or second_wind_uses == "per_short_or_long_rest"
    if should_reset_second_wind and _SECOND_WIND_RUNTIME_KEY in runtime:
        runtime.pop(_SECOND_WIND_RUNTIME_KEY, None)
        changed = True

    action_surge_entry = find_class_feature_entry(
        class_features,
        feature_key="action_surge",
        mechanic_type=_ACTION_SURGE_MECHANIC_TYPE,
    )
    action_surge_mechanics_raw = (action_surge_entry or {}).get("mechanics")
    action_surge_mechanics = dict(action_surge_mechanics_raw) if isinstance(action_surge_mechanics_raw, dict) else {}
    action_surge_uses = str(action_surge_mechanics.get("uses") or "").strip().lower()
    should_reset_action_surge = long_rest or action_surge_uses == "per_short_or_long_rest"
    if should_reset_action_surge and _ACTION_SURGE_RUNTIME_KEY in runtime:
        runtime.pop(_ACTION_SURGE_RUNTIME_KEY, None)
        changed = True

    if not changed:
        return False

    _store_class_feature_runtime(ch, class_features, runtime)
    return True
