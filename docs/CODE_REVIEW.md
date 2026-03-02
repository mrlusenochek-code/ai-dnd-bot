# CODE REVIEW: ai-dnd-bot

## Scope
- Формат: обзор текущей архитектуры и потоков данных без рефакторинга и без изменений бизнес-логики.
- Источники: `app/web`, `app/gm`, `app/combat`, `app/rules`, `app/ai`, `app/db`.
- Фокус: WebSocket-пайплайн, GM two-pass, боевая машина, проверки (`@@CHECK`), карта мира/энкаунтеры, хранение состояния, риски.

## 1) Карта модулей

### `app/web`
- Главная точка сборки системы: `app/web/server.py` (FastAPI, REST, WS, orchestration).
- Что делает:
- lifecycle сессий, ходы/фазы (`turns`, `collecting_actions`, `gm_pending`, `lore_pending`);
- WebSocket endpoint `/ws/{session_id}` и `ConnectionManager`;
- построение состояния UI (`build_state`) и рассылка (`broadcast_state`);
- запуск background-задач мастера (`_auto_gm_reply_task`, `_auto_round_task`, `_auto_lore_task`);
- интеграция боя: machine-команды, live actions, журнал боя, синхронизация персонажей.
- Технический факт: файл очень крупный (6845 строк), совмещает transport + domain orchestration + часть бизнес-правил.

### `app/gm`
- `service.py`: основной two-pass pipeline (`run_two_pass`): draft -> checks -> finalize + guard/repair циклы.
- `checks.py`: парсинг `@@CHECK`, детект обязательных проверок, нормализация навыков/статов, автоген fallback-проверок.
- `sanitize.py`: многоуровневая очистка LLM-вывода (meta/механика/мусор/языковые правки).
- `narration.py`: локационный блок, world-aware input для GM, базовая sanitize-поддержка и move intent hook.
- `contracts.py`: сборка prompt-контрактов.

### `app/combat`
- `state.py`: in-memory combat state per session (`_COMBAT_BY_SESSION`), сериализация/restore.
- `machine_commands.py`: парсер `@@COMBAT_*` и `@@RANDOM_EVENT`.
- `apply_machine.py`: применение machine-команд к боевому state + patch для UI.
- `live_actions.py`: runtime боевых действий (`combat_attack`, `combat_end_turn`, `combat_dodge`, и т.д.).
- `log_ui.py`: нормализация/дополнение UI-патчей боевого журнала.
- `sync_pcs.py`: перенос данных персонажей из БД в combat state.

### `app/rules`
- `move_intents.py`: распознавание направлений движения из текста игрока.
- `world_map.py`: процедурная карта мира (чанки, биомы, move patch).
- `encounters.py`: вероятность стычки и подбор врага по env/party level.
- Дополнительно: derived stats, defeat outcomes, loot tables, catalog-и.

### `app/ai`
- `gm.py`: адаптер к Ollama (`generate_from_prompt`, `generate_lore`), нормализует ответ к формату `{text, finish_reason, usage}`.

### `app/db`
- `models.py`: SQLAlchemy-модели `sessions`, `players`, `session_players`, `characters`, `skills`, `events`.
- `connection.py`: `AsyncSessionLocal`, engine и fallback на SQLite при отсутствии `DATABASE_URL_ASYNC`.

## 2) Потоки данных

### 2.1 Игрок -> ws -> server -> gm two-pass -> events -> broadcast_state -> UI
- Игрок пишет в WS (`ws_room`, action `say`).
- Сервер валидирует фазу/права/lock-условия (combat lock, admin-only и т.п.).
- Формируется контекст и prompt (`_build_turn_draft_prompt` или `_build_round_draft_prompt`).
- Вызывается `_run_gm_two_pass` -> `gm_service.run_two_pass`.
- Внутри two-pass:
- draft generation;
- извлечение `@@CHECK` и/или fallback-логика;
- расчет check results;
- финальный ответ + sanitize/guards/repair.
- Результат пишется в `events` через `add_system_event`, вместе с `result_json` (checks, check_results, machine-команды).
- При необходимости применяются machine-команды (combat, inventory, zone).
- Затем `broadcast_state` собирает `build_state` и рассылает всем WS-клиентам.
- UI (`session.html`) получает `state` и полностью перерисовывает список игроков/лог/таймер + отдельно применяет `combat_log_ui_patch`.

### 2.2 Бой: machine commands -> state -> log_ui
- Источник: `@@COMBAT_START/@@COMBAT_ENEMY_ADD/@@COMBAT_END` в GM тексте либо bootstrap/admin.
- Парсинг: `combat.machine_commands.extract_combat_machine_commands`.
- Применение: `combat.apply_machine.apply_combat_machine_commands` -> mutation `combat.state`.
- Одновременно формируется patch для панели боя (`status/open/reset/lines`).
- `broadcast_state` прогоняет patch через `combat.log_ui.normalize_combat_log_ui_patch`, сохраняет историю в `sessions.settings` и отправляет в UI.
- UI применяет patch инкрементально (`applyCombatLogUiPatch`), держит локальный лимит строк журнала.

### 2.3 Checks: `@@CHECK` -> `check_results` -> xp/skills
- На draft-фазе `gm.checks._extract_checks_from_draft` извлекает JSON-строки `@@CHECK`.
- Если проверок нет, включаются fallback-механизмы (forced reprompt, parse textual check, autogen by category).
- В `gm.service.run_two_pass` для каждого check считается модификатор, бросок, итог.
- Затем обновляются:
- `characters.xp_total`, `characters.level`;
- `skills.rank`, `skills.xp` (с upsert по `character_id + skill_key`).
- Результаты сохраняются в `result_json` GM-события, и опционально публикуются отдельным системным событием (`GM_SHOW_CHECK_RESULTS=1`).

