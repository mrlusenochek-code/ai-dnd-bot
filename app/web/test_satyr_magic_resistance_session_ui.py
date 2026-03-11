from __future__ import annotations

from pathlib import Path


def test_satyr_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Сопротивление магии: преимущество на спасброски от заклинаний и прочих магических эффектов" in template
