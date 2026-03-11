from __future__ import annotations

from app.web import ws_handlers


def test_parse_check_command_supports_pastlife_variants() -> None:
    assert ws_handlers._parse_check_command("skillcheck pastlife perception dc 15") == (
        "skillcheck",
        "roll",
        True,
        "perception",
        15,
        "",
        None,
    )
    assert ws_handlers._parse_check_command("statcheck adv pastlife wis dc 12") == (
        "statcheck",
        "adv",
        True,
        "wis",
        12,
        "",
        None,
    )
    assert ws_handlers._parse_check_command("check dis pastlife history") == (
        "check",
        "dis",
        True,
        "history",
        None,
        "",
        None,
    )


def test_parse_check_command_reports_clear_errors() -> None:
    _cmd, _mode, _pastlife, _key, _dc, _tag, err_usage = ws_handlers._parse_check_command("skillcheck")
    assert err_usage is not None and "Использование" in err_usage

    _cmd, _mode, _pastlife, _key, _dc, _tag, err_dc = ws_handlers._parse_check_command("statcheck pastlife wis dc")
    assert err_dc is not None and "dc" in err_dc.lower()

    _cmd, _mode, _pastlife, _key, _dc, _tag, err_bad_dc = ws_handlers._parse_check_command("check pastlife arcana dc -1")
    assert err_bad_dc == "DC должен быть не меньше 0"


def test_check_log_shows_reborn_past_life_bonus_and_remaining_uses() -> None:
    log = ws_handlers._format_check_log(
        character_name="Reborn Scholar",
        key="perception",
        roll_a=12,
        roll_b=None,
        roll=12,
        mod=3,
        tp_bonus_text="",
        extra_bonus_texts=["Knowledge from a Past Life 1d6(4)"],
        past_life_uses_text="Осталось использований: 1/2",
        total=19,
        dc=15,
    )

    assert "Knowledge from a Past Life 1d6(4)" in log
    assert "Осталось использований: 1/2" in log
    assert "(DC 15) SUCCESS" in log


def test_toolcheck_log_shows_reborn_past_life_bonus_and_remaining_uses() -> None:
    log = ws_handlers._format_toolcheck_log(
        tool_name_ru="Воровские инструменты",
        mode="normal",
        roll_a=13,
        roll_b=None,
        roll=13,
        mod=0,
        tp_bonus=0,
        tp_bonus_text="",
        extra_bonus_texts=["Knowledge from a Past Life: +1d6(5)"],
        past_life_uses_text="Осталось использований: 0/2",
        total=18,
        dc=15,
    )

    assert "Knowledge from a Past Life: +1d6(5)" in log
    assert "Осталось использований: 0/2" in log
    assert "DC 15 -> успех" in log
