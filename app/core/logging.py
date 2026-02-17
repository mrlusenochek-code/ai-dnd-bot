from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.log_context import get_log_context


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        payload.update(get_log_context())
        # include structured extras (e.g., logger.info(..., extra={"http": {...}}))
        for k, v in record.__dict__.items():
            if k in ("name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
                     "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
                     "relativeCreated", "thread", "threadName", "processName", "process", "message"):
                continue
            # don't overwrite our core fields
            if k in payload:
                continue
            payload[k] = v
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        try:
            return json.dumps(payload, ensure_ascii=False, default=str)
        except Exception as e:
            fallback: dict[str, Any] = {
                "ts": payload.get("ts"),
                "level": payload.get("level"),
                "logger": payload.get("logger"),
                "message": payload.get("message"),
            }
            fallback.update(get_log_context())
            fallback["json_error"] = str(e)
            return json.dumps(fallback, ensure_ascii=False, default=str)



def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
        uvicorn_logger.setLevel(level)

