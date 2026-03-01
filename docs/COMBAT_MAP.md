# COMBAT_MAP

Краткая карта боевой подсистемы по текущему коду.

## 1) Точки входа в `app/web/server.py`

- Файл: `app/web/server.py`
- Ключевые константы/импорты:
  - `COMBAT_LOG_HISTORY_KEY = "combat_log_history"`, `COMBAT_STATE_KEY = "combat_state_v1"`, `MAX_COMBAT_LOG_LINES = 200`
  - Импорты боевого слоя: `apply_combat_machine_commands`, `handle_live_combat_action`, `normalize_combat_log_ui_patch`, `extract_combat_narration_facts`, `extract_combat_machine_commands`, `snapshot_combat_state/restore_combat_state`

- Где включается бой:
  - WebSocket action `admin_combat_live_start`: собирает `@@COMBAT_START + @@COMBAT_ENEMY_ADD`, вызывает `apply_combat_machine_commands(...)`, синхронизирует PC через `sync_pcs_from_chars(...)`, добавляет preamble, шлёт patch.
  - Чат-ветка `say` с `start_intent` (`"войти в бой"`, `"начать бой"`, `"бой с ..."`): формирует bootstrap-команды (`cause="bootstrap"`), запускает бой через `apply_combat_machine_commands(...)`.
  - Автовосстановление bootstrap: если in-memory state пуст, берётся `settings["combat_live_bootstrap"]`, заново строятся `@@COMBAT_*`, вызывается `apply_combat_machine_commands(...)`.

- Где боевые команды и lock:
  - Session lock: `_get_session_gm_lock(session_id)` + `async with lock` в обработке WS-сообщений.
  - Combat Lock (внутри ветки `say`): при активном бое пропускаются только OOC, админский `gm`, либо распознанные боевые действия (`_detect_chat_combat_action`). Иначе возвращается ошибка про доступные команды.
  - Выполнение действий: `handle_live_combat_action(combat_action, session_id)`; после действия при ходе врага запускается авто-ответ врага (`handle_live_combat_action("combat_attack", ...)`) в цикле.
  - Админские action-команды (`combat_attack`, `combat_end_turn`, `combat_dodge`, `combat_dash`, `combat_disengage`, `combat_escape`, `combat_use_object`, `combat_help`) также идут через `handle_live_combat_action`.

- Где формируется/сохраняется combat log + bootstrap:
  - История UI-лога: `_get_combat_log_history(...)`, `_persist_combat_log_patch(...)`, `_combat_log_snapshot_patch(...)`.
  - Нормализация перед записью: `normalize_combat_log_ui_patch(...)` в `broadcast_state(...)`.
  - Persist состояния боя в settings: `_persist_combat_state(...)` и restore через `_maybe_restore_combat_state(...)`.
  - Bootstrap хранится в settings как `combat_live_bootstrap` (ставится в `admin_combat_live_start`, читается в chat-ветке при пустом состоянии).

## 2) State (`app/combat/state.py`)

- Файл: `app/combat/state.py`
- Структуры:
  - `Combatant`: участник (`key`, `name`, `side`, HP/AC/initiative + флаги действий).
  - `CombatState`: состояние боя (`active`, `round_no`, `turn_index`, `order`, `combatants`, `started_at_iso`).
  - In-memory хранилище: `_COMBAT_BY_SESSION: dict[str, CombatState]`.

- Ключевые функции:
  - Lifecycle: `start_combat`, `end_combat`, `get_combat`.
  - Состав боя: `add_enemy`, `upsert_pc` (с пересборкой `order` через `build_initiative_order`).
  - Изменения: `apply_damage`, `advance_turn`, `current_turn_label`.
  - Сериализация/восстановление: `combat_state_to_dict`, `snapshot_combat_state`, `combat_state_from_dict`, `restore_combat_state`.

- Что делает:
  - Держит «истину» live-боя в памяти по `session_id`, плюс умеет сохранять/восстанавливать payload для persistence в `Session.settings`.

## 3) Turns (`app/combat/turns.py`)

- Файл: `app/combat/turns.py`
- Ключевые функции:
  - `build_initiative_order(combatants)`: сортировка по инициативе (desc), затем `pc` перед `enemy`, затем имя/ключ.
  - `advance_turn_in_state(state)`: сдвиг `turn_index`, инкремент `round_no` при переходе через начало.

- Что делает:
  - Централизует порядок ходов и смену раундов.
  - На входе нового активного бойца сбрасывает его временные флаги (`dodge_active`, `dash_active`, `disengage_active`, `use_object_active`).

## 4) Actions (`app/combat/live_actions.py`)

- Файл: `app/combat/live_actions.py`
- Точка входа:
  - `handle_live_combat_action(action, session_id)`.

- Поддерживаемые action:
  - `combat_end_turn`, `combat_attack`, `combat_dodge`, `combat_dash`, `combat_disengage`, `combat_use_object`, `combat_help`, `combat_escape`.

- Где считается попадание/урон:
  - Ветка `combat_attack`: определяет цель через `_first_living_opponent(...)`, считает бросок/adv-disadv, вызывает `resolve_attack_roll(...)`, применяет `apply_damage(...)`.

- Где завершение боя:
  - В `combat_attack`: проверка `_is_side_alive(state, "pc"|"enemy")`; если одна сторона выбыла, `end_combat(...)` и patch со статусом `"Бой завершён"`.
  - В ряде веток, если нет целей/order, также возвращается завершение боя.
  - В `combat_escape`: при успехе побега тоже `end_combat(...)`.

