from __future__ import annotations

from app.rules.equipment_slots import EquipmentSlot
from app.rules.items import ArmorCategory, EquipSpec, ItemDef, ItemKind, WeaponStats


ITEMS: dict[str, ItemDef] = {
    # Core skeleton
    "leather_armor": ItemDef(
        key="leather_armor",
        name_ru="Кожаная броня",
        kind=ItemKind.armor,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.body,),
            wear_group="armor",
            armor_category=ArmorCategory.light,
            base_ac=11,
        ),
        description_ru="Базовая легкая броня.",
    ),
    "chain_mail": ItemDef(
        key="chain_mail",
        name_ru="Кольчуга",
        kind=ItemKind.armor,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.body,),
            wear_group="armor",
            armor_category=ArmorCategory.heavy,
            base_ac=16,
            str_req=13,
            stealth_disadvantage=True,
        ),
        description_ru="Тяжелая металлическая броня.",
    ),
    "shield": ItemDef(
        key="shield",
        name_ru="Щит",
        kind=ItemKind.shield,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.off_hand,),
            wear_group="shield",
            grants_ac_bonus=2,
        ),
        description_ru="Базовый щит для дополнительной защиты.",
    ),
    "dagger": ItemDef(
        key="dagger",
        name_ru="Кинжал",
        kind=ItemKind.weapon,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.main_hand, EquipmentSlot.off_hand),
            wear_group="weapon",
            weapon=WeaponStats(
                damage_dice="1d4",
                damage_type="piercing",
                properties=("finesse", "light", "thrown"),
                range_normal=20,
                range_long=60,
                mastery="nick",
            ),
        ),
        description_ru="Короткое легкое оружие ближнего боя.",
    ),
    "longsword": ItemDef(
        key="longsword",
        name_ru="Длинный меч",
        kind=ItemKind.weapon,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.main_hand, EquipmentSlot.off_hand),
            wear_group="weapon",
            weapon=WeaponStats(
                damage_dice="1d8",
                damage_type="slashing",
                properties=("versatile",),
                versatile_dice="1d10",
                mastery="sap",
            ),
        ),
        description_ru="Надежное одноручное оружие.",
    ),
    "shortbow": ItemDef(
        key="shortbow",
        name_ru="Короткий лук",
        kind=ItemKind.weapon,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.main_hand,),
            wear_group="weapon",
            two_handed=True,
            weapon=WeaponStats(
                damage_dice="1d6",
                damage_type="piercing",
                properties=("ammunition", "two-handed"),
                range_normal=80,
                range_long=320,
                mastery="vex",
            ),
        ),
        description_ru="Легкое двуручное дальнобойное оружие.",
    ),
    # Legacy examples moved from app/rules/items.py
    "simple_sword": ItemDef(
        key="simple_sword",
        name_ru="Простой меч",
        kind=ItemKind.weapon,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.main_hand, EquipmentSlot.off_hand),
        ),
        description_ru="Обычный одноручный меч для базовых атак.",
    ),
    "wooden_shield": ItemDef(
        key="wooden_shield",
        name_ru="Деревянный щит",
        kind=ItemKind.shield,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.off_hand,),
            grants_ac_bonus=2,
        ),
        description_ru="Легкий щит из дерева.",
    ),
    "traveler_cloak": ItemDef(
        key="traveler_cloak",
        name_ru="Плащ путника",
        kind=ItemKind.accessory,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.back,),
            armor_category=ArmorCategory.clothing,
        ),
        description_ru="Защищает от дождя и пыли в дороге.",
    ),
    "silver_ring": ItemDef(
        key="silver_ring",
        name_ru="Серебряное кольцо",
        kind=ItemKind.accessory,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.ring_left, EquipmentSlot.ring_right),
        ),
        description_ru="Простое кольцо без магических свойств.",
    ),
    "healing_potion": ItemDef(
        key="healing_potion",
        name_ru="Зелье лечения",
        kind=ItemKind.consumable,
        stackable=True,
        max_stack=10,
        description_ru="Восстанавливает немного здоровья.",
    ),
    "quest_key": ItemDef(
        key="quest_key",
        name_ru="Квестовый ключ",
        kind=ItemKind.quest,
        description_ru="Ключ от важной двери по заданию.",
    ),
}


# ШАБЛОН нового предмета:
# "new_item_key": ItemDef(
#     key="new_item_key",
#     name_ru="Название предмета",
#     kind=ItemKind.misc,
#     equip=EquipSpec(
#         allowed_slots=(EquipmentSlot.main_hand,),
#     ),
#     description_ru="Краткое описание.",
# ),
