from __future__ import annotations

from pathlib import Path


def test_genasi_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Наследие стихий:" in template
    assert "Бесконечное дыхание: можете задерживать дыхание без ограничений" in template
    assert "Смешаться с ветром: Левитация — " in template
    assert ". Базовая характеристика — Телосложение" in template
    assert "Огненная магия: Создание огня — доступно всегда; Горящие руки — " in template
    assert "Ходьба по земле: сложная местность из земли и камня не требует дополнительного перемещения" in template
    assert "Плавание: ${Number(speeds.swim_ft)} фт" in template
    assert "Амфибия: можете дышать и воздухом, и водой" in template
