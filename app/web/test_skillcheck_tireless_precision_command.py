from __future__ import annotations

from app.web import ws_handlers


def test_skillcheck_log_includes_tireless_precision_and_dc_result() -> None:
    log = ws_handlers._format_check_log(
        character_name="Vedalken Sage",
        key="arcana",
        roll_a=13,
        roll_b=None,
        roll=13,
        mod=4,
        tp_bonus_text="1d4(3)",
        extra_bonus_texts=[],
        total=20,
        dc=15,
    )

    assert "[CHECK] Vedalken Sage: arcana = 13 + +4" in log
    assert "Tireless Precision 1d4(3)" in log
    assert "(DC 15) SUCCESS" in log


def test_statcheck_log_does_not_show_tireless_precision_bonus() -> None:
    log = ws_handlers._format_check_log(
        character_name="Vedalken Sage",
        key="int",
        roll_a=11,
        roll_b=17,
        roll=17,
        mod=3,
        tp_bonus_text="",
        extra_bonus_texts=[],
        total=20,
        dc=None,
    )

    assert "[CHECK] Vedalken Sage: int = 11/17->17 + +3 => 20" == log
    assert "Tireless Precision" not in log
