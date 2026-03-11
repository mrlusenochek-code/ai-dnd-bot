from __future__ import annotations

from pathlib import Path


def test_session_template_shows_brave_text() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert 'const braveText = saveAdvantageConditions.includes("frightened")' in template
    assert "Храбрый: преим. спасброски против испуга" in template
