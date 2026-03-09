from app.rules.derived_stats import compute_ac


def test_loxodon_natural_armor_chosen_when_worn_armor_is_worse() -> None:
    stats = {"dex": 50, "con": 70}
    inv = [{"id": "a1", "def": "leather_armor"}]
    equip_map = {"body": "a1"}
    race_features = {
        "natural_armor": {
            "ac_formula": "12 + con_mod",
            "shield_applies": True,
            "requires_unarmored": True,
            "allow_when_armored_if_better": True,
        }
    }
    # leather: 11 + DEX(0) = 11, natural armor: 12 + CON(2) = 14
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 14


def test_loxodon_natural_armor_not_chosen_when_worn_armor_is_better() -> None:
    stats = {"dex": 50, "con": 70}
    inv = [{"id": "a1", "def": "chain_mail"}]
    equip_map = {"body": "a1"}
    race_features = {
        "natural_armor": {
            "ac_formula": "12 + con_mod",
            "shield_applies": True,
            "requires_unarmored": True,
            "allow_when_armored_if_better": True,
        }
    }
    # chain mail: 16, natural armor: 14
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 16
