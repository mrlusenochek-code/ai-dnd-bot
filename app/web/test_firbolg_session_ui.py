from pathlib import Path


def test_firbolg_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Магия фирболга: Обнаружение магии — ${firbolgSharedStatus}; Маскировка — ${firbolgSharedStatus}. Базовая характеристика — Мудрость" in session_template
    assert "Общение с мелкими зверями: можете передавать простые идеи маленьким и ещё меньшим зверям" in session_template
    assert "восстановится после короткого/долгого отдыха" in session_template
