from __future__ import annotations

from enum import Enum

try:
    from enum import StrEnum
except ImportError:
    # Python < 3.11 fallback: keep enum members as `str` values.
    class StrEnum(str, Enum):
        pass


# Единая база слотов экипировки для профиля, инвентаря и боевых проверок.
# Значения в enum — стабильные ключи для хранения и обмена данными.
class EquipmentSlot(StrEnum):
    head = "head"
    neck = "neck"
    shoulders = "shoulders"
    body = "body"
    back = "back"
    belt = "belt"
    hands = "hands"
    wrists = "wrists"
    ring_left = "ring_left"
    ring_right = "ring_right"
    legs = "legs"
    feet = "feet"
    main_hand = "main_hand"
    off_hand = "off_hand"
    ranged = "ranged"
    artifact = "artifact"


# Порядок отображения слотов в профиле персонажа ("Одето:").
EQUIPMENT_SLOT_ORDER: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.head,
    EquipmentSlot.neck,
    EquipmentSlot.shoulders,
    EquipmentSlot.body,
    EquipmentSlot.back,
    EquipmentSlot.belt,
    EquipmentSlot.hands,
    EquipmentSlot.wrists,
    EquipmentSlot.ring_left,
    EquipmentSlot.ring_right,
    EquipmentSlot.legs,
    EquipmentSlot.feet,
    EquipmentSlot.main_hand,
    EquipmentSlot.off_hand,
    EquipmentSlot.ranged,
    EquipmentSlot.artifact,
)


# Человекочитаемые подписи для UI.
EQUIPMENT_SLOT_LABELS_RU: dict[EquipmentSlot, str] = {
    EquipmentSlot.head: "Голова",
    EquipmentSlot.neck: "Шея",
    EquipmentSlot.shoulders: "Плечи",
    EquipmentSlot.body: "Тело",
    EquipmentSlot.back: "Спина",
    EquipmentSlot.belt: "Пояс",
    EquipmentSlot.hands: "Руки",
    EquipmentSlot.wrists: "Запястья",
    EquipmentSlot.ring_left: "Кольцо (лев.)",
    EquipmentSlot.ring_right: "Кольцо (прав.)",
    EquipmentSlot.legs: "Ноги",
    EquipmentSlot.feet: "Ступни",
    EquipmentSlot.main_hand: "Основная рука",
    EquipmentSlot.off_hand: "Вторая рука",
    EquipmentSlot.ranged: "Дальний слот",
    EquipmentSlot.artifact: "Артефакт",
}


RING_SLOTS: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.ring_left,
    EquipmentSlot.ring_right,
)

WEAPON_SLOTS: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.main_hand,
    EquipmentSlot.off_hand,
    EquipmentSlot.ranged,
)

# Бронеслоты без колец и артефакта.
ARMOR_SLOTS: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.head,
    EquipmentSlot.neck,
    EquipmentSlot.shoulders,
    EquipmentSlot.body,
    EquipmentSlot.back,
    EquipmentSlot.belt,
    EquipmentSlot.hands,
    EquipmentSlot.wrists,
    EquipmentSlot.legs,
    EquipmentSlot.feet,
)


def slot_label_ru(slot: EquipmentSlot) -> str:
    """Возвращает русский label слота; fallback — техническое значение слота."""
    return EQUIPMENT_SLOT_LABELS_RU.get(slot, slot.value)
