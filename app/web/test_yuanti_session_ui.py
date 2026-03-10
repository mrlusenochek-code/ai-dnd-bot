from pathlib import Path


def test_yuanti_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Иммунитет к яду: иммунитет к урону ядом и состоянию «отравленный»" in session_template
    assert "Сопротивление магии: преимущество на спасброски от заклинаний и других магических эффектов" in session_template
    assert "Врождённая магия: Ядовитые брызги — доступно всегда; Дружба с животными (только змеи) — доступно всегда; Внушение —" in session_template
    assert "откроется на 3 уровне" in session_template
    assert "восстановится после долгого отдыха" in session_template
