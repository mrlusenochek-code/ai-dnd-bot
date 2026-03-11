from __future__ import annotations

from pathlib import Path


def test_orc_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Прилив адреналина: бонусным действием совершаете Рывок и получаете temp HP = PB." in template
    assert "потрачено, восстановится после долгого отдыха" in template
    assert "использований: ${orcAdrenalineRemaining}/${orcPb}" in template
