from __future__ import annotations


def test_ws_handlers_imports_set_ready() -> None:
    import app.web.ws_handlers as m

    assert hasattr(m, "_set_ready")
    assert callable(m._set_ready)
