from __future__ import annotations

from app.web import ws_handlers


def test_save_log_shows_advantage_and_vedalken_dispassion_reason() -> None:
    log = ws_handlers._format_save_log(
        character_name="Vedalken Sage",
        save_prefix="save",
        ability="wis",
        vs_tag="",
        mode="advantage",
        roll_a=6,
        roll_b=17,
        roll=17,
        mod=3,
        extra_bonus_texts=[],
        auto_advantage_reason="Vedalken Dispassion",
        total=20,
        dc=15,
    )

    assert "[SAVE] Vedalken Sage: save wis = adv d20(6, 17) -> 17 + +3 => 20" in log
    assert "[Источник преимущества: Vedalken Dispassion]" in log
    assert "(DC 15) SUCCESS" in log


def test_save_log_without_auto_advantage_reason_stays_plain() -> None:
    log = ws_handlers._format_save_log(
        character_name="Commoner",
        save_prefix="save",
        ability="str",
        vs_tag="",
        mode="normal",
        roll_a=11,
        roll_b=None,
        roll=11,
        mod=1,
        extra_bonus_texts=[],
        auto_advantage_reason="",
        total=12,
        dc=None,
    )

    assert log == "[SAVE] Commoner: save str = d20(11) + +1 => 12"
    assert "Источник преимущества" not in log
