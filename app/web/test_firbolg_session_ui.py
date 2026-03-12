from pathlib import Path


def test_firbolg_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Магия фирболга: Обнаружение магии — ${firbolgSharedStatus}; Маскировка — ${firbolgSharedStatus}. Базовая характеристика — Мудрость" in session_template
    assert "Язык зверей и листвы: можете передавать простые идеи зверям и растениям; преимущество на проверки Харизмы, чтобы на них повлиять" in session_template
    assert "восстановится после короткого/долгого отдыха" in session_template
