from __future__ import annotations

from pathlib import Path


def test_session_template_shows_reborn_deathless_nature_text() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Бессмертная природа: преимущество на спасброски от болезней и отравления" in template
    assert "преимущество на спасброски смерти" in template
    assert "сопротивление урону ядом" in template
    assert "магия не может усыпить" in template
    assert "не нужно есть/пить/дышать/спать" in template
