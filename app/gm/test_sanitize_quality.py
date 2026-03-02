from __future__ import annotations

from app.gm.sanitize import sanitize_gm_output


def test_regression_removes_empty_brackets_before_dialogue() -> None:
    raw = (
        "[]\n"
        "Старик поправляет плащ и кивает тебе.\n"
        "«У ворот шумно, но путь открыт», — бормочет он.\n"
        "Что делаете дальше?"
    )
    out = sanitize_gm_output(raw)
    assert "[]" not in out
    assert "Что делаете дальше?" in out
    assert "Старик поправляет плащ" in out


def test_regression_drops_meta_block_and_keeps_scene_text() -> None:
    raw = (
        "Мы продолжаем действие в этой сцене.\n"
        "[]\n"
        "...\n"
        "Тусклый свет факела дрожит на сыром камне, в глубине коридора скрипит дверь.\n"
        "Что делаете дальше?"
    )
    out = sanitize_gm_output(raw)
    assert "Мы продолжаем действие" not in out
    assert "[]" not in out
    assert "Тусклый свет факела дрожит" in out
    assert "Что делаете дальше?" in out
