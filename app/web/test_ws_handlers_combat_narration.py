from __future__ import annotations

from app.web import ws_handlers


def test_resolved_live_combat_action_skips_gm_narration() -> None:
    assert ws_handlers._should_skip_gm_narration_for_resolved_combat_action(
        "combat_attack",
        {"status": "ok", "open": True, "lines": [{"text": "Атака: Hero → Goblin"}]},
    ) is True


def test_unrecognized_text_in_combat_does_not_force_skip() -> None:
    assert ws_handlers._should_skip_gm_narration_for_resolved_combat_action(
        "",
        {"status": "ok", "open": True, "lines": [{"text": "Что-то произошло"}]},
    ) is False
    assert ws_handlers._should_skip_gm_narration_for_resolved_combat_action(
        None,
        {"status": "ok", "open": True, "lines": [{"text": "Что-то произошло"}]},
    ) is False


def test_out_of_combat_or_missing_patch_does_not_force_skip() -> None:
    assert ws_handlers._should_skip_gm_narration_for_resolved_combat_action("combat_attack", None) is False
    assert ws_handlers._should_skip_gm_narration_for_resolved_combat_action(None, None) is False
