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


def test_human_reference_schema_payload() -> None:
    human = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "human"), None)
    assert human is not None
    assert str(human.get("size") or "") == "medium"
    assert int(human.get("speed_ft") or 0) == 30

    asi = human.get("asi") or []
    expected_stats = {"str", "dex", "con", "int", "wis", "cha"}
    asi_plus_one_stats = {
        str(item.get("stat") or "")
        for item in asi
        if isinstance(item, dict) and int(item.get("bonus") or 0) == 1
    }
    assert expected_stats.issubset(asi_plus_one_stats)

    traits = {str(item.get("key") or ""): item for item in (human.get("traits") or []) if isinstance(item, dict)}
    assert "extra_language" in traits

    subraces = {str(item.get("key") or ""): item for item in (human.get("subraces") or []) if isinstance(item, dict)}
    assert "variant_human" in subraces

    variant_human = subraces["variant_human"]
    variant_traits = {
        str(item.get("key") or ""): item
        for item in (variant_human.get("traits") or [])
        if isinstance(item, dict)
    }
    assert "variant_asi" in variant_traits
    assert "variant_skill" in variant_traits
    assert "variant_feat" in variant_traits
    assert "extra_language" in variant_traits


def test_aarakocra_reference_schema_payload() -> None:
    aarakocra = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "aarakocra"), None)
    assert aarakocra is not None
    assert str(aarakocra.get("size") or "") == "medium"
    assert int(aarakocra.get("speed_ft") or 0) == 25

    asi = aarakocra.get("asi") or []
    assert any(item.get("stat") == "dex" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))
    assert any(item.get("stat") == "wis" and int(item.get("bonus") or 0) == 1 for item in asi if isinstance(item, dict))

    languages = set(aarakocra.get("languages") or [])
    assert "common" in languages
    assert "auran" in languages
    assert "aarakocra" in languages

    traits = {str(item.get("key") or ""): item for item in (aarakocra.get("traits") or []) if isinstance(item, dict)}
    assert "flight_aarakocra" in traits
    assert "claws" in traits

    flight = traits["flight_aarakocra"]
    flight_mechanics = flight.get("mechanics") or {}
    assert int(flight_mechanics.get("speed_ft") or 0) == 50
    restrictions = (flight_mechanics.get("restriction") or {}).get("no_armor_categories") or []
    assert "medium" in restrictions
    assert "heavy" in restrictions


def test_genasi_reference_schema_payload() -> None:
    genasi = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "genasi"), None)
    assert genasi is not None
    assert str(genasi.get("size") or "") == "medium"
    assert int(genasi.get("speed_ft") or 0) == 30

    asi = genasi.get("asi") or []
    assert any(item.get("stat") == "con" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))

    languages = set(genasi.get("languages") or [])
    assert "common" in languages
    assert "primordial" in languages

    subraces = {str(item.get("key") or ""): item for item in (genasi.get("subraces") or []) if isinstance(item, dict)}
    assert "air_genasi" in subraces
    assert "earth_genasi" in subraces
    assert "fire_genasi" in subraces
    assert "water_genasi" in subraces

    air_genasi = subraces["air_genasi"]
    air_asi = air_genasi.get("asi") or []
    assert any(item.get("stat") == "dex" and int(item.get("bonus") or 0) == 1 for item in air_asi if isinstance(item, dict))
    air_traits = {str(item.get("key") or ""): item for item in (air_genasi.get("traits") or []) if isinstance(item, dict)}
    assert "unending_breath" in air_traits
    assert "mingle_with_the_wind" in air_traits

    earth_genasi = subraces["earth_genasi"]
    earth_asi = earth_genasi.get("asi") or []
    assert any(item.get("stat") == "str" and int(item.get("bonus") or 0) == 1 for item in earth_asi if isinstance(item, dict))
    earth_traits = {str(item.get("key") or ""): item for item in (earth_genasi.get("traits") or []) if isinstance(item, dict)}
    assert "earth_walk" in earth_traits
    assert "merge_with_stone" in earth_traits

    fire_genasi = subraces["fire_genasi"]
    fire_asi = fire_genasi.get("asi") or []
    assert any(item.get("stat") == "int" and int(item.get("bonus") or 0) == 1 for item in fire_asi if isinstance(item, dict))
    fire_traits = {str(item.get("key") or ""): item for item in (fire_genasi.get("traits") or []) if isinstance(item, dict)}
    assert "darkvision_60_red" in fire_traits
    assert "fire_resistance" in fire_traits
    assert "reach_to_the_blaze" in fire_traits

    water_genasi = subraces["water_genasi"]
    water_asi = water_genasi.get("asi") or []
    assert any(item.get("stat") == "wis" and int(item.get("bonus") or 0) == 1 for item in water_asi if isinstance(item, dict))
    water_traits = {str(item.get("key") or ""): item for item in (water_genasi.get("traits") or []) if isinstance(item, dict)}
    assert "acid_resistance" in water_traits
    assert "amphibious" in water_traits
    assert "swim_speed" in water_traits
    assert "call_to_the_wave" in water_traits


