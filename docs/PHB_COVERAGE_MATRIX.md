# PHB Coverage Matrix

Документ фиксирует первичную матрицу покрытия Player's Handbook по текущему состоянию репозитория `ai-dnd-bot`.

Принципы:
- статусы выставлены консервативно;
- учитывается только то, что реально видно в коде и уже существующих документах проекта;
- каталожные заготовки и placeholder-данные не считаются полным покрытием;
- если блок реализован только для части сценариев или в race-specific виде, статус — `Partial`.

Статусы:
- `Supported` — базовый PHB-блок реализован и используется в коде как рабочая механика;
- `Partial` — есть важные куски, но покрытие неполное, фрагментированное или ограничено отдельными сценариями;
- `Missing` — в репозитории нет заметной рабочей реализации блока.

## Character creation

- Status: `Partial`
- Что уже есть в проекте:
  - есть HTTP-поток создания персонажа с выбором класса, расы, подрасы, части race choices, ASI и стартовых skill ranks;
  - персонаж создаётся на 1 уровне, получает hit die по классу, базовые HP/STA и скорость;
  - race features собираются в структурированный payload и сохраняются в `Character`.
- Чего не хватает:
  - нет полноценной PHB-сборки персонажа по всем классам/бэкграундам/стартовому снаряжению;
  - нет отдельной завершённой модели class features при создании;
  - стартовое снаряжение в class catalog в основном placeholder;
  - нет общего PHB-пайплайна выбора background, saving throw proficiencies, class proficiencies и class equipment packages как законченного шага создания.
- Источники истины:
  - `app/web/http_routes.py`
  - `app/web/gameplay_helpers.py`
  - `app/rules/character_catalog.py`
  - `docs/PROJECT_CONTEXT.md`

## Ability scores and modifiers

- Status: `Supported`
- Что уже есть в проекте:
  - зафиксирован переход `0..100 -> ability score 3..20`;
  - ability modifier считается по PHB-формуле;
  - proficiency bonus считается по PHB-диапазонам уровней;
  - эти значения реально используются в derived AC, attack profile, initiative и checks.
- Чего не хватает:
  - нет отдельной полноценной PHB-системы point buy / standard array как завершённого правила;
  - часть UI/создания использует проектные ограничения поверх PHB-поведения.
- Источники истины:
  - `docs/PHB_TRUTH.md`
  - `app/rules/phb_math.py`
  - `app/rules/derived_stats.py`
  - `app/web/ws_checks.py`

## Skills and proficiency

- Status: `Partial`
- Что уже есть в проекте:
  - есть отображение навыков на базовые характеристики;
  - бонус навыка строится из ability mod и proficiency bonus;
  - поддержан legacy/compat слой для rank-based skill model, включая expertise-подобный режим;
  - starter skills поднимаются при создании персонажа;
  - skill XP и отдельный progression payload реально существуют в web-слое.
- Чего не хватает:
  - skill-система не совпадает с чистым PHB, потому что завязана на `rank/xp` вместо только proficiency/expertise;
  - нет полной PHB-модели proficiencies по классам/бэкграундам как единого источника истины;
  - не видно завершённой общей модели tool proficiencies.
- Источники истины:
  - `docs/PHB_TRUTH.md`
  - `app/web/ws_checks.py`
  - `app/web/server_impl.py`
  - `app/web/http_routes.py`
  - `app/rules/character_catalog.py`

## Saving throws

- Status: `Partial`
- Что уже есть в проекте:
  - PHB-модификаторы и proficiency bonus доступны как строительные блоки;
  - есть множество race-specific save hooks: advantage против frightened/charmed/poison, magic resistance, death save advantage и похожие случаи;
  - часть save-логики покрыта как runtime в `ws_handlers` и как combat/rules tests.
- Чего не хватает:
  - нет единого общего save engine для всех PHB saving throws;
  - нет законченной общей модели class saving throw proficiencies, применяемой по всем персонажам;
  - save flow остаётся во многом фрагментированным по feature-specific helper-ам.
- Источники истины:
  - `app/web/ws_handlers.py`
  - `app/web/ws_checks.py`
  - `app/rules/phb_math.py`
  - `app/rules/character_catalog.py`
  - `app/combat/test_shared_save_advantage_pipeline.py`

## Combat core

- Status: `Partial`
- Что уже есть в проекте:
  - есть отдельный live combat runtime;
  - поддержаны initiative order, round/turn flow, атака по AC, hit/miss/crit, damage application, победа/завершение боя;
  - есть persist/restore combat snapshot и combat log UI patch flow;
  - combat narration и bridge к web-слою оформлены отдельными модулями.
- Чего не хватает:
  - не видно полного PHB-покрытия по cover, ready action, grappling rules, shove rules, mounted combat и другим базовым подсистемам;
  - часть боёвки всё ещё собрана как MVP и расширяется race-specific логикой;
  - production-ограничение на in-memory combat runtime остаётся.
