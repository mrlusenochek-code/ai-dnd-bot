from __future__ import annotations

from pathlib import Path


def test_locathah_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Воля Левиафана: преимущество на спасброски от испуга/яда/очарования/ошеломления/паралича/усыпления" in template
