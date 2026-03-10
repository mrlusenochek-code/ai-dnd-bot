from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _firbolg_race_features() -> dict[str, object]:
    return {
        "race_key": "firbolg",
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
        "features": {
            "innate_spellcasting": {
                "type": "innate_spellcasting",
                "ability": "wis",
                "spells": [
                    {"name": "detect_magic", "frequency": "shared_1_per_short_or_long_rest", "min_level": 1},
                    {"name": "disguise_self", "frequency": "shared_1_per_short_or_long_rest", "min_level": 1},
                ],
            },
            "firbolg_magic": {
                "ability": "wis",
                "spells": ["detect_magic", "disguise_self"],
                "shared_group": "firbolg_magic",
                "shared_recharge": "per_short_or_long_rest",
                "special": {"disguise_self_height_delta_ft": -3},
                "allow_spell_slots": False,
            },
        },
        "runtime": {
            "firbolg_detect_magic_used": False,
            "firbolg_disguise_self_used": False,
        },
    }


def test_firbolg_detect_magic_and_disguise_self_use_common_shared_pipeline() -> None:
    ch = SimpleNamespace(level=1, race_features=_firbolg_race_features())

    assert ws_handlers._detect_innate_spell_key("кастую обнаружение магии") == "detect_magic"
    assert ws_handlers._detect_innate_spell_key("кастую маскировку") == "disguise_self"

    first_name, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "detect_magic")
    second_name, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "disguise_self")

    runtime = ((ch.race_features or {}).get("runtime") or {})
    shared_uses = runtime.get("innate_shared_uses") or {}
    assert first_name == "Обнаружение магии"
    assert first_err is None
    assert first_changed is True
    assert second_name is None
    assert second_err is not None and "короткого/долгого отдыха" in second_err
    assert second_changed is False
    assert int(shared_uses.get("firbolg_magic") or 0) == 1


def test_firbolg_shared_cooldown_resets_on_rest_helper() -> None:
    ch = SimpleNamespace(level=1, race_features=_firbolg_race_features())

    first_name, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "disguise_self")
    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    runtime_after_reset = ((ch.race_features or {}).get("runtime") or {})
    second_name, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "detect_magic")

    assert first_name == "Маскировка"
    assert first_err is None
    assert first_changed is True
    assert reset_changed is True
    assert "innate_shared_uses" not in runtime_after_reset
    assert second_name == "Обнаружение магии"
    assert second_err is None
    assert second_changed is True
