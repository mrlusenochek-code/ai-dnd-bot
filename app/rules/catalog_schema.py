from __future__ import annotations

from typing import Any, NotRequired, TypedDict


STAT_KEYS = {"str", "dex", "con", "int", "wis", "cha"}
SIZE_KEYS = {"small", "medium", "large"}


class RaceDef(TypedDict):
    key: str
    name_ru: str
    description_ru: str
    asi: list[dict[str, Any]]
    age: dict[str, Any]
    alignment: str
    size: str
    speed_ft: int
    speed_notes_ru: str
    languages: list[str]
    traits: list[dict[str, Any]]
    subraces: list[dict[str, Any]]
    source: str
    tags: list[str]
    # Legacy/UI compatibility field (optional)
    name: NotRequired[str]


class ClassDef(TypedDict):
    key: str
    name_ru: str
    description_ru: str
    hit_die: int
    primary_abilities: list[str]
    saving_throws: list[str]
    proficiencies: dict[str, Any]
    skill_choices: dict[str, Any]
    starting_equipment: list[dict[str, Any]]
    features_by_level: dict[int, list[dict[str, Any]]]
    subclasses: list[dict[str, Any]]
    spellcasting: dict[str, Any]
    spell_lists: dict[str, Any]
    source: str
    tags: list[str]
    # Legacy/UI compatibility field (optional)
    name: NotRequired[str]


def _slug(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _as_stat_keys(value: Any) -> list[str]:
    out: list[str] = []
    for item in _as_str_list(value):
        key = _slug(item)
        if key in STAT_KEYS and key not in out:
            out.append(key)
    return out


def _normalize_size(value: Any) -> str:
    size = _slug(value)
    if size in SIZE_KEYS:
        return size
    return "medium"


def _normalize_languages(value: Any) -> list[str]:
    out: list[str] = []
    for item in _as_str_list(value):
        key = _slug(item)
        if key and key not in out:
            out.append(key)
    return out


def _normalize_features_by_level(raw: Any) -> dict[int, list[dict[str, Any]]]:
    payload = _as_dict(raw)
    out: dict[int, list[dict[str, Any]]] = {}
    for level_raw, entries_raw in payload.items():
        level = _as_int(level_raw, 0)
        if level < 1 or level > 20:
            continue
        entries = _as_list_of_dicts(entries_raw)
        out[level] = entries
    return out


def _normalize_spell_lists(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, list):
        return {"default": _as_str_list(raw)}
    return {}


def normalize_race(raw: dict[str, Any]) -> dict[str, Any] | None:
    key = _slug(raw.get("key") or raw.get("id"))
    if not key:
        return None

    name_ru = str(raw.get("name_ru") or raw.get("name") or key).strip()
    out: RaceDef = {
        "key": key,
        "name_ru": name_ru,
        "description_ru": str(raw.get("description_ru") or raw.get("description") or "").strip(),
        "asi": _as_list_of_dicts(raw.get("asi")),
        "age": _as_dict(raw.get("age")),
        "alignment": str(raw.get("alignment") or "").strip(),
        "size": _normalize_size(raw.get("size")),
        "speed_ft": max(0, _as_int(raw.get("speed_ft"), 30)),
        "speed_notes_ru": str(raw.get("speed_notes_ru") or "").strip(),
        "languages": _normalize_languages(raw.get("languages")),
        "traits": _as_list_of_dicts(raw.get("traits")),
        "subraces": _as_list_of_dicts(raw.get("subraces")),
        "source": str(raw.get("source") or "custom").strip() or "custom",
        "tags": _as_str_list(raw.get("tags")),
    }
    legacy_name = str(raw.get("name") or "").strip()
    if legacy_name:
        out["name"] = legacy_name
    return dict(out)


def normalize_class(raw: dict[str, Any]) -> dict[str, Any] | None:
    key = _slug(raw.get("key") or raw.get("id"))
    if not key:
        return None

    name_ru = str(raw.get("name_ru") or raw.get("name") or key).strip()
    features_by_level_raw = raw.get("features_by_level")
    if features_by_level_raw is None:
        features_by_level_raw = raw.get("level_progression")

    out: ClassDef = {
        "key": key,
        "name_ru": name_ru,
        "description_ru": str(raw.get("description_ru") or raw.get("description") or "").strip(),
        "hit_die": max(1, _as_int(raw.get("hit_die"), 8)),
        "primary_abilities": _as_stat_keys(raw.get("primary_abilities")),
        "saving_throws": _as_stat_keys(raw.get("saving_throws")),
        "proficiencies": _as_dict(raw.get("proficiencies")),
        "skill_choices": _as_dict(raw.get("skill_choices")),
        "starting_equipment": _as_list_of_dicts(raw.get("starting_equipment")),
        "features_by_level": _normalize_features_by_level(features_by_level_raw),
        "subclasses": _as_list_of_dicts(raw.get("subclasses")),
        "spellcasting": _as_dict(raw.get("spellcasting")),
        "spell_lists": _normalize_spell_lists(raw.get("spell_lists")),
        "source": str(raw.get("source") or "custom").strip() or "custom",
        "tags": _as_str_list(raw.get("tags")),
    }
    legacy_name = str(raw.get("name") or "").strip()
    if legacy_name:
        out["name"] = legacy_name
    return dict(out)
