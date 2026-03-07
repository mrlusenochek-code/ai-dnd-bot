from __future__ import annotations

from app.rules.character_catalog import CLASS_CATALOG, RACE_CATALOG


STAT_KEYS = {"str", "dex", "con", "int", "wis", "cha"}
SIZE_KEYS = {"small", "medium", "large"}


def test_catalog_keys_are_unique() -> None:
    class_keys = [str(item.get("key") or "") for item in CLASS_CATALOG]
    race_keys = [str(item.get("key") or "") for item in RACE_CATALOG]
    assert all(class_keys)
    assert all(race_keys)
    assert len(class_keys) == len(set(class_keys))
    assert len(race_keys) == len(set(race_keys))


def test_race_schema_contracts() -> None:
    for race in RACE_CATALOG:
        assert str(race.get("key") or "").strip()
        assert str(race.get("name_ru") or "").strip()
        assert isinstance(race.get("speed_ft"), int)
        assert int(race.get("speed_ft") or 0) >= 0
        assert str(race.get("size") or "medium") in SIZE_KEYS
        assert isinstance(race.get("traits"), list)
        assert isinstance(race.get("subraces"), list)
        assert isinstance(race.get("languages"), list)
        assert isinstance(race.get("asi"), list)


def test_class_schema_contracts() -> None:
    for klass in CLASS_CATALOG:
        assert str(klass.get("key") or "").strip()
        assert str(klass.get("name_ru") or "").strip()
        assert isinstance(klass.get("hit_die"), int)
        assert int(klass.get("hit_die") or 0) >= 1
        assert isinstance(klass.get("primary_abilities"), list)
        assert isinstance(klass.get("saving_throws"), list)

        for stat in klass.get("primary_abilities") or []:
            assert stat in STAT_KEYS
        for stat in klass.get("saving_throws") or []:
            assert stat in STAT_KEYS

        levels = klass.get("features_by_level") or {}
        assert isinstance(levels, dict)
        for level in levels.keys():
            assert isinstance(level, int)
            assert 1 <= level <= 20


def test_artificer_exists_and_hit_die_8() -> None:
    artificer = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "artificer"), None)
    assert artificer is not None
    assert int(artificer.get("hit_die") or 0) == 8


def test_dwarf_reference_schema_payload() -> None:
    dwarf = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "dwarf"), None)
    assert dwarf is not None
    assert int(dwarf.get("speed_ft") or 0) == 25

    languages = set(dwarf.get("languages") or [])
    assert "common" in languages
    assert "dwarvish" in languages

    asi = dwarf.get("asi") or []
    assert any(item.get("stat") == "con" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))

    subraces = {str(item.get("key") or ""): item for item in (dwarf.get("subraces") or []) if isinstance(item, dict)}
    assert "hill_dwarf" in subraces
    assert "mountain_dwarf" in subraces

    hill = subraces["hill_dwarf"]
    hill_asi = hill.get("asi") or []
    assert any(item.get("stat") == "wis" and int(item.get("bonus") or 0) == 1 for item in hill_asi if isinstance(item, dict))
    hill_traits = {str(item.get("key") or ""): item for item in (hill.get("traits") or []) if isinstance(item, dict)}
    assert "dwarven_toughness" in hill_traits
    assert (hill_traits["dwarven_toughness"].get("mechanics") or {}).get("type") == "hp_scaling"

    mountain = subraces["mountain_dwarf"]
    mountain_asi = mountain.get("asi") or []
    assert any(item.get("stat") == "str" and int(item.get("bonus") or 0) == 2 for item in mountain_asi if isinstance(item, dict))


def test_barbarian_reference_schema_payload() -> None:
    barbarian = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "barbarian"), None)
    assert barbarian is not None
    assert int(barbarian.get("hit_die") or 0) == 12
    assert set(barbarian.get("saving_throws") or []) == {"str", "con"}

    levels = barbarian.get("features_by_level") or {}
    assert isinstance(levels, dict)
    for level in (1, 2, 3, 5, 20):
        assert level in levels

    lvl3 = {str(item.get("key") or ""): item for item in (levels.get(3) or []) if isinstance(item, dict)}
    assert "primal_path" in lvl3

    subclasses = {str(item.get("key") or ""): item for item in (barbarian.get("subclasses") or []) if isinstance(item, dict)}
    assert "berserker" in subclasses
    assert "totem_warrior" in subclasses


def test_elf_reference_schema_payload() -> None:
    elf = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "elf"), None)
    assert elf is not None
    assert int(elf.get("speed_ft") or 0) == 30

    languages = set(elf.get("languages") or [])
    assert "common" in languages
    assert "elvish" in languages

    asi = elf.get("asi") or []
    assert any(item.get("stat") == "dex" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))

    subraces = {str(item.get("key") or ""): item for item in (elf.get("subraces") or []) if isinstance(item, dict)}
    assert "high_elf" in subraces
    assert "wood_elf" in subraces
    assert "drow" in subraces

    wood_elf = subraces["wood_elf"]
    assert int(wood_elf.get("speed_ft") or 0) == 35

    drow = subraces["drow"]
    drow_traits = {str(item.get("key") or ""): item for item in (drow.get("traits") or []) if isinstance(item, dict)}
    assert "superior_darkvision_120" in drow_traits
    assert "sunlight_sensitivity" in drow_traits