- Источники истины:
  - `docs/COMBAT_MAP.md`
  - `docs/PROJECT_CONTEXT.md`
  - `app/combat/state.py`
  - `app/combat/turns.py`
  - `app/combat/live_actions.py`
  - `app/combat/resolution.py`
  - `app/web/combat_bridge.py`

## Action economy

- Status: `Partial`
- Что уже есть в проекте:
  - в combat state есть `action_available`, `bonus_action_available`, `reaction_available`;
  - поддержаны стандартные action-команды вроде attack, dodge, dash, disengage, help, use object, end turn, escape;
  - есть tests на границы action economy и на race features, завязанные на bonus action / reaction.
- Чего не хватает:
  - не видно полной общей PHB-модели всех action types и их системных ограничений;
  - bonus action и reaction coverage выглядит точечным, а не всеобъемлющим;
  - нет общей модели Ready action и concentration interaction.
- Источники истины:
  - `app/combat/state.py`
  - `app/combat/live_actions.py`
  - `app/combat/test_action_available_guard.py`
  - `app/combat/test_opportunity_attack_reaction.py`
  - `docs/COMBAT_MAP.md`

## Weapons and armor

- Status: `Partial`
- Что уже есть в проекте:
  - есть typed item schema для weapon/armor/shield;
  - в item catalog описаны базовые образцы оружия, брони и щита;
  - `compute_ac` учитывает light/medium/heavy armor, dex cap и shield bonus;
  - `compute_attack_profile` выбирает STR/DEX по PHB-подобным правилам для ranged/finesse/ammunition;
  - есть natural armor и natural weapon integration через `race_features`.
- Чего не хватает:
  - item catalog очень узкий, далеко не полный PHB arsenal;
  - weapon mastery поля есть в модели, но это не PHB 2014 core и не выглядит как завершённый боевой слой;
  - не видно общей поддержки всех weapon properties, dual wielding rules, versatile usage, loading/ammunition logistics.
- Источники истины:
  - `docs/PHB_TRUTH.md`
  - `docs/EQUIPMENT_SPEC.md`
  - `app/rules/item_catalog.py`
  - `app/rules/items.py`
  - `app/rules/derived_stats.py`
  - `app/rules/equipment_slots.py`

## Equipment / inventory

- Status: `Partial`
- Что уже есть в проекте:
  - есть отдельная inventory normalization и equip map;
  - предметы имеют `def`, quantity, slots, wear groups, consume spec;
  - есть команды equip/unequip в web-слое;
  - consumables, включая healing potions, реально используются в бою.
- Чего не хватает:
  - нет полного PHB equipment catalog;
  - нет завершённой экономики веса/encumbrance, стоимости, контейнеров и общего item interaction уровня PHB;
  - стартовое снаряжение классов пока не развёрнуто в полный набор.
- Источники истины:
  - `docs/EQUIPMENT_SPEC.md`
  - `app/web/inventory_helpers.py`
  - `app/web/server_impl.py`
  - `app/rules/item_catalog.py`
  - `app/rules/items.py`

## Rest / healing / death saves

- Status: `Partial`
- Что уже есть в проекте:
  - есть long rest / short rest helpers;
  - есть hit dice recovery и spend logic;
  - healing consumables работают в бою;
  - death saves, stabilization, damage at 0 HP и auto-logic на 0 HP покрыты тестами и live combat flow;
  - long rest умеет сбрасывать часть innate spell usages.
- Чего не хватает:
  - short/long rest rules не выглядят полным PHB rest subsystem;
  - `apply_short_rest` и `apply_long_rest` в rules-слое пока очень упрощены;
  - не видно полного покрытия exhaustion, rest interruptions, class resource refresh по PHB.
- Источники истины:
  - `docs/PROJECT_CONTEXT.md`
  - `app/rules/phb_rest.py`
  - `app/combat/live_actions.py`
  - `app/combat/test_death_saves.py`
  - `app/combat/test_stabilize_action.py`
  - `app/web/test_long_rest_resets_innate_spells.py`

## Conditions

- Status: `Partial`
- Что уже есть в проекте:
  - runtime хранит `conditions` внутри `race_features.runtime` для ряда feature-specific сценариев;
  - есть boundary tests для `poisoned`, `frightened`, `grappled` и связанной очистки runtime;
  - есть immunities/advantages against conditions в race feature payloads.
- Чего не хватает:
  - нет единой полноценной PHB conditions engine;
  - condition behavior в основном точечный и встроен в race/combat helper-ы;
  - нет общего системного слоя для blinded, stunned, restrained, prone и других условий как полного PHB набора.
