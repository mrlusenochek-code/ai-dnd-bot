from pathlib import Path


def test_gith_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Псионика гитъянки: Волшебная рука — доступно всегда (невидима); Прыжок — ${githSpellStatus(\"jump\", 3, !!runtime.githyanki_jump_used)}; Туманный шаг — ${githSpellStatus(\"misty_step\", 5, !!runtime.githyanki_misty_step_used)}. Базовая характеристика — Интеллект" in session_template
    assert "Псионика гитцераев: Волшебная рука — доступно всегда (невидима); Щит — ${githSpellStatus(\"shield\", 3, !!runtime.githzerai_shield_used)}; Обнаружение мыслей — ${githSpellStatus(\"detect_thoughts\", 5, !!runtime.githzerai_detect_thoughts_used)}. Базовая характеристика — Мудрость" in session_template
