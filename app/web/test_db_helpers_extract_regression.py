from pathlib import Path

import app.web.db_helpers as dbh


def test_server_no_db_helper_defs() -> None:
    server_src = Path(__file__).with_name("server.py").read_text(encoding="utf-8")
    assert "def get_or_create_player_web" not in server_src
    assert "def get_player_by_uid" not in server_src
    assert "def get_session" not in server_src
    assert "def list_session_players" not in server_src


def test_db_helpers_exports_callable() -> None:
    assert callable(dbh.get_or_create_player_web)
    assert callable(dbh.get_player_by_uid)
    assert callable(dbh.get_session)
    assert callable(dbh.list_session_players)
