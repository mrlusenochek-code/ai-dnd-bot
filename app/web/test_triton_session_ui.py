from pathlib import Path


def test_triton_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Амфибия: можете дышать и воздухом, и водой" in session_template
    assert "Стражи глубин: сопротивление холоду, устойчивость к давлению глубин" in session_template
    assert "Посланник моря: можете общаться простыми идеями с морскими зверями" in session_template
    assert "Управление воздухом и водой: Создание/уничтожение воды — доступно всегда; Порыв ветра —" in session_template
    assert "откроется на ${requiredLevel} уровне" in session_template
    assert "восстановится после долгого отдыха" in session_template