def test_goliath_reference_schema_payload() -> None:
    goliath = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "goliath"), None)
    assert goliath is not None
    assert str(goliath.get("size") or "") == "medium"
    assert int(goliath.get("speed_ft") or 0) == 30

    asi = goliath.get("asi") or []
    assert any(item.get("stat") == "str" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))
    assert any(item.get("stat") == "con" and int(item.get("bonus") or 0) == 1 for item in asi if isinstance(item, dict))

    languages = set(goliath.get("languages") or [])
    assert "common" in languages
    assert "giant" in languages

    traits = {str(item.get("key") or ""): item for item in (goliath.get("traits") or []) if isinstance(item, dict)}
    assert "stone_endurance" in traits
    assert "powerful_build" in traits
    assert "mountain_born" in traits
    assert "athletics_proficiency" in traits


def test_aasimar_reference_schema_payload() -> None:
    aasimar = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "aasimar"), None)
    assert aasimar is not None
    assert str(aasimar.get("size") or "") == "medium"
    assert int(aasimar.get("speed_ft") or 0) == 30

    traits = {str(item.get("key") or ""): item for item in (aasimar.get("traits") or []) if isinstance(item, dict)}
    assert "darkvision_60" in traits
    assert "celestial_resistance" in traits
    assert "healing_hands" in traits
    assert "light_cantrip" in traits

    subraces = {str(item.get("key") or ""): item for item in (aasimar.get("subraces") or []) if isinstance(item, dict)}
    assert "aasimar_protector" in subraces
    assert "aasimar_scourge" in subraces
    assert "aasimar_fallen" in subraces

    protector = subraces["aasimar_protector"]
    protector_asi = protector.get("asi") or []
    assert any(item.get("stat") == "wis" and int(item.get("bonus") or 0) == 1 for item in protector_asi if isinstance(item, dict))
    protector_traits = {str(item.get("key") or ""): item for item in (protector.get("traits") or []) if isinstance(item, dict)}
    protector_mech = (protector_traits["radiant_soul"].get("mechanics") or {})
    assert int(protector_mech.get("fly_speed_ft") or 0) == 30

    scourge = subraces["aasimar_scourge"]
    scourge_asi = scourge.get("asi") or []
    assert any(item.get("stat") == "con" and int(item.get("bonus") or 0) == 1 for item in scourge_asi if isinstance(item, dict))
    scourge_traits = {str(item.get("key") or ""): item for item in (scourge.get("traits") or []) if isinstance(item, dict)}
    scourge_mech = (scourge_traits["radiant_consumption"].get("mechanics") or {})
    aura = scourge_mech.get("end_of_turn_aura_damage") or {}
    light = scourge_mech.get("light_emission") or {}
    assert int(aura.get("radius_ft") or 0) == 10
    assert str(aura.get("amount") or "") == "ceil(level/2)"
    assert int(light.get("bright_ft") or 0) == 10
    assert int(light.get("dim_ft") or 0) == 10

    fallen = subraces["aasimar_fallen"]
    fallen_asi = fallen.get("asi") or []
    assert any(item.get("stat") == "str" and int(item.get("bonus") or 0) == 1 for item in fallen_asi if isinstance(item, dict))
    fallen_traits = {str(item.get("key") or ""): item for item in (fallen.get("traits") or []) if isinstance(item, dict)}
    fallen_mech = (fallen_traits["necrotic_shroud"].get("mechanics") or {})
    fear = fallen_mech.get("fear_on_transform") or {}
    assert str(fear.get("dc_formula") or "") == "8 + proficiency_bonus + cha_mod"
    assert "fly_speed_ft" not in fallen_mech


