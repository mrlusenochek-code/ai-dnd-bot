# REFACTOR ROADMAP

Документ описывает безопасный план рефакторинга без изменения продуктового поведения на первом этапе.

## Цели
- Распилить `app/web/server.py` на логические контексты.
- Усилить конкурентность через явную per-session синхронизацию.
- Подготовить UI к инкрементальным патчам вместо полного перерендеринга.

## Ограничения
- Этап 1: без изменения поведения, только перенос кода/интерфейсов/тестов.
- Любой функциональный change только после фиксации структуры и покрытия регрессий.

## Этап A. Распил `server.py` (без behavioral changes)

### Целевая структура (первый шаг: 5 модулей)
- `app/web/server.py`
  - FastAPI app/lifespan, route registration, wiring зависимостей.
- `app/web/ws_handlers.py`
  - `ws_room`, parsing входящих WS action, dispatch в orchestration API.
- `app/web/gm_orchestrator.py`
  - `_run_gm_two_pass`, `_auto_gm_reply_task`, `_auto_round_task`, helper-ы prompt/check results.
- `app/web/combat_bridge.py`
  - machine/apply/live action bridge, combat patch merge, preamble/status assembly.
- `app/web/state_builder.py`
  - `build_state`, `broadcast_state`, `send_state_to_ws`, combat_log_history persistence helpers.
- `app/web/session_state.py`
  - `settings_get/settings_set`, phase/ready/initiative helpers, typed accessors к `sessions.settings`.
  - `app/web/constants.py`
  - Единый источник ключей/лимитов web-state (без дублей в модулях).
  - Сейчас хранит: `COMBAT_LOG_HISTORY_KEY`, `COMBAT_STATE_KEY`, `MAX_COMBAT_LOG_LINES`.
  - Используется `server.py`, `state_builder.py`, тестами (через re-export из `server.py`).

### Таблица переноса
| Что переносим из `server.py` | Куда | Комментарий |
| --- | --- | --- |
| `ws_room` и связанные action ветки | `ws_handlers.py` | Только перенос + thin adapter к existing functions |
| `_auto_gm_reply_task`, `_auto_round_task`, `_auto_lore_task`, `_run_gm_two_pass` | `gm_orchestrator.py` | Сохраняем текущие сигнатуры |
| `apply/merge` боевых patch и bootstrap paths | `combat_bridge.py` | Без изменения формата patch |
| `build_state`, `broadcast_state`, `send_state_to_ws`, `_persist_combat_*` | `state_builder.py` | Отдельно от transport слоя |
| `_ensure_settings`, `settings_get/set`, phase/ready/initiative accessors | `session_state.py` | Единый владелец `sessions.settings` keys |

### Публичные интерфейсы (минимально)
- `gm_orchestrator.py`
  - `async def run_turn_gm(session_id: str, expected_action_id: str) -> None`
  - `async def run_round_gm(session_id: str, expected_action_id: str) -> None`
  - `async def run_lore_generation(session_id: str) -> None`
- `combat_bridge.py`
  - `def apply_machine_text(session_id: str, text: str) -> dict[str, Any] | None`
  - `def run_live_action(session_id: str, action: str) -> tuple[dict[str, Any] | None, str | None]`
- `state_builder.py`
  - `async def build_state_payload(db: AsyncSession, sess: Session) -> dict[str, Any]`
  - `async def broadcast_session_state(session_id: str, combat_patch: dict[str, Any] | None = None) -> None`
- `session_state.py`
  - typed wrappers `get_phase/set_phase`, `get_ready_map/set_ready_map`, `get_combat_markers/set_combat_markers`.

### Порядок PR/коммитов (маленькие и безопасные)
1. PR1: ввести `session_state.py`; заменить прямые обращения к settings helper-ами (без move сложных функций).
2. PR2: вынести `state_builder.py` + тесты на shape payload/broadcast side effects.
3. PR3: вынести `combat_bridge.py` + тесты merge/patch/status.
4. PR4: вынести `gm_orchestrator.py` + сохранить вызовы из `ws_room`.
5. PR5: очистить `server.py` до wiring/router/lifespan.
6. PR6: точечная правка импортов/циклических зависимостей и доки.

### Критерии готовности этапа A
- Поведение e2e прежнее (регрессионные тесты зелёные).
- `server.py` больше не содержит доменную логику GM/combat/state assembly.
- Для каждого вынесенного модуля есть хотя бы smoke/contract тесты.

## Этап B. Конкурентность и критические секции

### Стратегия per-session lock
### Актуальная реализация session lock (и правила без дедлоков)

Сейчас в коде используется один per-session lock:

- `asyncio.Lock` на `session_id`: `_get_session_gm_lock(session_id)` (см. `app/web/server.py`).
- Этот lock используется как “мутационный” для одной сессии:
  - сериализация `broadcast_state(...)` (внутри `broadcast_state` берётся lock),
  - боевые мутации в `ws_room` (ветки `apply_combat_machine_commands`, `handle_live_combat_action`, `end_combat`),
  - фоновые GM-задачи (`_auto_gm_reply_task`, `_auto_round_task`) и их критические секции.

