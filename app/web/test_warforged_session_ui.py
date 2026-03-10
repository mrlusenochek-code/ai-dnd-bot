from pathlib import Path


def test_warforged_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Специальная сборка: навык" in session_template
    assert "Встроенная защита: +" in session_template
    assert "Стойкость кованых: преимущество к спасброскам от отравления; сопротивление урону ядом; иммунитет к болезням; не нужно есть, пить, дышать и спать; нельзя магически усыпить" in session_template
    assert "Отдых стража: во время длительного отдыха" in session_template
