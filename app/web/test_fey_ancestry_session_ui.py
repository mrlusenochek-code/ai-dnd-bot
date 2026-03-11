from __future__ import annotations

from pathlib import Path


def test_session_template_shows_fey_ancestry_text() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Наследие фей: " in template
    assert "преимущество против очарования" in template
    assert "иммунитет к магическому сну" in template
