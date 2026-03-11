from pathlib import Path


def test_aasimar_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Несущий свет: Свет — доступно всегда. Базовая характеристика — Харизма" in session_template
    assert "Небесная устойчивость: сопротивление некротическому урону и урону излучением" in session_template
