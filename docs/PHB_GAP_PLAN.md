# PHB Gap Closure Plan

## 1. Цель

Этот план нужен, чтобы перевести текущий проект от частичного и местами фрагментированного покрытия PHB к предсказуемому `PHB-player-core`, на который можно безопасно опирать создание персонажа, checks, бой, отдых, экипировку и базовое исследование мира.

Целевое состояние:
- у проекта есть единый PHB-core для игрока, а не набор race-specific и web-specific исключений;
- базовая математика, action economy, combat core, spellcasting core и inventory/equipment truth синхронизированы между документами, rules-слоем, combat runtime и web-слоем;
- архитектура выдерживает дальнейшее расширение без разрастания `server/web` оркестрации и without drift между docs и кодом.

## 2. Принципы приоритизации

- Сначала закрываем `PHB-core игрока`: ability math, proficiency, saves, skills, conditions, базовые derived rules.
- Затем доводим `character creation` и `progression`, чтобы вход в систему правил был корректным и воспроизводимым.
- Затем выстраиваем `action economy`, чтобы бой и игровые команды опирались на единые ограничения.
- Потом закрываем `combat truth`, чтобы атака, AC, damage, 0 HP, conditions и turn flow жили на одном наборе правил.
- Потом строим `spellcasting core`, начиная с общего каркаса class spellcasting, а не с новых частных feature-ов.
- После этого доводим `equipment and inventory truth`, чтобы derived stats и item interactions не расходились.
- Только после появления устойчивого player/combat core делаем полную `integration с exploration`.
- `DMG`-подобные и advanced GM rules идут только после стабилизации PHB player/combat core.
- Любой новый behavioral change должен опираться на уже зафиксированные truth-docs и сопровождаться тестами.
- Архитектурный долг (`server.py`, locks, in-memory runtime, broadcast flow) нельзя откладывать до самого конца, но он должен идти в поддержке PHB-core, а не вместо него.

## 3. Этапы работ

### Этап 1. Player core truth

- Цель этапа:
  - собрать единый минимальный PHB-core игрока, который станет общей опорой для checks, saves, derived stats и feature-логики.
- Что входит:
  - нормализация ability/skill/save/proficiency truth;
  - единый слой для generic proficiency и expertise вместо разрозненных вычислений в web;
  - единый базовый слой conditions/saves hooks, на который потом можно повесить race/class features;
  - синхронизация `PHB_TRUTH.md`, rules-слоя и реально используемых helper-ов.
- Что НЕ входит:
  - полное class spellcasting;
  - полный catalog equipment;
  - exploration/region logic;
  - UI redesign.
- Зависимости:
  - `docs/PHB_TRUTH.md`;
  - текущие helper-ы в `app/rules/phb_math.py`, `app/rules/derived_stats.py`, `app/web/ws_checks.py`, `app/web/ws_handlers.py`.
- Что можно делать параллельно:
  - документирование truth contracts;
  - выделение общего save/condition helper layer;
  - инвентаризация race-specific save/condition hooks.
- Результат на выходе:
  - единый и тестируемый `player core truth`, который используется как минимум в checks, saves, AC и attack profile.

### Этап 2. Character creation and progression

- Цель этапа:
  - довести создание персонажа и progression до состояния, где персонаж собирается и растёт по предсказуемой PHB-логике.
- Что входит:
  - явный creation contract для class/race/background/proficiency/lang choices;
  - нормализация starter proficiencies и starter equipment packages;
  - PHB-aware level progression backbone: ASI/feat milestones, subclass unlock points, hit dice sync;
  - отделение project XP model от PHB progression truth.
- Что НЕ входит:
  - полная боевая реализация class features;
  - общий spell slot engine;
  - exploration-specific onboarding logic.
- Зависимости:
  - этап 1;
  - `app/web/http_routes.py`;
  - `app/web/gameplay_helpers.py`;
  - `app/rules/character_catalog.py`;
  - `app/rules/phb_progression.py`.
- Что можно делать параллельно:
  - чистка class/subclass catalog data;
  - формализация background/proficiency/lang input contracts;
  - вынос level-up side effects в отдельные helper-ы.
- Результат на выходе:
  - creation/progression pipeline, который создаёт и развивает персонажа без скрытых расхождений между catalog, runtime и web flow.

### Этап 3. Action economy

- Цель этапа:
  - перевести боевые и связанные игровые действия на единый action-economy contract.
- Что входит:
  - единый truth для action / bonus action / reaction / movement;
  - фиксация того, какие live actions потребляют какие ресурсы хода;
  - подготовка общего каркаса для Ready-like и opportunity/reaction-like действий;
  - устранение разрозненных ограничений в runtime и feature-specific ветках.
