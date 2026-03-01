from app.rules.item_catalog import ITEMS


def test_healing_potion_consume_specs() -> None:
    assert ITEMS["healing_potion"].consume is not None
    assert ITEMS["healing_potion"].consume.heal_dice == "2d4+2"
    assert ITEMS["greater_healing_potion"].consume is not None
    assert ITEMS["greater_healing_potion"].consume.heal_dice == "4d4+4"


def test_non_consumables_have_no_consume_spec() -> None:
    assert ITEMS["dagger"].consume is None
    assert ITEMS["shield"].consume is None
    assert ITEMS["leather_armor"].consume is None
