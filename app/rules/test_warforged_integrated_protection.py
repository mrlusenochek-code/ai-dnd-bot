from app.rules.derived_stats import compute_ac


def test_warforged_integrated_protection_adds_plus_one_unarmored() -> None:
    stats = {"dex": 70}
    inv: list[dict] = []
    equip_map: dict[str, str] = {}
    race_features = {"features": {"integrated_protection": {"ac_bonus": 1}}}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 13


def test_warforged_integrated_protection_stacks_with_armor_and_shield_normally() -> None:
    stats = {"dex": 50}
    inv = [
        {"id": "a1", "def": "chain_mail"},
        {"id": "s1", "def": "shield"},
    ]
    equip_map = {"body": "a1", "off_hand": "s1"}
    race_features = {"features": {"integrated_protection": {"ac_bonus": 1}}}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, race_features=race_features) == 19
