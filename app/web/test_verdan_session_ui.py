from pathlib import Path


def test_verdan_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Ограниченная телепатия:" in template
    assert "простые идеи" in template
    assert "цель должна знать язык" in template
    assert "Чёрная исцеляющая кровь" in template
    assert "Скачок роста" in template
