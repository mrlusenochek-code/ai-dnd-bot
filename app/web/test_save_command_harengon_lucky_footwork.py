from __future__ import annotations

from app.web import ws_handlers


def test_parse_save_command_supports_footwork_variants() -> None:
    assert ws_handlers._parse_save_command("save footwork dex dc 15") == (
        False,
        "roll",
        True,
        "dex",
        "",
        15,
        None,
    )
    assert ws_handlers._parse_save_command("save adv footwork dex dc 15") == (
        False,
        "adv",
        True,
        "dex",
        "",
        15,
        None,
    )
    assert ws_handlers._parse_save_command("save magic dis footwork dex vs poison dc 14") == (
        True,
        "dis",
        True,
        "dex",
        "poison",
        14,
        None,
    )


def test_save_log_shows_lucky_footwork_when_needed() -> None:
    log = ws_handlers._format_save_log(
        character_name="Harengon Scout",
        save_prefix="save",
        ability="dex",
        vs_tag="",
        mode="normal",
        roll_a=9,
        roll_b=None,
        roll=9,
        mod=3,
        extra_bonus_texts=[],
        auto_advantage_reason="",
        total=12,
        dc=15,
        footwork_bonus_text="1d4(4)",
        footwork_new_total=16,
    )

    assert "[SAVE] Harengon Scout: save dex = d20(9) + +3 => 12" in log
    assert "Lucky Footwork: +1d4(4)" in log
    assert "Новый итог: 16 (DC 15) SUCCESS" in log


def test_save_log_shows_when_lucky_footwork_was_not_needed() -> None:
    log = ws_handlers._format_save_log(
        character_name="Harengon Scout",
        save_prefix="save",
        ability="dex",
        vs_tag="",
        mode="advantage",
        roll_a=5,
        roll_b=16,
        roll=16,
        mod=2,
        extra_bonus_texts=[],
        auto_advantage_reason="",
        total=18,
        dc=15,
        footwork_note="Lucky Footwork не понадобилась.",
    )

    assert "[SAVE] Harengon Scout: save dex = adv d20(5, 16) -> 16 + +2 => 18" in log
    assert "Lucky Footwork не понадобилась." in log
