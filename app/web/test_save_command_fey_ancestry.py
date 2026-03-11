from __future__ import annotations

from app.web import ws_handlers


def test_save_log_shows_fey_ancestry_reason_for_charmed_save() -> None:
    log = ws_handlers._format_save_log(
        character_name="Elf Hero",
        save_prefix="save",
        ability="wis",
        vs_tag="charmed",
        mode="advantage",
        roll_a=7,
        roll_b=15,
        roll=15,
        mod=2,
        extra_bonus_texts=[],
        auto_advantage_reason="Fey Ancestry",
        total=17,
        dc=14,
    )

    assert "[SAVE] Elf Hero: save wis vs charmed = adv d20(7, 15) -> 15 + +2 => 17" in log
    assert "[Источник преимущества: Fey Ancestry]" in log
    assert "(DC 14) SUCCESS" in log


def test_non_charmed_save_log_has_no_fey_ancestry_reason() -> None:
    log = ws_handlers._format_save_log(
        character_name="Elf Hero",
        save_prefix="save",
        ability="wis",
        vs_tag="frightened",
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

    assert log == "[SAVE] Elf Hero: save wis vs frightened = d20(11) + +2 => 13"
    assert "Fey Ancestry" not in log
