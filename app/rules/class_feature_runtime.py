from __future__ import annotations

import random
import re
from typing import Any


_SECOND_WIND_RUNTIME_KEY = "second_wind_used"
_SECOND_WIND_MECHANIC_TYPE = "second_wind"
_FIGHTING_STYLE_MECHANIC_TYPE = "fighting_style"
_ACTION_SURGE_RUNTIME_KEY = "action_surge_used"
_ACTION_SURGE_MECHANIC_TYPE = "action_surge"
_ACTION_SURGE_IMPROVEMENT_TYPE = "action_surge_improvement"
_EXTRA_ATTACK_MECHANIC_TYPE = "extra_attack"
_INDOMITABLE_RUNTIME_KEY = "indomitable_used"
_INDOMITABLE_PENDING_KEY = "indomitable_pending_failed_save"
_INDOMITABLE_MECHANIC_TYPE = "indomitable"
_INDOMITABLE_IMPROVEMENT_TYPE = "indomitable_improvement"
_CUNNING_ACTION_MECHANIC_TYPE = "cunning_action"
_SNEAK_ATTACK_RUNTIME_KEY = "sneak_attack_last_turn_id"
_SNEAK_ATTACK_MECHANIC_TYPE = "sneak_attack"
_EXPERTISE_MECHANIC_TYPE = "expertise"
_UNCANNY_DODGE_MECHANIC_TYPE = "uncanny_dodge"
_UNCANNY_DODGE_USED_DAMAGE_KEYS = "uncanny_dodge_used_damage_keys"
_EVASION_MECHANIC_TYPE = "evasion"
_RELIABLE_TALENT_MECHANIC_TYPE = "reliable_talent"
_BLINDSENSE_MECHANIC_TYPE = "blindsense"
_SAVING_THROW_PROFICIENCY_MECHANIC_TYPE = "saving_throw_proficiency"
_ELUSIVE_MECHANIC_TYPE = "elusive"
_STROKE_OF_LUCK_RUNTIME_KEY = "stroke_of_luck_used"
_STROKE_OF_LUCK_PENDING_KEY = "stroke_of_luck_pending_miss"
_STROKE_OF_LUCK_CHECK_PENDING_KEY = "stroke_of_luck_pending_failed_check"
_STROKE_OF_LUCK_MECHANIC_TYPE = "stroke_of_luck"
_ABILITY_SCORE_IMPROVEMENT_MECHANIC_TYPE = "ability_score_improvement"
_CLASS_ASI_CHOICE_KEY = "asi"
_ABILITY_SCORE_KEYS = ("str", "dex", "con", "int", "wis", "cha")
_IMPROVED_CRITICAL_MECHANIC_TYPE = "improved_critical"


def _default_class_asi_mechanics() -> dict[str, Any]:
    return {
        "type": _ABILITY_SCORE_IMPROVEMENT_MECHANIC_TYPE,
        "options": [
            {"kind": "single", "amount": 10, "count": 1},
            {"kind": "split", "amount": 5, "count": 2},
        ],
        "stat_keys": list(_ABILITY_SCORE_KEYS),
        "cap": 100,
    }


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


def _subclass_feature_entries(class_features: dict[str, Any], *, level: int | None = None) -> list[dict[str, Any]]:
    subclass_raw = class_features.get("subclass")
    subclass = subclass_raw if isinstance(subclass_raw, dict) else {}
    features_by_level_raw = subclass.get("features_by_level")
    if not isinstance(features_by_level_raw, dict):
        return []
    max_level = _as_int(level, 0) if level is not None else 0
    entries: list[dict[str, Any]] = []
    for level_key, level_entries_raw in features_by_level_raw.items():
        feature_level = _as_int(level_key, 0)
        if feature_level <= 0:
            continue
        if max_level > 0 and feature_level > max_level:
            continue
        level_entries = level_entries_raw if isinstance(level_entries_raw, list) else []
        for entry in level_entries:
            if not isinstance(entry, dict):
                continue
            normalized = dict(entry)
            normalized["level"] = feature_level
            entries.append(normalized)
    return entries


def _improved_critical_min_roll_for_entry(entry: dict[str, Any]) -> int | None:
    key = str(entry.get("key") or "").strip().lower()
    name = str(entry.get("name") or entry.get("name_ru") or "").strip().lower()
    mechanics_raw = entry.get("mechanics")
    mechanics = mechanics_raw if isinstance(mechanics_raw, dict) else {}
    mechanic_type = str(mechanics.get("type") or "").strip().lower()
    applies_to = str(mechanics.get("applies_to") or "").strip().lower()
    if mechanic_type == _IMPROVED_CRITICAL_MECHANIC_TYPE:
        if applies_to and applies_to != "weapon_attacks":
            return None
        crit_min_roll = _as_int(mechanics.get("crit_min_roll"), 20)
        return max(1, min(20, crit_min_roll))
    if key == "improved_critical" or name == "improved critical" or name == "улучшенный критический удар":
        return 19
    if key == "superior_critical" or name == "superior critical" or name == "превосходный критический удар":
        return 18
    return None


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
    class_features = ch if isinstance(ch, dict) else _class_features_dict(ch)
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


