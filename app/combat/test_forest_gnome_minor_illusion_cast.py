from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def test_forest_gnome_minor_illusion_uses_common_innate_pipeline_without_rest_limit() -> None:
    ch = SimpleNamespace(
        level=1,
        race_features={
            "race_key": "gnome",
            "subrace": {"key": "forest_gnome"},
            "innate_spells": [
                {
                    "name": "minor_illusion",
                    "frequency": "at_will",
                    "min_level": 1,
                    "ability": "int",
                    "source": "forest_gnome_cantrip",
                }
            ],
            "features": {
                "innate_spellcasting": {
                    "type": "innate_spellcasting",
                    "ability": "int",
                    "spells": [{"name": "minor_illusion", "frequency": "at_will", "min_level": 1}],
                },
                "forest_gnome_cantrip": {
                    "type": "innate_spellcasting",
                    "ability": "int",
                    "spell": {"name": "minor_illusion", "frequency": "at_will", "min_level": 1, "ability": "int"},
                },
            },
            "runtime": {},
        },
    )

    assert ws_handlers._detect_innate_spell_key("кастую малую иллюзию") == "minor_illusion"

    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "minor_illusion")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "minor_illusion")

    assert err_1 is None and err_2 is None
    assert display_name_1 == "Малая иллюзия"
    assert display_name_2 == "Малая иллюзия"
    assert changed_1 is False
    assert changed_2 is False
    assert "innate_spell_uses" not in ((ch.race_features or {}).get("runtime") or {})
