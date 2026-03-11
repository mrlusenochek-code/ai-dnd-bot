from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _hexblood_race_features() -> dict[str, object]:
    return {
        "race_key": "hexblood",
        "innate_spells": [
            {
                "ability": "wis",
                "level": 1,
                "name": "disguise_self",
                "frequency": "shared_1_per_long_rest",
                "min_level": 1,
                "shared_group": "hex_magic",
                "shared_recharge": "per_long_rest",
            },
            {
                "ability": "wis",
                "level": 1,
                "name": "hex",
                "frequency": "shared_1_per_long_rest",
                "min_level": 1,
                "shared_group": "hex_magic",
                "shared_recharge": "per_long_rest",
            },
        ],
        "features": {
            "hex_magic": {
                "ability": "wis",
                "spells": ["disguise_self", "hex"],
                "shared_group": "hex_magic",
                "shared_recharge": "per_long_rest",
                "allow_spell_slots": True,
            },
            "innate_spellcasting": {
                "type": "innate_spellcasting",
                "ability": "wis",
                "spells": [
                    {"name": "disguise_self", "frequency": "shared_1_per_long_rest", "min_level": 1},
                    {"name": "hex", "frequency": "shared_1_per_long_rest", "min_level": 1},
                ],
            },
        },
        "runtime": {},
    }


def test_hexblood_hex_magic_uses_common_innate_pipeline_and_long_rest_reset() -> None:
    ch = SimpleNamespace(level=3, race_features=_hexblood_race_features())

    assert ws_handlers._detect_innate_spell_key("кастую маскировку") == "disguise_self"
    assert ws_handlers._detect_innate_spell_key("кастую сглаз") == "hex"

    first_name, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "disguise_self")
    second_name, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "hex")

    assert first_name == "Маскировка"
    assert first_err is None
    assert first_changed is True
    assert second_name is None
    assert second_changed is False
    assert second_err is not None and "долгого отдыха" in second_err

    short_reset_changed = ws_handlers._reset_racial_rest_uses(ch, long_rest=False)
    runtime_after_short = ((ch.race_features or {}).get("runtime") or {})
    assert short_reset_changed is False
    assert int(((runtime_after_short.get("innate_shared_uses") or {}).get("hex_magic") or 0)) == 1

    long_reset_changed = ws_handlers._reset_racial_rest_uses(ch, long_rest=True)
    runtime_after_long = ((ch.race_features or {}).get("runtime") or {})
    third_name, third_err, third_changed = ws_handlers._apply_innate_spell_usage(ch, "hex")

    assert long_reset_changed is True
    assert "innate_shared_uses" not in runtime_after_long
    assert third_name == "Сглаз"
    assert third_err is None
    assert third_changed is True