def _class_feature_choices(class_features: dict[str, Any]) -> dict[str, Any]:
    choices_raw = class_features.get("choices")
    return dict(choices_raw) if isinstance(choices_raw, dict) else {}


def _store_class_feature_choices(ch: Any, class_features: dict[str, Any], choices: dict[str, Any]) -> None:
    if choices:
        class_features["choices"] = choices
    else:
        class_features.pop("choices", None)
    ch.class_features = class_features


def _find_class_feature_entry_at_level(
    class_features: dict[str, Any],
    *,
    feature_key: str,
    level: int,
) -> dict[str, Any] | None:
    expected_key = str(feature_key or "").strip().lower()
    expected_level = max(1, _as_int(level, 0))
    if not expected_key or expected_level <= 0:
        return None
    for entry in _class_feature_entries(class_features):
        key = str(entry.get("key") or "").strip().lower()
        entry_level = _as_int(entry.get("level"), 0)
        if key == expected_key and entry_level == expected_level:
            return entry
    return None


def _class_asi_mechanics_for_level(ch: Any, feature_level: int) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    class_features = _class_features_dict(ch)
    entry = _find_class_feature_entry_at_level(
        class_features,
        feature_key="asi",
        level=feature_level,
    )
    mechanics_raw = (entry or {}).get("mechanics")
    mechanics = dict(mechanics_raw) if isinstance(mechanics_raw, dict) else {}
    mechanic_type = str(mechanics.get("type") or "").strip().lower()
    if not entry:
        return class_features, {}, "Улучшение характеристик недоступно на этом уровне."
    if mechanic_type == _ABILITY_SCORE_IMPROVEMENT_MECHANIC_TYPE:
        return class_features, mechanics, None
    return class_features, _default_class_asi_mechanics(), None


def apply_class_asi_choice(ch: Any, feature_level: int, choice: Any) -> dict[str, Any]:
    level = max(1, _as_int(feature_level, 0))
    result: dict[str, Any] = {
        "applied": False,
        "changed": False,
        "level": level,
        "changes": [],
        "reason": None,
        "error": None,
    }
    class_features, mechanics, err = _class_asi_mechanics_for_level(ch, level)
    if err:
        result["reason"] = err
        result["error"] = err
        return result

    stats_raw = getattr(ch, "stats", None)
    stats = dict(stats_raw) if isinstance(stats_raw, dict) else {}
    if not stats:
        err = "У персонажа нет характеристик для применения ASI."
        result["reason"] = err
        result["error"] = err
        return result

    choices = _class_feature_choices(class_features)
    asi_raw = choices.get(_CLASS_ASI_CHOICE_KEY)
    asi_choices = dict(asi_raw) if isinstance(asi_raw, dict) else {}
    level_key = str(level)
    if level_key in asi_choices:
        err = "Улучшение характеристик для этого уровня уже выбрано."
        result["reason"] = err
        result["error"] = err
        return result

    allowed_stats_raw = mechanics.get("stat_keys")
    allowed_stats = {
        str(item or "").strip().lower()
        for item in allowed_stats_raw
        if str(item or "").strip()
    } if isinstance(allowed_stats_raw, list) else set(_ABILITY_SCORE_KEYS)
    if not allowed_stats:
        allowed_stats = set(_ABILITY_SCORE_KEYS)
    cap = max(0, _as_int(mechanics.get("cap"), 100))
    options_raw = mechanics.get("options")
    options = options_raw if isinstance(options_raw, list) else []
    option_by_kind = {
        str((item or {}).get("kind") or "").strip().lower(): item
        for item in options
        if isinstance(item, dict)
    }

    normalized_choice = choice if isinstance(choice, dict) else {}
    mode = str(normalized_choice.get("mode") or "").strip().lower()
    target_stats: list[str]
    option = option_by_kind.get(mode)
    if mode == "single":
        stat = str(normalized_choice.get("stat") or "").strip().lower()
        target_stats = [stat]
    elif mode == "split":
        stats_raw = normalized_choice.get("stats")
        stats_items = stats_raw if isinstance(stats_raw, list) else []
        target_stats = [str(item or "").strip().lower() for item in stats_items]
    else:
        target_stats = []

    if not isinstance(option, dict):
        err = "Некорректный режим ASI."
        result["reason"] = err
        result["error"] = err
        return result

    expected_count = max(1, _as_int(option.get("count"), 1))
    amount = max(0, _as_int(option.get("amount"), 0))
    if len(target_stats) != expected_count:
        err = "Некорректное количество характеристик для ASI."
        result["reason"] = err
        result["error"] = err
        return result
    if any(stat not in allowed_stats for stat in target_stats):
        err = "Некорректная характеристика для ASI."
        result["reason"] = err
        result["error"] = err
        return result
    if mode == "split" and len(set(target_stats)) != len(target_stats):
        err = "Split ASI требует две разные характеристики."
        result["reason"] = err
        result["error"] = err
        return result

    applied_changes: list[dict[str, Any]] = []
    changed = False
    for stat_key in target_stats:
        old_value = max(0, _as_int(stats.get(stat_key), 50))
        new_value = min(cap, old_value + amount)
        stats[stat_key] = new_value
        applied_changes.append(
            {
                "stat": stat_key,
                "old": old_value,
                "new": new_value,
                "delta": new_value - old_value,
            }
        )
        changed = changed or new_value != old_value

    ch.stats = stats
    asi_choices[level_key] = {
        "mode": mode,
        "stat": target_stats[0] if mode == "single" else None,
        "stats": list(target_stats) if mode == "split" else None,
        "changes": applied_changes,
    }
    choices[_CLASS_ASI_CHOICE_KEY] = asi_choices
    _store_class_feature_choices(ch, class_features, choices)

    result["applied"] = True
    result["changed"] = changed
    result["changes"] = applied_changes
    result["choice"] = dict(asi_choices[level_key])
    return result


