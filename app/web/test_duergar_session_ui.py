from pathlib import Path


def test_duergar_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Магия дуэргара: Увеличение — ${duergarSpellStatus(\"enlarge\", 3, !!runtime.duergar_enlarge_used)}; Невидимость — ${duergarSpellStatus(\"invisibility\", 5, !!runtime.duergar_invisibility_used)}. Базовая характеристика — Интеллект" in session_template