- Источники истины:
  - `app/combat/state.py`
  - `app/combat/live_actions.py`
  - `app/combat/test_shared_condition_runtime_boundary.py`
  - `app/combat/test_shared_nested_condition_poisoned_boundary.py`
  - `app/combat/test_shared_nested_condition_frightened_boundary.py`
  - `app/combat/test_shared_nested_condition_grappled_boundary.py`

## Classes / subclasses

- Status: `Partial`
- Что уже есть в проекте:
  - есть PHB class keys и базовый class catalog;
  - hit die по классу реально используется при создании персонажа;
  - для варвара каталог заметно подробнее: features by level и subclasses;
  - есть class presets и starter skills в web-слое.
- Чего не хватает:
  - большинство классов в `BASE_CLASS_CATALOG` представлены минимальными заглушками;
  - нет полноценного runtime class feature layer;
  - subclasses в коде скорее данные каталога, чем реально поддержанный игровой слой.
- Источники истины:
  - `app/rules/character_catalog.py`
  - `app/rules/phb_progression.py`
  - `app/web/gameplay_helpers.py`
  - `app/web/server_impl.py`

## Level progression

- Status: `Partial`
- Что уже есть в проекте:
  - есть level cap 20;
  - hit dice sync/recovery при level change вынесены в отдельные helpers;
  - proficiency bonus корректно зависит от уровня;
  - UI payload показывает xp_total / to_next_level.
- Чего не хватает:
  - текущая XP-кривая в `server_impl.py` выглядит проектной, а не PHB;
  - нет законченной PHB-системы level-up с выдачей class features, spell slots, ASI/feat choices и subclass unlocks;
  - классовый progression catalog почти не превращён в исполняемую механику.
- Источники истины:
  - `app/rules/phb_progression.py`
  - `app/rules/phb_rest.py`
  - `app/rules/phb_math.py`
  - `app/web/server_impl.py`
  - `app/web/gameplay_helpers.py`

## Spellcasting

- Status: `Partial`
- Что уже есть в проекте:
  - хорошо поддержан пласт `innate spellcasting` для рас и похожих feature packages;
  - create flow умеет собирать innate spells и innate spellcasting metadata в общий формат;
  - usage tracking на `1_per_long_rest` и shared cooldown реально работает;
  - UI показывает innate spell data.
- Чего не хватает:
  - нет общего PHB class spellcasting: spell slots, prepared/known spells, concentration, spell lists, spellbook и каст обычных class spells;
  - spellcasting support сейчас в основном ограничен racial innate magic;
  - class catalog содержит поля `spellcasting`/`spell_lists`, но это не выглядит завершённой runtime-механикой.
- Источники истины:
  - `app/web/http_routes.py`
  - `app/web/ws_handlers.py`
  - `app/rules/character_catalog.py`
  - `app/web/templates/session.html`
  - `app/web/test_innate_spellcasting_usage.py`

## Backgrounds / proficiencies / languages

- Status: `Partial`
- Что уже есть в проекте:
  - race-driven languages и часть proficiencies реально собираются и сохраняются при создании;
  - есть выбор дополнительных языков, инструментов, навыков и некоторых feat-like choices для отдельных рас/подрас;
  - UI показывает languages/proficiencies из `race_features`.
- Чего не хватает:
  - не видно отдельной PHB background system;
  - нет законченной общей модели background proficiencies/equipment/features;
  - proficiencies собраны главным образом через race choices и project presets, а не через полный PHB player build pipeline.
- Источники истины:
  - `app/web/http_routes.py`
  - `app/rules/character_catalog.py`
  - `app/web/templates/session.html`
  - `app/web/server_impl.py`

## Главные пробелы

- Полный PHB class/subclass runtime практически отсутствует: есть в основном каталоги и точечные feature implementations.
- Общее class spellcasting отсутствует; поддержан главным образом innate racial spellcasting.
- Background system как отдельный PHB-блок не просматривается.
- Conditions и saving throws реализованы фрагментированно, через частные helper-ы и race-specific исключения.
- Equipment, weapon properties и стартовое снаряжение покрыты только частично и на небольшом каталоге.
- Level progression и XP в части web-слоя опираются на проектную модель, а не на полный PHB level-up workflow.

## Следующие 5 приоритетных шагов

1. Собрать единый `PHB player rules core`: generic saves, conditions и action economy без race-specific разрозненных helper-ов.
2. Довести class catalog до исполняемого уровня: class features, subclass unlocks, ASI/feat milestones и level-up application.
3. Вынести отдельный class spellcasting subsystem: slots, prepared/known spells, concentration, usage/reset.
4. Закрыть PHB creation pipeline end-to-end: backgrounds, proficiencies, starting equipment, languages, feat/ASI choices.
5. Расширить equipment/weapon coverage: полный PHB-каталог предметов, свойства оружия и более полная интеграция в combat/runtime.