def get_class_asi_choices(ch: Any) -> dict[str, Any]:
    class_features = _class_features_dict(ch)
    choices = _class_feature_choices(class_features)
    asi_raw = choices.get(_CLASS_ASI_CHOICE_KEY)
    return dict(asi_raw) if isinstance(asi_raw, dict) else {}


def get_pending_class_asi_levels(ch: Any) -> list[int]:
    class_features = _class_features_dict(ch)
    selected = get_class_asi_choices(ch)
    pending: list[int] = []
    for entry in _class_feature_entries(class_features):
        key = str(entry.get("key") or "").strip().lower()
        level = max(1, _as_int(entry.get("level"), 0))
        if key != "asi" or level <= 0:
            continue
        if str(level) in selected:
            continue
        pending.append(level)
    pending.sort()
    return pending


def get_class_asi_options(ch: Any) -> dict[str, Any]:
    class_features = _class_features_dict(ch)
    for entry in _class_feature_entries(class_features):
        key = str(entry.get("key") or "").strip().lower()
        mechanics_raw = entry.get("mechanics")
        mechanics = dict(mechanics_raw) if isinstance(mechanics_raw, dict) else {}
        mechanic_type = str(mechanics.get("type") or "").strip().lower()
        if key != "asi":
            continue
        if mechanic_type == _ABILITY_SCORE_IMPROVEMENT_MECHANIC_TYPE:
            return {
                "stat_keys": list(mechanics.get("stat_keys") or []),
                "cap": max(0, _as_int(mechanics.get("cap"), 100)),
                "options": list(mechanics.get("options") or []),
            }
        return _default_class_asi_mechanics()
    return _default_class_asi_mechanics()


def get_weapon_attack_crit_min_roll(ch: Any, level: int | None = None) -> int:
    class_features = _class_features_dict(ch)
    current_level = _as_int(level, _as_int(getattr(ch, "level", 0), 0))
    crit_min_roll = 20
    for entry in _class_feature_entries(class_features):
        improved_critical_min_roll = _improved_critical_min_roll_for_entry(entry)
        if improved_critical_min_roll is None:
            continue
        crit_min_roll = min(crit_min_roll, improved_critical_min_roll)
    for entry in _subclass_feature_entries(class_features, level=current_level if current_level > 0 else None):
        improved_critical_min_roll = _improved_critical_min_roll_for_entry(entry)
        if improved_critical_min_roll is None:
            continue
        crit_min_roll = min(crit_min_roll, improved_critical_min_roll)
    return crit_min_roll


def get_cunning_action_mechanics(ch: Any) -> tuple[dict[str, Any], str | None]:
    _class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="cunning_action",
        mechanic_type=_CUNNING_ACTION_MECHANIC_TYPE,
    )
    if not mechanics:
        return {}, "Хитрое действие недоступно вашему классу."
    return mechanics, None


