from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def test_detect_hex_phrase_as_innate_spell_action() -> None:
    assert _detect_chat_combat_action("кастую сглаз") == "combat_innate_spell"
    assert _detect_chat_combat_action("cast hex") == "combat_innate_spell"


def test_hexblood_hex_magic_shared_cooldown_resets_only_on_long_rest() -> None:
    ch = SimpleNamespace(
        level=3,
        race_features={
            "innate_spells": [
                {
                    "ability": "wis",
                    "level": 1,
                    "name": "disguise_self",
                    "frequency": "shared_1_per_long_rest",
                    "shared_group": "hex_magic",
                    "shared_recharge": "per_long_rest",
                },
                {
                    "ability": "wis",
                    "level": 1,
                    "name": "hex",
                    "frequency": "shared_1_per_long_rest",
                    "shared_group": "hex_magic",
                    "shared_recharge": "per_long_rest",
                },
            ],
            "runtime": {},
        },
    )

    first_name, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "disguise_self")
    assert first_err is None
    assert first_changed is True
    assert first_name is not None
    runtime = (ch.race_features or {}).get("runtime") or {}
    shared = runtime.get("innate_shared_uses") or {}
    assert int(shared.get("hex_magic") or 0) == 1

    second_name, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "hex")
    assert second_name is None
    assert second_changed is False
    assert second_err is not None and "долгого" in second_err.lower()

    short_reset_changed = ws_handlers._reset_racial_rest_uses(ch, long_rest=False)
    assert short_reset_changed is False
    runtime_after_short = (ch.race_features or {}).get("runtime") or {}
    shared_after_short = runtime_after_short.get("innate_shared_uses") or {}
    assert int(shared_after_short.get("hex_magic") or 0) == 1

    long_reset_changed = ws_handlers._reset_racial_rest_uses(ch, long_rest=True)
    assert long_reset_changed is True
    runtime_after_long = (ch.race_features or {}).get("runtime") or {}
    assert "innate_shared_uses" not in runtime_after_long

    third_name, third_err, third_changed = ws_handlers._apply_innate_spell_usage(ch, "hex")
    assert third_err is None
    assert third_changed is True
    assert third_name is not None
