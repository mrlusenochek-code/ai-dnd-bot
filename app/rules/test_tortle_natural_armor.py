from app.rules.derived_stats import compute_ac


def test_tortle_natural_armor_base_ac_is_17() -> None:
    stats = {"dex": 70}
    inv: list[dict] = []
    equip_map: dict[str, str] = {}
    race_features = {"natural_armor": {"ac": 17, "no_armor_stack": True}}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 17


def test_tortle_natural_armor_does_not_stack_with_worn_armor() -> None:
    stats = {"dex": 70}
    inv = [{"id": "i1", "def": "chain_mail"}]
    equip_map = {"body": "i1"}
    race_features = {"natural_armor": {"ac": 17, "no_armor_stack": True}}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 16


def test_tortle_natural_armor_keeps_shield_bonus() -> None:
    stats = {"dex": 50}
    inv = [{"id": "s1", "def": "shield"}]
    equip_map = {"off_hand": "s1"}
    race_features = {"natural_armor": {"ac": 17, "no_armor_stack": True}}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 19
