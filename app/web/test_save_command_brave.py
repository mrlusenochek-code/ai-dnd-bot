from __future__ import annotations

from app.web import ws_handlers


def test_save_log_shows_brave_reason_for_frightened_save() -> None:
    log = ws_handlers._format_save_log(
        character_name="Halfling Hero",
        save_prefix="save",
        ability="wis",
        vs_tag="frightened",
        mode="advantage",
        roll_a=5,
        roll_b=14,
        roll=14,
        mod=2,
        extra_bonus_texts=[],
        auto_advantage_reason="Brave",
        total=16,
        dc=15,
    )

    assert "[SAVE] Halfling Hero: save wis vs frightened = adv d20(5, 14) -> 14 + +2 => 16" in log
    assert "[Источник преимущества: Brave]" in log


def test_non_frightened_save_log_has_no_brave_reason() -> None:
    log = ws_handlers._format_save_log(
        character_name="Halfling Hero",
        save_prefix="save",
        ability="wis",
        vs_tag="poisoned",
        mode="normal",
        roll_a=11,
        roll_b=None,
        roll=11,
        mod=2,
        extra_bonus_texts=[],
        auto_advantage_reason="",
        total=13,
        dc=None,
    )

    assert log == "[SAVE] Halfling Hero: save wis vs poisoned = d20(11) + +2 => 13"
