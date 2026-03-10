from pathlib import Path


def test_rock_gnome_tinker_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Устройства механика:" in session_template
    assert "Активных устройств нет" in session_template
    assert "Гномий механик: можно поддерживать до 3 устройств одновременно; каждое устройство работает 24 часа;" in session_template
    assert "Заводная игрушка" in session_template
    assert "Зажигалка" in session_template
    assert "Музыкальная шкатулка" in session_template