def test_vedalken_reference_schema_payload() -> None:
    vedalken = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "vedalken"), None)
    assert vedalken is not None
    assert str(vedalken.get("size") or "") == "medium"
    assert int(vedalken.get("speed_ft") or 0) == 30

    asi = vedalken.get("asi") or []
    assert any(item.get("stat") == "int" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))
    assert any(item.get("stat") == "wis" and int(item.get("bonus") or 0) == 1 for item in asi if isinstance(item, dict))

    languages = set(vedalken.get("languages") or [])
    assert "common" in languages
    assert "vedalken" in languages

    traits = {str(item.get("key") or ""): item for item in (vedalken.get("traits") or []) if isinstance(item, dict)}
    assert "vedalken_dispassion" in traits
    assert "tireless_precision" in traits
    assert "partially_amphibious" in traits
    assert "extra_language" in traits

    precision_mechanics = (traits["tireless_precision"].get("mechanics") or {})
    assert str(precision_mechanics.get("bonus_die") or "") == "1d4"
    skill_choices = precision_mechanics.get("choose_skill_from") or []
    assert skill_choices == ["performance", "history", "sleight_of_hand", "arcana", "medicine", "investigation"]


def test_verdan_reference_schema_payload() -> None:
    verdan = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "verdan"), None)
    assert verdan is not None
    assert str(verdan.get("size") or "") == "small"
    assert int(verdan.get("speed_ft") or 0) == 30

    asi = verdan.get("asi") or []
    assert any(item.get("stat") == "cha" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))
    assert any(item.get("stat") == "con" and int(item.get("bonus") or 0) == 1 for item in asi if isinstance(item, dict))

    languages = set(verdan.get("languages") or [])
    assert "common" in languages
    assert "goblin" in languages

    traits = {str(item.get("key") or ""): item for item in (verdan.get("traits") or []) if isinstance(item, dict)}
    assert "black_blood_healing" in traits
    assert "limited_telepathy" in traits
    assert "persuasive" in traits
    assert "telepathic_insight" in traits
    assert "extra_language" in traits
    assert "growth_spurt" in traits

    growth_mechanics = traits["growth_spurt"].get("mechanics") or {}
    assert int(growth_mechanics.get("level_from") or 0) == 5
    assert str(growth_mechanics.get("size") or "") == "medium"


def test_dragonborn_reference_schema_payload() -> None:
    dragonborn = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "dragonborn"), None)
    assert dragonborn is not None
    assert str(dragonborn.get("size") or "") == "medium"
    assert int(dragonborn.get("speed_ft") or 0) == 30

    asi = dragonborn.get("asi") or []
    assert any(item.get("stat") == "str" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))
    assert any(item.get("stat") == "cha" and int(item.get("bonus") or 0) == 1 for item in asi if isinstance(item, dict))

    languages = set(dragonborn.get("languages") or [])
    assert "common" in languages
    assert "draconic" in languages

    traits = {str(item.get("key") or ""): item for item in (dragonborn.get("traits") or []) if isinstance(item, dict)}
    assert "draconic_ancestry" in traits
    assert "breath_weapon" in traits
    assert "damage_resistance" in traits

    ancestry_options = ((traits["draconic_ancestry"].get("mechanics") or {}).get("options") or [])
    ancestry_keys = {str(item.get("key") or "") for item in ancestry_options if isinstance(item, dict)}
    assert len(ancestry_keys) == 10
    assert ancestry_keys == {"red", "green", "blue", "black", "white", "gold", "silver", "bronze", "copper", "brass"}


def test_gnome_reference_schema_payload() -> None:
    gnome = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "gnome"), None)
    assert gnome is not None
    assert str(gnome.get("size") or "") == "small"
    assert int(gnome.get("speed_ft") or 0) == 25

    asi = gnome.get("asi") or []
    assert any(item.get("stat") == "int" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))

    languages = set(gnome.get("languages") or [])
    assert "common" in languages
    assert "gnomish" in languages

    traits = {str(item.get("key") or ""): item for item in (gnome.get("traits") or []) if isinstance(item, dict)}
    assert "darkvision_60" in traits
    assert "gnome_cunning" in traits

    subraces = {str(item.get("key") or ""): item for item in (gnome.get("subraces") or []) if isinstance(item, dict)}
    assert "forest_gnome" in subraces
    assert "rock_gnome" in subraces

    forest_gnome = subraces["forest_gnome"]
    forest_asi = forest_gnome.get("asi") or []
    assert any(item.get("stat") == "dex" and int(item.get("bonus") or 0) == 1 for item in forest_asi if isinstance(item, dict))
    forest_traits = {str(item.get("key") or ""): item for item in (forest_gnome.get("traits") or []) if isinstance(item, dict)}
    assert "natural_illusionist" in forest_traits

    rock_gnome = subraces["rock_gnome"]
    rock_asi = rock_gnome.get("asi") or []
    assert any(item.get("stat") == "con" and int(item.get("bonus") or 0) == 1 for item in rock_asi if isinstance(item, dict))
    rock_traits = {str(item.get("key") or ""): item for item in (rock_gnome.get("traits") or []) if isinstance(item, dict)}
    assert "tinker" in rock_traits
    assert "artificers_lore" in rock_traits


