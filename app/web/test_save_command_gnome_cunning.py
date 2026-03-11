from __future__ import annotations

from app.web import ws_handlers


def test_save_log_shows_advantage_and_gnome_cunning_reason_for_magic_save() -> None:
    log = ws_handlers._format_save_log(
        character_name="Gnome Sage",
        save_prefix="save magic",
        ability="wis",
        vs_tag="",
        mode="advantage",
        roll_a=4,
        roll_b=16,
        roll=16,
        mod=2,
        extra_bonus_texts=[],
        auto_advantage_reason="Gnome Cunning",
        total=18,
        dc=15,
    )

    assert "[SAVE] Gnome Sage: save magic wis = adv d20(4, 16) -> 16 + +2 => 18" in log
    assert "[Источник преимущества: Gnome Cunning]" in log
    assert "(DC 15) SUCCESS" in log


def test_nonmagical_save_log_has_no_gnome_cunning_reason() -> None:
    log = ws_handlers._format_save_log(
        character_name="Gnome Sage",
        save_prefix="save",
        ability="wis",
        vs_tag="",
        mode="normal",
        roll_a=12,
        roll_b=None,
        roll=12,
        mod=2,
        extra_bonus_texts=[],
        auto_advantage_reason="",
        total=14,
        dc=None,
    )

    assert log == "[SAVE] Gnome Sage: save wis = d20(12) + +2 => 14"
    assert "Gnome Cunning" not in log
