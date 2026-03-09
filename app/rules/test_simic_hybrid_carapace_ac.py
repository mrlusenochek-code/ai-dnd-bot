from app.rules.derived_stats import compute_ac


def test_simic_carapace_grants_plus_one_ac_without_heavy_armor() -> None:
    race_features = {"features": {"ac_bonus_if_no_heavy_armor": {"ac_bonus": 1}}}
    assert compute_ac(stats={"dex": 50}, inventory=[], equip_map={}, race_features=race_features) == 11


def test_simic_carapace_does_not_apply_in_heavy_armor() -> None:
    race_features = {"features": {"ac_bonus_if_no_heavy_armor": {"ac_bonus": 1}}}
    inventory = [{"id": "c1", "def": "chain_mail"}]
    equip_map = {"body": "c1"}
    assert compute_ac(stats={"dex": 80}, inventory=inventory, equip_map=equip_map, race_features=race_features) == 16
