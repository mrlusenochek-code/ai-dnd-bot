from __future__ import annotations


def test_ws_handlers_can_resolve_build_player_gm_action_text() -> None:
    import app.web.ws_handlers as ws
    import app.web.server as server

    fn = ws._resolve_build_player_gm_action_text()
    assert fn is server._build_player_gm_action_text
    assert callable(fn)