def test_half_elf_reference_schema_payload() -> None:
    half_elf = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "half_elf"), None)
    assert half_elf is not None
    assert str(half_elf.get("size") or "") == "medium"
    assert int(half_elf.get("speed_ft") or 0) == 30

    languages = set(half_elf.get("languages") or [])
    assert "common" in languages
    assert "elvish" in languages

    asi = half_elf.get("asi") or []
    assert any(item.get("stat") == "cha" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))

    traits = {str(item.get("key") or ""): item for item in (half_elf.get("traits") or []) if isinstance(item, dict)}
    assert "darkvision_60" in traits
    assert "fey_ancestry" in traits
    assert "half_elf_versatility_asi" in traits
    assert "skill_versatility" in traits
    assert "extra_language" in traits


def test_half_orc_reference_schema_payload() -> None:
    half_orc = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "half_orc"), None)
    assert half_orc is not None
    assert str(half_orc.get("size") or "") == "medium"
    assert int(half_orc.get("speed_ft") or 0) == 30

    languages = set(half_orc.get("languages") or [])
    assert "common" in languages
    assert "orc" in languages

    asi = half_orc.get("asi") or []
    assert any(item.get("stat") == "str" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))
    assert any(item.get("stat") == "con" and int(item.get("bonus") or 0) == 1 for item in asi if isinstance(item, dict))

    traits = {str(item.get("key") or ""): item for item in (half_orc.get("traits") or []) if isinstance(item, dict)}
    assert "darkvision_60" in traits
    assert "menacing" in traits
    assert "relentless_endurance" in traits
    assert "savage_attacks" in traits


def test_tiefling_reference_schema_payload() -> None:
    tiefling = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "tiefling"), None)
    assert tiefling is not None
    assert str(tiefling.get("size") or "") == "medium"
    assert int(tiefling.get("speed_ft") or 0) == 30

    languages = set(tiefling.get("languages") or [])
    assert "common" in languages
    assert "infernal" in languages

    asi = tiefling.get("asi") or []
    assert any(item.get("stat") == "int" and int(item.get("bonus") or 0) == 1 for item in asi if isinstance(item, dict))
    assert any(item.get("stat") == "cha" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))

    traits = {str(item.get("key") or ""): item for item in (tiefling.get("traits") or []) if isinstance(item, dict)}
    assert "darkvision_60" in traits
    assert "hellish_resistance" in traits
    assert "infernal_legacy" in traits

    grants = ((traits["infernal_legacy"].get("mechanics") or {}).get("grants") or [])
    assert len(grants) == 3
    by_level = {
        int(item.get("min_level") or 0): str(item.get("spell") or "")
        for item in grants
        if isinstance(item, dict)
    }
    assert by_level.get(1) == "thaumaturgy"
    assert by_level.get(3) == "hellish_rebuke"
    assert by_level.get(5) == "darkness"


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


def test_halfling_reference_schema_payload() -> None:
    halfling = next((item for item in RACE_CATALOG if str(item.get("key") or "") == "halfling"), None)
    assert halfling is not None
    assert str(halfling.get("size") or "") == "small"
    assert int(halfling.get("speed_ft") or 0) == 25

    asi = halfling.get("asi") or []
    assert any(item.get("stat") == "dex" and int(item.get("bonus") or 0) == 2 for item in asi if isinstance(item, dict))

    traits = {str(item.get("key") or ""): item for item in (halfling.get("traits") or []) if isinstance(item, dict)}
    assert "lucky" in traits
    assert "brave" in traits
    assert "halfling_nimbleness" in traits

    subraces = {str(item.get("key") or ""): item for item in (halfling.get("subraces") or []) if isinstance(item, dict)}
    assert "lightfoot" in subraces
    assert "stout" in subraces

    lightfoot = subraces["lightfoot"]
    lightfoot_asi = lightfoot.get("asi") or []
    assert any(item.get("stat") == "cha" and int(item.get("bonus") or 0) == 1 for item in lightfoot_asi if isinstance(item, dict))

    stout = subraces["stout"]
    stout_asi = stout.get("asi") or []
    assert any(item.get("stat") == "con" and int(item.get("bonus") or 0) == 1 for item in stout_asi if isinstance(item, dict))
