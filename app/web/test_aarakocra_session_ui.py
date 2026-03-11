from pathlib import Path


def test_aarakocra_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Полёт: скорость полёта ${Number(speeds.fly_ft)} фт; средние и тяжёлые доспехи мешают полёту${flyBlockedByArmor ? \". Полёт недоступен в текущих доспехах.\" : \"\"}" in session_template
    assert "Полёт недоступен в текущих доспехах." in session_template
