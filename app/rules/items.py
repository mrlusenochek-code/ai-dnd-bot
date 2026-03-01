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
