from pathlib import Path


def test_forest_gnome_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Природный иллюзионист: Малая иллюзия. Это врождённая магия, базовая характеристика — Интеллект. Статус: доступно всегда" in session_template
    assert "Общение с мелкими зверями: можете передавать простые идеи маленьким и ещё меньшим зверям" in session_template
