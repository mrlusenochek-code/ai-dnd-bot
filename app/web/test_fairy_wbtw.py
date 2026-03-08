from types import SimpleNamespace

from app.rules.character_catalog import resolve_race
from app.web.http_routes import _build_race_features
from app.web.ws_handlers import _apply_innate_spell_usage, _detect_innate_spell_key


def test_fairy_catalog_and_build_features():
    race = resolve_race("fairy")
    assert race is not None

    rf = _build_race_features({"details": race})
    speeds = rf.get("speeds") if isinstance(rf, dict) else {}
    assert isinstance(speeds, dict)
    assert speeds.get("walk_ft") == 30
    assert speeds.get("fly_ft") == 0
    fly_restriction = speeds.get("fly_restriction")
    assert isinstance(fly_restriction, dict)
    assert fly_restriction.get("no_armor_categories") == ["medium", "heavy"]

    spells = rf.get("innate_spells") if isinstance(rf, dict) else []
    assert isinstance(spells, list)
    names = {s.get("name") for s in spells if isinstance(s, dict)}
    assert {"druidcraft", "faerie_fire", "enlarge_reduce"} <= names

    faerie = next(s for s in spells if isinstance(s, dict) and s.get("name") == "faerie_fire")
    assert faerie.get("frequency") == "1_per_long_rest"
    assert int(faerie.get("min_level") or 0) == 3


def test_fairy_innate_spell_regex_and_usage():
    assert _detect_innate_spell_key("кастую искусство друидов") == "druidcraft"
    assert _detect_innate_spell_key("накладываю увеличение/уменьшение") == "enlarge_reduce"

    ch = SimpleNamespace(
        level=1,
        race_features={
            "innate_spells": [
                {"name": "druidcraft", "frequency": "at_will", "ability": "wis"},
                {"name": "faerie_fire", "frequency": "1_per_long_rest", "min_level": 3, "ability": "wis"},
                {"name": "enlarge_reduce", "frequency": "1_per_long_rest", "min_level": 5, "ability": "wis"},
            ]
        },
    )

    name, err, changed = _apply_innate_spell_usage(ch, "druidcraft")
    assert err is None
    assert name is not None and "друид" in name.lower()
    assert changed is False

    name, err, changed = _apply_innate_spell_usage(ch, "faerie_fire")
    assert name is None
    assert err is not None and "3" in err
    assert changed is False
