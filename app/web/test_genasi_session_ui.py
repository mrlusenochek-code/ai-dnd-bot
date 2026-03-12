from __future__ import annotations

from pathlib import Path


def test_genasi_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Наследие стихий:" in template
    assert "Ходьба по земле: сложная местность из земли и камня не требует дополнительного перемещения" in template
    assert "Плавание: ${Number(speeds.swim_ft)} фт" in template
    assert "Амфибия: можете дышать и воздухом, и водой" in template
