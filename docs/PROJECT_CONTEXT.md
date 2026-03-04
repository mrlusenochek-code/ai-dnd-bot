# PROJECT CONTEXT (Quickstart)

## Что это за проект
`ai-dnd-bot` — веб-движок DnD-подобной игры на `FastAPI + WebSocket + Postgres`.

Есть два слоя:
- Нарративный чат: игрок пишет свободным текстом, GM (LLM) отвечает художественно под ограничителями (`sanitize/guards`), чтобы не ломать сцену и не писать за игрока.
- Боевой режим: структурная механика боя (`@@COMBAT_*`, очередь, live actions, death saves, предметы/лечение, награды, идемпотентность).

Опора на механику — документы/референсы в репозитории (`SRD/PHB/DMG` и сопутствующие материалы).

## Карта модулей
- `app/web/server.py`: wiring-only entrypoint (реэкспорт из `server_impl`, без доменной логики).
- `app/web/server_impl.py`: центр оркестрации (WS, фазы/ходы, GM pipeline, combat patch, `broadcast_state`).
- `app/gm/*`:
- `service.py`: two-pass и repair-циклы.
- `sanitize.py`: очистка шумов/мета/псевдо-механик.
- `checks.py`: `@@CHECK` -> броски -> результаты + XP/skills.
- `narration.py`: контекст локации, `MOVED:true/false`.
- `app/combat/*`: in-memory runtime, parser/apply `@@COMBAT_*`, live actions, UI patch журнала.
- `app/rules/*`: world map, move intents, encounters, loot/defeat/death/enemy catalog.
- `app/db/*`: модели (`sessions`, `characters`, `skills`, `events` и др.).
- `app/ai/gm.py`: адаптер генерации GM/lore.

## Где хранится состояние
- Долгоживущее: таблицы `characters`, `skills`, `events`.
- Оперативное JSON: `sessions.settings` (мир, combat snapshot/history, фазы, идемпотентные ключи наград/поражений).
- Runtime: активный бой хранится в памяти процесса.
- Ограничение деплоя: из-за in-memory runtime боёвки production сейчас запускать только с `1` worker.
- Startup guard блокирует `workers > 1` (если не задан явный override).
- Детали и примеры запуска: [DEPLOYMENT.md](./DEPLOYMENT.md).

## Уже реализовано (ключевое)
- Идемпотентные боевые награды/лут.
- `def` у инвентарных предметов и связанные фиксы.
- Defeat outcomes/effects (идемпотентно).
- Death saves, stabilize, лечение предметами (включая auto-логику на 0 HP).
- Каталог врагов из `dnd.su`, world map + movement + encounters.
- Усиленный GM-слой (`two-pass`, guards/repair).
- Рабочий `@@CHECK` с записью XP/skills.
- Починенный UI навыков и прогресса уровня.

## Главный риск
Самый большой техдолг: концентрация логики в `app/web/server.py` + конкурентность (`WS`, background tasks, in-memory combat runtime).

## Приоритетные next steps
1. Разделить `server.py` на контексты (`ws handlers`, `gm orchestrator`, `combat bridge`, `state builder`).
2. Усилить per-session lock стратегию для боевых мутаций и критических секций.
3. Упорядочить transaction/commit-границы (меньше частичных коммитов в одном сценарии).
4. Декомпозировать `session.html` и уменьшить полный перерендер.
5. Подготовить план выноса combat runtime из памяти процесса (для scale-out/рестартов).

## Правила работы по репо
- Работаем в `main` (без веток, пока явно не требуется иначе).
- После изменений: `python -m py_compile` -> `pytest -q` -> `git commit` -> `git push origin main`.
- Изменения кода выполняются через Codex.
- Для механик ориентир — документы/референсы в репозитории.

## Дополнительно
Подробный архитектурный обзор, риски и рекомендации:
- [CODE_REVIEW.md](./CODE_REVIEW.md)

## Контракт entrypoint
- `app/web/server.py` должен оставаться wiring-only: импорт/реэкспорт, без route-декораторов и доменной логики.
- Реализация Web/API должна добавляться в `app/web/server_impl.py`.
