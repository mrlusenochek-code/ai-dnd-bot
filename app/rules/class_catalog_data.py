from __future__ import annotations

from typing import Any


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
                "summary_ru": "а) двуручный топор или б) любое воинское рукопашное оружие; а) два ручных топора или б) любое простое оружие; набор путешественника и 4 метательных копья.",
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
                "description_ru": "Берсерк делает ставку на чистую ярость, давление и безумную агрессию в ближнем бою.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "frenzy",
                            "name_ru": "Исступление",
                            "summary_ru": "Во время ярости может входить в исступление и получать дополнительную атаку ценой истощения после окончания ярости.",
                        }
                    ],
                    6: [
                        {
                            "key": "mindless_rage",
                            "name_ru": "Безумная ярость",
                            "summary_ru": "Во время ярости сложнее поддаться очарованию и испугу.",
                        }
                    ],
                    10: [
                        {
                            "key": "intimidating_presence",
                            "name_ru": "Устрашающее присутствие",
                            "summary_ru": "Может подавлять врагов своей яростью и страхом.",
                        }
                    ],
                    14: [
                        {
                            "key": "retaliation",
                            "name_ru": "Возмездие",
                            "summary_ru": "Может немедленно ударить врага в ответ, если тот ранил его рядом.",
                        }
                    ],
                },
            },
            {
                "key": "totem_warrior",
                "name_ru": "Путь тотемного воина",
                "description_ru": "Тотемный воин черпает силу духов зверей и получает защитные, охотничьи и ритуальные способности.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "spirit_seeker",
                            "name_ru": "Искатель духов",
                            "summary_ru": "Получает ритуальные духовные практики и связь с тотемами.",
                        },
                        {
                            "key": "totem_spirit",
                            "name_ru": "Тотемный дух",
                            "summary_ru": "Выбирает духа тотема, который усиливает ярость и стиль боя.",
                        }
                    ],
                    6: [
                        {
                            "key": "aspect_of_the_beast",
                            "name_ru": "Аспект зверя",
                            "summary_ru": "Получает постоянную звериную особенность вне ярости.",
                        }
                    ],
                    10: [
                        {
                            "key": "spirit_walker",
                            "name_ru": "Странник духов",
                            "summary_ru": "Может обращаться к духам за советом и видениями.",
                        }
                    ],
                    14: [
                        {
                            "key": "totemic_attunement",
                            "name_ru": "Единение с тотемом",
                            "summary_ru": "Получает высшую силу выбранного тотема в бою.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {},
        "spell_lists": {},
        "tags": [],
    },
    {
        "key": "bard",
        "name": "Bard",
        "name_ru": "Бард",
        "source": "PHB",
        "description_ru": "Вдохновляющий заклинатель, использующий музыку, слово и харизму для поддержки союзников и управления ходом сцены.",
        "hit_die": 8,
        "primary_abilities": ["cha"],
        "saving_throws": ["dex", "cha"],
        "proficiencies": {
            "armor": ["light"],
            "weapons": ["simple", "longsword", "shortsword", "rapier", "hand_crossbow"],
            "tools": ["musical_instrument", "musical_instrument", "musical_instrument"],
            "skills_choose": {
                "count": 3,
                "from": [
                    "athletics",
                    "acrobatics",
                    "sleight_of_hand",
                    "stealth",
                    "arcana",
                    "history",
                    "investigation",
                    "nature",
                    "religion",
                    "animal_handling",
                    "insight",
                    "medicine",
                    "perception",
                    "survival",
                    "deception",
                    "intimidation",
                    "performance",
                    "persuasion",
                ],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_bard_starting_equipment",
                "name_ru": "Стартовое снаряжение барда",
                "summary_ru": "а) рапира, б) длинный меч или в) любое простое оружие; а) набор дипломата или б) набор артиста; а) лютня или б) любой другой музыкальный инструмент; кожаный доспех и кинжал.",
            }
        ],
        "features_by_level": {
            1: [
                {
                    "key": "spellcasting",
                    "name_ru": "Использование заклинаний",
                    "summary_ru": "Бард использует Харизму для заклинаний и может творить известные заклинания из списка барда.",
                    "mechanics": {
                        "type": "spellcasting",
                        "ability": "cha",
                        "progression": "full",
                        "known_style": "known",
                        "focus": ["musical_instrument"],
                        "ritual": True,
                    },
                },
                {"key": "bardic_inspiration", "name_ru": "Вдохновение барда", "summary_ru": "Бонусным действием вдохновляет союзника костью вдохновения.", "mechanics": {"type": "bardic_inspiration"}},
            ],
            2: [
                {"key": "jack_of_all_trades", "name_ru": "Мастер на все руки", "summary_ru": "Добавляет половину бонуса мастерства к проверкам, где мастерство не применяется.", "mechanics": {}},
                {"key": "song_of_rest", "name_ru": "Песнь отдыха", "summary_ru": "Во время короткого отдыха союзники дополнительно восстанавливают хиты.", "mechanics": {}},
            ],
            3: [
                {"key": "bard_college", "name_ru": "Коллегия бардов", "summary_ru": "Выбор подкласса барда.", "mechanics": {"type": "subclass_choice"}},
                {"key": "expertise", "name_ru": "Компетентность", "summary_ru": "Удвоение бонуса мастерства для выбранных навыков.", "mechanics": {}},
            ],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            5: [{"key": "font_of_inspiration", "name_ru": "Источник вдохновения", "summary_ru": "Вдохновение барда восстанавливается после короткого отдыха.", "mechanics": {}}],
            6: [{"key": "countercharm", "name_ru": "Контрочарование", "summary_ru": "Использует выступление, чтобы дать преимущество против очарования и испуга.", "mechanics": {}}],
            8: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            10: [
                {"key": "expertise_2", "name_ru": "Компетентность", "summary_ru": "Выбор ещё двух навыков для удвоенного бонуса мастерства.", "mechanics": {}},
                {"key": "magical_secrets", "name_ru": "Тайны магии", "summary_ru": "Изучает заклинания из списков других классов.", "mechanics": {}},
            ],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            14: [{"key": "magical_secrets_2", "name_ru": "Тайны магии", "summary_ru": "Изучает дополнительные заклинания из списков других классов.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            18: [{"key": "magical_secrets_3", "name_ru": "Тайны магии", "summary_ru": "Изучает дополнительные заклинания из списков других классов.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "superior_inspiration", "name_ru": "Превосходное вдохновение", "summary_ru": "Если вдохновение закончилось, бард получает одно использование в начале столкновения.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "lore",
                "name_ru": "Коллегия знаний",
                "description_ru": "Эти барды собирают тайны мира, знания, легенды и умело используют магию, слова и мастерство навыков.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "bonus_proficiencies",
                            "name_ru": "Дополнительные владения",
                            "summary_ru": "Получает больше навыков и становится ещё гибче вне боя.",
                        },
                        {
                            "key": "cutting_words",
                            "name_ru": "Едкие слова",
                            "summary_ru": "Может словами ослаблять броски врага, мешая атаке, проверке или урону.",
                        }
                    ],
                    6: [
                        {
                            "key": "additional_magical_secrets",
                            "name_ru": "Дополнительные тайны магии",
                            "summary_ru": "Раньше других получает доступ к заклинаниям из списков других классов.",
                        }
                    ],
                    14: [
                        {
                            "key": "peerless_skill",
                            "name_ru": "Непревзойдённое мастерство",
                            "summary_ru": "Может тратить вдохновение барда, чтобы усиливать собственные проверки.",
                        }
                    ],
                },
            },
            {
                "key": "valor",
                "name_ru": "Коллегия доблести",
                "description_ru": "Бард доблести сочетает поддержку союзников, вдохновение и уверенное участие в бою оружием.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "bonus_proficiencies_valor",
                            "name_ru": "Дополнительные владения",
                            "summary_ru": "Получает владение доспехами, щитами и боевым оружием для более уверенного боя.",
                        },
                        {
                            "key": "combat_inspiration",
                            "name_ru": "Боевое вдохновение",
                            "summary_ru": "Вдохновение барда помогает союзникам не только в проверках, но и в бою.",
                        }
                    ],
                    6: [
                        {
                            "key": "extra_attack",
                            "name_ru": "Дополнительная атака",
                            "summary_ru": "Может атаковать дважды действием.",
                        }
                    ],
                    14: [
                        {
                            "key": "battle_magic",
                            "name_ru": "Боевая магия",
                            "summary_ru": "После наложения заклинания может быстро перейти к удару оружием.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {
            "type": "full_caster_known",
            "ability": "cha",
            "focus": ["musical_instrument"],
            "ritual": True,
            "spell_list_key": "bard",
        },
        "spell_lists": {"class": "bard"},
        "tags": [],
    },
    {
        "key": "cleric",
        "name": "Cleric",
        "name_ru": "Жрец",
        "source": "PHB",
        "description_ru": "Священнослужитель, проводник божественной силы, сочетающий поддержку, защиту и силу домена своего божества.",
        "hit_die": 8,
        "primary_abilities": ["wis"],
        "saving_throws": ["wis", "cha"],
        "proficiencies": {
            "armor": ["light", "medium", "shields"],
            "weapons": ["simple"],
            "tools": [],
            "skills_choose": {
                "count": 2,
                "from": ["history", "insight", "medicine", "persuasion", "religion"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_cleric_starting_equipment",
                "name_ru": "Стартовое снаряжение жреца",
                "summary_ru": "а) булава или б) боевой молот (если есть владение); а) чешуйчатый доспех, б) кожаный доспех или в) кольчуга (если есть владение); а) лёгкий арбалет и 20 болтов или б) любое простое оружие; а) набор священника или б) набор путешественника; щит и священный символ.",
            }
        ],
        "features_by_level": {
            1: [
                {
                    "key": "spellcasting",
                    "name_ru": "Использование заклинаний",
                    "summary_ru": "Жрец подготавливает заклинания из списка жреца и использует Мудрость как базовую характеристику заклинаний.",
                    "mechanics": {
                        "type": "spellcasting",
                        "ability": "wis",
                        "progression": "full",
                        "known_style": "prepared",
                        "focus": ["holy_symbol"],
                        "ritual": True,
                    },
                },
                {"key": "divine_domain", "name_ru": "Божественный домен", "summary_ru": "Выбор домена, определяющего силу жреца.", "mechanics": {"type": "subclass_choice"}},
            ],
            2: [
                {"key": "channel_divinity", "name_ru": "Божественный канал", "summary_ru": "Направляет божественную силу для эффектов домена и изгнания нежити.", "mechanics": {}},
                {"key": "domain_feature_2", "name_ru": "Умение домена (2)", "summary_ru": "Особенность выбранного божественного домена.", "mechanics": {}},
            ],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            5: [{"key": "destroy_undead", "name_ru": "Уничтожение нежити", "summary_ru": "Изгнанная нежить низкой опасности может быть уничтожена.", "mechanics": {}}],
            6: [
                {"key": "channel_divinity_2", "name_ru": "Божественный канал (2)", "summary_ru": "Жрец использует Божественный канал дважды между отдыхами.", "mechanics": {}},
                {"key": "domain_feature_6", "name_ru": "Умение домена (6)", "summary_ru": "Новая особенность выбранного домена.", "mechanics": {}},
            ],
            8: [
                {"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}},
                {"key": "domain_feature_8", "name_ru": "Умение домена (8)", "summary_ru": "Усиление выбранного домена на 8 уровне.", "mechanics": {}},
            ],
            10: [{"key": "divine_intervention", "name_ru": "Божественное вмешательство", "summary_ru": "Может воззвать к своему божеству о прямой помощи.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            17: [{"key": "domain_feature_17", "name_ru": "Умение домена (17)", "summary_ru": "Высшая особенность выбранного домена.", "mechanics": {}}],
            18: [{"key": "channel_divinity_3", "name_ru": "Божественный канал (3)", "summary_ru": "Жрец использует Божественный канал трижды между отдыхами.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "improved_divine_intervention", "name_ru": "Совершенное божественное вмешательство", "summary_ru": "Божественное вмешательство становится гарантированным.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "knowledge",
                "name_ru": "Домен знаний",
                "description_ru": "Жрец знаний собирает тайны мира, раскрывает скрытое и превращает эрудицию в божественное преимущество.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "blessings_of_knowledge",
                            "name_ru": "Благословения знания",
                            "summary_ru": "Получает дополнительные языки и навыки, связанные с учёностью и памятью.",
                        }
                    ],
                    2: [
                        {
                            "key": "knowledge_of_the_ages",
                            "name_ru": "Знание веков",
                            "summary_ru": "Временно осваивает нужный навык или инструмент через божественное знание.",
                        }
                    ],
                    6: [
                        {
                            "key": "read_thoughts",
                            "name_ru": "Чтение мыслей",
                            "summary_ru": "Проникает в разум цели и легче выуживает скрытые сведения.",
                        }
                    ],
                    8: [
                        {
                            "key": "potent_spellcasting_knowledge",
                            "name_ru": "Могущественное колдовство",
                            "summary_ru": "Усиливает урон заговоров силой божественного знания.",
                        }
                    ],
                    17: [
                        {
                            "key": "visions_of_the_past",
                            "name_ru": "Видения прошлого",
                            "summary_ru": "Считывает отголоски прошлого с предметов и мест.",
                        }
                    ],
                },
            },
            {
                "key": "life",
                "name_ru": "Домен жизни",
                "description_ru": "Жрец жизни сосредоточен на исцелении, защите союзников и поддержании сил отряда.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "disciple_of_life",
                            "name_ru": "Ученик жизни",
                            "summary_ru": "Его исцеляющие заклинания восстанавливают заметно больше хитов.",
                        }
                    ],
                    2: [
                        {
                            "key": "preserve_life",
                            "name_ru": "Сохранение жизни",
                            "summary_ru": "Божественной силой быстро поднимает на ноги тяжело раненых союзников.",
                        }
                    ],
                    6: [
                        {
                            "key": "blessed_healer",
                            "name_ru": "Благословенный целитель",
                            "summary_ru": "Леча других, жрец частично поддерживает и собственные силы.",
                        }
                    ],
                    8: [
                        {
                            "key": "divine_strike_life",
                            "name_ru": "Божественный удар",
                            "summary_ru": "Его оружейные удары наполняются дополнительной священной силой.",
                        }
                    ],
                    17: [
                        {
                            "key": "supreme_healing",
                            "name_ru": "Высшее исцеление",
                            "summary_ru": "Его целительная магия почти всегда работает на максимуме.",
                        }
                    ],
                },
            },
            {
                "key": "light",
                "name_ru": "Домен света",
                "description_ru": "Жрец света несёт очищающее сияние, жжёт врагов огнём и разгоняет тьму.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "bonus_cantrip_light",
                            "name_ru": "Дополнительный заговор",
                            "summary_ru": "Получает световой заговор и лучше управляет священным пламенем.",
                        },
                        {
                            "key": "warding_flare",
                            "name_ru": "Защитная вспышка",
                            "summary_ru": "Ослепляющей вспышкой мешает врагу точно попасть по союзнику или по себе.",
                        }
                    ],
                    2: [
                        {
                            "key": "radiance_of_the_dawn",
                            "name_ru": "Сияние рассвета",
                            "summary_ru": "Выплёскивает волну света, которая жжёт врагов и разгоняет магическую тьму.",
                        }
                    ],
                    6: [
                        {
                            "key": "improved_flare",
                            "name_ru": "Улучшенная вспышка",
                            "summary_ru": "Может защищать своей вспышкой уже не только себя, но и союзников рядом.",
                        }
                    ],
                    8: [
                        {
                            "key": "potent_spellcasting_light",
                            "name_ru": "Могущественное колдовство",
                            "summary_ru": "Усиливает урон заговоров яростью священного света.",
                        }
                    ],
                    17: [
                        {
                            "key": "corona_of_light",
                            "name_ru": "Корона света",
                            "summary_ru": "Окружает себя сиянием, делая врагов уязвимее для огненной и световой магии.",
                        }
                    ],
                },
            },
            {
                "key": "nature",
                "name_ru": "Домен природы",
                "description_ru": "Жрец природы соединяет божественную веру с дикой средой, зверями и стихийной стойкостью.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "acolyte_of_nature",
                            "name_ru": "Послушник природы",
                            "summary_ru": "Получает знания друидической магии и лучше чувствует природный мир.",
                        }
                    ],
                    2: [
                        {
                            "key": "charm_animals_and_plants",
                            "name_ru": "Очарование зверей и растений",
                            "summary_ru": "Божественной силой успокаивает зверей и живые растения вокруг.",
                        }
                    ],
                    6: [
                        {
                            "key": "dampen_elements",
                            "name_ru": "Ослабление стихий",
                            "summary_ru": "Снижает разрушительное действие огня, холода, молнии и других стихий.",
                        }
                    ],
                    8: [
                        {
                            "key": "divine_strike_nature",
                            "name_ru": "Божественный удар",
                            "summary_ru": "Оружейные атаки наполняются дополнительной природной силой.",
                        }
                    ],
                    17: [
                        {
                            "key": "master_of_nature",
                            "name_ru": "Повелитель природы",
                            "summary_ru": "Получает особенно сильный контроль над зверями и растительным миром.",
                        }
                    ],
                },
            },
            {
                "key": "tempest",
                "name_ru": "Домен бури",
                "description_ru": "Жрец бури приносит гром, молнии и карающую ярость неба прямо в центр схватки.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "wrath_of_the_storm",
                            "name_ru": "Гнев бури",
                            "summary_ru": "Отвечает на удар молнией или громом, наказывая тех, кто подошёл слишком близко.",
                        }
                    ],
                    2: [
                        {
                            "key": "destructive_wrath",
                            "name_ru": "Разрушительный гнев",
                            "summary_ru": "Может сделать урон грома и молнии особенно сокрушительным.",
                        }
                    ],
                    6: [
                        {
                            "key": "thunderbolt_strike",
                            "name_ru": "Удар грома",
                            "summary_ru": "Молнии жреца начинают отбрасывать врагов с позиции.",
                        }
                    ],
                    8: [
                        {
                            "key": "divine_strike_tempest",
                            "name_ru": "Божественный удар",
                            "summary_ru": "Оружейные атаки усиливаются раскатом грома.",
                        }
                    ],
                    17: [
                        {
                            "key": "stormborn",
                            "name_ru": "Рождённый бурей",
                            "summary_ru": "Летает на силе шторма и свободнее движется над полем боя.",
                        }
                    ],
                },
            },
            {
                "key": "trickery",
                "name_ru": "Домен обмана",
                "description_ru": "Жрец обмана полагается на хитрость, маскировку, двойников и запутывание врага.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "blessing_of_the_trickster",
                            "name_ru": "Благословение плута",
                            "summary_ru": "Помогает союзнику становиться заметно скрытнее и тише.",
                        }
                    ],
                    2: [
                        {
                            "key": "invoke_duplicity",
                            "name_ru": "Призыв двойника",
                            "summary_ru": "Создаёт иллюзорного двойника, который путает врагов и помогает колдовать.",
                        }
                    ],
                    6: [
                        {
                            "key": "cloak_of_shadows",
                            "name_ru": "Покров теней",
                            "summary_ru": "На короткое время скрывается во тьме прямо на поле боя.",
                        }
                    ],
                    8: [
                        {
                            "key": "divine_strike_trickery",
                            "name_ru": "Божественный удар",
                            "summary_ru": "Оружейные атаки получают дополнительную ядовитую или скрытную силу.",
                        }
                    ],
                    17: [
                        {
                            "key": "improved_duplicity",
                            "name_ru": "Совершенный двойник",
                            "summary_ru": "Может поддерживать сразу несколько обманных образов.",
                        }
                    ],
                },
            },
            {
                "key": "war",
                "name_ru": "Домен войны",
                "description_ru": "Жрец войны ведёт союзников в бой, усиливает удары и решает схватку прямым натиском.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "war_priest",
                            "name_ru": "Жрец войны",
                            "summary_ru": "Может чаще наносить дополнительные удары, поддерживая давление в ближнем бою.",
                        }
                    ],
                    2: [
                        {
                            "key": "guided_strike",
                            "name_ru": "Направленный удар",
                            "summary_ru": "Божественной волей превращает промах в точное попадание.",
                        }
                    ],
                    6: [
                        {
                            "key": "war_gods_blessing",
                            "name_ru": "Благословение бога войны",
                            "summary_ru": "Помогает союзнику рядом нанести решающий удар.",
                        }
                    ],
                    8: [
                        {
                            "key": "divine_strike_war",
                            "name_ru": "Божественный удар",
                            "summary_ru": "Оружейные атаки наполняются дополнительной священной мощью.",
                        }
                    ],
                    17: [
                        {
                            "key": "avatar_of_battle",
                            "name_ru": "Аватар битвы",
                            "summary_ru": "Становится заметно устойчивее к обычному оружию среди сражения.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {
            "type": "full_caster_prepared",
            "ability": "wis",
            "focus": ["holy_symbol"],
            "ritual": True,
            "spell_list_key": "cleric",
        },
        "spell_lists": {"class": "cleric"},
        "tags": [],
    },
    {
        "key": "druid",
        "name": "Druid",
        "name_ru": "Друид",
        "source": "PHB",
        "description_ru": "Хранитель природной магии, превращающийся в зверей и управляющий силами мира.",
        "hit_die": 8,
        "primary_abilities": ["wis"],
        "saving_throws": ["int", "wis"],
        "proficiencies": {
            "armor": ["light", "medium", "shields"],
            "weapons": ["club", "dagger", "dart", "javelin", "mace", "quarterstaff", "scimitar", "sickle", "sling", "spear"],
            "tools": ["herbalism_kit"],
            "skills_choose": {
                "count": 2,
                "from": ["arcana", "animal_handling", "insight", "medicine", "nature", "perception", "religion", "survival"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_druid_starting_equipment",
                "name_ru": "Стартовое снаряжение друида",
                "summary_ru": "а) деревянный щит или б) любое простое оружие; а) серп или б) любое простое рукопашное оружие; кожаный доспех, набор исследователя и друидический фокус.",
            }
        ],
        "features_by_level": {
            1: [
                {
                    "key": "druidic",
                    "name_ru": "Друидический",
                    "summary_ru": "Знает тайный язык друидов.",
                    "mechanics": {},
                },
                {
                    "key": "spellcasting",
                    "name_ru": "Использование заклинаний",
                    "summary_ru": "Друид подготавливает заклинания из списка друида и использует Мудрость как базовую характеристику.",
                    "mechanics": {
                        "type": "spellcasting",
                        "ability": "wis",
                        "progression": "full",
                        "known_style": "prepared",
                        "focus": ["druidic_focus"],
                        "ritual": True,
                    },
                },
            ],
            2: [
                {"key": "wild_shape", "name_ru": "Дикий облик", "summary_ru": "Может принимать форму зверя.", "mechanics": {}},
                {"key": "druid_circle", "name_ru": "Круг друидов", "summary_ru": "Выбор подкласса друида.", "mechanics": {"type": "subclass_choice"}},
            ],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            6: [{"key": "circle_feature_6", "name_ru": "Умение круга (6)", "summary_ru": "Особенность выбранного круга на 6 уровне.", "mechanics": {}}],
            8: [
                {"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}},
                {"key": "wild_shape_improvement", "name_ru": "Улучшение дикого облика", "summary_ru": "Дикий облик получает новые формы и мобильность.", "mechanics": {}},
            ],
            10: [{"key": "circle_feature_10", "name_ru": "Умение круга (10)", "summary_ru": "Особенность выбранного круга на 10 уровне.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            14: [{"key": "circle_feature_14", "name_ru": "Умение круга (14)", "summary_ru": "Высшая особенность выбранного круга.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            18: [
                {"key": "timeless_body", "name_ru": "Безвременное тело", "summary_ru": "Стареет медленнее и хуже ощущает возраст.", "mechanics": {}},
                {"key": "beast_spells", "name_ru": "Заклинания зверя", "summary_ru": "Может накладывать заклинания в форме зверя.", "mechanics": {}},
            ],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "archdruid", "name_ru": "Архидруид", "summary_ru": "Почти без ограничений использует Дикий облик.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "land",
                "name_ru": "Круг Земли",
                "description_ru": "Друид Земли опирается на силу выбранной местности, устойчивую магию и долгую связь с природой.",
                "choice_level": 2,
                "features_by_level": {
                    2: [
                        {
                            "key": "bonus_cantrip_land",
                            "name_ru": "Дополнительный заговор",
                            "summary_ru": "Получает ещё один друидический заговор и магическую тему своей местности.",
                        },
                        {
                            "key": "natural_recovery",
                            "name_ru": "Природное восстановление",
                            "summary_ru": "Частично возвращает ячейки заклинаний во время короткого отдыха.",
                        }
                    ],
                    6: [
                        {
                            "key": "lands_stride_circle",
                            "name_ru": "Шаг земли",
                            "summary_ru": "Свободнее движется через растения и трудную природную местность.",
                        }
                    ],
                    10: [
                        {
                            "key": "natures_ward",
                            "name_ru": "Защита природы",
                            "summary_ru": "Природа сама помогает жрецу против ядов, чар и вмешательства фей.",
                        }
                    ],
                    14: [
                        {
                            "key": "natures_sanctuary",
                            "name_ru": "Святилище природы",
                            "summary_ru": "Зверям и лесным существам сложнее решиться напасть на друида.",
                        }
                    ],
                },
            },
            {
                "key": "moon",
                "name_ru": "Круг Луны",
                "description_ru": "Друид Луны делает ставку на боевое превращение и использует Дикий облик как главную силу в схватке.",
                "choice_level": 2,
                "features_by_level": {
                    2: [
                        {
                            "key": "combat_wild_shape",
                            "name_ru": "Боевой дикий облик",
                            "summary_ru": "Превращается быстрее и эффективнее использует форму зверя прямо в бою.",
                        },
                        {
                            "key": "circle_forms",
                            "name_ru": "Формы круга",
                            "summary_ru": "Получает доступ к более опасным звериным обликам раньше других друидов.",
                        }
                    ],
                    6: [
                        {
                            "key": "primal_strike",
                            "name_ru": "Первобытный удар",
                            "summary_ru": "Удары в звериной форме считаются магическими.",
                        }
                    ],
                    10: [
                        {
                            "key": "elemental_wild_shape",
                            "name_ru": "Стихийный дикий облик",
                            "summary_ru": "Может принимать форму крупных стихийных существ.",
                        }
                    ],
                    14: [
                        {
                            "key": "thousand_forms",
                            "name_ru": "Тысяча форм",
                            "summary_ru": "Свободнее меняет внешний облик и использует превращение вне боя.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {
            "type": "full_caster_prepared",
            "ability": "wis",
            "focus": ["druidic_focus"],
            "ritual": True,
            "spell_list_key": "druid",
        },
        "spell_lists": {"class": "druid"},
        "tags": [],
    },
    {
        "key": "fighter",
        "name": "Fighter",
        "name_ru": "Воин",
        "source": "PHB",
        "description_ru": "Универсальный мастер оружия и доспехов, доводящий боевое ремесло до совершенства.",
        "hit_die": 10,
        "primary_abilities": ["str", "dex"],
        "saving_throws": ["str", "con"],
        "proficiencies": {
            "armor": ["light", "medium", "heavy", "shields"],
            "weapons": ["simple", "martial"],
            "tools": [],
            "skills_choose": {
                "count": 2,
                "from": ["acrobatics", "animal_handling", "athletics", "history", "insight", "intimidation", "perception", "survival"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_fighter_starting_equipment",
                "name_ru": "Стартовое снаряжение воина",
                "summary_ru": "а) кольчуга или б) кожаный доспех, длинный лук и 20 стрел; а) воинское оружие и щит или б) два воинских оружия; а) лёгкий арбалет и 20 болтов или б) два ручных топора; а) набор исследователя подземелий или б) набор путешественника.",
            }
        ],
        "features_by_level": {
            1: [
                {"key": "fighting_style", "name_ru": "Стиль боя", "summary_ru": "Выбор боевого стиля, определяющего сильную сторону воина.", "mechanics": {}},
                {"key": "second_wind", "name_ru": "Второе дыхание", "summary_ru": "Бонусным действием восстанавливает 1d10 + уровень воина хитов один раз до короткого или долгого отдыха.", "mechanics": {"type": "second_wind", "uses": "per_short_or_long_rest", "heal_dice": "1d10", "heal_bonus": "level", "action_cost": "bonus_action"}},
            ],
            2: [{"key": "action_surge", "name_ru": "Всплеск действий", "summary_ru": "Иногда получает дополнительное действие в ход.", "mechanics": {"type": "action_surge", "uses": "per_short_or_long_rest", "uses_max": 1, "action_cost": "none"}}],
            3: [{"key": "martial_archetype", "name_ru": "Воинский архетип", "summary_ru": "Выбор подкласса воина.", "mechanics": {"type": "subclass_choice"}}],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            5: [{"key": "extra_attack", "name_ru": "Дополнительная атака", "summary_ru": "Совершает больше атак действием.", "mechanics": {}}],
            6: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            7: [{"key": "archetype_feature_7", "name_ru": "Умение архетипа (7)", "summary_ru": "Особенность выбранного архетипа на 7 уровне.", "mechanics": {}}],
            8: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            9: [{"key": "indomitable_1", "name_ru": "Несгибаемый (1)", "summary_ru": "Может перебросить неудачный спасбросок.", "mechanics": {"type": "indomitable", "uses": "per_long_rest", "uses_max": 1}}],
            10: [{"key": "archetype_feature_10", "name_ru": "Умение архетипа (10)", "summary_ru": "Особенность выбранного архетипа на 10 уровне.", "mechanics": {}}],
            11: [{"key": "extra_attack_2", "name_ru": "Дополнительная атака (2)", "summary_ru": "Совершает три атаки действием.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            13: [{"key": "indomitable_2", "name_ru": "Несгибаемый (2)", "summary_ru": "Ещё одно применение Несгибаемого между отдыхами.", "mechanics": {"type": "indomitable_improvement", "uses_max_bonus": 1}}],
            14: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            15: [{"key": "archetype_feature_15", "name_ru": "Умение архетипа (15)", "summary_ru": "Особенность выбранного архетипа на 15 уровне.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            17: [
                {"key": "action_surge_2", "name_ru": "Всплеск действий (2)", "summary_ru": "Получает два использования Всплеска действий между отдыхами.", "mechanics": {"type": "action_surge_improvement", "uses_max_bonus": 1}},
                {"key": "indomitable_3", "name_ru": "Несгибаемый (3)", "summary_ru": "Третье использование Несгибаемого между отдыхами.", "mechanics": {"type": "indomitable_improvement", "uses_max_bonus": 1}},
            ],
            18: [{"key": "archetype_feature_18", "name_ru": "Умение архетипа (18)", "summary_ru": "Высшая особенность выбранного архетипа.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "extra_attack_3", "name_ru": "Дополнительная атака (3)", "summary_ru": "Совершает четыре атаки действием.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "champion",
                "name_ru": "Чемпион",
                "description_ru": "Чемпион делает ставку на чистую физическую форму, простую эффективность и стабильное давление в бою.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "improved_critical",
                            "name_ru": "Улучшенный критический удар",
                            "summary_ru": "Чаще наносит критические попадания обычными атаками.",
                        }
                    ],
                    7: [
                        {
                            "key": "remarkable_athlete",
                            "name_ru": "Выдающийся атлет",
                            "summary_ru": "Становится заметно сильнее в физических проверках и движении.",
                        }
                    ],
                    10: [
                        {
                            "key": "additional_fighting_style",
                            "name_ru": "Дополнительный стиль боя",
                            "summary_ru": "Осваивает ещё один стиль боя и становится универсальнее.",
                        }
                    ],
                    15: [
                        {
                            "key": "superior_critical",
                            "name_ru": "Превосходный критический удар",
                            "summary_ru": "Критические попадания случаются ещё чаще.",
                        }
                    ],
                    18: [
                        {
                            "key": "survivor",
                            "name_ru": "Выживший",
                            "summary_ru": "Быстро восстанавливает силы, пока ещё держится на ногах в бою.",
                        }
                    ],
                },
            },
            {
                "key": "battle_master",
                "name_ru": "Мастер боевых искусств",
                "description_ru": "Мастер боевых искусств побеждает за счёт приёмов, тактики и точного управления схваткой.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "combat_superiority",
                            "name_ru": "Превосходство в бою",
                            "summary_ru": "Получает кости превосходства и манёвры для точного контроля боя.",
                        },
                        {
                            "key": "student_of_war",
                            "name_ru": "Ученик войны",
                            "summary_ru": "Осваивает ремесленный инструмент как часть военной подготовки.",
                        }
                    ],
                    7: [
                        {
                            "key": "know_your_enemy",
                            "name_ru": "Познай врага",
                            "summary_ru": "Наблюдением оценивает сильные и слабые стороны противника.",
                        }
                    ],
                    10: [
                        {
                            "key": "improved_combat_superiority",
                            "name_ru": "Улучшенное превосходство",
                            "summary_ru": "Манёвры становятся сильнее и надёжнее.",
                        }
                    ],
                    15: [
                        {
                            "key": "relentless",
                            "name_ru": "Неутомимый",
                            "summary_ru": "Легче удерживает боевой ритм, даже когда ресурсы уже на исходе.",
                        }
                    ],
                    18: [
                        {
                            "key": "combat_superiority_master",
                            "name_ru": "Мастер превосходства",
                            "summary_ru": "Доводит манёвры и тактическое давление до вершины мастерства.",
                        }
                    ],
                },
            },
            {
                "key": "eldritch_knight",
                "name_ru": "Мистический рыцарь",
                "description_ru": "Мистический рыцарь сочетает воинское мастерство с защитной и боевой арканной магией.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "weapon_bond",
                            "name_ru": "Связь с оружием",
                            "summary_ru": "Привязывает к себе оружие и почти не рискует остаться без него.",
                        }
                    ],
                    7: [
                        {
                            "key": "war_magic",
                            "name_ru": "Боевая магия",
                            "summary_ru": "После заговора быстро переходит к удару оружием.",
                        }
                    ],
                    10: [
                        {
                            "key": "eldritch_strike",
                            "name_ru": "Мистический удар",
                            "summary_ru": "Попадание оружием делает следующую магию по цели опаснее.",
                        }
                    ],
                    15: [
                        {
                            "key": "arcane_charge",
                            "name_ru": "Магический рывок",
                            "summary_ru": "Используя боевой всплеск, перемещается по полю боя особенно резко.",
                        }
                    ],
                    18: [
                        {
                            "key": "improved_war_magic",
                            "name_ru": "Улучшенная боевая магия",
                            "summary_ru": "Ещё свободнее чередует заклинания и удары оружием.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {},
        "spell_lists": {},
        "tags": [],
    },
    {
        "key": "monk",
        "name": "Monk",
        "name_ru": "Монах",
        "source": "PHB",
        "description_ru": "Дисциплинированный мастер тела и духа, использующий ки и безоружные техники.",
        "hit_die": 8,
        "primary_abilities": ["dex", "wis"],
        "saving_throws": ["str", "dex"],
        "proficiencies": {
            "armor": [],
            "weapons": ["simple", "shortsword"],
            "tools": [],
            "tools_choose": {"count": 1, "from": ["artisan_tools", "musical_instrument"]},
            "skills_choose": {
                "count": 2,
                "from": ["acrobatics", "athletics", "history", "insight", "religion", "stealth"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_monk_starting_equipment",
                "name_ru": "Стартовое снаряжение монаха",
                "summary_ru": "а) короткий меч или б) любое простое оружие; а) набор исследователя подземелий или б) набор путешественника; 10 дротиков.",
            }
        ],
        "features_by_level": {
            1: [
                {"key": "unarmored_defense", "name_ru": "Защита без доспехов", "summary_ru": "КД рассчитывается от Мудрости и Ловкости.", "mechanics": {}},
                {"key": "martial_arts", "name_ru": "Боевые искусства", "summary_ru": "Безоружные удары и монашеское оружие становятся смертоноснее.", "mechanics": {}},
            ],
            2: [
                {"key": "ki", "name_ru": "Ки", "summary_ru": "Тратит очки ки на специальные боевые техники.", "mechanics": {}},
                {"key": "unarmored_movement", "name_ru": "Передвижение без доспехов", "summary_ru": "Двигается быстрее без доспехов и щита.", "mechanics": {}},
            ],
            3: [
                {"key": "monastic_tradition", "name_ru": "Монашеская традиция", "summary_ru": "Выбор подкласса монаха.", "mechanics": {"type": "subclass_choice"}},
                {"key": "deflect_missiles", "name_ru": "Отражение снарядов", "summary_ru": "Может уменьшать урон от стрел и подобных атак.", "mechanics": {}},
            ],
            4: [
                {"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}},
                {"key": "slow_fall", "name_ru": "Замедленное падение", "summary_ru": "Снижает урон от падения.", "mechanics": {}},
            ],
            5: [
                {"key": "extra_attack", "name_ru": "Дополнительная атака", "summary_ru": "Совершает больше атак действием.", "mechanics": {}},
                {"key": "stunning_strike", "name_ru": "Ошеломляющий удар", "summary_ru": "Может оглушить противника ударом ки.", "mechanics": {}},
            ],
            6: [
                {"key": "ki_empowered_strikes", "name_ru": "Удары, усиленные ки", "summary_ru": "Безоружные удары считаются магическими.", "mechanics": {}},
                {"key": "monastic_feature_6", "name_ru": "Умение традиции (6)", "summary_ru": "Особенность выбранной монашеской традиции.", "mechanics": {}},
            ],
            7: [
                {"key": "evasion", "name_ru": "Уклонение", "summary_ru": "Лучше избегает урона от областных эффектов.", "mechanics": {}},
                {"key": "stillness_of_mind", "name_ru": "Спокойствие разума", "summary_ru": "Может сбросить очарование и испуг действием.", "mechanics": {}},
            ],
            8: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            9: [{"key": "unarmored_movement_improvement", "name_ru": "Улучшенное передвижение", "summary_ru": "Может перемещаться по вертикалям и по воде в движении.", "mechanics": {}}],
            10: [{"key": "purity_of_body", "name_ru": "Чистота тела", "summary_ru": "Иммунитет к болезням и яду.", "mechanics": {}}],
            11: [{"key": "monastic_feature_11", "name_ru": "Умение традиции (11)", "summary_ru": "Особенность выбранной монашеской традиции.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            13: [{"key": "tongue_of_sun_and_moon", "name_ru": "Язык солнца и луны", "summary_ru": "Понимает речь любых существ и сам может быть понят.", "mechanics": {}}],
            14: [{"key": "diamond_soul", "name_ru": "Алмазная душа", "summary_ru": "Получает мастерство во всех спасбросках.", "mechanics": {}}],
            15: [{"key": "timeless_body", "name_ru": "Безвременное тело", "summary_ru": "Возраст почти не влияет на тело монаха.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            17: [{"key": "monastic_feature_17", "name_ru": "Умение традиции (17)", "summary_ru": "Высшая особенность выбранной монашеской традиции.", "mechanics": {}}],
            18: [{"key": "empty_body", "name_ru": "Пустое тело", "summary_ru": "Использует ки для невидимости и защиты от урона.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "perfect_self", "name_ru": "Совершенное я", "summary_ru": "В начале боя восстанавливает немного ки, если оно закончилось.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "open_hand",
                "name_ru": "Путь открытой ладони",
                "description_ru": "Монах открытой ладони полагается на чистую технику тела, контроль врага и идеальную дисциплину боя.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "open_hand_technique",
                            "name_ru": "Техника открытой ладони",
                            "summary_ru": "Удары ки позволяют сбивать врага, отталкивать его или рушить его стойку.",
                        }
                    ],
                    6: [
                        {
                            "key": "wholeness_of_body",
                            "name_ru": "Целостность тела",
                            "summary_ru": "Через внутреннюю дисциплину восстанавливает собственные силы.",
                        }
                    ],
                    11: [
                        {
                            "key": "tranquility",
                            "name_ru": "Безмятежность",
                            "summary_ru": "Окружает себя спокойствием, затрудняя прямое нападение врагов.",
                        }
                    ],
                    17: [
                        {
                            "key": "quivering_palm",
                            "name_ru": "Дрожащая ладонь",
                            "summary_ru": "Закладывает в цель разрушительный удар, который можно высвободить позже.",
                        }
                    ],
                },
            },
            {
                "key": "shadow",
                "name_ru": "Путь тени",
                "description_ru": "Монах тени действует скрытно, полагается на темноту, отвлечение и внезапный удар из укрытия.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "shadow_arts",
                            "name_ru": "Искусства тени",
                            "summary_ru": "Использует ки для темноты, скрытности и тихого проникновения.",
                        }
                    ],
                    6: [
                        {
                            "key": "shadow_step",
                            "name_ru": "Шаг тени",
                            "summary_ru": "Мгновенно перемещается между тенями и получает выгодную позицию.",
                        }
                    ],
                    11: [
                        {
                            "key": "cloak_of_shadows_monk",
                            "name_ru": "Покров теней",
                            "summary_ru": "Может растворяться во тьме, оставаясь почти незаметным.",
                        }
                    ],
                    17: [
                        {
                            "key": "opportunist",
                            "name_ru": "Оппортунист",
                            "summary_ru": "Молниеносно наказывает врага, который открылся рядом.",
                        }
                    ],
                },
            },
            {
                "key": "four_elements",
                "name_ru": "Путь четырёх стихий",
                "description_ru": "Монах четырёх стихий направляет ки в огонь, воду, воздух и землю, превращая технику в магию.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "disciple_of_the_elements",
                            "name_ru": "Ученик стихий",
                            "summary_ru": "Осваивает первые стихийные дисциплины и тратит ки на магические эффекты.",
                        }
                    ],
                    6: [
                        {
                            "key": "elemental_attunement_6",
                            "name_ru": "Углублённые стихии",
                            "summary_ru": "Открывает более сильные дисциплины и свободнее управляет стихиями.",
                        }
                    ],
                    11: [
                        {
                            "key": "elemental_attunement_11",
                            "name_ru": "Мастер стихий",
                            "summary_ru": "Стихийные техники становятся гибче и опаснее в бою.",
                        }
                    ],
                    17: [
                        {
                            "key": "elemental_attunement_17",
                            "name_ru": "Совершенство стихий",
                            "summary_ru": "Получает доступ к вершине стихийной дисциплины и контроля.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {},
        "spell_lists": {},
        "tags": [],
    },
    {
        "key": "paladin",
        "name": "Paladin",
        "name_ru": "Паладин",
        "source": "PHB",
        "description_ru": "Священный воитель, сочетающий тяжёлый бой, клятвы и божественную магию.",
        "hit_die": 10,
        "primary_abilities": ["str", "cha"],
        "saving_throws": ["wis", "cha"],
        "proficiencies": {
            "armor": ["light", "medium", "heavy", "shields"],
            "weapons": ["simple", "martial"],
            "tools": [],
            "skills_choose": {
                "count": 2,
                "from": ["athletics", "insight", "intimidation", "medicine", "persuasion", "religion"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_paladin_starting_equipment",
                "name_ru": "Стартовое снаряжение паладина",
                "summary_ru": "а) воинское оружие и щит или б) два воинских оружия; а) 5 метательных копий или б) любое простое рукопашное оружие; а) набор священника или б) набор исследователя подземелий; кольчуга и священный символ.",
            }
        ],
        "features_by_level": {
            1: [
                {"key": "divine_sense", "name_ru": "Божественное чутьё", "summary_ru": "Чувствует сильное зло, добро и святые места.", "mechanics": {}},
                {"key": "lay_on_hands", "name_ru": "Наложение рук", "summary_ru": "Лечит раны и очищает болезни запасом божественной силы.", "mechanics": {}},
            ],
            2: [
                {"key": "fighting_style", "name_ru": "Стиль боя", "summary_ru": "Выбор боевого стиля паладина.", "mechanics": {}},
                {
                    "key": "spellcasting",
                    "name_ru": "Использование заклинаний",
                    "summary_ru": "Паладин подготавливает заклинания и использует Харизму как базовую характеристику.",
                    "mechanics": {
                        "type": "spellcasting",
                        "ability": "cha",
                        "progression": "half",
                        "known_style": "prepared",
                        "spell_list_key": "paladin",
                    },
                },
                {"key": "divine_smite", "name_ru": "Божественная кара", "summary_ru": "Тратит ячейки заклинаний, чтобы усиливать удары светом.", "mechanics": {}},
            ],
            3: [
                {"key": "divine_health", "name_ru": "Божественное здоровье", "summary_ru": "Иммунитет к болезням.", "mechanics": {}},
                {"key": "sacred_oath", "name_ru": "Священная клятва", "summary_ru": "Выбор подкласса паладина.", "mechanics": {"type": "subclass_choice"}},
            ],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            5: [{"key": "extra_attack", "name_ru": "Дополнительная атака", "summary_ru": "Совершает больше атак действием.", "mechanics": {}}],
            6: [{"key": "aura_of_protection", "name_ru": "Аура защиты", "summary_ru": "Союзники рядом получают бонус к спасброскам.", "mechanics": {}}],
            7: [{"key": "oath_feature_7", "name_ru": "Умение клятвы (7)", "summary_ru": "Особенность выбранной клятвы на 7 уровне.", "mechanics": {}}],
            8: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            10: [{"key": "aura_of_courage", "name_ru": "Аура отваги", "summary_ru": "Паладин и союзники рядом не боятся испуга.", "mechanics": {}}],
            11: [{"key": "improved_divine_smite", "name_ru": "Улучшенная божественная кара", "summary_ru": "Каждый удар паладина несёт дополнительный светлый урон.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            14: [{"key": "cleansing_touch", "name_ru": "Очищающее касание", "summary_ru": "Может снять заклинание касанием.", "mechanics": {}}],
            15: [{"key": "oath_feature_15", "name_ru": "Умение клятвы (15)", "summary_ru": "Особенность выбранной клятвы на 15 уровне.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            18: [{"key": "aura_improvements", "name_ru": "Улучшенные ауры", "summary_ru": "Ауры паладина распространяются дальше.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "oath_feature_20", "name_ru": "Высшая особенность клятвы", "summary_ru": "Пиковая сила выбранной священной клятвы.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "devotion",
                "name_ru": "Клятва верности",
                "description_ru": "Паладин верности воплощает честь, защиту слабых и открытый священный свет на поле боя.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "sacred_weapon",
                            "name_ru": "Священное оружие",
                            "summary_ru": "Наполняет оружие светом и делает его опаснее для врагов.",
                        },
                        {
                            "key": "turn_the_unholy",
                            "name_ru": "Изгнание нечестивых",
                            "summary_ru": "Оттесняет нежить и исчадий силой священной клятвы.",
                        }
                    ],
                    7: [
                        {
                            "key": "aura_of_devotion",
                            "name_ru": "Аура верности",
                            "summary_ru": "Паладин и союзники рядом лучше противостоят очарованию.",
                        }
                    ],
                    15: [
                        {
                            "key": "purity_of_spirit",
                            "name_ru": "Чистота духа",
                            "summary_ru": "Постоянно находится под защитой от злонамеренной магии и влияний.",
                        }
                    ],
                    20: [
                        {
                            "key": "holy_nimbus",
                            "name_ru": "Священный нимб",
                            "summary_ru": "Окружает себя сиянием, которое жжёт врагов и усиливает присутствие паладина.",
                        }
                    ],
                },
            },
            {
                "key": "ancients",
                "name_ru": "Клятва древних",
                "description_ru": "Паладин древних хранит свет жизни, красоту мира и стойкость против тьмы и разрушения.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "natures_wrath",
                            "name_ru": "Гнев природы",
                            "summary_ru": "Призывает силы природы, чтобы удерживать и замедлять врагов.",
                        },
                        {
                            "key": "turn_the_faithless",
                            "name_ru": "Изгнание неверных",
                            "summary_ru": "Отталкивает фей и исчадий силой древней клятвы.",
                        }
                    ],
                    7: [
                        {
                            "key": "aura_of_warding",
                            "name_ru": "Аура защиты от чар",
                            "summary_ru": "Паладин и союзники рядом лучше переносят урон от заклинаний.",
                        }
                    ],
                    15: [
                        {
                            "key": "undying_sentinel",
                            "name_ru": "Неумирающий страж",
                            "summary_ru": "Становится особенно стойким и не так просто падает в бою.",
                        }
                    ],
                    20: [
                        {
                            "key": "elder_champion",
                            "name_ru": "Древний чемпион",
                            "summary_ru": "Ненадолго становится живым воплощением древней силы и обновления.",
                        }
                    ],
                },
            },
            {
                "key": "vengeance",
                "name_ru": "Клятва мести",
                "description_ru": "Паладин мести не отпускает опасную добычу и сосредоточен на преследовании главной цели.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "abjure_enemy",
                            "name_ru": "Отречение врага",
                            "summary_ru": "Сковывает опасного противника священной ненавистью и давлением воли.",
                        },
                        {
                            "key": "vow_of_enmity",
                            "name_ru": "Обет вражды",
                            "summary_ru": "Выбирает цель для беспощадного преследования и точных ударов.",
                        }
                    ],
                    7: [
                        {
                            "key": "relentless_avenger",
                            "name_ru": "Неумолимый мститель",
                            "summary_ru": "Легче держится за цель и быстро смещается вслед за ней.",
                        }
                    ],
                    15: [
                        {
                            "key": "soul_of_vengeance",
                            "name_ru": "Душа мести",
                            "summary_ru": "Нарушитель клятвы расплачивается за каждый шанс открыть защиту.",
                        }
                    ],
                    20: [
                        {
                            "key": "avenging_angel",
                            "name_ru": "Ангел мести",
                            "summary_ru": "Ненадолго превращается в крылатого карателя, наводящего ужас на врагов.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {
            "type": "half_caster_prepared",
            "ability": "cha",
            "spell_list_key": "paladin",
        },
        "spell_lists": {"class": "paladin"},
        "tags": [],
    },
    {
        "key": "ranger",
        "name": "Ranger",
        "name_ru": "Следопыт",
        "source": "PHB",
        "description_ru": "Охотник и разведчик, сочетающий боевые навыки, выживание и ограниченную природную магию.",
        "hit_die": 10,
        "primary_abilities": ["dex", "wis"],
        "saving_throws": ["str", "dex"],
        "proficiencies": {
            "armor": ["light", "medium", "shields"],
            "weapons": ["simple", "martial"],
            "tools": [],
            "skills_choose": {
                "count": 3,
                "from": ["animal_handling", "athletics", "insight", "investigation", "nature", "perception", "stealth", "survival"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_ranger_starting_equipment",
                "name_ru": "Стартовое снаряжение следопыта",
                "summary_ru": "а) чешуйчатый доспех или б) кожаный доспех; а) два коротких меча или б) два простых рукопашных оружия; а) набор исследователя подземелий или б) набор путешественника; длинный лук и колчан с 20 стрелами.",
            }
        ],
        "features_by_level": {
            1: [
                {"key": "favored_enemy", "name_ru": "Избранный враг", "summary_ru": "Специализируется на борьбе с выбранными типами врагов.", "mechanics": {}},
                {"key": "natural_explorer", "name_ru": "Исследователь природы", "summary_ru": "Лучше путешествует и выживает в избранной местности.", "mechanics": {}},
            ],
            2: [
                {"key": "fighting_style", "name_ru": "Стиль боя", "summary_ru": "Выбор боевого стиля следопыта.", "mechanics": {}},
                {
                    "key": "spellcasting",
                    "name_ru": "Использование заклинаний",
                    "summary_ru": "Следопыт знает ограниченное число заклинаний и использует Мудрость как базовую характеристику.",
                    "mechanics": {
                        "type": "spellcasting",
                        "ability": "wis",
                        "progression": "half",
                        "known_style": "known",
                        "spell_list_key": "ranger",
                    },
                },
            ],
            3: [
                {"key": "ranger_archetype", "name_ru": "Архетип следопыта", "summary_ru": "Выбор подкласса следопыта.", "mechanics": {"type": "subclass_choice"}},
                {"key": "primeval_awareness", "name_ru": "Первобытная осведомлённость", "summary_ru": "Чувствует присутствие особых существ через природную связь.", "mechanics": {}},
            ],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            5: [{"key": "extra_attack", "name_ru": "Дополнительная атака", "summary_ru": "Совершает больше атак действием.", "mechanics": {}}],
            6: [
                {"key": "favored_enemy_2", "name_ru": "Избранный враг (2)", "summary_ru": "Выбирает ещё одного избранного врага и усиливает прежних.", "mechanics": {}},
                {"key": "natural_explorer_2", "name_ru": "Исследователь природы (2)", "summary_ru": "Выбирает ещё один тип местности.", "mechanics": {}},
            ],
            7: [{"key": "archetype_feature_7", "name_ru": "Умение архетипа (7)", "summary_ru": "Особенность выбранного архетипа на 7 уровне.", "mechanics": {}}],
            8: [
                {"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}},
                {"key": "lands_stride", "name_ru": "Шаг земли", "summary_ru": "Легче проходит через сложную природную местность.", "mechanics": {}},
            ],
            10: [
                {"key": "natural_explorer_3", "name_ru": "Исследователь природы (3)", "summary_ru": "Выбирает третью любимую местность.", "mechanics": {}},
                {"key": "hide_in_plain_sight", "name_ru": "Скрытность на виду", "summary_ru": "Может особенно хорошо сливаться с окружением.", "mechanics": {}},
            ],
            11: [{"key": "archetype_feature_11", "name_ru": "Умение архетипа (11)", "summary_ru": "Особенность выбранного архетипа на 11 уровне.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            14: [{"key": "vanish", "name_ru": "Исчезновение", "summary_ru": "Может быстро прятаться и сложнее отслеживается.", "mechanics": {}}],
            15: [{"key": "archetype_feature_15", "name_ru": "Умение архетипа (15)", "summary_ru": "Высшая особенность выбранного архетипа.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            18: [{"key": "feral_senses", "name_ru": "Первобытные чувства", "summary_ru": "Чувствует скрытых врагов вокруг себя.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "foe_slayer", "name_ru": "Убийца врагов", "summary_ru": "Добавляет Мудрость к атаке или урону против избранных врагов.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "hunter",
                "name_ru": "Охотник",
                "description_ru": "Охотник подбирает приёмы под конкретную добычу и уверенно закрывает боевые роли следопыта.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "hunters_prey",
                            "name_ru": "Добыча охотника",
                            "summary_ru": "Выбирает боевой приём против одиночной цели, группы или убегающего врага.",
                        }
                    ],
                    7: [
                        {
                            "key": "defensive_tactics",
                            "name_ru": "Защитная тактика",
                            "summary_ru": "Осваивает способ лучше держаться под давлением врагов.",
                        }
                    ],
                    11: [
                        {
                            "key": "multiattack_hunter",
                            "name_ru": "Множественная атака",
                            "summary_ru": "Получает мощный приём для удара по нескольким врагам или по одной цели серией.",
                        }
                    ],
                    15: [
                        {
                            "key": "superior_hunters_defense",
                            "name_ru": "Высшая защита охотника",
                            "summary_ru": "Становится заметно труднее поразить или зажать в невыгодной позиции.",
                        }
                    ],
                },
            },
            {
                "key": "beast_master",
                "name_ru": "Повелитель зверей",
                "description_ru": "Повелитель зверей сражается не один, а вместе с верным животным спутником.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "rangers_companion",
                            "name_ru": "Спутник следопыта",
                            "summary_ru": "Получает зверя-компаньона, который растёт и помогает в бою.",
                        }
                    ],
                    7: [
                        {
                            "key": "exceptional_training",
                            "name_ru": "Исключительная дрессировка",
                            "summary_ru": "Зверь начинает действовать увереннее и полезнее в бою.",
                        }
                    ],
                    11: [
                        {
                            "key": "bestial_fury",
                            "name_ru": "Звериная ярость",
                            "summary_ru": "Спутник становится значительно опаснее при атаке.",
                        }
                    ],
                    15: [
                        {
                            "key": "share_spells",
                            "name_ru": "Общие заклинания",
                            "summary_ru": "Магия следопыта начинает лучше поддерживать его зверя.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {
            "type": "half_caster_known",
            "ability": "wis",
            "spell_list_key": "ranger",
        },
        "spell_lists": {"class": "ranger"},
        "tags": [],
    },
    {
        "key": "rogue",
        "name": "Rogue",
        "name_ru": "Плут",
        "source": "PHB",
        "description_ru": "Ловкий специалист по скрытности, обману и точечным ударам в уязвимые места.",
        "hit_die": 8,
        "primary_abilities": ["dex"],
        "saving_throws": ["dex", "int"],
        "proficiencies": {
            "armor": ["light"],
            "weapons": ["simple", "hand_crossbow", "longsword", "rapier", "shortsword"],
            "tools": ["thieves_tools"],
            "skills_choose": {
                "count": 4,
                "from": [
                    "acrobatics",
                    "athletics",
                    "deception",
                    "insight",
                    "intimidation",
                    "investigation",
                    "perception",
                    "performance",
                    "persuasion",
                    "sleight_of_hand",
                    "stealth",
                ],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_rogue_starting_equipment",
                "name_ru": "Стартовое снаряжение плута",
                "summary_ru": "а) рапира или б) короткий меч; а) короткий лук и колчан с 20 стрелами или б) короткий меч; а) набор взломщика, б) набор исследователя подземелий или в) набор путешественника; кожаный доспех, два кинжала и воровские инструменты.",
            }
        ],
        "features_by_level": {
            1: [
                {
                    "key": "expertise",
                    "name_ru": "Компетентность",
                    "summary_ru": "Удваивает бонус мастерства для выбранных навыков или инструментов.",
                    "mechanics": {
                        "type": "expertise",
                        "count": 2,
                        "allowed_kinds": ["skill", "tool"],
                        "default_choices": ["stealth", "tool:thieves_tools"],
                    },
                },
                {
                    "key": "sneak_attack",
                    "name_ru": "Скрытая атака",
                    "summary_ru": "Раз в ход наносит доп. урон атакой подходящим оружием при преимуществе или если союзник рядом с целью.",
                    "mechanics": {
                        "type": "sneak_attack",
                        "frequency": "once_per_turn",
                        "requires_weapon": True,
                        "requires_finesse_or_ranged": True,
                        "condition": "advantage_or_adjacent_ally_and_no_disadvantage",
                        "damage_progression": [
                            {"level_from": 1, "dice": "1d6"},
                            {"level_from": 3, "dice": "2d6"},
                            {"level_from": 5, "dice": "3d6"},
                            {"level_from": 7, "dice": "4d6"},
                            {"level_from": 9, "dice": "5d6"},
                            {"level_from": 11, "dice": "6d6"},
                            {"level_from": 13, "dice": "7d6"},
                            {"level_from": 15, "dice": "8d6"},
                            {"level_from": 17, "dice": "9d6"},
                            {"level_from": 19, "dice": "10d6"},
                        ],
                    },
                },
                {"key": "thieves_cant", "name_ru": "Воровской жаргон", "summary_ru": "Знает тайный язык преступного мира.", "mechanics": {}},
            ],
            2: [{"key": "cunning_action", "name_ru": "Хитрое действие", "summary_ru": "Бонусным действием может совершить Рывок, Отход или Засаду/Скрытие.", "mechanics": {"type": "cunning_action", "action_cost": "bonus_action", "allowed_actions": ["combat_dash", "combat_disengage", "combat_hide"]}}],
            3: [{"key": "roguish_archetype", "name_ru": "Архетип плута", "summary_ru": "Выбор подкласса плута.", "mechanics": {"type": "subclass_choice"}}],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            5: [
                {
                    "key": "uncanny_dodge",
                    "name_ru": "Невероятное уклонение",
                    "summary_ru": "Реакцией может уменьшить урон от одной атаки вдвое.",
                    "mechanics": {
                        "type": "uncanny_dodge",
                        "trigger": "after_hit_by_attack",
                        "cost": "reaction",
                        "damage_reduction": "half",
                    },
                }
            ],
            6: [
                {
                    "key": "expertise_2",
                    "name_ru": "Компетентность",
                    "summary_ru": "Получает ещё два случая удвоенного мастерства.",
                    "mechanics": {
                        "type": "expertise",
                        "count": 2,
                        "allowed_kinds": ["skill", "tool"],
                        "default_choices": ["perception", "sleight_of_hand"],
                    },
                }
            ],
            7: [
                {
                    "key": "evasion",
                    "name_ru": "Увёртливость",
                    "summary_ru": "При успешном спасброске Ловкости против эффекта на пол-урона не получает урон, а при провале получает только половину.",
                    "mechanics": {
                        "type": "evasion",
                        "trigger": "dex_save_for_half_damage",
                        "success_damage": "none",
                        "failure_damage": "half",
                    },
                }
            ],
            8: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            9: [{"key": "archetype_feature_9", "name_ru": "Умение архетипа (9)", "summary_ru": "Особенность выбранного архетипа на 9 уровне.", "mechanics": {}}],
            10: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            11: [
                {
                    "key": "reliable_talent",
                    "name_ru": "Надёжный талант",
                    "summary_ru": "Если при проверке с мастерством выпадает меньше 10 на d20, считается 10.",
                    "mechanics": {
                        "type": "reliable_talent",
                        "min_d20": 10,
                        "requires_proficiency": True,
                        "applies_to": ["ability_check"],
                    },
                }
            ],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            13: [{"key": "archetype_feature_13", "name_ru": "Умение архетипа (13)", "summary_ru": "Особенность выбранного архетипа на 13 уровне.", "mechanics": {}}],
            14: [
                {
                    "key": "blindsense",
                    "name_ru": "Слепое чутьё",
                    "summary_ru": "Чувствует скрытых или невидимых врагов рядом, полагаясь на слух и ощущения.",
                    "mechanics": {
                        "type": "blindsense",
                        "range_ft": 10,
                        "detects": ["hidden", "invisible"],
                        "requires_hearing": True,
                    },
                }
            ],
            15: [
                {
                    "key": "slippery_mind",
                    "name_ru": "Скользкий ум",
                    "summary_ru": "Получает мастерство в спасбросках Мудрости.",
                    "mechanics": {
                        "type": "saving_throw_proficiency",
                        "ability": "wis",
                        "source": "slippery_mind",
                    },
                }
            ],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            17: [{"key": "archetype_feature_17", "name_ru": "Умение архетипа (17)", "summary_ru": "Высшая особенность выбранного архетипа.", "mechanics": {}}],
            18: [
                {
                    "key": "elusive",
                    "name_ru": "Ускользание",
                    "summary_ru": "Пока плут не недееспособен, броски атаки против него не получают преимущество.",
                    "mechanics": {
                        "type": "elusive",
                        "denies_attack_advantage": True,
                        "unless_condition": "incapacitated",
                    },
                }
            ],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [
                {
                    "key": "stroke_of_luck",
                    "name_ru": "Удачный удар",
                    "summary_ru": "Раз за короткий или долгий отдых может превратить промах атакой в попадание; позже это же умение улучшит и проверки.",
                    "mechanics": {
                        "type": "stroke_of_luck",
                        "uses": "per_short_or_long_rest",
                        "uses_max": 1,
                        "attack_miss_to_hit": True,
                        "failed_check_d20_to_20": True,
                    },
                }
            ],
        },
        "subclasses": [
            {
                "key": "thief",
                "name_ru": "Вор",
                "description_ru": "Вор делает ставку на ловкость рук, скорость, проникновение и превосходство в городской среде.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "fast_hands",
                            "name_ru": "Быстрые руки",
                            "summary_ru": "Использует хитрое действие ещё гибче при работе с предметами и ловушками.",
                        },
                        {
                            "key": "second_story_work",
                            "name_ru": "Второй этаж",
                            "summary_ru": "Лучше карабкается и быстрее перемещается по сложной городской местности.",
                        }
                    ],
                    9: [
                        {
                            "key": "supreme_sneak",
                            "name_ru": "Высшая скрытность",
                            "summary_ru": "Особенно хорош в тихом подкрадывании и долгом скрытном движении.",
                        }
                    ],
                    13: [
                        {
                            "key": "use_magic_device",
                            "name_ru": "Использование магических устройств",
                            "summary_ru": "Легче обращается с магическими предметами, не предназначенными для него.",
                        }
                    ],
                    17: [
                        {
                            "key": "thiefs_reflexes",
                            "name_ru": "Рефлексы вора",
                            "summary_ru": "В самом начале схватки действует особенно быстро и резко.",
                        }
                    ],
                },
            },
            {
                "key": "assassin",
                "name_ru": "Убийца",
                "description_ru": "Убийца специализируется на внезапном ударе, маскировке и точечном устранении цели.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "assassinate",
                            "name_ru": "Устранение",
                            "summary_ru": "Особенно опасен против врагов, не успевших среагировать на начало боя.",
                        }
                    ],
                    9: [
                        {
                            "key": "infiltration_expertise",
                            "name_ru": "Мастер внедрения",
                            "summary_ru": "Умеет заранее готовить убедительное прикрытие и новую личность.",
                        }
                    ],
                    13: [
                        {
                            "key": "impostor",
                            "name_ru": "Самозванец",
                            "summary_ru": "Тонко копирует чужой облик, речь и манеры.",
                        }
                    ],
                    17: [
                        {
                            "key": "death_strike",
                            "name_ru": "Смертельный удар",
                            "summary_ru": "Внезапная атака по застигнутой цели становится особенно разрушительной.",
                        }
                    ],
                },
            },
            {
                "key": "arcane_trickster",
                "name_ru": "Мистический ловкач",
                "description_ru": "Мистический ловкач соединяет плутовские уловки с тонкой арканной магией и отвлечением врага.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "mage_hand_legerdemain",
                            "name_ru": "Ловкость волшебной руки",
                            "summary_ru": "Использует магическую руку для скрытных и особенно точных трюков.",
                        }
                    ],
                    9: [
                        {
                            "key": "magical_ambush",
                            "name_ru": "Магическая засада",
                            "summary_ru": "Если действует из скрытности, его магия труднее избегается.",
                        }
                    ],
                    13: [
                        {
                            "key": "versatile_trickster",
                            "name_ru": "Гибрый ловкач",
                            "summary_ru": "Использует магическую руку, чтобы легче открывать защиту противника.",
                        }
                    ],
                    17: [
                        {
                            "key": "spell_thief",
                            "name_ru": "Похититель заклинаний",
                            "summary_ru": "Может сорвать чужую магию и ненадолго присвоить её себе.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {},
        "spell_lists": {},
        "tags": [],
    },
    {
        "key": "sorcerer",
        "name": "Sorcerer",
        "name_ru": "Чародей",
        "source": "PHB",
        "description_ru": "Природный носитель магии, преобразующий врождённую силу через происхождение и метамагию.",
        "hit_die": 6,
        "primary_abilities": ["cha"],
        "saving_throws": ["con", "cha"],
        "proficiencies": {
            "armor": [],
            "weapons": ["dagger", "dart", "sling", "quarterstaff", "light_crossbow"],
            "tools": [],
            "skills_choose": {
                "count": 2,
                "from": ["arcana", "deception", "insight", "intimidation", "persuasion", "religion"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_sorcerer_starting_equipment",
                "name_ru": "Стартовое снаряжение чародея",
                "summary_ru": "а) лёгкий арбалет и 20 болтов или б) любое простое оружие; а) мешочек с компонентами или б) магическая фокусировка; а) набор исследователя подземелий или б) набор путешественника; два кинжала.",
            }
        ],
        "features_by_level": {
            1: [
                {
                    "key": "spellcasting",
                    "name_ru": "Использование заклинаний",
                    "summary_ru": "Чародей знает ограниченное число заклинаний и использует Харизму как базовую характеристику.",
                    "mechanics": {
                        "type": "spellcasting",
                        "ability": "cha",
                        "progression": "full",
                        "known_style": "known",
                        "spell_list_key": "sorcerer",
                    },
                },
                {"key": "sorcerous_origin", "name_ru": "Источник магии", "summary_ru": "Выбор подкласса чародея.", "mechanics": {"type": "subclass_choice"}},
            ],
            2: [{"key": "font_of_magic", "name_ru": "Источник магии", "summary_ru": "Получает очки чародейства для преобразования силы и ячеек.", "mechanics": {}}],
            3: [{"key": "metamagic", "name_ru": "Метамагия", "summary_ru": "Меняет способ действия заклинаний особыми приёмами.", "mechanics": {}}],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            6: [{"key": "origin_feature_6", "name_ru": "Умение происхождения (6)", "summary_ru": "Особенность выбранного магического происхождения.", "mechanics": {}}],
            8: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            10: [{"key": "metamagic_2", "name_ru": "Метамагия (2)", "summary_ru": "Осваивает дополнительные варианты метамагии.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            14: [{"key": "origin_feature_14", "name_ru": "Умение происхождения (14)", "summary_ru": "Особенность выбранного происхождения на 14 уровне.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            17: [{"key": "metamagic_3", "name_ru": "Метамагия (3)", "summary_ru": "Осваивает ещё одну форму метамагии.", "mechanics": {}}],
            18: [{"key": "origin_feature_18", "name_ru": "Умение происхождения (18)", "summary_ru": "Высшая особенность выбранного происхождения.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "sorcerous_restoration", "name_ru": "Восстановление чародейства", "summary_ru": "Короткий отдых возвращает часть очков чародейства.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "draconic_bloodline",
                "name_ru": "Наследие дракона",
                "description_ru": "Чародей драконьей крови черпает силу из древнего драконьего наследия и врождённой стойкости.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "dragon_ancestor",
                            "name_ru": "Драконий предок",
                            "summary_ru": "Выбирает тип драконьего наследия, который задаёт тему его силы.",
                        },
                        {
                            "key": "draconic_resilience",
                            "name_ru": "Драконья стойкость",
                            "summary_ru": "Становится живучее и крепче даже без доспехов.",
                        }
                    ],
                    6: [
                        {
                            "key": "elemental_affinity",
                            "name_ru": "Стихийное сродство",
                            "summary_ru": "Лучше проводит магию своего драконьего элемента и получает к ней защиту.",
                        }
                    ],
                    14: [
                        {
                            "key": "dragon_wings",
                            "name_ru": "Крылья дракона",
                            "summary_ru": "Отращивает крылья и уверенно поднимается в воздух.",
                        }
                    ],
                    18: [
                        {
                            "key": "draconic_presence",
                            "name_ru": "Драконье присутствие",
                            "summary_ru": "Подавляет врагов устрашающей или властной аурой.",
                        }
                    ],
                },
            },
            {
                "key": "wild_magic",
                "name_ru": "Дикая магия",
                "description_ru": "Чародей дикой магии управляет нестабильной силой, которая может резко менять ход сцены.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "wild_magic_surge",
                            "name_ru": "Всплеск дикой магии",
                            "summary_ru": "Иногда его заклинания вызывают непредсказуемые магические последствия.",
                        },
                        {
                            "key": "tides_of_chaos",
                            "name_ru": "Волны хаоса",
                            "summary_ru": "Может склонять удачу в свою сторону ценой новой нестабильности.",
                        }
                    ],
                    6: [
                        {
                            "key": "bend_luck",
                            "name_ru": "Искажение удачи",
                            "summary_ru": "Подправляет удачу союзника или врага в критический момент.",
                        }
                    ],
                    14: [
                        {
                            "key": "controlled_chaos",
                            "name_ru": "Управляемый хаос",
                            "summary_ru": "Лучше направляет случайный эффект дикой магии в нужную сторону.",
                        }
                    ],
                    18: [
                        {
                            "key": "spell_bombardment",
                            "name_ru": "Магическая бомбардировка",
                            "summary_ru": "Иногда его особенно мощные заклинания взрываются ещё сильнее.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {
            "type": "full_caster_known",
            "ability": "cha",
            "spell_list_key": "sorcerer",
        },
        "spell_lists": {"class": "sorcerer"},
        "tags": [],
    },
    {
        "key": "warlock",
        "name": "Warlock",
        "name_ru": "Колдун",
        "source": "PHB",
        "description_ru": "Заклинатель договора, получающий силу от потустороннего покровителя и тайных воззваний.",
        "hit_die": 8,
        "primary_abilities": ["cha"],
        "saving_throws": ["wis", "cha"],
        "proficiencies": {
            "armor": ["light"],
            "weapons": ["simple"],
            "tools": [],
            "skills_choose": {
                "count": 2,
                "from": ["arcana", "deception", "history", "intimidation", "investigation", "nature", "religion"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_warlock_starting_equipment",
                "name_ru": "Стартовое снаряжение колдуна",
                "summary_ru": "а) лёгкий арбалет и 20 болтов или б) любое простое оружие; а) мешочек с компонентами или б) магическая фокусировка; а) набор учёного или б) набор исследователя подземелий; кожаный доспех, любое простое оружие и два кинжала.",
            }
        ],
        "features_by_level": {
            1: [
                {"key": "otherworldly_patron", "name_ru": "Потусторонний покровитель", "summary_ru": "Выбор подкласса колдуна.", "mechanics": {"type": "subclass_choice"}},
                {
                    "key": "pact_magic",
                    "name_ru": "Магия договора",
                    "summary_ru": "Колдун использует особые ячейки договора и Харизму как базовую характеристику.",
                    "mechanics": {
                        "type": "spellcasting",
                        "ability": "cha",
                        "progression": "pact",
                        "known_style": "known",
                        "spell_list_key": "warlock",
                    },
                },
            ],
            2: [{"key": "eldritch_invocations", "name_ru": "Таинственные воззвания", "summary_ru": "Осваивает постоянные магические приёмы и улучшения.", "mechanics": {}}],
            3: [{"key": "pact_boon", "name_ru": "Предмет договора", "summary_ru": "Получает особый дар договора от покровителя.", "mechanics": {}}],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            6: [{"key": "patron_feature_6", "name_ru": "Умение покровителя (6)", "summary_ru": "Особенность выбранного покровителя на 6 уровне.", "mechanics": {}}],
            8: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            10: [{"key": "patron_feature_10", "name_ru": "Умение покровителя (10)", "summary_ru": "Особенность выбранного покровителя на 10 уровне.", "mechanics": {}}],
            11: [{"key": "mystic_arcanum_6", "name_ru": "Мистический арканум (6)", "summary_ru": "Получает одно великое заклинание 6 круга.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            13: [{"key": "mystic_arcanum_7", "name_ru": "Мистический арканум (7)", "summary_ru": "Получает одно великое заклинание 7 круга.", "mechanics": {}}],
            14: [{"key": "patron_feature_14", "name_ru": "Умение покровителя (14)", "summary_ru": "Высшая особенность выбранного покровителя.", "mechanics": {}}],
            15: [{"key": "mystic_arcanum_8", "name_ru": "Мистический арканум (8)", "summary_ru": "Получает одно великое заклинание 8 круга.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            17: [{"key": "mystic_arcanum_9", "name_ru": "Мистический арканум (9)", "summary_ru": "Получает одно великое заклинание 9 круга.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "eldritch_master", "name_ru": "Таинственный мастер", "summary_ru": "Быстро восстанавливает ячейки договора после короткой медитации.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "archfey",
                "name_ru": "Архифея",
                "description_ru": "Колдун архифеи действует через очарование, страх, уловки и неуловимую магию фей.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "fey_presence",
                            "name_ru": "Присутствие фей",
                            "summary_ru": "Может одним всплеском воли очаровать или напугать ближайших врагов.",
                        }
                    ],
                    6: [
                        {
                            "key": "misty_escape",
                            "name_ru": "Туманный побег",
                            "summary_ru": "После удара исчезает и отступает в безопасную позицию.",
                        }
                    ],
                    10: [
                        {
                            "key": "beguiling_defenses",
                            "name_ru": "Очаровывающая защита",
                            "summary_ru": "Лучше сопротивляется чужому очарованию и может обернуть его против врага.",
                        }
                    ],
                    14: [
                        {
                            "key": "dark_delirium",
                            "name_ru": "Тёмный бред",
                            "summary_ru": "Запирает цель в пугающем или чарующем личном наваждении.",
                        }
                    ],
                },
            },
            {
                "key": "fiend",
                "name_ru": "Исчадие",
                "description_ru": "Колдун исчадия получает силу через разрушение, огонь, жестокую волю и выживание любой ценой.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "dark_ones_blessing",
                            "name_ru": "Благословение Тёмного",
                            "summary_ru": "Падение врага временно подпитывает колдуна дополнительной живучестью.",
                        }
                    ],
                    6: [
                        {
                            "key": "dark_ones_own_luck",
                            "name_ru": "Собственная удача Тёмного",
                            "summary_ru": "В критический момент может резко улучшить свой бросок.",
                        }
                    ],
                    10: [
                        {
                            "key": "fiendish_resilience",
                            "name_ru": "Адская стойкость",
                            "summary_ru": "На время подстраивается под тип урона и переносит его легче.",
                        }
                    ],
                    14: [
                        {
                            "key": "hurl_through_hell",
                            "name_ru": "Швырок в преисподнюю",
                            "summary_ru": "На миг выбрасывает врага в адское видение, ломая ему бой и волю.",
                        }
                    ],
                },
            },
            {
                "key": "great_old_one",
                "name_ru": "Великий Древний",
                "description_ru": "Колдун Великого Древнего проникает в разум, ломает восприятие и использует чужое безумие.",
                "choice_level": 1,
                "features_by_level": {
                    1: [
                        {
                            "key": "awakened_mind",
                            "name_ru": "Пробуждённый разум",
                            "summary_ru": "Устанавливает мысленную связь и говорит прямо в сознание других существ.",
                        }
                    ],
                    6: [
                        {
                            "key": "entropic_ward",
                            "name_ru": "Энтропийная защита",
                            "summary_ru": "Искажает удачу врага и получает окно для ответного давления.",
                        }
                    ],
                    10: [
                        {
                            "key": "thought_shield",
                            "name_ru": "Щит мыслей",
                            "summary_ru": "Разум колдуна труднее прочитать или пробить психическим давлением.",
                        }
                    ],
                    14: [
                        {
                            "key": "create_thrall",
                            "name_ru": "Создание раба",
                            "summary_ru": "Ломает волю существа и надолго подчиняет его своему влиянию.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {
            "type": "pact_magic",
            "ability": "cha",
            "spell_list_key": "warlock",
        },
        "spell_lists": {"class": "warlock"},
        "tags": [],
    },
    {
        "key": "wizard",
        "name": "Wizard",
        "name_ru": "Волшебник",
        "source": "PHB",
        "description_ru": "Учёный заклинатель, собирающий магию через книгу заклинаний и школы волшебства.",
        "hit_die": 6,
        "primary_abilities": ["int"],
        "saving_throws": ["int", "wis"],
        "proficiencies": {
            "armor": [],
            "weapons": ["dagger", "dart", "sling", "quarterstaff", "light_crossbow"],
            "tools": [],
            "skills_choose": {
                "count": 2,
                "from": ["arcana", "history", "insight", "investigation", "medicine", "religion"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "phb_wizard_starting_equipment",
                "name_ru": "Стартовое снаряжение волшебника",
                "summary_ru": "а) боевой посох или б) кинжал; а) мешочек с компонентами или б) магическая фокусировка; а) набор учёного или б) набор путешественника; книга заклинаний.",
            }
        ],
        "features_by_level": {
            1: [
                {
                    "key": "spellcasting",
                    "name_ru": "Использование заклинаний",
                    "summary_ru": "Волшебник ведёт книгу заклинаний, готовит чары и использует Интеллект как базовую характеристику.",
                    "mechanics": {
                        "type": "spellcasting",
                        "ability": "int",
                        "progression": "full",
                        "known_style": "spellbook_prepared",
                        "ritual": True,
                        "spell_list_key": "wizard",
                    },
                },
                {"key": "arcane_recovery", "name_ru": "Магическое восстановление", "summary_ru": "Частично восстанавливает ячейки после короткого отдыха.", "mechanics": {}},
            ],
            2: [{"key": "arcane_tradition", "name_ru": "Магическая традиция", "summary_ru": "Выбор школы волшебства.", "mechanics": {"type": "subclass_choice"}}],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            6: [{"key": "tradition_feature_6", "name_ru": "Умение традиции (6)", "summary_ru": "Особенность выбранной школы на 6 уровне.", "mechanics": {}}],
            8: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            10: [{"key": "tradition_feature_10", "name_ru": "Умение традиции (10)", "summary_ru": "Особенность выбранной школы на 10 уровне.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            14: [{"key": "tradition_feature_14", "name_ru": "Умение традиции (14)", "summary_ru": "Высшая особенность выбранной школы волшебства.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            18: [{"key": "spell_mastery", "name_ru": "Мастерство заклинателя", "summary_ru": "Может свободно накладывать часть известных чар низкого круга.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "signature_spells", "name_ru": "Фирменные заклинания", "summary_ru": "Выбирает особые заклинания, к которым обращается чаще всего.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "abjuration",
                "name_ru": "Школа Ограждения",
                "description_ru": "Волшебник Ограждения сосредоточен на защите, преградах и выживании под магическим давлением.",
                "choice_level": 2,
                "features_by_level": {
                    2: [
                        {
                            "key": "abjuration_savant",
                            "name_ru": "Мастер Ограждения",
                            "summary_ru": "Быстрее и выгоднее осваивает заклинания своей школы.",
                        },
                        {
                            "key": "arcane_ward",
                            "name_ru": "Магический заслон",
                            "summary_ru": "Создаёт защитный запас магии, который принимает удары раньше самого волшебника.",
                        }
                    ],
                    6: [
                        {
                            "key": "projected_ward",
                            "name_ru": "Переданный заслон",
                            "summary_ru": "Может подставить свой магический щит под удар по союзнику рядом.",
                        }
                    ],
                    10: [
                        {
                            "key": "improved_abjuration",
                            "name_ru": "Улучшенное ограждение",
                            "summary_ru": "Становится особенно уверенным в противодействии чужой магии.",
                        }
                    ],
                    14: [
                        {
                            "key": "spell_resistance",
                            "name_ru": "Сопротивление заклинаниям",
                            "summary_ru": "Магия врагов хуже цепляется за самого волшебника.",
                        }
                    ],
                },
            },
            {
                "key": "conjuration",
                "name_ru": "Школа Вызова",
                "description_ru": "Волшебник Вызова управляет созданием предметов, переносом и призывом нужного в нужный момент.",
                "choice_level": 2,
                "features_by_level": {
                    2: [
                        {
                            "key": "conjuration_savant",
                            "name_ru": "Мастер Вызова",
                            "summary_ru": "Быстрее и выгоднее осваивает заклинания своей школы.",
                        },
                        {
                            "key": "minor_conjuration",
                            "name_ru": "Малое призывание",
                            "summary_ru": "Ненадолго создаёт нужный предмет прямо из магии.",
                        }
                    ],
                    6: [
                        {
                            "key": "benign_transposition",
                            "name_ru": "Безопасная перестановка",
                            "summary_ru": "Меняется местами с союзником или резко уходит из опасной позиции.",
                        }
                    ],
                    10: [
                        {
                            "key": "focused_conjuration",
                            "name_ru": "Сосредоточенный вызов",
                            "summary_ru": "Лучше удерживает концентрацию на своих призывающих чарах.",
                        }
                    ],
                    14: [
                        {
                            "key": "durable_summons",
                            "name_ru": "Стойкие призывы",
                            "summary_ru": "Призванные существа становятся заметно крепче и надёжнее.",
                        }
                    ],
                },
            },
            {
                "key": "divination",
                "name_ru": "Школа Прорицания",
                "description_ru": "Волшебник Прорицания читает нити вероятности и заранее подправляет ход событий.",
                "choice_level": 2,
                "features_by_level": {
                    2: [
                        {
                            "key": "divination_savant",
                            "name_ru": "Мастер Прорицания",
                            "summary_ru": "Быстрее и выгоднее осваивает заклинания своей школы.",
                        },
                        {
                            "key": "portent",
                            "name_ru": "Предзнаменование",
                            "summary_ru": "Заранее видит важные броски и может подменять ими исход сцены.",
                        }
                    ],
                    6: [
                        {
                            "key": "expert_divination",
                            "name_ru": "Опытный прорицатель",
                            "summary_ru": "Прорицательная магия помогает дольше поддерживать общий запас силы.",
                        }
                    ],
                    10: [
                        {
                            "key": "the_third_eye",
                            "name_ru": "Третий глаз",
                            "summary_ru": "Открывает особое чувство к скрытому, невидимому и тайному.",
                        }
                    ],
                    14: [
                        {
                            "key": "greater_portent",
                            "name_ru": "Великое предзнаменование",
                            "summary_ru": "Видит ещё больше ключевых вариантов будущего и чаще меняет судьбу.",
                        }
                    ],
                },
            },
            {
                "key": "enchantment",
                "name_ru": "Школа Очарования",
                "description_ru": "Волшебник Очарования управляет волей, вниманием и решениями других существ.",
                "choice_level": 2,
                "features_by_level": {
                    2: [
                        {
                            "key": "enchantment_savant",
                            "name_ru": "Мастер Очарования",
                            "summary_ru": "Быстрее и выгоднее осваивает заклинания своей школы.",
                        },
                        {
                            "key": "hypnotic_gaze",
                            "name_ru": "Гипнотический взгляд",
                            "summary_ru": "Может на короткое время буквально приковать цель к месту взглядом.",
                        }
                    ],
                    6: [
                        {
                            "key": "instinctive_charm",
                            "name_ru": "Инстинктивное очарование",
                            "summary_ru": "Заставляет врага в последний момент усомниться в выбранной цели.",
                        }
                    ],
                    10: [
                        {
                            "key": "split_enchantment",
                            "name_ru": "Разделённое очарование",
                            "summary_ru": "Некоторые чары начинают цеплять сразу две цели.",
                        }
                    ],
                    14: [
                        {
                            "key": "alter_memories",
                            "name_ru": "Изменение памяти",
                            "summary_ru": "Может стирать или подправлять воспоминание о магическом влиянии.",
                        }
                    ],
                },
            },
            {
                "key": "evocation",
                "name_ru": "Школа Воплощения",
                "description_ru": "Волшебник Воплощения управляет чистой боевой магией и умеет направлять разрушение точно в цель.",
                "choice_level": 2,
                "features_by_level": {
                    2: [
                        {
                            "key": "evocation_savant",
                            "name_ru": "Мастер Воплощения",
                            "summary_ru": "Быстрее и выгоднее осваивает заклинания своей школы.",
                        },
                        {
                            "key": "sculpt_spells",
                            "name_ru": "Формирование заклинаний",
                            "summary_ru": "Умеет щадить союзников, даже когда накрывает область мощной магией.",
                        }
                    ],
                    6: [
                        {
                            "key": "potent_cantrip",
                            "name_ru": "Мощный заговор",
                            "summary_ru": "Даже частично сорванный заговор всё равно оставляет давление на врага.",
                        }
                    ],
                    10: [
                        {
                            "key": "empowered_evocation",
                            "name_ru": "Усиленное воплощение",
                            "summary_ru": "Добавляет к боевой магии дополнительную личную мощь.",
                        }
                    ],
                    14: [
                        {
                            "key": "overchannel",
                            "name_ru": "Перенапряжение",
                            "summary_ru": "Может выжать из боевого заклинания максимум силы ценой перегрузки.",
                        }
                    ],
                },
            },
            {
                "key": "illusion",
                "name_ru": "Школа Иллюзии",
                "description_ru": "Волшебник Иллюзии побеждает обманом восприятия, ложными образами и гибкой сценической магией.",
                "choice_level": 2,
                "features_by_level": {
                    2: [
                        {
                            "key": "illusion_savant",
                            "name_ru": "Мастер Иллюзии",
                            "summary_ru": "Быстрее и выгоднее осваивает заклинания своей школы.",
                        },
                        {
                            "key": "improved_minor_illusion",
                            "name_ru": "Улучшенная малая иллюзия",
                            "summary_ru": "Даже простой иллюзорный трюк становится заметно убедительнее.",
                        }
                    ],
                    6: [
                        {
                            "key": "malleable_illusions",
                            "name_ru": "Податливые иллюзии",
                            "summary_ru": "Может по ходу сцены менять собственные иллюзии без полной перезагрузки.",
                        }
                    ],
                    10: [
                        {
                            "key": "illusory_self",
                            "name_ru": "Иллюзорное я",
                            "summary_ru": "В опасный момент подставляет под удар ложный образ вместо себя.",
                        }
                    ],
                    14: [
                        {
                            "key": "illusory_reality",
                            "name_ru": "Иллюзорная реальность",
                            "summary_ru": "Кратко делает часть своей иллюзии материальной и полезной на деле.",
                        }
                    ],
                },
            },
            {
                "key": "necromancy",
                "name_ru": "Школа Некромантии",
                "description_ru": "Волшебник Некромантии управляет жизненной силой, смертью и армией поднятых слуг.",
                "choice_level": 2,
                "features_by_level": {
                    2: [
                        {
                            "key": "necromancy_savant",
                            "name_ru": "Мастер Некромантии",
                            "summary_ru": "Быстрее и выгоднее осваивает заклинания своей школы.",
                        },
                        {
                            "key": "grim_harvest",
                            "name_ru": "Мрачная жатва",
                            "summary_ru": "Убийственная магия возвращает волшебнику часть сил.",
                        }
                    ],
                    6: [
                        {
                            "key": "undead_thralls",
                            "name_ru": "Слуги-нежить",
                            "summary_ru": "Поднятая нежить становится крепче, опаснее и послушнее.",
                        }
                    ],
                    10: [
                        {
                            "key": "inured_to_undeath",
                            "name_ru": "Привыкший к нежити",
                            "summary_ru": "Сам волшебник становится устойчивее к некротическим силам и истощению жизни.",
                        }
                    ],
                    14: [
                        {
                            "key": "command_undead",
                            "name_ru": "Подчинение нежити",
                            "summary_ru": "Может ломать волю нежити и обращать её себе на службу.",
                        }
                    ],
                },
            },
            {
                "key": "transmutation",
                "name_ru": "Школа Преобразования",
                "description_ru": "Волшебник Преобразования меняет свойства тел, предметов и среды под нужды отряда.",
                "choice_level": 2,
                "features_by_level": {
                    2: [
                        {
                            "key": "transmutation_savant",
                            "name_ru": "Мастер Преобразования",
                            "summary_ru": "Быстрее и выгоднее осваивает заклинания своей школы.",
                        },
                        {
                            "key": "minor_alchemy",
                            "name_ru": "Малая алхимия",
                            "summary_ru": "Ненадолго меняет свойства обычных материалов вокруг себя.",
                        }
                    ],
                    6: [
                        {
                            "key": "transmuters_stone",
                            "name_ru": "Камень преобразователя",
                            "summary_ru": "Создаёт камень, который даёт полезное улучшение выбранному носителю.",
                        }
                    ],
                    10: [
                        {
                            "key": "shapechanger",
                            "name_ru": "Меняющий облик",
                            "summary_ru": "Легче меняет собственную форму и приспосабливается к ситуации.",
                        }
                    ],
                    14: [
                        {
                            "key": "master_transmuter",
                            "name_ru": "Верховный преобразователь",
                            "summary_ru": "Выжимает из камня преобразователя мощный разовый эффект высшего уровня.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {
            "type": "full_caster_prepared_spellbook",
            "ability": "int",
            "ritual": True,
            "spell_list_key": "wizard",
        },
        "spell_lists": {"class": "wizard"},
        "tags": [],
    },
    {
        "key": "artificer",
        "name": "Artificer",
        "name_ru": "Изобретатель",
        "source": "TCE",
        "description_ru": "Магический ремесленник, сочетающий изобретательность, инструменты и подготовленную магию предметов.",
        "hit_die": 8,
        "primary_abilities": ["int"],
        "saving_throws": ["con", "int"],
        "proficiencies": {
            "armor": ["light", "medium", "shields"],
            "weapons": ["simple"],
            "tools": ["thieves_tools", "tinkers_tools"],
            "tools_choose": {"count": 1, "from": ["artisan_tools"]},
            "skills_choose": {
                "count": 2,
                "from": ["arcana", "history", "investigation", "medicine", "nature", "perception", "sleight_of_hand"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [
            {
                "key": "tce_artificer_starting_equipment",
                "name_ru": "Стартовое снаряжение изобретателя",
                "summary_ru": "Любые два простых оружия; лёгкий арбалет и 20 болтов; а) стёганый доспех или б) кожаный доспех; воровские инструменты и набор ремесленных инструментов на выбор; набор исследователя подземелий.",
            }
        ],
        "features_by_level": {
            1: [
                {
                    "key": "magical_tinkering",
                    "name_ru": "Магическое ремесло",
                    "summary_ru": "Наполняет крошечные предметы простыми магическими эффектами для света, звука, записи или запаха.",
                    "mechanics": {},
                },
                {
                    "key": "spellcasting",
                    "name_ru": "Использование заклинаний",
                    "summary_ru": "Изобретатель подготавливает заклинания из списка artificer и использует Интеллект как базовую характеристику.",
                    "mechanics": {
                        "type": "spellcasting",
                        "ability": "int",
                        "progression": "half",
                        "known_style": "prepared",
                        "focus": ["thieves_tools", "artisan_tools"],
                        "ritual": True,
                        "spell_list_key": "artificer",
                    },
                },
            ],
            2: [
                {"key": "infuse_item", "name_ru": "Инфузия предмета", "summary_ru": "Создаёт магические инфузии и временно наделяет ими предметы.", "mechanics": {}},
            ],
            3: [
                {"key": "artificer_specialist", "name_ru": "Специалист-изобретатель", "summary_ru": "Выбор подкласса изобретателя.", "mechanics": {"type": "subclass_choice"}},
                {"key": "the_right_tool_for_the_job", "name_ru": "Нужный инструмент для дела", "summary_ru": "Может быстро создать требуемый набор ремесленных инструментов.", "mechanics": {}},
            ],
            4: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            5: [{"key": "specialist_feature_5", "name_ru": "Умение специалиста (5)", "summary_ru": "Особенность выбранной специализации на 5 уровне.", "mechanics": {}}],
            6: [{"key": "tool_expertise", "name_ru": "Мастерство инструментов", "summary_ru": "Удваивает бонус мастерства для проверок инструментами, которыми владеет.", "mechanics": {}}],
            7: [{"key": "flash_of_genius", "name_ru": "Вспышка гениальности", "summary_ru": "Реакцией добавляет Интеллект к проверке или спасброску союзника либо своему.", "mechanics": {}}],
            8: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            9: [{"key": "specialist_feature_9", "name_ru": "Умение специалиста (9)", "summary_ru": "Особенность выбранной специализации на 9 уровне.", "mechanics": {}}],
            10: [
                {"key": "magic_item_adept", "name_ru": "Адепт магических предметов", "summary_ru": "Лучше настраивается на магические предметы и быстрее создаёт обычные магические вещи.", "mechanics": {}},
                {"key": "infused_item_improvement", "name_ru": "Улучшенные инфузии", "summary_ru": "Может поддерживать больше инфузий и знает более сильные варианты.", "mechanics": {}},
            ],
            11: [{"key": "spell_storing_item", "name_ru": "Предмет-хранилище заклинания", "summary_ru": "Закрепляет известное заклинание в предмете для многократного применения.", "mechanics": {}}],
            12: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            14: [{"key": "magic_item_savant", "name_ru": "Знаток магических предметов", "summary_ru": "Игнорирует часть требований к магическим предметам и настраивается на большее число вещей.", "mechanics": {}}],
            15: [{"key": "specialist_feature_15", "name_ru": "Умение специалиста (15)", "summary_ru": "Продвинутая особенность выбранной специализации.", "mechanics": {}}],
            16: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            18: [{"key": "magic_item_master", "name_ru": "Мастер магических предметов", "summary_ru": "Может одновременно настроиться на ещё большее число магических предметов.", "mechanics": {}}],
            19: [{"key": "asi", "name_ru": "Увеличение характеристик", "summary_ru": "Улучшение характеристик или выбор таланта.", "mechanics": {}}],
            20: [{"key": "soul_of_artifice", "name_ru": "Душа изобретения", "summary_ru": "Пиковая связь с магическими предметами усиливает спасброски и позволяет удержаться на грани поражения.", "mechanics": {}}],
        },
        "subclasses": [
            {
                "key": "alchemist",
                "name_ru": "Алхимик",
                "description_ru": "Алхимик работает с эликсирами, реагентами, поддержкой союзников и полезными магическими смесями.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "tool_proficiency_alchemist",
                            "name_ru": "Инструменты алхимика",
                            "summary_ru": "Получает рабочую специализацию через алхимические принадлежности.",
                        },
                        {
                            "key": "experimental_elixir",
                            "name_ru": "Экспериментальный эликсир",
                            "summary_ru": "Создаёт магические эликсиры с разными полезными эффектами.",
                        }
                    ],
                    5: [
                        {
                            "key": "alchemical_savant",
                            "name_ru": "Алхимический виртуоз",
                            "summary_ru": "Сильнее лечит и усиливает часть алхимической магии.",
                        }
                    ],
                    9: [
                        {
                            "key": "restorative_reagents",
                            "name_ru": "Восстанавливающие реагенты",
                            "summary_ru": "Лечит и поддерживает союзников ещё эффективнее.",
                        }
                    ],
                    15: [
                        {
                            "key": "chemical_mastery",
                            "name_ru": "Химическое мастерство",
                            "summary_ru": "Получает высший уровень контроля над алхимией и защитой от веществ.",
                        }
                    ],
                },
            },
            {
                "key": "armorer",
                "name_ru": "Бронник",
                "description_ru": "Бронник превращает доспех в магическую платформу: защитную, скрытную или штурмовую.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "tools_of_the_trade_armorer",
                            "name_ru": "Инструменты бронника",
                            "summary_ru": "Осваивает ремесло, связанное с тяжёлой магической бронёй.",
                        },
                        {
                            "key": "arcane_armor",
                            "name_ru": "Тайная броня",
                            "summary_ru": "Создаёт особую магическую броню, связанную с телом и силой изобретателя.",
                        },
                        {
                            "key": "armor_model",
                            "name_ru": "Модель брони",
                            "summary_ru": "Выбирает режим брони, например защитный или скрытный.",
                        }
                    ],
                    5: [
                        {
                            "key": "extra_attack_armorer",
                            "name_ru": "Дополнительная атака",
                            "summary_ru": "Может атаковать дважды действием.",
                        }
                    ],
                    9: [
                        {
                            "key": "armor_modifications",
                            "name_ru": "Модификации брони",
                            "summary_ru": "Улучшают броню дополнительными магическими настройками.",
                        }
                    ],
                    15: [
                        {
                            "key": "perfected_armor",
                            "name_ru": "Совершенная броня",
                            "summary_ru": "Высшая версия выбранной модели брони.",
                        }
                    ],
                },
            },
            {
                "key": "artillerist",
                "name_ru": "Артиллерист",
                "description_ru": "Артиллерист делает упор на боевую магию, разрушительные эффекты и магические орудия поддержки.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "tools_of_the_trade_artillerist",
                            "name_ru": "Инструменты артиллериста",
                            "summary_ru": "Осваивает ремесло, связанное с боевыми магическими устройствами.",
                        },
                        {
                            "key": "eldritch_cannon",
                            "name_ru": "Мистическая пушка",
                            "summary_ru": "Создаёт магическое орудие с разными режимами атаки и поддержки.",
                        }
                    ],
                    5: [
                        {
                            "key": "arcane_firearm",
                            "name_ru": "Тайное огнестрельное орудие",
                            "summary_ru": "Усиливает урон некоторых заклинаний через специально подготовленный предмет.",
                        }
                    ],
                    9: [
                        {
                            "key": "explosive_cannon",
                            "name_ru": "Взрывная пушка",
                            "summary_ru": "Пушка становится опаснее и гибче в бою.",
                        }
                    ],
                    15: [
                        {
                            "key": "fortified_position",
                            "name_ru": "Укреплённая позиция",
                            "summary_ru": "Создаёт устойчивую боевую точку и усиливает контроль пространства.",
                        }
                    ],
                },
            },
            {
                "key": "battle_smith",
                "name_ru": "Боевой кузнец",
                "description_ru": "Боевой кузнец сочетает магическое ремесло, оружие и боевого конструкта-помощника.",
                "choice_level": 3,
                "features_by_level": {
                    3: [
                        {
                            "key": "tools_of_the_trade_battle_smith",
                            "name_ru": "Инструменты боевого кузнеца",
                            "summary_ru": "Осваивает ремесло, связанное с оружием и боевыми механизмами.",
                        },
                        {
                            "key": "battle_ready",
                            "name_ru": "Готовность к бою",
                            "summary_ru": "Лучше использует магический интеллект в бою с оружием.",
                        },
                        {
                            "key": "steel_defender",
                            "name_ru": "Стальной защитник",
                            "summary_ru": "Создаёт боевого металлического спутника, который помогает в бою.",
                        }
                    ],
                    5: [
                        {
                            "key": "extra_attack_battle_smith",
                            "name_ru": "Дополнительная атака",
                            "summary_ru": "Может атаковать дважды действием.",
                        }
                    ],
                    9: [
                        {
                            "key": "arcane_jolt",
                            "name_ru": "Тайный импульс",
                            "summary_ru": "Усиливает удары или помогает лечить союзников через магический разряд.",
                        }
                    ],
                    15: [
                        {
                            "key": "improved_defender",
                            "name_ru": "Улучшенный защитник",
                            "summary_ru": "Стальной защитник становится заметно опаснее и надёжнее.",
                        }
                    ],
                },
            },
        ],
        "spellcasting": {
            "type": "half_caster_prepared",
            "ability": "int",
            "focus": ["thieves_tools", "artisan_tools"],
            "ritual": True,
            "spell_list_key": "artificer",
        },
        "spell_lists": {"class": "artificer"},
        "tags": [],
    },
    {
        "key": "mage",
        "name": "Mage",
        "name_ru": "Маг",
        "source": "legacy",
        "description_ru": "Legacy-запись для обратной совместимости старого ключа класса; в актуальном каталоге должна резолвиться как wizard.",
        "hit_die": 6,
        "primary_abilities": ["int"],
        "saving_throws": ["int", "wis"],
        "proficiencies": {
            "armor": [],
            "weapons": ["dagger", "dart", "sling", "quarterstaff", "light_crossbow"],
            "tools": [],
            "skills_choose": {
                "count": 2,
                "from": ["arcana", "history", "insight", "investigation", "medicine", "religion"],
            },
        },
        "skill_choices": {},
        "starting_equipment": [],
        "features_by_level": {},
        "subclasses": [],
        "spellcasting": {
            "type": "full_caster_prepared_spellbook",
            "ability": "int",
            "ritual": True,
            "spell_list_key": "wizard",
            "legacy_alias_for": "wizard",
        },
        "spell_lists": {"class": "wizard"},
        "tags": ["legacy", "alias_for_wizard", "not_for_new_characters"],
    },
]
