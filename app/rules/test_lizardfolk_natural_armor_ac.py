from app.rules.derived_stats import compute_ac


def test_lizardfolk_natural_armor_applies_when_unarmored_and_shield_works() -> None:
    stats = {"dex": 70}
    inv = [{"id": "s1", "def": "shield"}]
    equip_map = {"off_hand": "s1"}
    race_features = {"natural_armor": {"ac_formula": "13 + dex_mod", "shield_applies": True, "requires_unarmored": True}}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 17


def test_lizardfolk_natural_armor_does_not_apply_when_wearing_armor() -> None:
    stats = {"dex": 70}
    inv = [{"id": "a1", "def": "leather_armor"}, {"id": "s1", "def": "shield"}]
    equip_map = {"body": "a1", "off_hand": "s1"}
    race_features = {"natural_armor": {"ac_formula": "13 + dex_mod", "shield_applies": True, "requires_unarmored": True}}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 15
