from __future__ import annotations

from app.web import ws_handlers


def test_save_log_shows_magic_resistance_reason_for_magic_save() -> None:
    log = ws_handlers._format_save_log(
        character_name="Satyr Magebane",
        save_prefix="save magic",
        ability="wis",
        vs_tag="",
        mode="advantage",
        roll_a=6,
        roll_b=17,
        roll=17,
        mod=3,
        extra_bonus_texts=[],
        auto_advantage_reason="Magic Resistance",
        total=20,
        dc=15,
    )

    assert "[SAVE] Satyr Magebane: save magic wis = adv d20(6, 17) -> 17 + +3 => 20" in log
    assert "[Источник преимущества: Magic Resistance]" in log
    assert "(DC 15) SUCCESS" in log


def test_nonmagical_save_log_has_no_magic_resistance_reason() -> None:
    log = ws_handlers._format_save_log(
        character_name="Satyr Magebane",
        save_prefix="save",
        ability="wis",
        vs_tag="",
        mode="normal",
        roll_a=11,
        roll_b=None,
        roll=11,
        mod=3,
        extra_bonus_texts=[],
        auto_advantage_reason="",
        total=14,
        dc=None,
    )

    assert log == "[SAVE] Satyr Magebane: save wis = d20(11) + +3 => 14"
    assert "Magic Resistance" not in log
