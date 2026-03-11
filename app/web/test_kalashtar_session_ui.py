from __future__ import annotations

from pathlib import Path


def test_kalashtar_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Связь разумов" in template
    assert "связь не активна" in template
    assert "телепатия (дистанция = уровень×10 фт)" in template
