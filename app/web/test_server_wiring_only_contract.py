from __future__ import annotations

import ast
from pathlib import Path


APP_WEB_DIR = Path(__file__).resolve().parent


def test_server_py_is_wiring_only_contract() -> None:
    p = APP_WEB_DIR / "server.py"
    src = p.read_text(encoding="utf-8")

    # must stay small / thin
    assert src.count("\n") + 1 <= 140

    # no route decorators in entrypoint
    assert "@app." not in src
    assert ".websocket(" not in src

    # no domain defs in entrypoint
    tree = ast.parse(src)
    defs = [
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    assert not defs

    # must reference server_impl (the implementation module)
    assert "server_impl" in src

    # sanity: entrypoint still exposes FastAPI app
    from app.web import server as server_mod  # noqa: WPS433

    assert hasattr(server_mod, "app")
