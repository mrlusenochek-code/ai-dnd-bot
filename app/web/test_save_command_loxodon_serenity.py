from __future__ import annotations

from app.web import ws_handlers


def test_save_log_shows_loxodon_serenity_reason_for_charmed_save() -> None:
    log = ws_handlers._format_save_log(
        character_name="Loxodon Hero",
        save_prefix="save",
        ability="wis",
        vs_tag="charmed",
        mode="advantage",
        roll_a=6,
        roll_b=15,
        roll=15,
        mod=2,
        extra_bonus_texts=[],
        auto_advantage_reason="Loxodon Serenity",
        total=17,
        dc=14,
    )

    assert "[SAVE] Loxodon Hero: save wis vs charmed = adv d20(6, 15) -> 15 + +2 => 17" in log
    assert "[Источник преимущества: Loxodon Serenity]" in log
    assert "(DC 14) SUCCESS" in log


def test_save_log_shows_loxodon_serenity_reason_for_frightened_save_only() -> None:
    log = ws_handlers._format_save_log(
        character_name="Loxodon Hero",
        save_prefix="save",
        ability="wis",
        vs_tag="frightened",
        mode="advantage",
        roll_a=4,
        roll_b=16,
        roll=16,
        mod=2,
        extra_bonus_texts=[],
        auto_advantage_reason="Loxodon Serenity",
        total=18,
        dc=15,
    )

    assert "[SAVE] Loxodon Hero: save wis vs frightened = adv d20(4, 16) -> 16 + +2 => 18" in log
    assert "[Источник преимущества: Loxodon Serenity]" in log


def test_nonmatching_save_log_has_no_loxodon_serenity_reason() -> None:
    log = ws_handlers._format_save_log(
        character_name="Loxodon Hero",
        save_prefix="save",
        ability="wis",
        vs_tag="poison",
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

    assert log == "[SAVE] Loxodon Hero: save wis vs poison = d20(11) + +2 => 13"
    assert "Loxodon Serenity" not in log
