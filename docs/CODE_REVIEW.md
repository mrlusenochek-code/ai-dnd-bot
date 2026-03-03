# CODE REVIEW: ai-dnd-bot

## Scope
- Режим: технический обзор текущей реализации без изменения поведения.
- Фокус: WebSocket pipeline, GM orchestration, combat machine/log/idempotency, watcher-задачи, `sessions.settings`, риски конкурентности/регрессий.
- Основные файлы: `app/web/server.py`, `app/combat/*`, `app/gm/*`, `app/web/templates/session.html`, `app/db/models.py`, `migrations/versions/*`.

## 1) Архитектура и границы ответственности

### 1.1 Web/API слой (`app/web/server.py`)
- Один крупный композиционный модуль: транспорт (HTTP/WS), orchestration game-loop, вызовы GM/combat, background watchers, state-builder и broadcast в одном файле.
- Ключевые части:
  - Lifecycle + watchers: `lifespan` запускает `timer_watcher`/`inactive_watcher` ([app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L406), [app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L6753), [app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L6791)).
  - Session JSON helpers: `settings_get/settings_set`, combat log/history snapshot, combat snapshot restore ([app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L497)).
  - WS endpoint `ws_room` с обработкой всех команд/фаз/боевых веток ([app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L5125)).
  - Auto-GM задачи: `_auto_gm_reply_task`, `_auto_round_task`, `_auto_lore_task` ([app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L4164), [app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L4440), [app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L4332)).
  - UI state assembly: `build_state` и `broadcast_state` ([app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L3452), [app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L3985)).

