from app.rules.derived_stats import parse_dice as parse_damage_dice
from app.rules.item_catalog import ITEMS
from app.rules.items import ArmorCategory, ItemKind
from app.web.dice import parse_dice as parse_heal_dice


def test_item_catalog_contracts() -> None:
    for dict_key, item in ITEMS.items():
        assert item.key == dict_key

        equip = item.equip
        if equip is not None:
            assert equip.allowed_slots

        if item.kind == ItemKind.weapon:
            assert equip is not None
            assert equip.weapon is not None
            assert equip.wear_group == "weapon"
            assert parse_damage_dice(equip.weapon.damage_dice) is not None

        if item.kind == ItemKind.armor:
            assert equip is not None
            assert equip.base_ac is not None
            assert equip.armor_category is not None
            assert equip.wear_group == "armor"
            if equip.dex_cap is not None:
                assert equip.armor_category == ArmorCategory.medium

        if item.kind == ItemKind.shield:
            assert equip is not None
            assert equip.grants_ac_bonus > 0
            assert equip.wear_group == "shield"

        if item.kind == ItemKind.consumable:
            assert item.consume is not None
            if item.consume.heal_dice is not None:
                assert item.consume.heal_dice.strip()
                assert parse_heal_dice(item.consume.heal_dice) is not None
