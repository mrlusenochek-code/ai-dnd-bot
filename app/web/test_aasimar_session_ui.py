from pathlib import Path


def test_aasimar_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Исцеляющие руки: статус" in session_template
    assert "Несущий свет: Свет — доступно всегда. Базовая характеристика — Харизма" in session_template
    assert "Небесная устойчивость: сопротивление некротическому урону и урону излучением" in session_template
    assert "Небесное преобразование:" in session_template
    assert "статус: " in session_template
    assert "эффект: " in session_template
    assert "потрачено, восстановится после долгого отдыха" in session_template
