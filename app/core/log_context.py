from __future__ import annotations

from contextvars import ContextVar
from typing import Any


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
session_id_var: ContextVar[str | None] = ContextVar("session_id", default=None)
uid_var: ContextVar[int | None] = ContextVar("uid", default=None)
ws_conn_id_var: ContextVar[str | None] = ContextVar("ws_conn_id", default=None)
client_id_var: ContextVar[str | None] = ContextVar("client_id", default=None)


def get_log_context() -> dict[str, Any]:
    return {
        "request_id": request_id_var.get(),
        "session_id": session_id_var.get(),
        "uid": uid_var.get(),
        "ws_conn_id": ws_conn_id_var.get(),
        "client_id": client_id_var.get(),
    }