- Что НЕ входит:
  - полный spellcasting;
  - полный tactical combat feature set;
  - exploration routing/session state.
- Зависимости:
  - этап 1;
  - частично этап 2, если actions завязаны на class/race progression.
- Что можно делать параллельно:
  - тестовая матрица live actions;
  - формализация movement/action budget в combat state;
  - выделение shared guards из `app/combat/live_actions.py`.
- Результат на выходе:
  - единый action economy contract, на который могут безопасно опираться combat actions и feature runtime.

### Этап 4. Combat truth

- Цель этапа:
  - сделать live combat устойчивым PHB-core слоем, а не смесью MVP и частных feature exceptions.
- Что входит:
  - согласование derived attack/AC/damage truth с combat runtime;
  - формализация 0 HP / downed / stable / dead transitions;
  - общее condition application/cleanup поведение для combat state;
  - сокращение hardcoded combat numbers и перенос на derived/rules helpers;
  - выравнивание `COMBAT_MAP.md` с актуальным combat truth.
- Что НЕ входит:
  - narrative/exploration integration;
  - массовое расширение enemy AI;
  - non-PHB advanced tactical rules.
- Зависимости:
  - этап 1;
  - этап 3;
  - частично этап 6 для weapon/armor truth.
- Что можно делать параллельно:
  - работа над death/0 HP;
  - чистка attack profile integration;
  - condition runtime boundary work;
  - reward/defeat idempotency hardening.
- Результат на выходе:
  - combat core, в котором атака, AC, damage, actions, 0 HP и ключевые conditions живут на общей модели.

### Этап 5. Spellcasting core

- Цель этапа:
  - перейти от mostly innate spellcasting support к общему PHB spellcasting core.
- Что входит:
  - общий spellcasting data contract: known/prepared, slots, usage, DC/attack bonus foundation;
  - разделение innate spellcasting и class spellcasting;
  - базовые runtime contracts для кастов, проверок доступности и reset на rest;
  - привязка к level progression и class catalog.
- Что НЕ входит:
  - полный список заклинаний PHB;
  - high-level spell UX polish;
  - exploration-specific spell affordances.
- Зависимости:
  - этап 1;
  - этап 2;
  - частично этап 3 и 4.
- Что можно делать параллельно:
  - spellcasting catalog contract;
  - reset/usage infrastructure;
  - отделение innate spellcasting current flow от будущего class spellcasting flow.
- Результат на выходе:
  - единый spellcasting core, где innate magic остаётся частным случаем, а не единственной реальной spell system.

### Этап 6. Equipment and inventory truth

- Цель этапа:
  - довести предметный слой до состояния, где экипировка и инвентарь надёжно питают derived stats и runtime interactions.
- Что входит:
  - расширение PHB-ядра item catalog;
  - формализация weapon properties и armor interactions, реально используемых в derived/combat;
  - согласование inventory normalization, equip rules и combat/runtime usage;
  - минимальная truth-модель starting equipment packages.
- Что НЕ входит:
  - полная экономика магазина/веса/контейнеров;
  - loot/treasure balancing за пределами PHB-core needs.
- Зависимости:
  - этап 1;
  - этап 2;
  - этап 4.
- Что можно делать параллельно:
  - catalog expansion;
  - equip/runtime contract cleanup;
  - derive AC/attack dependency cleanup.
- Результат на выходе:
  - equipment/inventory truth, который стабильно поддерживает player core и combat core.

### Этап 7. Exploration integration

- Цель этапа:
  - интегрировать уже выстроенный PHB-player-core с exploration/session state, не размазывая правила по narrative-only слоям.
- Что входит:
  - привязка rest, movement intent, inventory use и player state к exploration/session flows;
  - использование PHB-core данных в world/exploration командах;
  - cleanup мест, где narrative/exploration команды обходят системный rules-layer.
- Что НЕ входит:
  - новый региональный контент;
  - расширение authored map content;
  - advanced travel subsystems beyond current project needs.
- Зависимости:
  - этапы 1–6.
- Что можно делать параллельно:
  - session-state integration;
  - command wording/UI payload cleanup;
  - tests на end-to-end player journey с уже новым rules core.
- Результат на выходе:
  - exploration/web flows используют тот же player/combat truth, что и runtime rules.

### Этап 8. Architecture and hardening

- Цель этапа:
  - убрать архитектурные ограничения, которые мешают безопасно развивать PHB-core.
