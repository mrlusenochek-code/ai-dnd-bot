from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.rules.equipment_slots import EquipmentSlot, RING_SLOTS, WEAPON_SLOTS

try:
    from enum import StrEnum
except ImportError:
    # Python < 3.11 fallback: keep enum members as `str` values.
    class StrEnum(str, Enum):
        pass


# Базовый слой правил предметов (описания/экипируемость) для профиля персонажа,
# инвентаря и боевки; хранение в БД и UI будут добавлены позже.
class ItemKind(StrEnum):
    weapon = "weapon"
    armor = "armor"
    shield = "shield"
    accessory = "accessory"
    consumable = "consumable"
    quest = "quest"
    misc = "misc"


class ArmorCategory(StrEnum):
    light = "light"
    medium = "medium"
    heavy = "heavy"
    clothing = "clothing"


@dataclass(frozen=True)
class EquipSpec:
    allowed_slots: tuple[EquipmentSlot, ...]
    two_handed: bool = False
    armor_category: ArmorCategory | None = None
    base_ac: int | None = None
    grants_ac_bonus: int = 0
    notes: str | None = None


@dataclass(frozen=True)
class ItemDef:
    key: str
    name_ru: str
    kind: ItemKind
    stackable: bool = False
    max_stack: int = 1
    equip: EquipSpec | None = None
    description_ru: str | None = None


def is_equipable(item: ItemDef) -> bool:
    return item.equip is not None and bool(item.equip.allowed_slots)


def allowed_equip_slots(item: ItemDef) -> tuple[EquipmentSlot, ...]:
    if item.equip is None:
        return ()
    return item.equip.allowed_slots


def can_equip_to_slot(item: ItemDef, slot: EquipmentSlot) -> bool:
    return slot in allowed_equip_slots(item)


DEFAULT_RING_ALLOWED_SLOTS = RING_SLOTS
DEFAULT_WEAPON_ALLOWED_SLOTS = WEAPON_SLOTS


EXAMPLE_ITEMS: dict[str, ItemDef] = {
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
    "leather_armor": ItemDef(
        key="leather_armor",
        name_ru="Кожаная броня",
        kind=ItemKind.armor,
        equip=EquipSpec(
            allowed_slots=(EquipmentSlot.body,),
            armor_category=ArmorCategory.light,
            base_ac=11,
        ),
        description_ru="Базовая легкая броня.",
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
            allowed_slots=DEFAULT_RING_ALLOWED_SLOTS,
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
