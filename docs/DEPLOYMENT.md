# DEPLOYMENT

## Single-worker only (current architecture)

На текущей архитектуре боевой runtime хранится в памяти процесса (`app/combat/state.py`), поэтому production запускать только с `1` worker.

- `uvicorn`: `python -m uvicorn app.web.server:app --host 127.0.0.1 --port 8000 --workers 1`
- `gunicorn`: `gunicorn -w 1 -k uvicorn.workers.UvicornWorker app.web.server:app`

## Guard and override

На старте приложения включен guard: если обнаружено `workers > 1`, приложение завершится с `RuntimeError`.

Снять запрет можно только осознанно:
- `DND_ALLOW_MULTI_WORKER=1`

Это рискованно: разные workers будут иметь разный in-memory combat state, что может ломать целостность боевых сессий.

## Perf logs

- `DND_PERF_LOG=1` включает лёгкие perf-логи для session lock/broadcast таймингов.
- `DND_PERF_WARN_MS=250` задаёт порог для `WARNING` (ниже порога — `DEBUG`).