Правила (строго):
- **НЕЛЬЗЯ** вызывать `broadcast_state(...)` внутри `async with _get_session_gm_lock(session_id):`  
  (будет дедлок, потому что `broadcast_state` берёт lock внутри себя).
- Если lock уже взят — вызывать **только** `_broadcast_state_unlocked(...)`.
- Любая новая ветка, которая мутирует боёвку (in-memory combat state) или делает важные изменения в `sessions.settings`,
  должна быть сериализована per-session lock’ом.
- **LLM вызовы** (`generate_from_prompt`, `gm_combat_narration...`) должны быть **вне** lock’а. Lock держим только на короткую
  секцию: “мутация → (unlocked) broadcast”.
- Текущий компромисс: отправка состояния в WS (`manager.broadcast_json`) сейчас происходит внутри `_broadcast_state_unlocked`,
  значит lock может держаться во время отправки. Это упрощает порядок/атомарность, но может увеличивать задержки.
  Будущая оптимизация: собирать payload под lock, а отправку делать после release (потребует контроля порядка через revision).

- Ввести единый registry lock-ов: `SessionLockRegistry`.
- Ключ lock: `session_id` (UUID string).
- Использовать один базовый lock для всех mutation paths:
  - `ws_room` mutating actions,
  - `_auto_gm_reply_task`/`_auto_round_task`/`_auto_lore_task`,
  - `timer_watcher`/`inactive_watcher` при изменении сессии,
  - `broadcast_state`, если внутри есть mutations (`settings`, rewards, defeat effects, combat snapshot).

### Где нельзя держать lock долго
- Нельзя держать lock вокруг внешних LLM вызовов (`generate_from_prompt`, `generate_lore`).
- Нельзя держать lock во время `manager.broadcast_json` (I/O на WS).
- Подход: read snapshot -> release -> slow call -> reacquire + compare action_id/version -> apply if still актуально.

### Критические секции (минимум)
1. Phase/action_id transitions (`collecting_actions -> gm_pending -> turns`).
2. Combat runtime mutation + persist snapshot в settings.
3. Выдача reward/defeat и установка idempotency markers.
4. Watcher auto-pass/inactive transitions.

### Требования к транзакциям
- Один логический сценарий = один транзакционный блок commit.
- Избегать sequence `commit -> add_event -> commit -> broadcast` в середине критических переходов.
- Добавить явный `session_version` (или updated_at/etag) для optimistic check после длительных async операций.

### Минимальный первый шаг (даёт пользу сразу)
- Расширить текущий `_get_session_gm_lock` до `session mutation lock` и применить в:
  - `ws_room` для mutating action branches,
  - `timer_watcher`/`inactive_watcher` перед `advance_turn`/`sp.is_active` updates.
- Это уменьшит самые частые гонки без полного рефакторинга.

### Критерии готовности этапа B
- Нет несериализованных мутаций одной сессии из разных задач.
- Набор race-тестов стабильно зелёный (concurrent say/combat action/watcher tick).
- Уменьшено количество частичных commit в ключевых сценариях.

## Этап C. UI: переход на инкрементальные патчи

### Текущая проблема
- `renderState` в `session.html` полностью перерисовывает players и events log на каждый state.
- Combat log уже patch-based, но остальная часть UI нет.

### Мини-план (дизайн)
1. Ввести клиентский store: `state_store.js` (last snapshot + revision).
2. Добавить серверные патчи:
   - `players_patch` (upsert/remove/flags),
   - `events_patch` (append/truncate, cursor).
3. Перевести players рендерер на keyed update по `player.id` вместо полного `innerHTML = ""`.
4. Перевести events log на append-only + лимит окна, full snapshot оставить как recovery.
5. Оставить `state` full snapshot как periodic resync (например, при reconnect/каждые N обновлений).

### Риски этапа C
- Потеря синхронизации client store при пропущенных patch сообщениях.
- Неправильный merge патчей при reorder WS кадров.

### Митигации
- Нумерация `state_revision` и `patch_base_revision`.
- При mismatch ревизии клиент запрашивает/ждёт full state ресинк.

### Критерии готовности этапа C
- Снижено количество полного DOM rebuild.
- Реконнект и пропуск сообщений корректно восстанавливаются через full snapshot fallback.
- Нагрузка (частые broadcast) не приводит к деградации UI responsiveness.

## Общая стратегия тестирования по roadmap
- Unit: модули `session_state`, `state_builder`, `combat_bridge`, `gm_orchestrator`.
- Integration: WS сценарии `say -> gm_pending -> gm_reply`, combat live-actions, watcher race cases.
- Regression: идемпотентность rewards/defeat, restore combat после restart.

## Definition of Done (в целом)
- Монолит `server.py` сокращён до wiring-уровня.
- Пер-сессионная конкурентность формализована и покрыта тестами.
- UI использует патчи для hot-path обновлений, snapshot остаётся резервом.
- Документация и архитектурные контракты синхронизированы с кодом.
