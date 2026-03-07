from __future__ import annotations

from typing import Any


def _slug(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


PHB_CLASS_KEYS: tuple[str, ...] = (
    "barbarian",
    "bard",
    "cleric",
    "druid",
    "fighter",
    "monk",
    "paladin",
    "ranger",
    "rogue",
    "sorcerer",
    "warlock",
    "wizard",
)


PHB_RACE_KEYS: tuple[str, ...] = (
    "dragonborn",
    "dwarf",
    "elf",
    "gnome",
    "half_elf",
    "half_orc",
    "halfling",
    "human",
    "tiefling",
)


CLASS_CATALOG: list[dict[str, Any]] = [
    {"key": "barbarian", "name": "Barbarian", "source": "PHB", "hit_die": 12, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "bard", "name": "Bard", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "cleric", "name": "Cleric", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "druid", "name": "Druid", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "fighter", "name": "Fighter", "source": "PHB", "hit_die": 10, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "monk", "name": "Monk", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "paladin", "name": "Paladin", "source": "PHB", "hit_die": 10, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "ranger", "name": "Ranger", "source": "PHB", "hit_die": 10, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "rogue", "name": "Rogue", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "sorcerer", "name": "Sorcerer", "source": "PHB", "hit_die": 6, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "warlock", "name": "Warlock", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    {"key": "wizard", "name": "Wizard", "source": "PHB", "hit_die": 6, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
    # Legacy compatibility
    {"key": "mage", "name": "Mage", "source": "legacy", "hit_die": 6, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": []},
]


RACE_CATALOG: list[dict[str, Any]] = [
    {"key": "human", "name": "Human", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": []},
    {"key": "dragonborn", "name": "Dragonborn", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": []},
    {"key": "dwarf", "name": "Dwarf", "source": "PHB", "speed_ft": 25, "hit_die": 8, "subraces": []},
    {"key": "elf", "name": "Elf", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": []},
    {"key": "gnome", "name": "Gnome", "source": "PHB", "speed_ft": 25, "hit_die": 8, "subraces": []},
    {"key": "half_elf", "name": "Half-Elf", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": []},
    {"key": "half_orc", "name": "Half-Orc", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": []},
    {"key": "halfling", "name": "Halfling", "source": "PHB", "speed_ft": 25, "hit_die": 8, "subraces": []},
    {"key": "tiefling", "name": "Tiefling", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": []},
]


CLASS_ALIASES: dict[str, str] = {
    "mage": "wizard",
}


RACE_ALIASES: dict[str, str] = {
    "man": "human",
    "human_variant": "human",
}


CLASS_BY_KEY: dict[str, dict[str, Any]] = {item["key"]: item for item in CLASS_CATALOG}
RACE_BY_KEY: dict[str, dict[str, Any]] = {item["key"]: item for item in RACE_CATALOG}


def resolve_class_key(raw_key: Any) -> str:
    key = _slug(raw_key)
    if not key:
        return ""
    return CLASS_ALIASES.get(key, key)


def resolve_race_key(raw_key: Any) -> str:
    key = _slug(raw_key)
    if not key:
        return ""
    return RACE_ALIASES.get(key, key)


def resolve_class(raw_key: Any) -> dict[str, Any] | None:
    return CLASS_BY_KEY.get(resolve_class_key(raw_key))


def resolve_race(raw_key: Any) -> dict[str, Any] | None:
    return RACE_BY_KEY.get(resolve_race_key(raw_key))


def class_hit_die_by_catalog(class_kit: Any, class_skin: Any) -> int:
    by_kit = resolve_class(class_kit)
    if by_kit is not None:
        return max(1, int(by_kit.get("hit_die") or 8))

    by_skin = resolve_class(class_skin)
    if by_skin is not None:
        return max(1, int(by_skin.get("hit_die") or 8))

    return 8


def race_speed_ft_by_catalog(race_kit: Any, race_skin: Any) -> int:
    by_kit = resolve_race(race_kit)
    if by_kit is not None:
        return max(0, int(by_kit.get("speed_ft") or 30))

    by_skin = resolve_race(race_skin)
    if by_skin is not None:
        return max(0, int(by_skin.get("speed_ft") or 30))

    return 30
