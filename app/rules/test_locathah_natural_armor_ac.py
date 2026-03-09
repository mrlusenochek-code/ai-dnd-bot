from app.rules.derived_stats import compute_ac


def test_locathah_natural_armor_applies_when_unarmored() -> None:
    stats = {"dex": 70}
    inv = []
    equip_map = {}
    race_features = {"natural_armor": {"ac_formula": "12 + dex_mod", "requires_unarmored": True}}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 14


def test_locathah_natural_armor_ignored_when_wearing_armor() -> None:
    stats = {"dex": 70}
    inv = [{"id": "a1", "def": "leather_armor"}]
    equip_map = {"body": "a1"}
    race_features = {"natural_armor": {"ac_formula": "12 + dex_mod", "requires_unarmored": True}}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 13
