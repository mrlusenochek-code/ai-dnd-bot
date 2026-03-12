from __future__ import annotations

from pathlib import Path


def test_satyr_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Таран: рога 1к4 + СИЛ дробящий (природное оружие)" in template
    assert "Сопротивление магии: преимущество на спасброски от заклинаний и прочих магических эффектов" in template
    assert "Зрелищные прыжки: +1к8 футов к прыжку в длину/высоту" in template
