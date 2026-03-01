from app.rules.derived_stats import compute_ac


def test_compute_ac_light_armor_and_shield() -> None:
    stats = {"dex": 50}
    inv = [
        {"id": "i1", "def": "leather_armor"},
        {"id": "i2", "def": "shield"},
    ]
    equip_map = {"body": "i1", "off_hand": "i2"}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map) == 13


def test_compute_ac_heavy_armor_ignores_dex_with_shield() -> None:
    stats = {"dex": 90}
    inv = [
        {"id": "c1", "def": "chain_mail"},
        {"id": "s1", "def": "shield"},
    ]
    equip_map = {"body": "c1", "off_hand": "s1"}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map) == 18


def test_compute_ac_fallback_without_armor_or_shield() -> None:
    stats = {"dex": 70}
    inv: list[dict] = []
    equip_map: dict[str, str] = {}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map) == 13