- Где авто-skip 0 HP:
  - `_auto_skip_dead_turns(session_id, state)` вызывается в самом начале `handle_live_combat_action`.
  - Цикл до `len(state.order) + 1`, на каждый пропуск добавляет `"Ход пропущен: {name} (0 HP)."`.
  - Если после пропусков жива только одна сторона, бой завершается; иначе возвращается patch с текущим живым ходом (`_combat_status(state)`).

## 5) Machine commands (`app/combat/machine_commands.py`, `app/combat/apply_machine.py`)

- Файл: `app/combat/machine_commands.py`
- Ключевая функция:
  - `extract_combat_machine_commands(text)`.

- Какие `@@` команды поддержаны парсером:
  - `@@COMBAT_START(...)`
  - `@@COMBAT_ENEMY_ADD(...)`
  - `@@COMBAT_END(...)`
  - `@@RANDOM_EVENT(...)`

- Что делает:
  - Разбирает машинные строки в typed-структуры (`ParsedMachineCommands`) и отдаёт `visible_text` без скрытых команд.

- Файл: `app/combat/apply_machine.py`
- Ключевая функция:
  - `apply_combat_machine_commands(session_id, text)`.

- Что меняют команды:
  - `COMBAT_START` (только `cause in {admin, bootstrap}`): создаёт state боя, отдаёт patch `reset/open/status`.
  - `COMBAT_ENEMY_ADD` (разрешено только вместе с разрешённым start): добавляет врагов в state + строки `"Противник добавлен..."`.
  - `COMBAT_END`: завершает бой (`end_combat`) и закрывает панель.
  - `RANDOM_EVENT`: сейчас учитывается как распознанная команда, но state боя напрямую не меняет.
  - Fallback: если команд нет и бой неактивен, при «боевом» тексте может стартовать упрощённый бой (fallback enemy).

## 6) Log UI (`app/combat/log_ui.py`)

- Файл: `app/combat/log_ui.py`
- Ключевые функции:
  - `build_combat_log_ui_patch_from_text(...)`: мини-конвертер `@@COMBAT_START/END` в UI patch.
  - `normalize_combat_log_ui_patch(...)`: нормализация patch перед persist.

- Что такое `status` vs `lines`:
  - `status` — текущий заголовок состояния боя (например, `⚔ Бой • Раунд N • Ход: ...`).
  - `lines` — лента событий (читаемый лог); в неё также добавляется status-line с `kind="status"` для истории.

- Нормализация/assumptions:
  - Если в patch нет `status`, он вычисляется из `combat_state`.
  - При `enemy added` и пустой истории может добавляться preamble (`Бой начался между...`, `Добавлен в бой...`).
  - При смене раунда добавляется разделитель `====================`.
  - Исключается дублирование одинаковой status-строки в `lines`.

- Persist (где реально сохраняется):
  - В `server.py` (`_persist_combat_log_patch`, `_get_combat_log_history`, `_combat_log_snapshot_patch`), а `log_ui.py` отвечает за нормализацию и структуру patch.

## 7) Narration (`app/combat/combat_narration_facts.py` + ветка в `server.py`)

- Файл: `app/combat/combat_narration_facts.py`
- Ключевая функция:
  - `extract_combat_narration_facts(patch)`.

- Что делает:
  - Из `patch["lines"]` извлекает факты для художественного текста: атака/исход/состояние HP, побег, победа/поражение/завершение.
  - Отбрасывает механику/служебные линии (`status`, броски, `Урон:`, разделитель и т.д.), отдаёт приоритетные + обычные факты (до 10).

- Ветка в `server.py` (combat narration pipeline):
  - После боевых patch вызывается `extract_combat_narration_facts(...)`.
  - Считается покрытие фактов: `_combat_narration_fact_coverage(text, facts)`.
  - Проверяется drift/запрещённая механика: `_looks_like_combat_drift(...)` + фильтры по числам/HP/AC/gear.
  - При провале ограничений выполняется reprompt; в крайнем случае — безопасный fallback-нарратив.

## Куда встраивать дальше

- Смерть/0 HP (`downed/defeated`):
  - Развести состояния `0 HP` на `downed` vs `defeated`; добавить это в `Combatant`, в lines/status и в narration facts.
  - Вынести правила «когда можно/нельзя пропускать ход» в единый policy helper (сейчас skip завязан на `hp_current <= 0`).

- XP награды:
  - На точке `end_combat` (и/или при `Победа`) сформировать результат боя, вычислить XP по `threat`, записать в event/result_json.
  - Добавить idempotent guard, чтобы награда не выдавалась повторно при restore/rebroadcast.

- Экипировка -> derived stats (AC/атака/урон):
  - Централизовать derived-расчёты в отдельном модуле (например, `combat/derived_stats.py`) и использовать его в `sync_pcs_from_chars` + `live_actions`.
  - Сейчас боевые числа частично захардкожены (`attack_bonus=3`, `damage d6+2`) — это главный кандидат на замену derived-параметрами.

- Что лучше тестировать (`pytest`):
  - Unit: `live_actions` (auto-skip, victory/defeat, escape success/fail, edge cases empty order).
  - Unit: `machine_commands/apply_machine` (разбор @@, allowlist cause, fallback behavior).
  - Unit: `log_ui.normalize` (дедуп status, round separator, preamble injection).
  - Integration: WS combat lock + auto enemy turn loop + persistence/restore (`combat_state_v1`, `combat_log_history`).
  - Narration: extraction + coverage/drift guard (чтобы репромпт и fallback срабатывали детерминированно).