def get_fighting_style_mechanics(ch: Any) -> tuple[dict[str, Any], str | None]:
    _class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="fighting_style",
        mechanic_type=_FIGHTING_STYLE_MECHANIC_TYPE,
    )
    if not mechanics:
        return {}, "Стиль боя недоступен вашему классу."
    return mechanics, None


def get_fighting_style_choice(ch: Any) -> str:
    mechanics, err = get_fighting_style_mechanics(ch)
    if err or not mechanics:
        return ""
    allowed_raw = mechanics.get("allowed_styles")
    allowed = {
        str(item or "").strip().lower()
        for item in allowed_raw
        if str(item or "").strip()
    } if isinstance(allowed_raw, list) else set()
    if not allowed:
        return ""
    class_features = ch if isinstance(ch, dict) else _class_features_dict(ch)
    choices_raw = class_features.get("choices")
    choices = dict(choices_raw) if isinstance(choices_raw, dict) else {}
    selected = choices.get(str(mechanics.get("choice_key") or "fighting_style").strip() or "fighting_style")
    if isinstance(selected, str):
        key = selected.strip().lower()
        return key if key in allowed else ""
    if isinstance(selected, dict):
        key = str(selected.get("key") or "").strip().lower()
        return key if key in allowed else ""
    return ""


def has_fighting_style(ch_or_class_features: Any, style_key: str) -> bool:
    expected = str(style_key or "").strip().lower()
    if not expected:
        return False
    return get_fighting_style_choice(ch_or_class_features) == expected


def fighter_has_great_weapon_fighting(ch_or_class_features: Any) -> bool:
    return has_fighting_style(ch_or_class_features, "great_weapon_fighting")


def fighter_has_protection_style(ch_or_class_features: Any) -> bool:
    return has_fighting_style(ch_or_class_features, "protection")


def fighter_has_two_weapon_fighting_style(ch_or_class_features: Any) -> bool:
    return has_fighting_style(ch_or_class_features, "two_weapon_fighting")


def _normalized_expertise_target(raw: Any) -> tuple[str, str] | None:
    if isinstance(raw, str):
        text = raw.strip().lower()
        if not text:
            return None
        if ":" in text:
            kind, key = text.split(":", 1)
            kind = kind.strip().lower()
            key = key.strip().lower()
            if kind in {"skill", "tool"} and key:
                return kind, key
            return None
        return "skill", text
    if isinstance(raw, dict):
        kind = str(raw.get("kind") or "skill").strip().lower()
        key = str(raw.get("key") or "").strip().lower()
        if kind in {"skill", "tool"} and key:
            return kind, key
    return None


def get_expertise_targets(ch: Any) -> dict[str, set[str]]:
    class_features = _class_features_dict(ch)
    out: dict[str, set[str]] = {"skill": set(), "tool": set()}
    choices_raw = class_features.get("choices")
    choices = dict(choices_raw) if isinstance(choices_raw, dict) else {}
    explicit_raw = choices.get("expertise")
    explicit_items = explicit_raw if isinstance(explicit_raw, list) else []
    explicit_targets = [_normalized_expertise_target(item) for item in explicit_items]
    explicit_targets = [item for item in explicit_targets if item is not None]
    if explicit_targets:
        for kind, key in explicit_targets:
            out.setdefault(kind, set()).add(key)
        return out

    for entry in _class_feature_entries(class_features):
        mechanics_raw = entry.get("mechanics")
        mechanics = mechanics_raw if isinstance(mechanics_raw, dict) else {}
        if str(mechanics.get("type") or "").strip().lower() != _EXPERTISE_MECHANIC_TYPE:
            continue
        defaults_raw = mechanics.get("default_choices")
        defaults = defaults_raw if isinstance(defaults_raw, list) else []
        for item in defaults:
            target = _normalized_expertise_target(item)
            if target is None:
                continue
            kind, key = target
            out.setdefault(kind, set()).add(key)
    return out


def has_expertise(ch: Any, kind: str, key: str) -> bool:
    normalized_kind = str(kind or "skill").strip().lower()
    normalized_key = str(key or "").strip().lower()
    if normalized_kind not in {"skill", "tool"} or not normalized_key:
        return False
    targets = get_expertise_targets(ch)
    return normalized_key in targets.get(normalized_kind, set())


def get_sneak_attack_mechanics(ch: Any) -> tuple[dict[str, Any], str | None]:
    _class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="sneak_attack",
        mechanic_type=_SNEAK_ATTACK_MECHANIC_TYPE,
    )
    if not mechanics:
        return {}, "Скрытая атака недоступна вашему классу."
    return mechanics, None


