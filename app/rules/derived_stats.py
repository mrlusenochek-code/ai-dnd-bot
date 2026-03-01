from __future__ import annotations

from typing import Any

from app.rules.equipment_slots import EquipmentSlot
from app.rules.item_catalog import ITEMS
from app.rules.items import ArmorCategory, ItemDef


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
