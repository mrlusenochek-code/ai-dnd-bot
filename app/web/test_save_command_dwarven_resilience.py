from __future__ import annotations

from app.web import ws_handlers


def test_save_log_shows_dwarven_resilience_reason_for_poison_save() -> None:
    log = ws_handlers._format_save_log(
        character_name="Dwarf Hero",
        save_prefix="save",
        ability="con",
        vs_tag="poison",
        mode="advantage",
        roll_a=4,
        roll_b=15,
        roll=15,
        mod=3,
        extra_bonus_texts=[],
        auto_advantage_reason="Dwarven Resilience",
        total=18,
        dc=14,
    )

    assert "[SAVE] Dwarf Hero: save con vs poison = adv d20(4, 15) -> 15 + +3 => 18" in log
    assert "[Источник преимущества: Dwarven Resilience]" in log


def test_non_poison_save_log_has_no_dwarven_resilience_reason() -> None:
    log = ws_handlers._format_save_log(
        character_name="Dwarf Hero",
        save_prefix="save",
        ability="con",
        vs_tag="frightened",
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

    assert log == "[SAVE] Dwarf Hero: save con vs frightened = d20(11) + +3 => 14"
