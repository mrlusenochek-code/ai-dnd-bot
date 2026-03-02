# ai-dnd-bot (ИИ ДНД)

Веб-движок DnD-подобной игры на FastAPI + WebSocket + Postgres: нарративный чат + структурный бой.

## Документация (с чего начать)
- Контекст проекта: [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)
- Обзор архитектуры / риски: [docs/CODE_REVIEW.md](docs/CODE_REVIEW.md)
- Карта боёвки: [docs/COMBAT_MAP.md](docs/COMBAT_MAP.md)
- Спека экипировки: [docs/EQUIPMENT_SPEC.md](docs/EQUIPMENT_SPEC.md)
- Регресс-чек: [REGRESSION.md](REGRESSION.md)

## Правила работы по репо
- По умолчанию работаем напрямую в `main` (без веток, пока явно не требуется иначе).
- После любых изменений: `python -m py_compile` → `pytest -q` → `git commit` → `git push origin main`.
- Изменения кода выполняем через Codex.

## Быстрый старт (WSL)
1) Перейти в проект:
```bash
cd ~/code/ai-dnd-bot
```

2) Запустить сервер (подхватит venv и `.env`):
```bash
./run.sh
```

3) Открыть в браузере:
- http://127.0.0.1:8000

## Поднять БД и миграции (Postgres)
```bash
./db_up.sh
```

## Smoke-test (проверка, что сервер жив)
В отдельном терминале:
```bash
cd ~/code/ai-dnd-bot
./smoke.sh
```

## База данных
- Обычно используется Postgres из `.env` (`DATABASE_URL_ASYNC`).
- Если переменная не задана, включится dev-fallback на SQLite: `sqlite+aiosqlite:///./dev.db`.
