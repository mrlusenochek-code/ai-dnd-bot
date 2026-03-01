from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.rules.equipment_slots import EquipmentSlot
from app.rules.item_catalog import ITEMS
from app.rules.items import ArmorCategory, ItemDef


@dataclass(frozen=True)
class AttackProfile:
    attack_bonus: int
    damage_dice: str
    damage_bonus: int
    damage_type: str
    properties: tuple[str, ...] = ()
    mastery: str | None = None


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _item_def_for_inventory_entry(entry: dict[str, Any]) -> ItemDef | None:
    item_def_key = str(entry.get("def") or "").strip()
    if item_def_key and item_def_key in ITEMS:
        return ITEMS[item_def_key]
    entry_name_cf = str(entry.get("name") or "").strip().casefold()
    if not entry_name_cf:
        return None
    for cand in ITEMS.values():
        if cand.name_ru.casefold() == entry_name_cf:
            return cand
    return None


def dex_mod_from_stat(dex: int) -> int:
    return int((dex - 50) // 20)


def stat_mod_from_stat(stat: int) -> int:
    return int((stat - 50) // 20)


def parse_dice(dice: str) -> tuple[int, int] | None:
    parts = str(dice or "").strip().lower().split("d")
    if len(parts) != 2:
        return None
    if not parts[0].isdigit() or not parts[1].isdigit():
        return None
    n, m = int(parts[0]), int(parts[1])
    if n <= 0 or m <= 0:
        return None
    return n, m


def compute_attack_profile(*, stats: dict, inventory: list[dict], equip_map: dict[str, str]) -> AttackProfile:
    str_stat = _safe_int(stats.get("str", 50), 50) if isinstance(stats, dict) else 50
    dex_stat = _safe_int(stats.get("dex", 50), 50) if isinstance(stats, dict) else 50
    str_mod = stat_mod_from_stat(str_stat)
    dex_mod = dex_mod_from_stat(dex_stat)

    by_id: dict[str, dict[str, Any]] = {}
    for entry in inventory if isinstance(inventory, list) else []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip().lower()
        if entry_id:
            by_id[entry_id] = entry

    chosen_slot: EquipmentSlot | None = None
    chosen_entry: dict[str, Any] | None = None
    for slot in (EquipmentSlot.main_hand, EquipmentSlot.ranged, EquipmentSlot.off_hand):
        item_id = str(equip_map.get(slot.value) or "").strip().lower() if isinstance(equip_map, dict) else ""
        if not item_id:
            continue
        entry = by_id.get(item_id)
        if entry:
            chosen_slot = slot
            chosen_entry = entry
            break

    item_def = _item_def_for_inventory_entry(chosen_entry) if chosen_entry else None
    weapon = item_def.equip.weapon if item_def and item_def.equip and item_def.equip.weapon else None

    if weapon:
        properties = tuple(weapon.properties or ())
        properties_cf = {p.casefold() for p in properties}
        if "ammunition" in properties_cf or chosen_slot == EquipmentSlot.ranged:
            stat_mod = dex_mod
        elif "finesse" in properties_cf:
            stat_mod = max(str_mod, dex_mod)
        else:
            stat_mod = str_mod
        attack_bonus = _clamp(3 + stat_mod, 0, 20)
        damage_bonus = _clamp(2 + stat_mod, 0, 20)
        return AttackProfile(
            attack_bonus=attack_bonus,
            damage_dice=weapon.damage_dice,
            damage_bonus=damage_bonus,
            damage_type=weapon.damage_type,
            properties=properties,
            mastery=weapon.mastery,
        )

    attack_bonus = _clamp(3 + str_mod, 0, 20)
    damage_bonus = _clamp(2 + str_mod, 0, 20)
    return AttackProfile(
        attack_bonus=attack_bonus,
        damage_dice="1d4",
        damage_bonus=damage_bonus,
        damage_type="bludgeoning",
    )


def compute_ac(*, stats: dict, inventory: list[dict], equip_map: dict[str, str]) -> int:
    dex = _safe_int(stats.get("dex", 50), 50) if isinstance(stats, dict) else 50
    dex_mod = dex_mod_from_stat(dex)
    ac = 12 + dex_mod

    by_id: dict[str, dict[str, Any]] = {}
    for entry in inventory if isinstance(inventory, list) else []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip().lower()
        if entry_id:
            by_id[entry_id] = entry

    body_item_id = str(equip_map.get(EquipmentSlot.body.value) or "").strip().lower() if isinstance(equip_map, dict) else ""
    shield_item_id = (
        str(equip_map.get(EquipmentSlot.off_hand.value) or "").strip().lower()
        if isinstance(equip_map, dict)
        else ""
    )

    armor_entry = by_id.get(body_item_id)
    armor_def = _item_def_for_inventory_entry(armor_entry) if armor_entry else None
    armor_equip = armor_def.equip if armor_def else None
    if armor_equip and armor_equip.base_ac is not None:
        armor_base_ac = int(armor_equip.base_ac)
        armor_category = armor_equip.armor_category
        if armor_category in (ArmorCategory.light, ArmorCategory.clothing):
            ac = armor_base_ac + dex_mod
        elif armor_category == ArmorCategory.medium:
            dex_cap = 2 if armor_equip.dex_cap is None else int(armor_equip.dex_cap)
            ac = armor_base_ac + min(dex_mod, dex_cap)
        elif armor_category == ArmorCategory.heavy:
            ac = armor_base_ac
        else:
            ac = armor_base_ac

    shield_entry = by_id.get(shield_item_id)
    shield_def = _item_def_for_inventory_entry(shield_entry) if shield_entry else None
    shield_equip = shield_def.equip if shield_def else None
    if shield_equip and shield_equip.grants_ac_bonus:
        ac += int(shield_equip.grants_ac_bonus)

    return _clamp(ac, 10, 25)
