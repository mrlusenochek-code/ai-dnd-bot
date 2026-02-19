# ai-dnd-bot (ИИ ДНД)

Локальный запуск для разработки (WSL).

## Быстрый старт
1) Перейти в проект:
```bash
cd ~/code/ai-dnd-bot
```

2) Запустить сервер (подхватит venv и .env):
```bash
./run.sh
```

3) Открыть в браузере:
- http://127.0.0.1:8000

## Smoke-test (проверка, что сервер жив)
В отдельном терминале:
```bash
cd ~/code/ai-dnd-bot
./smoke.sh
```

## База данных
- Обычно используется Postgres из `.env` (`DATABASE_URL_ASYNC`).
- Если переменная не задана, включится dev-fallback на SQLite: `sqlite+aiosqlite:///./dev.db`.

## Регресс-чек
Смотри: `REGRESSION.md`

## Ветки
Рабочая ветка: `ws-logging`
