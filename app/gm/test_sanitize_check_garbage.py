from app.gm.sanitize import sanitize_gm_output


def test_sanitize_drops_check_garbage_lines() -> None:
    raw = (
        "ПРОВЕРКА_НАВЫКОВ\n"
        "@.-check_template_d20_dc\n"
        "Ты осторожно касаешься замка и слушаешь щелчки механизма.\n"
        "Что делаете дальше?"
    )
    out = sanitize_gm_output(raw)
    assert "ПРОВЕРКА_НАВЫКОВ" not in out
    assert "@.-check_template_d20_dc" not in out
    assert "Ты осторожно касаешься замка" in out
    assert out.endswith("Что делаете дальше?")


def test_sanitize_keeps_regular_bullet_line() -> None:
    raw = (
        "- Ты держишься в тени колонны.\n"
        "Пыль медленно оседает на каменный пол.\n"
        "Что делаете дальше?"
    )
    out = sanitize_gm_output(raw)
    assert "Ты держишься в тени колонны." in out
