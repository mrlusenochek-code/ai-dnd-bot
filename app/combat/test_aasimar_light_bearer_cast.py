from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def test_aasimar_light_bearer_cast_uses_common_innate_pipeline_without_rest_limit() -> None:
    ch = SimpleNamespace(
        level=1,
        race_features={
            "race_key": "aasimar",
            "subrace": {"key": "aasimar_protector"},
            "innate_spells": [
                {
                    "name": "light",
                    "frequency": "at_will",
                    "min_level": 1,
                    "ability": "cha",
                    "source": "light_bearer",
                }
            ],
            "features": {
                "innate_spellcasting": {
                    "type": "innate_spellcasting",
                    "ability": "cha",
                    "spells": [
                        {"name": "light", "frequency": "at_will", "min_level": 1},
                    ],
                },
                "light_bearer": {
                    "type": "innate_spellcasting",
                    "ability": "cha",
                    "spell": {"name": "light", "frequency": "at_will", "min_level": 1, "ability": "cha"},
                },
            },
            "runtime": {},
        },
    )

    assert ws_handlers._detect_innate_spell_key("кастую свет") == "light"

    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "light")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "light")

    assert err_1 is None and err_2 is None
    assert display_name_1 == "Свет"
    assert display_name_2 == "Свет"
    assert changed_1 is False
    assert changed_2 is False
    assert "innate_spell_uses" not in ((ch.race_features or {}).get("runtime") or {})

