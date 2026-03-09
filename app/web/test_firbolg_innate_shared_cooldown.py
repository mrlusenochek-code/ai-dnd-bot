from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def test_detect_hidden_step_phrase_as_action() -> None:
    action = _detect_chat_combat_action("использую незримую поступь")
    assert action == "combat_hidden_step"


def test_firbolg_innate_spells_share_short_long_rest_cooldown() -> None:
    ch = SimpleNamespace(
        level=3,
        race_features={
            "innate_spells": [
                {
                    "ability": "wis",
                    "level": 1,
                    "name": "detect_magic",
                    "frequency": "shared_1_per_short_or_long_rest",
                    "shared_group": "firbolg_magic",
                    "shared_recharge": "per_short_or_long_rest",
                },
                {
                    "ability": "wis",
                    "level": 1,
                    "name": "disguise_self",
                    "frequency": "shared_1_per_short_or_long_rest",
                    "shared_group": "firbolg_magic",
                    "shared_recharge": "per_short_or_long_rest",
                },
            ],
            "runtime": {},
        },
    )

    first_name, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "detect_magic")
    second_name, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "disguise_self")

    assert first_err is None
    assert first_name is not None
    assert first_changed is True
    assert second_name is None
    assert second_err is not None
    assert second_changed is False

    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    assert reset_changed is True
    runtime_after_reset = (ch.race_features or {}).get("runtime") or {}
    assert "innate_shared_uses" not in runtime_after_reset

    third_name, third_err, third_changed = ws_handlers._apply_innate_spell_usage(ch, "disguise_self")
    assert third_err is None
    assert third_name is not None
    assert third_changed is True
