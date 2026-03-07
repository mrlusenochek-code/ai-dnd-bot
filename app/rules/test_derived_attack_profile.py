from app.rules.derived_stats import compute_attack_profile


def test_compute_attack_profile_dagger_finesse_uses_best_of_str_and_dex() -> None:
    stats = {"str": 70, "dex": 90}
    inv = [
        {"id": "w1", "def": "dagger"},
    ]
    equip_map = {"main_hand": "w1"}

    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map, level=1)

    assert profile.attack_bonus == 6
    assert profile.damage_bonus == 4
    assert profile.damage_dice == "1d4"
    assert profile.damage_type == "piercing"


def test_compute_attack_profile_longsword_uses_str() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [
        {"id": "w2", "def": "longsword"},
    ]
    equip_map = {"main_hand": "w2"}

    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map, level=1)

    assert profile.attack_bonus == 6
    assert profile.damage_bonus == 4
    assert profile.damage_dice == "1d8"
    assert profile.damage_type == "slashing"


def test_compute_attack_profile_shortbow_ammunition_uses_dex() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [
        {"id": "w3", "def": "shortbow"},
    ]
    equip_map = {"ranged": "w3"}

    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map, level=1)

    assert profile.attack_bonus == 2
    assert profile.damage_bonus == 0
    assert profile.damage_dice == "1d6"
    assert profile.damage_type == "piercing"


def test_compute_attack_profile_shortbow_level_five_gains_prof_bonus() -> None:
    stats = {"str": 50, "dex": 50}
    inv = [
        {"id": "w3", "def": "shortbow"},
    ]
    equip_map = {"ranged": "w3"}

    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map, level=5)

    assert profile.attack_bonus == 3
    assert profile.damage_bonus == 0


def test_compute_attack_profile_uses_race_natural_unarmed_weapon_when_no_weapon_equipped() -> None:
    stats = {"str": 50, "dex": 50}
    inv: list[dict] = []
    equip_map: dict[str, str] = {}
    race_features = {
        "natural_weapons": [
            {
                "damage_dice": "1d4",
                "damage_type": "slashing",
                "kind": "unarmed",
                "ability": "str",
            }
        ]
    }

    profile = compute_attack_profile(
        stats=stats,
        inventory=inv,
        equip_map=equip_map,
        level=1,
        race_features=race_features,
    )

    assert profile.damage_dice == "1d4"
    assert profile.damage_type == "slashing"
