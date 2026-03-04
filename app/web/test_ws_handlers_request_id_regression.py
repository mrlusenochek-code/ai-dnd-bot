from __future__ import annotations


def test_ws_handlers_has_new_request_id_helper() -> None:
    import app.web.ws_handlers as m

    rid = m._new_request_id()
    assert isinstance(rid, str)
    assert len(rid) == 32
    assert all(c in "0123456789abcdef" for c in rid)
