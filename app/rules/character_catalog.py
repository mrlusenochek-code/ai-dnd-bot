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
    {
        "key": "barbarian",
        "name": "Barbarian",
        "name_ru": "Варвар",
        "source": "PHB",
        "description_ru": "Неистовый воин, полагающийся на ярость, стойкость и грубую силу.",
        "hit_die": 12,
        "primary_abilities": ["str"],
        "saving_throws": ["str", "con"],
        "proficiencies": {
            "armor": ["light", "medium", "shields"],
            "weapons": ["simple", "martial"],
            "tools": [],
            "skills_choose": {
                "count": 2,
                "from": ["athletics", "intimidation", "nature", "perception", "survival", "animal_handling"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_barbarian_starting_equipment",
                "name_ru": "Стартовое снаряжение варвара",
                "summary_ru": "TODO: PHB equipment choices",
            }
        ],
        "features_by_level": {
            1: [
                {"key": "rage", "name_ru": "Ярость", "summary_ru": "В бою усиливает урон и выживаемость.", "mechanics": {}},
                {"key": "unarmored_defense", "name_ru": "Защита без доспехов", "summary_ru": "КД рассчитывается от Телосложения и Ловкости.", "mechanics": {}},
            ],
            2: [
                {"key": "reckless_attack", "name_ru": "Безрассудная атака", "summary_ru": "Можно атаковать агрессивно, повышая шанс попадания ценой защиты.", "mechanics": {}},
                {"key": "danger_sense", "name_ru": "Чувство опасности", "summary_ru": "Лучше избегает видимых угроз и ловушек.", "mechanics": {}},
            ],
            3: [
                {"key": "primal_path", "name_ru": "Путь дикости", "summary_ru": "Выбор подкласса варвара.", "mechanics": {"type": "subclass_choice"}},
            ],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            5: [
                {"key": "extra_attack", "name_ru": "Дополнительная атака", "summary_ru": "Совершает больше атак действием.", "mechanics": {}},
                {"key": "fast_movement", "name_ru": "Быстрое передвижение", "summary_ru": "Увеличивает скорость передвижения.", "mechanics": {}},
            ],
            6: [{"key": "path_feature_6", "name_ru": "Особенность пути (6)", "summary_ru": "Классовая особенность выбранного пути на 6 уровне.", "mechanics": {}}],
            7: [{"key": "feral_instinct", "name_ru": "Звериный инстинкт", "summary_ru": "Быстрее реагирует на начало схватки.", "mechanics": {}}],
            8: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            9: [{"key": "brutal_critical_1", "name_ru": "Жестокий критический удар (1)", "summary_ru": "Критические удары наносят больше урона.", "mechanics": {}}],
            10: [{"key": "path_feature_10", "name_ru": "Особенность пути (10)", "summary_ru": "Классовая особенность выбранного пути на 10 уровне.", "mechanics": {}}],
            11: [{"key": "relentless_rage", "name_ru": "Неукротимая ярость", "summary_ru": "Может удержаться на ногах после тяжёлого удара.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            13: [{"key": "brutal_critical_2", "name_ru": "Жестокий критический удар (2)", "summary_ru": "Критические удары становятся ещё опаснее.", "mechanics": {}}],
            14: [{"key": "path_feature_14", "name_ru": "Особенность пути (14)", "summary_ru": "Классовая особенность выбранного пути на 14 уровне.", "mechanics": {}}],
            15: [{"key": "persistent_rage", "name_ru": "Постоянная ярость", "summary_ru": "Ярость удерживается дольше в сражении.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            17: [{"key": "brutal_critical_3", "name_ru": "Жестокий критический удар (3)", "summary_ru": "Максимальная ступень усиления критических ударов.", "mechanics": {}}],
            18: [{"key": "indomitable_might", "name_ru": "Несокрушимая мощь", "summary_ru": "Чистая сила помогает в проверках даже при плохом броске.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "primal_champion", "name_ru": "Первобытный чемпион", "summary_ru": "Пик физической мощи и выносливости варвара.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "berserker",
                "name_ru": "Путь берсерка",
                "features_by_level": {
                    3: [{"key": "frenzy", "name_ru": "Исступление", "summary_ru": "В ярости сражается с предельной агрессией.", "mechanics": {}}],
                    6: [{"key": "mindless_rage", "name_ru": "Безумная ярость", "summary_ru": "Ярость помогает игнорировать ментальные помехи.", "mechanics": {}}],
                    10: [{"key": "intimidating_presence", "name_ru": "Пугающее присутствие", "summary_ru": "Давит на врагов одним присутствием.", "mechanics": {}}],
                    14: [{"key": "retaliation", "name_ru": "Возмездие", "summary_ru": "Отвечает ударом на вражескую атаку.", "mechanics": {}}],
                },
            },
            {
                "key": "totem_warrior",
                "name_ru": "Путь тотемного воина",
                "features_by_level": {
                    3: [
                        {"key": "spirit_seeker", "name_ru": "Искатель духов", "summary_ru": "Осваивает ритуалы общения с духами природы.", "mechanics": {}},
                        {"key": "totem_spirit", "name_ru": "Дух тотема", "summary_ru": "Выбирает духа-покровителя, меняющего стиль боя.", "mechanics": {}},
                    ],
                    6: [{"key": "aspect_of_beast", "name_ru": "Аспект зверя", "summary_ru": "Получает дополнительную особенность выбранного тотема.", "mechanics": {}}],
                    10: [{"key": "commune_with_nature", "name_ru": "Единение с природой", "summary_ru": "Лучше чувствует окружающую местность и духов.", "mechanics": {}}],
                    14: [{"key": "totemic_attunement", "name_ru": "Тотемное единение", "summary_ru": "Высшая форма связи с тотемом в бою.", "mechanics": {}}],
                },
            },
        ],
        "spellcasting": {},
        "spell_lists": {},
        "tags": [],
    },
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
    {
        "key": "dwarf",
        "name": "Dwarf",
        "name_ru": "Дварф",
        "source": "PHB",
        "description_ru": "Крепкий и выносливый народ, привыкший к подземным залам и камню.",
        "asi": [{"stat": "con", "bonus": 2}],
        "age": {},
        "alignment": "",
        "size": "medium",
        "speed_ft": 25,
        "speed_notes_ru": "Ношение тяжёлых доспехов не снижает скорость.",
        "languages": ["common", "dwarvish"],
        "traits": [
            {
                "key": "darkvision",
                "name_ru": "Тёмное зрение",
                "text_ru": "Видит в темноте на ограничённой дистанции.",
                "mechanics": {"type": "sense", "name": "darkvision", "range_ft": 60},
            },
            {
                "key": "dwarven_resilience",
                "name_ru": "Дварфская стойкость",
                "text_ru": "Устойчив к яду и лучше сопротивляется его эффектам.",
                "mechanics": {"saves_advantage": ["poison"], "resistances": ["poison"]},
            },
            {
                "key": "dwarven_combat_training",
                "name_ru": "Дварфская боевая выучка",
                "text_ru": "Обучен традиционному оружию дварфов.",
                "mechanics": {
                    "type": "proficiency",
                    "weapons": ["battleaxe", "handaxe", "light_hammer", "warhammer"],
                },
            },
            {
                "key": "tool_proficiency",
                "name_ru": "Владение инструментами",
                "text_ru": "Выбирает один ремесленный набор дварфов.",
                "mechanics": {"choose": 1, "from": ["smith_tools", "brewer_supplies", "mason_tools"]},
            },
            {
                "key": "stonecunning",
                "name_ru": "Знание камня",
                "text_ru": "Особо хорошо разбирается в истории и происхождении каменной кладки.",
                "mechanics": {"type": "skill_bonus", "skill": "history", "context": "stonework", "proficiency_multiplier": 2},
            },
        ],
        "subraces": [
            {
                "key": "hill_dwarf",
                "name_ru": "Холмовой дварф",
                "asi": [{"stat": "wis", "bonus": 1}],
                "traits": [
                    {
                        "key": "dwarven_toughness",
                        "name_ru": "Дварфская живучесть",
                        "text_ru": "Дополнительная живучесть увеличивает максимальные хиты.",
                        "mechanics": {"type": "hp_scaling", "base_bonus": 1, "per_level_bonus": 1},
                    }
                ],
            },
            {
                "key": "mountain_dwarf",
                "name_ru": "Горный дварф",
                "asi": [{"stat": "str", "bonus": 2}],
                "traits": [
                    {
                        "key": "dwarf_armor_training",
                        "name_ru": "Дварфская доспешная выучка",
                        "text_ru": "Владеет лёгкими и средними доспехами.",
                        "mechanics": {"type": "proficiency", "armor": ["light", "medium"]},
                    }
                ],
            },
        ],
        "tags": [],
    },
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
