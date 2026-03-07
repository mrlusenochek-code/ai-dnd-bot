from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from app.rules.catalog_schema import normalize_class, normalize_race


DEFAULT_PRIVATE_DATA_DIR = "./data_private"
PRIVATE_RACES_FILE = "dndsu_races.json"
PRIVATE_GENERATED_RACES_FILE = "races_generated.json"
PRIVATE_CLASSES_FILE = "dndsu_classes.json"
CATALOG_ENABLE_PRIVATE_ENV = "CATALOG_ENABLE_PRIVATE"


def _slug(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _private_data_dir() -> Path:
    return Path(os.getenv("DNDSU_PRIVATE_DATA_DIR", DEFAULT_PRIVATE_DATA_DIR)).expanduser()


def _private_enabled() -> bool:
    raw = str(os.getenv(CATALOG_ENABLE_PRIVATE_ENV, "0") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


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
    merged_classes: list[dict[str, Any]] = []
    merged_races: list[dict[str, Any]] = []

    class_keys: dict[str, int] = {}
    race_keys: dict[str, int] = {}

    for item in base_classes:
        normalized = normalize_class(copy.deepcopy(item))
        if not normalized:
            continue
        key = _slug(normalized.get("key"))
        if not key or key in class_keys:
            continue
        class_keys[key] = len(merged_classes)
        merged_classes.append(normalized)

    for item in base_races:
        normalized = normalize_race(copy.deepcopy(item))
        if not normalized:
            continue
        key = _slug(normalized.get("key"))
        if not key or key in race_keys:
            continue
        race_keys[key] = len(merged_races)
        merged_races.append(normalized)

    if _private_enabled():
        for raw in _load_private_catalog(PRIVATE_CLASSES_FILE):
            normalized = normalize_class(raw)
            if not normalized:
                continue
            key = normalized["key"]
            if key in class_keys:
                continue
            class_keys[key] = len(merged_classes)
            merged_classes.append(normalized)

        for raw in _load_private_catalog(PRIVATE_RACES_FILE):
            normalized = normalize_race(raw)
            if not normalized:
                continue
            key = normalized["key"]
            if key in race_keys:
                continue
            race_keys[key] = len(merged_races)
            merged_races.append(normalized)

        for raw in _load_private_catalog(PRIVATE_GENERATED_RACES_FILE):
            normalized = normalize_race(raw)
            if not normalized:
                continue
            key = normalized["key"]
            if key in race_keys:
                continue
            race_keys[key] = len(merged_races)
            merged_races.append(normalized)

    return merged_classes, merged_races
