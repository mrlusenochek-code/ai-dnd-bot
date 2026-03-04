import logging
import os
from typing import Any


def perf_enabled() -> bool:
    return os.getenv("DND_PERF_LOG", "").strip() == "1"


def perf_warn_ms() -> int:
    raw = os.getenv("DND_PERF_WARN_MS", "250").strip()
    try:
        value = int(raw)
    except Exception:
        value = 250
    return max(50, min(60000, value))


def log_perf(
    logger: logging.Logger,
    name: str,
    ms: float,
    *,
    fields: dict[str, Any] | None = None,
    warn_ms: int | None = None,
) -> None:
    if not perf_enabled():
        return

    threshold = perf_warn_ms() if warn_ms is None else warn_ms
    level = logging.WARNING if ms >= threshold else logging.DEBUG
    payload = {"name": name, "ms": round(float(ms), 2)}
    if fields:
        payload.update(fields)

    logger.log(level, "perf", extra={"perf": payload})
