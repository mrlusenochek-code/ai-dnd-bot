from pathlib import Path


def test_hexblood_ui_texts_present_in_session_template() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Ведьмовская магия: Маскировка — ${hexbloodSpellStatus()}; Сглаз — ${hexbloodSpellStatus()}. Базовая характеристика — ${hexbloodAbilityRu || \"—\"}" in template
    assert "можно кастовать ячейками, если есть" in template
