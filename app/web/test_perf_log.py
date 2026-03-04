import logging

from app.web.perf_log import log_perf, perf_enabled


class _CollectHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_perf_enabled_flag(monkeypatch):
    monkeypatch.setenv("DND_PERF_LOG", "0")
    assert perf_enabled() is False

    monkeypatch.setenv("DND_PERF_LOG", "1")
    assert perf_enabled() is True


def test_log_perf_levels(monkeypatch):
    monkeypatch.setenv("DND_PERF_LOG", "1")
    monkeypatch.setenv("DND_PERF_WARN_MS", "10")

    logger = logging.getLogger("app.web.test_perf_log")
    handler = _CollectHandler()
    old_level = logger.level
    old_handlers = list(logger.handlers)
    old_propagate = logger.propagate
    try:
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        log_perf(logger, "fast", 5.0)
        log_perf(logger, "slow", 55.0)
    finally:
        logger.handlers = old_handlers
        logger.setLevel(old_level)
        logger.propagate = old_propagate

    assert len(handler.records) == 2
    assert handler.records[0].levelno == logging.DEBUG
    assert handler.records[1].levelno == logging.WARNING
