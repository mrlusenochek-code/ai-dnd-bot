from app.rules.derived_stats import compute_attack_profile


def test_compute_attack_profile_dagger_finesse_uses_best_of_str_and_dex() -> None:
    stats = {"str": 70, "dex": 90}
    inv = [
        {"id": "w1", "def": "dagger"},
    ]
    equip_map = {"main_hand": "w1"}

    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map)

    assert profile.attack_bonus == 5
    assert profile.damage_bonus == 4
    assert profile.damage_dice == "1d4"
    assert profile.damage_type == "piercing"


def test_compute_attack_profile_longsword_uses_str() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [
        {"id": "w2", "def": "longsword"},
    ]
    equip_map = {"main_hand": "w2"}

    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map)

    assert profile.attack_bonus == 5
    assert profile.damage_bonus == 4
    assert profile.damage_dice == "1d8"
    assert profile.damage_type == "slashing"


def test_compute_attack_profile_shortbow_ammunition_uses_dex() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [
        {"id": "w3", "def": "shortbow"},
    ]
    equip_map = {"ranged": "w3"}

    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map)

    assert profile.attack_bonus == 3
    assert profile.damage_bonus == 2
    assert profile.damage_dice == "1d6"
    assert profile.damage_type == "piercing"
