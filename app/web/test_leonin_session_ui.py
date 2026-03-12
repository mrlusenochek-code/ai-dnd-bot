from __future__ import annotations

from pathlib import Path


def test_leonin_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Когти: природное оружие 1к4 + СИЛ рубящий" in template
    assert "Инстинкты охотника: владение навыком" in template
    assert "Устрашающий рёв: бонусным действием" in template
