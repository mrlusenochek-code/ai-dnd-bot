from __future__ import annotations

from typing import Any


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_class_feature_entry(entry: Any, *, level: int) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None

    mechanics = entry.get("mechanics")
    mechanics_dict = dict(mechanics) if isinstance(mechanics, dict) else {}

    return {
        "level": level,
        "key": str(entry.get("key") or "").strip().lower(),
        "name_ru": str(entry.get("name_ru") or "").strip(),
        "name": str(entry.get("name") or "").strip(),
        "summary_ru": str(entry.get("summary_ru") or "").strip(),
        "summary": str(entry.get("summary") or "").strip(),
        "mechanics": mechanics_dict,
    }


def sync_class_features_for_level(class_features: Any, level: int) -> dict[str, Any]:
    """
    Rebuild unlocked class features from stored features_by_level up to character level.

    This keeps existing top-level metadata, including selected subclass data.
    Subclass features are stored separately under class_features["subclass"] and are not
    copied into class_features["features"] here.
    """
    if not isinstance(class_features, dict):
        return {}

    result = dict(class_features)
    features_by_level_raw = result.get("features_by_level")
    if not isinstance(features_by_level_raw, dict):
        result.setdefault("features", [])
        return result

    current_level = max(1, min(_as_int(level, 1), 20))
    unlocked: list[dict[str, Any]] = []

    for level_key, entries_raw in features_by_level_raw.items():
        feature_level = _as_int(level_key, 0)
        if feature_level <= 0 or feature_level > current_level:
            continue

        entries = entries_raw if isinstance(entries_raw, list) else []
        for entry in entries:
            normalized = _normalize_class_feature_entry(entry, level=feature_level)
            if not normalized:
                continue

            mechanics = normalized.get("mechanics")
            mechanic_type = ""
            if isinstance(mechanics, dict):
                mechanic_type = str(mechanics.get("type") or "").strip().lower()

            if mechanic_type == "subclass_choice":
                continue

            unlocked.append(normalized)

    unlocked.sort(
        key=lambda item: (
            _as_int(item.get("level"), 0),
            str(item.get("name_ru") or item.get("name") or item.get("key") or ""),
        )
    )
    result["features"] = unlocked
    return result
