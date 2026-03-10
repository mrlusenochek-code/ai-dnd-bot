from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def test_high_elf_cantrip_cast_uses_common_innate_pipeline_without_rest_limit() -> None:
    ch = SimpleNamespace(
        level=1,
        race_features={
            "race_key": "elf",
            "subrace": {"key": "high_elf"},
            "innate_spells": [
                {
                    "name": "fire_bolt",
                    "frequency": "at_will",
                    "min_level": 1,
                    "ability": "int",
                    "source": "high_elf_cantrip",
                }
            ],
            "features": {
                "high_elf_cantrip": {
                    "type": "innate_spellcasting",
                    "ability": "int",
                    "spell": {"name": "fire_bolt", "frequency": "at_will", "min_level": 1, "ability": "int"},
                }
            },
            "runtime": {},
        },
    )

    assert ws_handlers._detect_innate_spell_key("кастую огненный снаряд") == "fire_bolt"

    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "fire_bolt")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "fire_bolt")

    assert err_1 is None and err_2 is None
    assert display_name_1 == "Огненный снаряд"
    assert display_name_2 == "Огненный снаряд"
    assert changed_1 is False
    assert changed_2 is False
    assert "innate_spell_uses" not in ((ch.race_features or {}).get("runtime") or {})
