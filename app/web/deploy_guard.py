import logging
import os
import shlex
from typing import Optional


logger = logging.getLogger(__name__)


def _parse_positive_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    txt = str(raw).strip()
    if not txt:
        return None
    try:
        value = int(txt)
    except Exception:
        return None
    if value <= 0:
        return None
    return value


def _workers_from_gunicorn_cmd_args(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        tokens = shlex.split(raw)
    except Exception:
        return None
    for i, token in enumerate(tokens):
        if token in {"--workers", "-w"}:
            if i + 1 < len(tokens):
                parsed = _parse_positive_int(tokens[i + 1])
                if parsed is not None:
                    return parsed
            continue
        if token.startswith("--workers="):
            parsed = _parse_positive_int(token.split("=", 1)[1])
            if parsed is not None:
                return parsed
        if token.startswith("-w") and token != "-w":
            parsed = _parse_positive_int(token[2:])
            if parsed is not None:
                return parsed
    return None


def detect_worker_count() -> int | None:
    for key in ("WEB_CONCURRENCY", "UVICORN_WORKERS", "WORKERS"):
        parsed = _parse_positive_int(os.getenv(key))
        if parsed is not None:
            return parsed
    return _workers_from_gunicorn_cmd_args(os.getenv("GUNICORN_CMD_ARGS"))


def ensure_single_worker() -> None:
    if os.getenv("DND_ALLOW_MULTI_WORKER", "").strip() == "1":
        return

    workers = detect_worker_count()
    if workers is not None and workers > 1:
        msg = (
            "Multi-worker startup blocked: combat runtime is in-memory and not shared across workers. "
            f"Detected workers={workers}. Use workers=1 (uvicorn/gunicorn) or set DND_ALLOW_MULTI_WORKER=1 "
            "to override at your own risk."
        )
        logger.error(msg)
        raise RuntimeError(msg)
