import pytest

from app.web.deploy_guard import detect_worker_count, ensure_single_worker


def _clear_worker_env(monkeypatch):
    for key in (
        "WEB_CONCURRENCY",
        "UVICORN_WORKERS",
        "WORKERS",
        "GUNICORN_CMD_ARGS",
        "DND_ALLOW_MULTI_WORKER",
    ):
        monkeypatch.delenv(key, raising=False)


def test_detect_worker_count_from_web_concurrency(monkeypatch):
    _clear_worker_env(monkeypatch)
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    assert detect_worker_count() == 2


def test_detect_worker_count_from_gunicorn_long_flag(monkeypatch):
    _clear_worker_env(monkeypatch)
    monkeypatch.setenv("GUNICORN_CMD_ARGS", "--workers 3")
    assert detect_worker_count() == 3


def test_detect_worker_count_from_gunicorn_short_flag(monkeypatch):
    _clear_worker_env(monkeypatch)
    monkeypatch.setenv("GUNICORN_CMD_ARGS", "-w 4")
    assert detect_worker_count() == 4


def test_ensure_single_worker_raises_for_multi_worker(monkeypatch):
    _clear_worker_env(monkeypatch)
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    with pytest.raises(RuntimeError):
        ensure_single_worker()


def test_ensure_single_worker_allows_override(monkeypatch):
    _clear_worker_env(monkeypatch)
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    monkeypatch.setenv("DND_ALLOW_MULTI_WORKER", "1")
    ensure_single_worker()