def get_uncanny_dodge_mechanics(ch: Any) -> tuple[dict[str, Any], str | None]:
    _class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="uncanny_dodge",
        mechanic_type=_UNCANNY_DODGE_MECHANIC_TYPE,
    )
    if not mechanics:
        return {}, "Невероятное уклонение недоступно вашему классу."
    return mechanics, None


def get_evasion_mechanics(ch: Any) -> tuple[dict[str, Any], str | None]:
    _class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="evasion",
        mechanic_type=_EVASION_MECHANIC_TYPE,
    )
    if not mechanics:
        return {}, "Увёртливость недоступна вашему классу."
    return mechanics, None


def has_evasion(ch: Any) -> bool:
    mechanics, err = get_evasion_mechanics(ch)
    return bool(mechanics) and err is None


def get_reliable_talent_mechanics(ch: Any) -> tuple[dict[str, Any], str | None]:
    _class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="reliable_talent",
        mechanic_type=_RELIABLE_TALENT_MECHANIC_TYPE,
    )
    if not mechanics:
        return {}, "Надёжный талант недоступен вашему классу."
    return mechanics, None


def has_reliable_talent(ch: Any) -> bool:
    mechanics, err = get_reliable_talent_mechanics(ch)
    return bool(mechanics) and err is None


def apply_reliable_talent_to_d20(
    ch: Any,
    *,
    kind: str,
    roll: int,
    proficient: bool,
) -> tuple[int, bool]:
    mechanics, err = get_reliable_talent_mechanics(ch)
    if err or not mechanics:
        return int(roll), False
    normalized_kind = str(kind or "").strip().lower()
    if normalized_kind not in {"skill", "tool", "ability", "check"}:
        return int(roll), False
    if not bool(proficient):
        return int(roll), False
    min_d20 = max(1, _as_int(mechanics.get("min_d20"), 10))
    normalized_roll = max(1, int(roll))
    if normalized_roll < min_d20:
        return min_d20, True
    return normalized_roll, False


def get_blindsense_mechanics(ch: Any) -> tuple[dict[str, Any], str | None]:
    _class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="blindsense",
        mechanic_type=_BLINDSENSE_MECHANIC_TYPE,
    )
    if not mechanics:
        return {}, "Слепое чутьё недоступно вашему классу."
    return mechanics, None


def has_blindsense(ch: Any) -> bool:
    mechanics, err = get_blindsense_mechanics(ch)
    return bool(mechanics) and err is None


def blindsense_range_ft(ch: Any) -> int:
    mechanics, err = get_blindsense_mechanics(ch)
    if err or not mechanics:
        return 0
    return max(0, _as_int(mechanics.get("range_ft"), 0))


def get_slippery_mind_mechanics(ch: Any) -> tuple[dict[str, Any], str | None]:
    _class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="slippery_mind",
        mechanic_type=_SAVING_THROW_PROFICIENCY_MECHANIC_TYPE,
    )
    if not mechanics:
        return {}, "Скользкий ум недоступен вашему классу."
    return mechanics, None


def has_slippery_mind(ch: Any) -> bool:
    mechanics, err = get_slippery_mind_mechanics(ch)
    return bool(mechanics) and err is None


def class_feature_saving_throw_proficient(ch: Any, ability: str) -> bool:
    normalized_ability = str(ability or "").strip().lower()
    if normalized_ability not in {"str", "dex", "con", "int", "wis", "cha"}:
        return False
    mechanics, err = get_slippery_mind_mechanics(ch)
    if err or not mechanics:
        return False
    mechanic_type = str(mechanics.get("type") or "").strip().lower()
    mechanic_ability = str(mechanics.get("ability") or "").strip().lower()
    return (
        mechanic_type == _SAVING_THROW_PROFICIENCY_MECHANIC_TYPE
        and mechanic_ability == "wis"
        and normalized_ability == "wis"
    )


def get_elusive_mechanics(ch: Any) -> tuple[dict[str, Any], str | None]:
    _class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="elusive",
        mechanic_type=_ELUSIVE_MECHANIC_TYPE,
    )
    if not mechanics:
        return {}, "Ускользание недоступно вашему классу."
    return mechanics, None


def has_elusive(ch: Any) -> bool:
    mechanics, err = get_elusive_mechanics(ch)
    return bool(mechanics) and err is None


def elusive_denies_attack_advantage(ch: Any) -> bool:
    mechanics, err = get_elusive_mechanics(ch)
    if err or not mechanics:
        return False
    return bool(mechanics.get("denies_attack_advantage"))


def get_stroke_of_luck_mechanics(ch: Any) -> tuple[dict[str, Any], str | None]:
    _class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="stroke_of_luck",
        mechanic_type=_STROKE_OF_LUCK_MECHANIC_TYPE,
    )
    if not mechanics:
        return {}, "Удачный удар недоступен вашему классу."
    return mechanics, None


