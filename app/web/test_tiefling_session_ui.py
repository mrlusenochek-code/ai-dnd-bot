from pathlib import Path


def test_tiefling_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Адская стойкость: сопротивление огню" in session_template
    assert "Адское наследие: Тауматургия — доступно всегда; Адская кара —" in session_template
    assert "Тьма — ${tieflingSpellStatus(\"darkness\", 5, !!runtime.tiefling_darkness_used)}. Базовая характеристика — Харизма" in session_template
    assert "откроется на ${requiredLevel} уровне" in session_template
    assert "восстановится после долгого отдыха" in session_template
