from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_PRIVATE_DATA_DIR = "./data_private"
PRIVATE_RACES_FILE = "dndsu_races.json"
PRIVATE_CLASSES_FILE = "dndsu_classes.json"


def _slug(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _private_data_dir() -> Path:
    return Path(os.getenv("DNDSU_PRIVATE_DATA_DIR", DEFAULT_PRIVATE_DATA_DIR)).expanduser()


def _normalize_class_entry(raw: dict[str, Any]) -> dict[str, Any] | None:
    key = _slug(raw.get("key") or raw.get("id"))
    if not key:
        return None

    name_ru = str(raw.get("name_ru") or raw.get("name") or key).strip()
    name = str(raw.get("name") or name_ru or key).strip()
    source = str(raw.get("source") or "custom").strip() or "custom"

    return {
        "key": key,
        "name": name,
        "name_ru": name_ru,
        "source": source,
        "hit_die": max(1, _as_int(raw.get("hit_die"), 8)),
        "speed_ft": max(0, _as_int(raw.get("speed_ft"), 30)),
        "subclasses": list(raw.get("subclasses") or []),
        "level_progression": dict(raw.get("level_progression") or {}),
        "spell_lists": list(raw.get("spell_lists") or []),
        "traits": list(raw.get("traits") or []),
        "features": list(raw.get("features") or []),
        "spells": list(raw.get("spells") or []),
    }


def _normalize_race_entry(raw: dict[str, Any]) -> dict[str, Any] | None:
    key = _slug(raw.get("key") or raw.get("id"))
    if not key:
        return None

    name_ru = str(raw.get("name_ru") or raw.get("name") or key).strip()
    name = str(raw.get("name") or name_ru or key).strip()
    source = str(raw.get("source") or "custom").strip() or "custom"

    return {
        "key": key,
        "name": name,
        "name_ru": name_ru,
        "source": source,
        "speed_ft": max(0, _as_int(raw.get("speed_ft"), 30)),
        "hit_die": max(1, _as_int(raw.get("hit_die"), 8)),
        "subraces": list(raw.get("subraces") or []),
        "traits": list(raw.get("traits") or []),
        "features": list(raw.get("features") or []),
        "spells": list(raw.get("spells") or []),
    }


def _load_private_catalog(filename: str) -> list[dict[str, Any]]:
    path = _private_data_dir() / filename
    if not path.exists() or not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def load_catalogs(
    *,
    base_classes: list[dict[str, Any]],
    base_races: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    merged_classes = [copy.deepcopy(item) for item in base_classes]
    merged_races = [copy.deepcopy(item) for item in base_races]

    class_keys = {_slug(item.get("key")): idx for idx, item in enumerate(merged_classes)}
    race_keys = {_slug(item.get("key")): idx for idx, item in enumerate(merged_races)}

    for raw in _load_private_catalog(PRIVATE_CLASSES_FILE):
        normalized = _normalize_class_entry(raw)
        if not normalized:
            continue
        key = normalized["key"]
        if key in class_keys:
            continue
        class_keys[key] = len(merged_classes)
        merged_classes.append(normalized)

    for raw in _load_private_catalog(PRIVATE_RACES_FILE):
        normalized = _normalize_race_entry(raw)
        if not normalized:
            continue
        key = normalized["key"]
        if key in race_keys:
            continue
        race_keys[key] = len(merged_races)
        merged_races.append(normalized)

    return merged_classes, merged_races
