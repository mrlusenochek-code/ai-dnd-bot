from __future__ import annotations

from app.web import ws_handlers


def test_save_log_shows_advantage_and_kalashtar_dual_mind_reason() -> None:
    log = ws_handlers._format_save_log(
        character_name="Kalashtar Seer",
        save_prefix="save",
        ability="wis",
        vs_tag="",
        mode="advantage",
        roll_a=5,
        roll_b=16,
        roll=16,
        mod=2,
        extra_bonus_texts=[],
        auto_advantage_reason="Kalashtar Dual Mind",
        total=18,
        dc=15,
    )

    assert "[SAVE] Kalashtar Seer: save wis = adv d20(5, 16) -> 16 + +2 => 18" in log
    assert "[Источник преимущества: Kalashtar Dual Mind]" in log
    assert "(DC 15) SUCCESS" in log


def test_save_log_without_kalashtar_dual_mind_reason_stays_plain() -> None:
    log = ws_handlers._format_save_log(
        character_name="Commoner",
        save_prefix="save",
        ability="wis",
        vs_tag="",
        mode="normal",
        roll_a=11,
        roll_b=None,
        roll=11,
        mod=0,
        extra_bonus_texts=[],
        auto_advantage_reason="",
        total=11,
        dc=None,
    )

    assert log == "[SAVE] Commoner: save wis = d20(11) + +0 => 11"
    assert "Источник преимущества" not in log
