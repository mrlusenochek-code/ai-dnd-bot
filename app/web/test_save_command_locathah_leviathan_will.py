from __future__ import annotations

from app.web import ws_handlers


def test_save_log_shows_leviathan_will_reason_for_matching_condition_save() -> None:
    log = ws_handlers._format_save_log(
        character_name="Locathah Hero",
        save_prefix="save",
        ability="wis",
        vs_tag="charmed",
        mode="advantage",
        roll_a=6,
        roll_b=15,
        roll=15,
        mod=2,
        extra_bonus_texts=[],
        auto_advantage_reason="Leviathan Will",
        total=17,
        dc=14,
    )

    assert "[SAVE] Locathah Hero: save wis vs charmed = adv d20(6, 15) -> 15 + +2 => 17" in log
    assert "[Источник преимущества: Leviathan Will]" in log


def test_nonmatching_save_log_has_no_leviathan_will_reason() -> None:
    log = ws_handlers._format_save_log(
        character_name="Locathah Hero",
        save_prefix="save",
        ability="wis",
        vs_tag="disease",
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

    assert log == "[SAVE] Locathah Hero: save wis vs disease = d20(11) + +2 => 13"
    assert "Leviathan Will" not in log