def has_stroke_of_luck(ch: Any) -> bool:
    mechanics, err = get_stroke_of_luck_mechanics(ch)
    return bool(mechanics) and err is None


def can_use_stroke_of_luck(ch: Any) -> tuple[dict[str, Any], str | None]:
    mechanics, err = get_stroke_of_luck_mechanics(ch)
    if err:
        return {}, err
    _class_features, runtime = get_class_feature_runtime(ch)
    if bool(runtime.get(_STROKE_OF_LUCK_RUNTIME_KEY)):
        return mechanics, "Удачный удар уже использован до короткого или долгого отдыха."
    return mechanics, None


def can_use_stroke_of_luck_for_failed_check(ch: Any, *, check_key: str = "", kind: str = "") -> tuple[dict[str, Any], str | None]:
    mechanics, err = can_use_stroke_of_luck(ch)
    if err:
        return mechanics, err
    if not bool(mechanics.get("failed_check_d20_to_20")):
        return mechanics, "Удачный удар не может быть применён к этой проверке."
    normalized_kind = str(kind or "").strip().lower()
    if normalized_kind in {"stat"}:
        normalized_kind = "ability"
    if normalized_kind not in {"ability", "skill", "tool", "check"}:
        return mechanics, "Удачный удар можно применить только к проваленной проверке характеристики, навыка или инструмента."
    return mechanics, None


def mark_stroke_of_luck_check_pending(ch: Any, payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict) or not payload:
        return False
    class_features, runtime = get_class_feature_runtime(ch)
    pending = dict(payload)
    if runtime.get(_STROKE_OF_LUCK_CHECK_PENDING_KEY) == pending:
        return False
    runtime[_STROKE_OF_LUCK_CHECK_PENDING_KEY] = pending
    _store_class_feature_runtime(ch, class_features, runtime)
    return True


def get_stroke_of_luck_check_pending(ch: Any) -> dict[str, Any]:
    _class_features, runtime = get_class_feature_runtime(ch)
    pending_raw = runtime.get(_STROKE_OF_LUCK_CHECK_PENDING_KEY)
    return dict(pending_raw) if isinstance(pending_raw, dict) else {}


def clear_stroke_of_luck_check_pending(ch: Any) -> bool:
    class_features, runtime = get_class_feature_runtime(ch)
    if _STROKE_OF_LUCK_CHECK_PENDING_KEY not in runtime:
        return False
    runtime.pop(_STROKE_OF_LUCK_CHECK_PENDING_KEY, None)
    _store_class_feature_runtime(ch, class_features, runtime)
    return True


def mark_stroke_of_luck_used(ch: Any) -> bool:
    class_features, runtime = get_class_feature_runtime(ch)
    if bool(runtime.get(_STROKE_OF_LUCK_RUNTIME_KEY)):
        return False
    runtime[_STROKE_OF_LUCK_RUNTIME_KEY] = True
    runtime.pop(_STROKE_OF_LUCK_PENDING_KEY, None)
    runtime.pop(_STROKE_OF_LUCK_CHECK_PENDING_KEY, None)
    _store_class_feature_runtime(ch, class_features, runtime)
    return True


def _normalized_damage_key(raw: Any) -> str:
    return str(raw or "").strip()


def can_use_uncanny_dodge(ch: Any, *, damage_key: str) -> tuple[dict[str, Any], str | None]:
    mechanics, err = get_uncanny_dodge_mechanics(ch)
    if err:
        return {}, err
    normalized_damage_key = _normalized_damage_key(damage_key)
    if not normalized_damage_key:
        return mechanics, "Нет подходящего полученного урона для Невероятного уклонения."
    _class_features, runtime = get_class_feature_runtime(ch)
    used_raw = runtime.get(_UNCANNY_DODGE_USED_DAMAGE_KEYS)
    used_items = used_raw if isinstance(used_raw, list) else []
    used = {_normalized_damage_key(item) for item in used_items if _normalized_damage_key(item)}
    if normalized_damage_key in used:
        return mechanics, "Невероятное уклонение уже применено к этому урону."
    return mechanics, None


def mark_uncanny_dodge_used_for_damage(ch: Any, damage_key: str) -> bool:
    normalized_damage_key = _normalized_damage_key(damage_key)
    if not normalized_damage_key:
        return False
    class_features, runtime = get_class_feature_runtime(ch)
    used_raw = runtime.get(_UNCANNY_DODGE_USED_DAMAGE_KEYS)
    used_items = used_raw if isinstance(used_raw, list) else []
    used = [_normalized_damage_key(item) for item in used_items if _normalized_damage_key(item)]
    if normalized_damage_key in used:
        return False
    used.append(normalized_damage_key)
    runtime[_UNCANNY_DODGE_USED_DAMAGE_KEYS] = used
    _store_class_feature_runtime(ch, class_features, runtime)
    return True


