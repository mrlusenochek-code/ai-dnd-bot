from __future__ import annotations

from pathlib import Path


def test_session_template_shows_dwarven_resilience_text() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Дварфская стойкость: " in template
    assert "сопротивление яду" in template
    assert "преимущество против яда" in template
