from __future__ import annotations

from pathlib import Path


def test_harengon_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Заячье сердце: +БМ к инициативе" in template
    assert "Сильные ноги: реакцией после провала спасброска Ловкости" in template
    assert "Кроличий прыжок: статус" in template
