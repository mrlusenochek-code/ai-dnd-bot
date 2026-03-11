from pathlib import Path


def test_fairy_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Магия фей: Искусство друидов — доступно всегда; Огонь фей — ${fairySpellStatus(\"faerie_fire\", 3)}; Увеличение/уменьшение — ${fairySpellStatus(\"enlarge_reduce\", 5)}. Базовая характеристика — ${fairyAbilityRu || \"—\"}" in session_template
    assert "Полёт: скорость полёта ${Number(speeds.fly_ft)} фт${flySpeedEqualsWalk ? \" (равна ходьбе)\" : \"\"}; средние и тяжёлые доспехи мешают полёту${flyBlockedByArmor ? \". Полёт недоступен в текущих доспехах.\" : \"\"}" in session_template
    assert "Полёт недоступен в текущих доспехах." in session_template
    assert "\"faerie_fire\": \"Огонь фей\"" in session_template