- Что входит:
  - roadmap-пункты по распилу `server.py` и стабилизации orchestration boundaries;
  - усиление per-session lock discipline и commit boundaries;
  - дальнейшая изоляция state builder / ws handlers / combat bridge / session state;
  - подготовка к уходу от жёсткой зависимости на in-memory combat runtime.
- Что НЕ входит:
  - продуктовые фичи сами по себе;
  - новые PHB-блоки без опоры на уже сделанный rules-layer.
- Зависимости:
  - может идти поддерживающе почти на всех этапах, но особенно критичен после этапов 3–5.
- Что можно делать параллельно:
  - decomposition `server.py`;
  - mutation lock hardening;
  - payload/broadcast cleanup;
  - race/integration tests.
- Результат на выходе:
  - архитектура перестаёт быть основным ограничением для дальнейшего закрытия PHB-пробелов.

## 4. Первый приоритетный пакет задач

Ниже ближайшие 10 задач в форме, пригодной для постановки в Codex:

1. Выделить единый `player_core` helper layer для `ability mod`, `proficiency bonus`, `skill total`, `save total` и заменить дублирующие вычисления в `ws_checks.py` и `ws_handlers.py`.
2. Собрать карту всех race-specific save/condition преимуществ в одном rules-модуле и перевести текущие вызовы на него без изменения поведения.
3. Зафиксировать и протестировать generic condition contract для `frightened`, `poisoned`, `grappled`, `prone`, `stunned`, даже если часть условий пока только scaffold.
4. Отдельно описать и реализовать class saving throw proficiency layer, не зависящий от race-specific feature helper-ов.
5. Превратить текущий `character_catalog` из placeholder-данных по классам в минимально пригодный PHB class progression skeleton для всех PHB классов.
6. Отделить project XP progression в `server_impl.py` от PHB progression truth и ввести явный комментарий/contract, где проектная модель допустима, а где нужна RAW-опора.
7. Вынести action economy policy из `app/combat/live_actions.py` в отдельный модуль с таблицей затрат `action / bonus action / reaction / movement`.
8. Убрать hardcoded combat attack defaults там, где уже можно опереться на `compute_attack_profile`, и покрыть это regression tests.
9. Ввести минимальный общий class spellcasting contract: `spellcasting ability`, `spell slots`, `known/prepared mode`, даже если сначала без полного списка spells.
10. Расширить `item_catalog.py` до минимального PHB-core набора оружия, брони и щитов, который нужен для derived stats и combat regression tests.

## 5. Риски

- Смешение custom-layer и RAW:
  - проект уже использует `stat100`, rank-based skills и project XP model; без явных границ это будет дальше размывать PHB-core.
- Race-specific logic вместо general engine:
  - сейчас значительная часть save/condition/spell/action behavior зашита как частные feature helper-ы, что тормозит переход к общему rules-layer.
- Fragile tests:
  - много тестов проверяют конкретные формулировки и локальные ветки, а не стабильные contracts; это замедляет рефакторинг.
- Web/server orchestration debt:
  - даже после распила логика остаётся чувствительной к boundaries между `ws_handlers`, `server_impl`, `combat_bridge`, `session_state`.
- In-memory runtime limits:
  - боевой runtime всё ещё ограничивает deployment и усложняет масштабирование, restart safety и долгие интеграционные сценарии.
- Расхождение docs и actual code:
  - truth-документы могут быстро устаревать, если изменения будут идти без синхронизации docs и tests.

## 6. Definition of Done

### PHB-player-core готов

- ability/proficiency/skills/saves/conditions truth оформлены в единый rules-layer;
- web/combat слои используют этот слой, а не локальные дублирующие вычисления;
- ключевые contracts покрыты unit и integration tests;
- `PHB_TRUTH.md`, `PHB_COVERAGE_MATRIX.md` и код не расходятся по базовой математике.

### Combat-core готов

- action economy, attack/AC/damage, 0 HP/death saves/stabilization и ключевые PHB conditions работают на одном наборе правил;
- derived stats подаются в combat runtime без hardcoded обходов там, где уже есть truth-layer;
- `COMBAT_MAP.md` и код совпадают по основным точкам входа и правилам;
- combat regression tests покрывают не только race features, но и generic core behavior.

### Spellcasting-core готов

- innate spellcasting и class spellcasting живут в одном общем контракте, но остаются разными режимами использования;
- есть общий слой spell availability / usage / reset / level gating;
- class progression умеет включать spellcasting features без ручной race-only логики;
- spellcasting tests покрывают не только innate magic, но и общий class spellcasting skeleton.