### 1.2 GM слой (`app/gm/*`)
- `service.run_two_pass` — основной двухпроходный pipeline (draft -> checks/xp/skills -> finalize + repair guards) ([service.py](/home/lus/code/ai-dnd-bot/app/gm/service.py#L383)).
- `checks.py` — извлечение `@@CHECK`, mandatory category, autogen/fallback чеков ([checks.py](/home/lus/code/ai-dnd-bot/app/gm/checks.py#L404), [checks.py](/home/lus/code/ai-dnd-bot/app/gm/checks.py#L429)).
- `sanitize.py`/`narration.py` — нормализация output, location-aware ограничения.

### 1.3 Combat слой (`app/combat/*`)
- Runtime state in-memory: `_COMBAT_BY_SESSION` в `state.py` ([state.py](/home/lus/code/ai-dnd-bot/app/combat/state.py#L44)).
- Machine parsing/apply:
  - `extract_combat_machine_commands` ([machine_commands.py](/home/lus/code/ai-dnd-bot/app/combat/machine_commands.py#L128)).
  - `apply_combat_machine_commands` ([apply_machine.py](/home/lus/code/ai-dnd-bot/app/combat/apply_machine.py#L36)).
- Live actions: `handle_live_combat_action` с авто-резолвом 0 HP, пошаговой мутацией state и патчами UI ([live_actions.py](/home/lus/code/ai-dnd-bot/app/combat/live_actions.py#L288)).
- UI-patch normalization/history behavior: `log_ui.py`.

### 1.4 Данные и хранение
- DB модели: `sessions`, `players`, `session_players`, `characters`, `skills`, `events` ([models.py](/home/lus/code/ai-dnd-bot/app/db/models.py#L11)).
- `sessions.settings` (JSONB) — operational state (phase/maps/world/combat snapshot/log history/idempotency markers).
- Миграции минимальные: init schema + timer/pause + web_user_id ([85c675...](/home/lus/code/ai-dnd-bot/migrations/versions/85c675229962_init.py), [80a1bf...](/home/lus/code/ai-dnd-bot/migrations/versions/80a1bf5d3ec6_turn_timer.py), [81f0f0...](/home/lus/code/ai-dnd-bot/migrations/versions/81f0f0157862_add_web_user_id_and_make_telegram_user_.py)).

## 2) Карта потоков

### 2.1 Игрок -> WS -> GM -> сохранение -> UI
1. Клиент отправляет `action=say` в `ws_room`.
2. Сервер валидирует фазу/права/combat lock, записывает player event (`events.result_json`).
3. Для turn/free-round запускается `gm_pending` и `action_id`, затем фоновая задача `_auto_gm_reply_task` или `_auto_round_task`.
4. Фоновая задача под `_get_session_gm_lock` строит prompt, вызывает `_run_gm_two_pass`, применяет machine-команды/инвентарь/zone, пишет GM event.
5. `broadcast_state`:
   - нормализует/сохраняет `combat_log_ui_patch`;
   - применяет идемпотентные награды/поражения;
   - сохраняет `combat_state_v1` в `sessions.settings`;
   - собирает `build_state` и рассылает в WS room.
6. `session.html` получает `state` и делает full rerender игроков/логов; `combat_log_ui_patch` применяется инкрементально.

### 2.2 Бой -> machine-команды -> UI patch
1. Источник: `@@COMBAT_*` в GM тексте или admin/chat bootstrap в `ws_room`.
2. `apply_combat_machine_commands` мутирует in-memory `CombatState`.
3. `broadcast_state` вызывает `normalize_combat_log_ui_patch`, обновляет `combat_log_history` в settings и отправляет patch клиенту.
4. Клиент `applyCombatLogUiPatch(...)` обновляет боевую панель.

## 3) Идемпотентность и где она критична

### 3.1 Уже реализовано
- Победные награды защищены маркером `combat_rewards_granted_for` ([app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L3928)).
- Defeat outcome и defeat effects защищены `combat_defeat_outcome_for` и `combat_defeat_effects_applied_for` ([app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L3904), [app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L3808)).
- Combat snapshot в settings (`combat_state_v1`) для restore после потери runtime ([app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L613), [app/web/server.py](/home/lus/code/ai-dnd-bot/app/web/server.py#L631)).

### 3.2 Где остаются окна для дублей/рассинхрона
- Идемпотентность завязана на `started_at_iso` из runtime snapshot: при неконсистентном restore/перезапуске есть риск второго цикла выдачи, если маркер и snapshot расходятся во времени фиксации.
- Несколько `commit` внутри одного сценария в `ws_room` и background tasks создают промежуточные состояния, где событие уже записано, а phase/state ещё нет (или наоборот).
- В боевых ветках часть update -> broadcast -> follow-up GM narration выполняется в несколько шагов; при исключении в середине возможен «полуприменённый» сценарий в истории.

## 4) Риски и слабые места

### 4.1 Конкурентность и гонки
1. Per-session lock теперь реально используется на hot-path.
- `broadcast_state(...)` сериализован per-session lock’ом, чтобы не было параллельной выдачи rewards/defeat и гонок при persist combat snapshot.
- В `ws_room` боевые мутации (`apply_combat_machine_commands`, `handle_live_combat_action`, `end_combat`) выполняются под тем же lock’ом.
- В фоновых GM-задачах критические секции также под lock’ом, а broadcast внутри lock делается через `_broadcast_state_unlocked(...)`.

2. Важное правило (иначе дедлок).
- `broadcast_state(...)` берёт lock внутри себя, поэтому **нельзя** вызывать `broadcast_state(...)` под `async with _get_session_gm_lock(...)`.
- Внутри lock использовать только `_broadcast_state_unlocked(...)`.

3. Что всё ещё остаётся риском/долгом.
- Watchers (`timer_watcher`, `inactive_watcher`) делают мутации сессии до вызова `broadcast_state`; сам broadcast сериализован, но изменения до него всё ещё могут пересекаться с WS/GM путями.
- Lock сейчас может держаться во время отправки state по WS (см. `_broadcast_state_unlocked` → `manager.broadcast_json`), что увеличивает время удержания lock при медленных клиентах.
- In-memory combat state всё ещё проблемен для multi-worker/scale-out: разные процессы не разделяют `_COMBAT_BY_SESSION`.

4. Практическая рекомендация на будущее.
- Любая новая мутация боёвки/critical settings должна попадать под per-session lock.
- Любые LLM/долгие операции — вне lock, с повторной проверкой `action_id/phase` перед применением результата.

### 4.2 Потеря состояния при рестарте
- Active combat runtime хранится в памяти процесса (`_COMBAT_BY_SESSION`); `sessions.settings` хранит только snapshot.
- Restore срабатывает лениво при обращении к сессии (`_maybe_restore_combat_state`).
- Риск: в multi-worker/runtime scale-out разные процессы имеют разный in-memory combat state.

### 4.3 Монолитность и связность
- `ws_room` объединяет transport, ACL, phase-machine, combat orchestration, GM orchestration, text command parsing.
- `build_state` и template `session.html` также «толстые» (большой объем responsibilities в одном месте).
- Это сильно увеличивает размер регрессии любого изменения: сложно стабильно изолировать и тестировать отдельно.

### 4.4 UI bottleneck
- `renderState` делает полный перерендер списка игроков и event log на каждый state update (`innerHTML = ""` + заново заполнение) ([session.html](/home/lus/code/ai-dnd-bot/app/web/templates/session.html#L818), [session.html](/home/lus/code/ai-dnd-bot/app/web/templates/session.html#L904)).
- При высокой частоте broadcast DOM-стоимость растет быстрее, чем фактические изменения данных.
- Combat log уже patch-based, но общий лог/players остаются full refresh.

## 5) Риски регрессий при будущих изменениях
1. Изменение phase/turn logic в `ws_room` может сломать таймерный flow и free-turns одновременно.
2. Изменение формата `sessions.settings` без versioning может нарушить restore combat и старые сессии.
3. Изменения sanitize/guards в GM pipeline могут сломать баланс между «безопасностью» и «продвижением сцены».
4. Любые правки combat actions без унифицированной lock-стратегии могут дать плавающие баги "не воспроизводится локально".

## 6) Конкретные рекомендации (next steps)
1. Распилить `server.py` по контекстам (см. [REFACTOR_ROADMAP.md](REFACTOR_ROADMAP.md)).
2. Ввести единый per-session synchronization primitive для всех mutating путей (WS + watchers + background GM).
3. Стабилизировать транзакционные границы: один логический сценарий -> одна критическая секция + один commit.
4. Зафиксировать contract для `sessions.settings` (ключи, owner-модуль, lifecycle, idempotency marker semantics).
5. Перевести UI на инкрементальные патчи для players/events, оставив полный snapshot как fallback.

## 7) Быстрый итог
- Система функционально насыщена и уже содержит полезные идемпотентные guards по наградам/поражению.
- Главный технический риск: конкурентная модель и концентрация orchestration-кода в `server.py`.
- Оптимальный путь: сначала структурная декомпозиция без изменения поведения, затем усиление lock/транзакций, затем UI patch architecture.
