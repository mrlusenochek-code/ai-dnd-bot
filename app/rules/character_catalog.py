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
    {"key": "barbarian", "name": "Barbarian", "name_ru": "Варвар", "source": "PHB", "description_ru": "", "hit_die": 12, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "bard", "name": "Bard", "name_ru": "Бард", "source": "PHB", "description_ru": "", "hit_die": 8, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "cleric", "name": "Cleric", "name_ru": "Жрец", "source": "PHB", "description_ru": "", "hit_die": 8, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "druid", "name": "Druid", "name_ru": "Друид", "source": "PHB", "description_ru": "", "hit_die": 8, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "fighter", "name": "Fighter", "name_ru": "Воин", "source": "PHB", "description_ru": "", "hit_die": 10, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "monk", "name": "Monk", "name_ru": "Монах", "source": "PHB", "description_ru": "", "hit_die": 8, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "paladin", "name": "Paladin", "name_ru": "Паладин", "source": "PHB", "description_ru": "", "hit_die": 10, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "ranger", "name": "Ranger", "name_ru": "Следопыт", "source": "PHB", "description_ru": "", "hit_die": 10, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "rogue", "name": "Rogue", "name_ru": "Плут", "source": "PHB", "description_ru": "", "hit_die": 8, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "sorcerer", "name": "Sorcerer", "name_ru": "Чародей", "source": "PHB", "description_ru": "", "hit_die": 6, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "warlock", "name": "Warlock", "name_ru": "Колдун", "source": "PHB", "description_ru": "", "hit_die": 8, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "wizard", "name": "Wizard", "name_ru": "Волшебник", "source": "PHB", "description_ru": "", "hit_die": 6, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    {"key": "artificer", "name": "Artificer", "name_ru": "Изобретатель", "source": "TCE", "description_ru": "", "hit_die": 8, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
    # Legacy compatibility
    {"key": "mage", "name": "Mage", "name_ru": "Маг", "source": "legacy", "description_ru": "", "hit_die": 6, "primary_abilities": [], "saving_throws": [], "proficiencies": {}, "skill_choices": {}, "starting_equipment": [], "features_by_level": {}, "subclasses": [], "spellcasting": {}, "spell_lists": {}, "tags": []},
]


BASE_RACE_CATALOG: list[dict[str, Any]] = [
    {"key": "human", "name": "Human", "name_ru": "Человек", "source": "PHB", "description_ru": "", "asi": [], "age": {}, "alignment": "", "size": "medium", "speed_ft": 30, "speed_notes_ru": "", "languages": [], "traits": [], "subraces": [], "tags": []},
    {"key": "dragonborn", "name": "Dragonborn", "name_ru": "Драконорождённый", "source": "PHB", "description_ru": "", "asi": [], "age": {}, "alignment": "", "size": "medium", "speed_ft": 30, "speed_notes_ru": "", "languages": [], "traits": [], "subraces": [], "tags": []},
    {"key": "dwarf", "name": "Dwarf", "name_ru": "Дварф", "source": "PHB", "description_ru": "", "asi": [], "age": {}, "alignment": "", "size": "medium", "speed_ft": 25, "speed_notes_ru": "", "languages": [], "traits": [], "subraces": [], "tags": []},
    {"key": "elf", "name": "Elf", "name_ru": "Эльф", "source": "PHB", "description_ru": "", "asi": [], "age": {}, "alignment": "", "size": "medium", "speed_ft": 30, "speed_notes_ru": "", "languages": [], "traits": [], "subraces": [], "tags": []},
    {"key": "gnome", "name": "Gnome", "name_ru": "Гном", "source": "PHB", "description_ru": "", "asi": [], "age": {}, "alignment": "", "size": "small", "speed_ft": 25, "speed_notes_ru": "", "languages": [], "traits": [], "subraces": [], "tags": []},
    {"key": "half_elf", "name": "Half-Elf", "name_ru": "Полуэльф", "source": "PHB", "description_ru": "", "asi": [], "age": {}, "alignment": "", "size": "medium", "speed_ft": 30, "speed_notes_ru": "", "languages": [], "traits": [], "subraces": [], "tags": []},
    {"key": "half_orc", "name": "Half-Orc", "name_ru": "Полуорк", "source": "PHB", "description_ru": "", "asi": [], "age": {}, "alignment": "", "size": "medium", "speed_ft": 30, "speed_notes_ru": "", "languages": [], "traits": [], "subraces": [], "tags": []},
    {"key": "halfling", "name": "Halfling", "name_ru": "Полурослик", "source": "PHB", "description_ru": "", "asi": [], "age": {}, "alignment": "", "size": "small", "speed_ft": 25, "speed_notes_ru": "", "languages": [], "traits": [], "subraces": [], "tags": []},
    {"key": "tiefling", "name": "Tiefling", "name_ru": "Тифлинг", "source": "PHB", "description_ru": "", "asi": [], "age": {}, "alignment": "", "size": "medium", "speed_ft": 30, "speed_notes_ru": "", "languages": [], "traits": [], "subraces": [], "tags": []},
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
