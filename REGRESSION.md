# Regression checklist (ИИ ДНД / ai-dnd-bot)

## Цель
Проверить, что после фиксов:
- ход/кнопка "Отправить" работает без ручных костылей со "Статус"
- список игроков не становится "пустым"
- init/roll/turn/pass/pause работают без исключений
- сервер и WS не падают, логи чистые

## Предусловия (WSL)
1) Активировать venv:
   source ~/venvs/ai-dnd-bot.venv/bin/activate

2) Загрузить env:
   set -a; source .env; set +a

3) База (если нужна):
   cd ~/code/ai-dnd-bot
   docker compose ps
   alembic upgrade head

4) Запуск сервера:
   python -m uvicorn app.web.server:app --host 127.0.0.1 --port 8000

## Ручной прогон (2 игрока + админ)
Сценарий:
1) Создать игру "S" (админ).
2) Подключить 2-го игрока.
3) Оба ставят ГОТОВ.
4) Старт игры — проверка, что первый ход норм.
5) На ходе игрока:
   - поле ввода активно
   - кнопка "Отправить" активируется сразу при вводе
   - не нужно нажимать "Статус" для активации
6) Передача хода туда-сюда:
   - сообщения проходят
   - "Следующий ход: игрок #..." соответствует реальности
7) Проверить команды:
   - pass/end на своём ходу: ход завершается
   - roll/adv/dis: бросок выводится, ход НЕ заканчивается
   - pause/resume: таймер/пауза не ломают ход
   - init (админ): не падает, не путает uuid/bigint

## Ожидаемые признаки успеха
- Нет ошибок/traceback в консоли uvicorn
- Нет “пустого состояния игроков” на фронте
- Кнопка "Отправить" не требует "Статус" для оживления

## Проверка реконнекта WS и join (без спама)
Цель: убедиться, что при падении сервера фронт не долбит /api/join в ошибку,
а при поднятии сервера восстанавливается сам (без F5).

### 1) Падение сервера (Ctrl+C)
1) Открыть сессию /s/<session_id> в браузере, DevTools → Network.
2) Остановить uvicorn (Ctrl+C).
Ожидаемо:
- WebSocket закрывается/становится завершённым.
- В Network НЕ появляется пачка красных запросов POST /api/join.
- В логе клиента видно backoff: 1s → 2s → 4s → 8s → (до 10s).

### 2) Поднятие сервера (без F5)
1) Запустить uvicorn снова.
Не обновляя страницу:
Ожидаемо:
- Клиент пишет `[client] connected`.
- Появляется новый `websocket 101`.
- Делается один `POST /api/join 200` (после открытия WS).
- Состояние и игроки отображаются корректно.

### 3) Первый заход "с нуля" (без localStorage)
1) DevTools → Application → Local Storage → удалить ключи `uid` и `name` (или Clear).
2) Обновить страницу.
Ожидаемо:
- Появляется prompt имени игрока 1 раз.
- Далее `websocket 101` и один `POST /api/join 200`.


“Админ: кнопка Кик подставляет /kick <order> и не показывает кик на себе”

“Кнопка Копировать ссылку: пишет link copied”



## Логи “золотого прогона” (пример)
(сюда можно вставлять последний успешный лог из консоли — коротким блоком,
чтобы сравнивать при будущих регрессиях)
lus@DESKTOP-TMTO836:~/code/ai-dnd-bot$ dnd-run
INFO:     Started server process [13409]
INFO:     Waiting for application startup.
{"ts": "2026-02-19T12:30:24.739622+00:00", "level": "INFO", "logger": "app.web.server", "message": "Web server starting", "request_id": null, "session_id": null, "uid": null, "ws_conn_id": null}
{"ts": "2026-02-19T12:30:24.744311+00:00", "level": "INFO", "logger": "uvicorn.error", "message": "Application startup complete.", "request_id": null, "session_id": null, "uid": null, "ws_conn_id": null}
{"ts": "2026-02-19T12:30:24.744991+00:00", "level": "INFO", "logger": "uvicorn.error", "message": "Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)", "request_id": null, "session_id": null, "uid": null, "ws_conn_id": null}
{"ts": "2026-02-19T12:30:25.405203+00:00", "level": "INFO", "logger": "uvicorn.error", "message": "127.0.0.1:34398 - \"WebSocket /ws/ffc99ecc-bd61-4d4e-948d-1e429a30eefb?uid=1622692024\" [accepted]", "request_id": "affab684f2d6409f96da3ae19575a9fc", "session_id": "ffc99ecc-bd61-4d4e-948d-1e429a30eefb", "uid": 1622692024, "ws_conn_id": "aa392185d910"}
{"ts": "2026-02-19T12:30:25.405392+00:00", "level": "INFO", "logger": "app.web.server", "message": "ws connected", "request_id": "affab684f2d6409f96da3ae19575a9fc", "session_id": "ffc99ecc-bd61-4d4e-948d-1e429a30eefb", "uid": 1622692024, "ws_conn_id": "aa392185d910"}
{"ts": "2026-02-19T12:30:25.408821+00:00", "level": "INFO", "logger": "uvicorn.error", "message": "connection open", "request_id": null, "session_id": null, "uid": null, "ws_conn_id": null}
{"ts": "2026-02-19T12:30:25.461267+00:00", "level": "INFO", "logger": "app.web.server", "message": "http request", "request_id": "f0e5de7e119b4770a72b49cb1aaf091d", "session_id": "ffc99ecc-bd61-4d4e-948d-1e429a30eefb", "uid": 1622692024, "ws_conn_id": null, "http": {"method": "POST", "path": "/api/join", "status": 200}}
{"ts": "2026-02-19T12:30:25.461416+00:00", "level": "INFO", "logger": "uvicorn.access", "message": "127.0.0.1:34400 - \"POST /api/join HTTP/1.1\" 200", "request_id": null, "session_id": null, "uid": null, "ws_conn_id": null}
^C{"ts": "2026-02-19T12:30:40.467840+00:00", "level": "INFO", "logger": "uvicorn.error", "message": "Shutting down", "request_id": null, "session_id": null, "uid": null, "ws_conn_id": null}
{"ts": "2026-02-19T12:30:40.468583+00:00", "level": "INFO", "logger": "uvicorn.error", "message": "connection closed", "request_id": null, "session_id": null, "uid": null, "ws_conn_id": null}
{"ts": "2026-02-19T12:30:40.568900+00:00", "level": "INFO", "logger": "uvicorn.error", "message": "Waiting for application shutdown.", "request_id": null, "session_id": null, "uid": null, "ws_conn_id": null}
{"ts": "2026-02-19T12:30:40.569095+00:00", "level": "INFO", "logger": "uvicorn.error", "message": "Application shutdown complete.", "request_id": null, "session_id": null, "uid": null, "ws_conn_id": null}
{"ts": "2026-02-19T12:30:40.569204+00:00", "level": "INFO", "logger": "uvicorn.error", "message": "Finished server process [13409]", "request_id": null, "session_id": null, "uid": null, "ws_conn_id": null}






















