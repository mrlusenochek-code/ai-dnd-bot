from pathlib import Path


def test_high_elf_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Заговор высшего эльфа:" in session_template
    assert "Это врождённое заклинание, базовая характеристика — Интеллект. Статус: доступно всегда" in session_template
