from __future__ import annotations

from pathlib import Path


def test_minotaur_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Пронзающий натиск: после Рывка и 20 фт — бонусным действием атака рогами" in template
    assert "Сокрушительные рога: после попадания melee в действии Атака" in template
