from pathlib import Path


def test_kenku_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Подражание: вы имитируете звуки/голоса; распознаётся проверкой Мудрость (Проницательность)" in template
    assert "Искусный подлог: вы умеете копировать почерк/рисунки" in template