def sneak_attack_dice_for_level(level: int, mechanics: dict[str, Any]) -> str:
    lvl = max(1, _as_int(level, 1))
    progression_raw = mechanics.get("damage_progression")
    progression = progression_raw if isinstance(progression_raw, list) else []
    out = "1d6"
    for step in progression:
        if not isinstance(step, dict):
            continue
        level_from = max(1, _as_int(step.get("level_from"), 1))
        dice = str(step.get("dice") or "").strip().lower()
        if not dice:
            continue
        if lvl >= level_from:
            out = dice
    return out


def can_use_sneak_attack_this_turn(ch: Any, *, turn_id: str) -> tuple[dict[str, Any], str | None]:
    mechanics, err = get_sneak_attack_mechanics(ch)
    if err:
        return {}, err
    _class_features, runtime = get_class_feature_runtime(ch)
    last_turn_id = str(runtime.get(_SNEAK_ATTACK_RUNTIME_KEY) or "").strip()
    normalized_turn_id = str(turn_id or "").strip()
    if normalized_turn_id and last_turn_id == normalized_turn_id:
        return mechanics, "Скрытая атака уже использована в этот ход."
    return mechanics, None


def mark_sneak_attack_used(ch: Any, *, turn_id: str) -> bool:
    normalized_turn_id = str(turn_id or "").strip()
    if not normalized_turn_id:
        return False
    class_features, runtime = get_class_feature_runtime(ch)
    if str(runtime.get(_SNEAK_ATTACK_RUNTIME_KEY) or "").strip() == normalized_turn_id:
        return False
    runtime[_SNEAK_ATTACK_RUNTIME_KEY] = normalized_turn_id
    _store_class_feature_runtime(ch, class_features, runtime)
    return True


def _store_class_feature_runtime(ch: Any, class_features: dict[str, Any], runtime: dict[str, Any]) -> None:
    if runtime:
        class_features["runtime"] = runtime
    else:
        class_features.pop("runtime", None)
    ch.class_features = class_features


def _roll_d20_mode(mode: str, *, rng: Any = None) -> tuple[int, int | None, int]:
    roller = rng if rng is not None else random
    normalized = str(mode or "normal").strip().lower()
    if normalized not in {"advantage", "disadvantage"}:
        roll = max(1, int(roller.randint(1, 20)))
        return roll, None, roll
    roll_a = max(1, int(roller.randint(1, 20)))
    roll_b = max(1, int(roller.randint(1, 20)))
    chosen = max(roll_a, roll_b) if normalized == "advantage" else min(roll_a, roll_b)
    return roll_a, roll_b, chosen


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


def get_extra_attack_count(ch: Any) -> int:
    class_features = _class_features_dict(ch)
    best = 1
    for entry in _class_feature_entries(class_features):
        key = str(entry.get("key") or "").strip().lower()
        mechanics_raw = entry.get("mechanics")
        mechanics = mechanics_raw if isinstance(mechanics_raw, dict) else {}
        mechanic_type = str(mechanics.get("type") or "").strip().lower()
        attacks = max(0, _as_int(mechanics.get("attacks"), 0))
        if mechanic_type == _EXTRA_ATTACK_MECHANIC_TYPE and attacks > 0:
            best = max(best, attacks)
            continue
        if key == "extra_attack_3":
            best = max(best, 4)
        elif key == "extra_attack_2":
            best = max(best, 3)
        elif key == "extra_attack":
            best = max(best, 2)
    return max(1, best)


def _indomitable_uses_max(class_features: dict[str, Any], mechanics: dict[str, Any]) -> int:
    uses_max = max(1, _as_int(mechanics.get("uses_max"), 1))
    uses_bonus = 0
    for feature_key in ("indomitable_2", "indomitable_3"):
        improvement = find_class_feature_entry(
            class_features,
            feature_key=feature_key,
        )
        improvement_mechanics_raw = (improvement or {}).get("mechanics")
        improvement_mechanics = dict(improvement_mechanics_raw) if isinstance(improvement_mechanics_raw, dict) else {}
        uses_bonus += max(0, _as_int(improvement_mechanics.get("uses_max_bonus"), 0))
    return uses_max + uses_bonus


