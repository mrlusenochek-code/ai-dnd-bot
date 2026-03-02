from __future__ import annotations

from app.gm.narration import build_gm_input_text, sanitize_gm_output


def test_sanitize_replaces_empty_list():
    out = sanitize_gm_output("[]")
    assert "[]" not in out
    assert "Что делаете дальше" in out


def test_build_gm_input_contains_location_and_contract_markers():
    settings = {}
    txt = build_gm_input_text(settings, "sess_test", "иду вперед", moved=True)
    assert "ТЕКУЩАЯ ЛОКАЦИЯ" in txt
    assert "ДЕЙСТВИЕ ИГРОКА" in txt
    assert "ФОРМАТ ОТВЕТА" in txt
    assert "MOVED: true" in txt
