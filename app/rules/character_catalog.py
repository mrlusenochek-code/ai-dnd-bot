from __future__ import annotations

from typing import Any

from app.rules.catalog_loader import load_catalogs


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


BASE_CLASS_CATALOG: list[dict[str, Any]] = [
    {"key": "barbarian", "name": "Barbarian", "name_ru": "Варвар", "source": "PHB", "hit_die": 12, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "bard", "name": "Bard", "name_ru": "Бард", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "cleric", "name": "Cleric", "name_ru": "Жрец", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "druid", "name": "Druid", "name_ru": "Друид", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "fighter", "name": "Fighter", "name_ru": "Воин", "source": "PHB", "hit_die": 10, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "monk", "name": "Monk", "name_ru": "Монах", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "paladin", "name": "Paladin", "name_ru": "Паладин", "source": "PHB", "hit_die": 10, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "ranger", "name": "Ranger", "name_ru": "Следопыт", "source": "PHB", "hit_die": 10, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "rogue", "name": "Rogue", "name_ru": "Плут", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "sorcerer", "name": "Sorcerer", "name_ru": "Чародей", "source": "PHB", "hit_die": 6, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "warlock", "name": "Warlock", "name_ru": "Колдун", "source": "PHB", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "wizard", "name": "Wizard", "name_ru": "Волшебник", "source": "PHB", "hit_die": 6, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    {"key": "artificer", "name": "Artificer", "name_ru": "Изобретатель", "source": "TCE", "hit_die": 8, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
    # Legacy compatibility
    {"key": "mage", "name": "Mage", "name_ru": "Маг", "source": "legacy", "hit_die": 6, "speed_ft": 30, "subclasses": [], "level_progression": {}, "spell_lists": [], "traits": [], "features": [], "spells": []},
]


BASE_RACE_CATALOG: list[dict[str, Any]] = [
    {"key": "human", "name": "Human", "name_ru": "Человек", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": [], "traits": [], "features": [], "spells": []},
    {"key": "dragonborn", "name": "Dragonborn", "name_ru": "Драконорождённый", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": [], "traits": [], "features": [], "spells": []},
    {"key": "dwarf", "name": "Dwarf", "name_ru": "Дварф", "source": "PHB", "speed_ft": 25, "hit_die": 8, "subraces": [], "traits": [], "features": [], "spells": []},
    {"key": "elf", "name": "Elf", "name_ru": "Эльф", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": [], "traits": [], "features": [], "spells": []},
    {"key": "gnome", "name": "Gnome", "name_ru": "Гном", "source": "PHB", "speed_ft": 25, "hit_die": 8, "subraces": [], "traits": [], "features": [], "spells": []},
    {"key": "half_elf", "name": "Half-Elf", "name_ru": "Полуэльф", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": [], "traits": [], "features": [], "spells": []},
    {"key": "half_orc", "name": "Half-Orc", "name_ru": "Полуорк", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": [], "traits": [], "features": [], "spells": []},
    {"key": "halfling", "name": "Halfling", "name_ru": "Полурослик", "source": "PHB", "speed_ft": 25, "hit_die": 8, "subraces": [], "traits": [], "features": [], "spells": []},
    {"key": "tiefling", "name": "Tiefling", "name_ru": "Тифлинг", "source": "PHB", "speed_ft": 30, "hit_die": 8, "subraces": [], "traits": [], "features": [], "spells": []},
]


CLASS_CATALOG, RACE_CATALOG = load_catalogs(
    base_classes=BASE_CLASS_CATALOG,
    base_races=BASE_RACE_CATALOG,
)


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
