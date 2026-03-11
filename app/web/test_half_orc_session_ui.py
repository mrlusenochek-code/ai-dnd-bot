from __future__ import annotations

from pathlib import Path


def test_half_orc_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Неукротимая стойкость: когда должны упасть до 0 HP, остаётесь на 1 HP" in template
    assert "Свирепые атаки: на крите рукопашным оружием +1 кость урона оружия" in template
    assert "потрачено, восстановится после долгого отдыха" in template
    assert "готово" in template