### 2.4 Мир: `move_intents` -> `world_map` -> `encounters` -> combat start
- Игроковое действие пропускается через `_apply_world_move_from_text`.
- `narration.apply_world_move_to_player_text` вызывает `parse_move_intent`; если распознано направление и нет активного боя, двигает `world_state`.
- При движении `_maybe_start_encounter_after_move` читает `settings.world` и вызывает `pick_encounter`.
- Если встреча сгенерирована, формируется GM machine-блок (`@@COMBAT_START` + `@@COMBAT_ENEMY_ADD`) и запускается бой.
- Далее patch боя встраивается в общий broadcast.

## 3) Где хранится состояние

### Session JSON (`sessions.settings`)
- Ключевой оперативный storage для серверной оркестрации:
- `combat_state_v1` (persist snapshot для restore in-memory state);
- `combat_log_history` (история UI боевого журнала);
- world data (`world`, включая seed/coords/chunks/env);
- turn/phase maps (`ready_map`, `init_map`, `last_seen`, `pc_positions`, `round_actions`, `phase`, `free_turns` и др.);
- story/lore/config flags;
- идемпотентные маркеры rewards/defeat (`combat_rewards_granted_for`, `combat_defeat_outcome_for`, `combat_defeat_effects_applied_for`).

### Реляционные таблицы
- `characters`: долгоживущее состояние персонажа (hp/sta/level/xp/stats и т.д.).
- `skills`: прогресс навыков (`rank`, `xp`), уникально по `(character_id, skill_key)`.
- `events`: журнал истории сессии (message_text + parsed/result JSON payloads).

### In-memory runtime
- `combat.state._COMBAT_BY_SESSION`: активный боевой runtime в памяти процесса.
- `server._GM_SESSION_LOCKS`: lock-и на сессию для сериализации GM background pipeline.
- `ConnectionManager.rooms`: активные WS-подключения.

## 4) Риски и техдолг

### 4.1 Крупные функции в `server.py`
- `ws_room` ~1628 строк: смешаны transport, auth checks, phase machine, combat commands, prompt orchestration, event logging, UI updates.
- `_auto_gm_reply_task`, `_auto_round_task`, `_apply_inventory_machine_commands`, `build_state` также крупные и перегружены cross-cutting логикой.
- Последствие: высокая цена изменений, повышенный риск регрессий, сложность тестирования веток.

### 4.2 Потенциальные гонки / lock-пробелы
- Lock (`_get_session_gm_lock`) защищает только GM background-задачи; часть WS-обработки и боевые live-actions идут вне этого lock.
- Боевой state in-memory (`_COMBAT_BY_SESSION`) мутируется без отдельного per-session combat lock.
- Есть множественные `commit` внутри одного логического сценария (event -> state mutate -> broadcast), что повышает вероятность промежуточных/рассинхронных состояний при конкуренции сообщений.
- Runtime state боя зависит от процесса; при scale-out/мультиворкере без external shared state будут расхождения.

### 4.3 Возможная избыточность sanitize/guards
- `gm/sanitize.py` содержит агрессивные regex-удаления (англ. токены, числовые механики, check garbage, meta-блоки); риск ложных срабатываний и потери полезного текста.
- В `gm/service.py` много guard-reprompt этапов (entity/backref/action-anchor/scene-lock/combat-lock); цепочка надежная, но может «переполировать» ответ и уводить от исходного смысла действия игрока.
- В `server.py` дублируются wrapper-функции для check logic (thin wrappers к `gm_checks`), что повышает риск дрейфа поведения в будущем.

### 4.4 UI узкие места
- `session.html` (1216 строк) содержит всю клиентскую логику в одном файле.
- На каждый `state` делается полная перерисовка игроков и лога событий (`innerHTML` + повторное построение), без диффа.
- При лимите 250 событий на сервере и частом `broadcast_state` это может стать bottleneck по DOM/JS.
- Боевой лог поддерживает patch-подход, но общий event log перерисовывается целиком.

## 5) Рекомендации (приоритетно)
1. Разделить `app/web/server.py` по bounded contexts: `ws_handlers`, `turn_engine`, `gm_orchestrator`, `combat_bridge`, `state_builder`.
2. Ввести явный per-session lock для мутаций боевого runtime (`_COMBAT_BY_SESSION`) и унифицировать критические секции WS + background tasks.
3. Свести commit-стратегию к предсказуемым транзакционным блокам (минимум частичных commit в одном сценарии действия).
4. Вынести session-phase machine в отдельный модуль/enum + таблицу переходов, чтобы сократить условные ветви в `ws_room`.
5. Уменьшить агрессивность sanitize через белые списки/контекстные тесты для regex, и добавить метрики «сколько текста удалено». 
6. Унифицировать check API: убрать дубли wrappers из `server.py`, оставить единый источник в `gm.checks`.
7. Декомпозировать `session.html`: вынести WS client, state store, view renderers; перейти к инкрементальному обновлению event log.
8. Добавить нагрузочный smoke для WS (N клиентов, burst сообщений) и сценарии race на бой/phase transitions.
9. Подготовить план выноса in-memory combat state в внешнее хранилище (Redis/DB snapshot + optimistic versioning) для устойчивости к рестартам и scale-out.
10. Добавить структурированные трассы по request_id/action_id на весь путь action -> gm -> event -> broadcast для ускорения отладки прод-инцидентов.

## Итог
- Архитектура уже покрывает требуемые фичи (WS, two-pass GM, checks, world/encounters, combat UI patching), но текущая концентрация логики в `server.py` и смешение runtime-state/DB-state создают основной техдолг.
- Приоритет №1: декомпозиция orchestration слоя + выравнивание concurrency-модели.