def mark_failed_save_for_indomitable(
    ch: Any,
    *,
    ability: str,
    vs_tag: str,
    dc: int,
    total: int,
    mode: str,
    mod: int,
    bonus_total: int = 0,
    bonus_texts: list[str] | None = None,
) -> bool:
    class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="indomitable_1",
        mechanic_type=_INDOMITABLE_MECHANIC_TYPE,
    )
    if not mechanics:
        return False

    runtime_raw = class_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    pending = {
        "kind": "save",
        "ability": str(ability or "").strip().lower(),
        "vs_tag": str(vs_tag or "").strip().lower(),
        "dc": max(0, int(dc)),
        "old_total": int(total),
        "mode": str(mode or "normal").strip().lower() or "normal",
        "mod": int(mod),
        "bonus_total": int(bonus_total),
        "bonus_texts": [str(text) for text in (bonus_texts or []) if str(text).strip()],
    }
    if runtime.get(_INDOMITABLE_PENDING_KEY) == pending:
        return False
    runtime[_INDOMITABLE_PENDING_KEY] = pending
    _store_class_feature_runtime(ch, class_features, runtime)
    return True


def apply_indomitable_usage(ch: Any, *, rng: Any = None) -> tuple[dict[str, Any] | None, str | None, bool]:
    class_features, mechanics = get_class_feature_mechanics(
        ch,
        feature_key="indomitable_1",
        mechanic_type=_INDOMITABLE_MECHANIC_TYPE,
    )
    if not mechanics:
        return None, "Несгибаемый недоступен вашему классу.", False

    runtime_raw = class_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    pending_raw = runtime.get(_INDOMITABLE_PENDING_KEY)
    pending = dict(pending_raw) if isinstance(pending_raw, dict) else {}
    if not pending:
        return None, "Нет проваленного спасброска для «Несгибаемого».", False

    uses = str(mechanics.get("uses") or "").strip().lower()
    uses_max = _indomitable_uses_max(class_features, mechanics)
    used = max(0, _as_int(runtime.get(_INDOMITABLE_RUNTIME_KEY), 0))
    if uses == "per_long_rest" and used >= uses_max:
        return None, "Несгибаемый уже использован до долгого отдыха.", False

    mode = str(pending.get("mode") or "normal").strip().lower() or "normal"
    roll_a, roll_b, new_roll = _roll_d20_mode(mode, rng=rng)
    mod = int(_as_int(pending.get("mod"), 0))
    bonus_total = int(_as_int(pending.get("bonus_total"), 0))
    new_total = int(new_roll + mod + bonus_total)
    dc = max(0, _as_int(pending.get("dc"), 0))

    runtime[_INDOMITABLE_RUNTIME_KEY] = used + 1
    runtime.pop(_INDOMITABLE_PENDING_KEY, None)
    _store_class_feature_runtime(ch, class_features, runtime)

    return {
        "ability": str(pending.get("ability") or "").strip().lower(),
        "vs_tag": str(pending.get("vs_tag") or "").strip().lower(),
        "dc": dc,
        "old_total": int(_as_int(pending.get("old_total"), 0)),
        "mode": mode,
        "roll_a": int(roll_a),
        "roll_b": int(roll_b) if roll_b is not None else None,
        "new_roll": int(new_roll),
        "mod": mod,
        "bonus_total": bonus_total,
        "bonus_texts": [str(text) for text in (pending.get("bonus_texts") or []) if str(text).strip()],
        "new_total": new_total,
        "success": bool(new_total >= dc),
    }, None, True


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

    if long_rest and _INDOMITABLE_RUNTIME_KEY in runtime:
        runtime.pop(_INDOMITABLE_RUNTIME_KEY, None)
        changed = True
    if long_rest and _INDOMITABLE_PENDING_KEY in runtime:
        runtime.pop(_INDOMITABLE_PENDING_KEY, None)
        changed = True
    if _SNEAK_ATTACK_RUNTIME_KEY in runtime:
        runtime.pop(_SNEAK_ATTACK_RUNTIME_KEY, None)
        changed = True
    if _UNCANNY_DODGE_USED_DAMAGE_KEYS in runtime:
        runtime.pop(_UNCANNY_DODGE_USED_DAMAGE_KEYS, None)
        changed = True
    if _STROKE_OF_LUCK_RUNTIME_KEY in runtime:
        runtime.pop(_STROKE_OF_LUCK_RUNTIME_KEY, None)
        changed = True
    if _STROKE_OF_LUCK_PENDING_KEY in runtime:
        runtime.pop(_STROKE_OF_LUCK_PENDING_KEY, None)
        changed = True
    if _STROKE_OF_LUCK_CHECK_PENDING_KEY in runtime:
        runtime.pop(_STROKE_OF_LUCK_CHECK_PENDING_KEY, None)
        changed = True

    if not changed:
        return False

    _store_class_feature_runtime(ch, class_features, runtime)
    return True
