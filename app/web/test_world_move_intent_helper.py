from types import SimpleNamespace

from app.combat.state import end_combat, start_combat
from app.web import server


def test_apply_world_move_from_text_moves_and_prefixes():
    sess = SimpleNamespace(id="sess_test", settings={})
    text, moved = server._apply_world_move_from_text(sess, "sess_test", "иду вперед")
    assert moved is True
    assert "ТЕКУЩАЯ МЕСТНОСТЬ" in text
    assert "ТРЕБОВАНИЕ" in text
    assert isinstance(sess.settings.get("world"), dict)
    assert isinstance(sess.settings["world"].get("env"), str)
    assert sess.settings["world"]["env"]


def test_apply_world_move_from_text_no_move_keeps_text():
    sess = SimpleNamespace(id="sess_test", settings={})
    text, moved = server._apply_world_move_from_text(sess, "sess_test", "осматриваюсь вокруг")
    assert moved is False
    assert text == "осматриваюсь вокруг"


def test_apply_world_move_from_text_ignored_when_combat_active():
    session_id = "sess_test_combat"
    start_combat(session_id)
    try:
        sess = SimpleNamespace(id=session_id, settings={})
        text, moved = server._apply_world_move_from_text(sess, session_id, "иду вперед")
        assert moved is False
        assert text == "иду вперед"
        assert sess.settings.get("world") is None
    finally:
        end_combat(session_id)
