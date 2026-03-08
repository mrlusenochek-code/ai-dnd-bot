from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def test_detect_long_rest_phrase_as_action() -> None:
    action = _detect_chat_combat_action("отдыхаю до утра")
    assert action == "rest_long"


def test_long_rest_reset_reenables_innate_spell_with_long_rest_limit() -> None:
    ch = SimpleNamespace(
        level=3,
        race_features={
            "innate_spells": [
                {"ability": "con", "level": 1, "name": "burning_hands", "frequency": "1_per_long_rest", "min_level": 3}
            ],
            "runtime": {"relentless_endurance_used": True},
        },
    )

    first_display, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")
    second_display, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")

    assert first_err is None
    assert first_display == "burning_hands"
    assert first_changed is True
    assert second_display is None
    assert second_err is not None
    assert second_changed is False

    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    assert reset_changed is True
    runtime_after_reset = (ch.race_features or {}).get("runtime") or {}
    assert "innate_spell_uses" not in runtime_after_reset
    assert "relentless_endurance_used" not in runtime_after_reset

    third_display, third_err, third_changed = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")
    assert third_err is None
    assert third_display == "burning_hands"
    assert third_changed is True
