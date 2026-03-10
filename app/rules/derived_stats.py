from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from app.rules.phb_math import ability_mod_from_stat100, proficiency_bonus
from app.rules.equipment_slots import EquipmentSlot
from app.rules.item_catalog import ITEMS
from app.rules.items import ArmorCategory, ItemDef


@dataclass(frozen=True)
class AttackProfile:
    attack_bonus: int
    damage_dice: str
    damage_bonus: int
    damage_type: str
    is_melee_weapon: bool = False
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


def equipped_armor_category(*, inventory: list[dict], equip_map: dict[str, str]) -> str | None:
    by_id: dict[str, dict[str, Any]] = {}
    for entry in inventory if isinstance(inventory, list) else []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip().lower()
        if entry_id:
            by_id[entry_id] = entry

    body_item_id = str(equip_map.get(EquipmentSlot.body.value) or "").strip().lower() if isinstance(equip_map, dict) else ""
    if not body_item_id:
        return None

    armor_entry = by_id.get(body_item_id)
    armor_def = _item_def_for_inventory_entry(armor_entry) if armor_entry else None
    armor_equip = armor_def.equip if armor_def else None
    armor_category = armor_equip.armor_category if armor_equip else None
    if armor_category is None:
        return None
    return str(armor_category.value if hasattr(armor_category, "value") else armor_category).strip().lower() or None


def fly_speed_available_by_armor(*, race_features: dict | None, inventory: list[dict], equip_map: dict[str, str]) -> tuple[bool, str | None]:
    rf = race_features if isinstance(race_features, dict) else {}
    speeds = rf.get("speeds") if isinstance(rf.get("speeds"), dict) else {}
    fly_ft = _safe_int(speeds.get("fly_ft"), 0)
    if fly_ft <= 0:
        return False, None

    restriction = speeds.get("fly_restriction") if isinstance(speeds.get("fly_restriction"), dict) else {}
    no_armor_categories_raw = restriction.get("no_armor_categories")
    no_armor_categories = (
        [str(x).strip().lower() for x in no_armor_categories_raw if str(x).strip()]
        if isinstance(no_armor_categories_raw, list)
        else []
    )
    if not no_armor_categories:
        return True, None

    armor_cat = equipped_armor_category(inventory=inventory, equip_map=equip_map)
    if armor_cat and armor_cat in no_armor_categories:
        return False, armor_cat
    return True, armor_cat


def effective_walk_speed_ft(
    base_speed_ft: int,
    *,
    inventory: list[dict],
    equip_map: dict[str, str],
    race_features: dict | None,
) -> int:
    base = max(0, _safe_int(base_speed_ft, 30))
    armor_cat = equipped_armor_category(inventory=inventory, equip_map=equip_map)
    if armor_cat != "heavy":
        return base

    rf = race_features if isinstance(race_features, dict) else {}
    movement = rf.get("movement") if isinstance(rf.get("movement"), dict) else {}
    if bool(movement.get("ignore_heavy_armor_speed_penalty")):
        return base

    if base == 25:
        return 15
    return base


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


def _ability_mod_by_key(ability_key: str, *, str_mod: int, dex_mod: int, con_mod: int, int_mod: int, wis_mod: int, cha_mod: int) -> int:
    key = str(ability_key or "").strip().lower()
    if key == "dex":
        return dex_mod
    if key == "con":
        return con_mod
    if key == "int":
        return int_mod
    if key == "wis":
        return wis_mod
    if key == "cha":
        return cha_mod
    return str_mod


def _first_unarmed_natural_weapon(race_features: dict | None) -> dict[str, Any] | None:
    if not isinstance(race_features, dict):
        return None
    raw = race_features.get("natural_weapons")
    items = raw if isinstance(raw, list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip().lower()
        damage_dice = str(item.get("damage_dice") or "").strip().lower()
        damage_type = str(item.get("damage_type") or "").strip().lower()
        if kind != "unarmed":
            continue
        if not damage_dice or not damage_type:
            continue
        return item
    return None


def compute_attack_profile(
    *,
    stats: dict,
    inventory: list[dict],
    equip_map: dict[str, str],
    level: int | None = None,
    race_features: dict | None = None,
) -> AttackProfile:
    str_stat = _safe_int(stats.get("str", 50), 50) if isinstance(stats, dict) else 50
    dex_stat = _safe_int(stats.get("dex", 50), 50) if isinstance(stats, dict) else 50
    con_stat = _safe_int(stats.get("con", 50), 50) if isinstance(stats, dict) else 50
    int_stat = _safe_int(stats.get("int", 50), 50) if isinstance(stats, dict) else 50
    wis_stat = _safe_int(stats.get("wis", 50), 50) if isinstance(stats, dict) else 50
    cha_stat = _safe_int(stats.get("cha", 50), 50) if isinstance(stats, dict) else 50
    str_mod = ability_mod_from_stat100(str_stat)
    dex_mod = ability_mod_from_stat100(dex_stat)
    con_mod = ability_mod_from_stat100(con_stat)
    int_mod = ability_mod_from_stat100(int_stat)
    wis_mod = ability_mod_from_stat100(wis_stat)
    cha_mod = ability_mod_from_stat100(cha_stat)
    prof = proficiency_bonus(level or 1)

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
        is_ranged_weapon = False
        if "ammunition" in properties_cf or chosen_slot == EquipmentSlot.ranged:
            is_ranged_weapon = True
        elif isinstance(weapon.range_normal, int) and weapon.range_normal > 0 and "thrown" not in properties_cf:
            is_ranged_weapon = True
        attack_bonus = stat_mod + prof
        damage_bonus = stat_mod
        return AttackProfile(
            attack_bonus=attack_bonus,
            damage_dice=weapon.damage_dice,
            damage_bonus=damage_bonus,
            damage_type=weapon.damage_type,
            is_melee_weapon=not is_ranged_weapon,
            properties=properties,
            mastery=weapon.mastery,
        )

    attack_bonus = str_mod + prof
    damage_bonus = str_mod
    nat_unarmed = _first_unarmed_natural_weapon(race_features)
    if nat_unarmed is not None:
        ability_key = str(nat_unarmed.get("ability") or "str").strip().lower()
        stat_mod = _ability_mod_by_key(
            ability_key,
            str_mod=str_mod,
            dex_mod=dex_mod,
            con_mod=con_mod,
            int_mod=int_mod,
            wis_mod=wis_mod,
            cha_mod=cha_mod,
        )
        attack_bonus = stat_mod + prof
        damage_bonus = stat_mod
        return AttackProfile(
            attack_bonus=attack_bonus,
            damage_dice=str(nat_unarmed.get("damage_dice") or "1d4").strip().lower(),
            damage_bonus=damage_bonus,
            damage_type=str(nat_unarmed.get("damage_type") or "bludgeoning").strip().lower(),
            is_melee_weapon=False,
            properties=(),
            mastery=None,
        )
    return AttackProfile(
        attack_bonus=attack_bonus,
        damage_dice="1d4",
        damage_bonus=damage_bonus,
        damage_type="bludgeoning",
        is_melee_weapon=False,
    )


def compute_ac(*, stats: dict, inventory: list[dict], equip_map: dict[str, str], race_features: dict | None = None) -> int:
    dex = _safe_int(stats.get("dex", 50), 50) if isinstance(stats, dict) else 50
    dex_mod = ability_mod_from_stat100(dex)
    ac = 10 + dex_mod
    # Natural armor from race (stored in Character.race_features)
    nat = (race_features or {}).get("natural_armor") if isinstance(race_features, dict) else None
    nat_ac_base: int | None = None
    nat_no_armor_stack = False
    nat_requires_unarmored = True
    nat_allow_when_armored_if_better = False
    if isinstance(nat, dict):
        nat_no_armor_stack = bool(nat.get("no_armor_stack"))
        if nat.get("requires_unarmored") is not None:
            nat_requires_unarmored = bool(nat.get("requires_unarmored"))
        nat_allow_when_armored_if_better = bool(nat.get("allow_when_armored_if_better"))
        if nat.get("ac") is not None:
            nat_ac_base = _safe_int(nat.get("ac"), None)  # type: ignore[arg-type]
        elif nat.get("ac_formula"):
            # Supported formulas: "13 + dex_mod", "12 + con_mod"
            formula = str(nat.get("ac_formula") or "").strip().lower().replace(" ", "")
            if formula in ("13+dex_mod", "13+dexmod"):
                nat_ac_base = 13 + dex_mod
            elif formula in ("12+dex_mod", "12+dexmod"):
                nat_ac_base = 12 + dex_mod
            elif formula in ("12+con_mod", "12+conmod"):
                con = _safe_int(stats.get("con", 50), 50) if isinstance(stats, dict) else 50
                con_mod = ability_mod_from_stat100(con)
                nat_ac_base = 12 + con_mod

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
    armor_is_worn = bool(armor_equip and armor_equip.base_ac is not None)
    if armor_is_worn and nat_requires_unarmored and not nat_allow_when_armored_if_better:
        nat_ac_base = None
    if armor_equip and armor_equip.base_ac is not None:
        # If race natural armor does not stack with worn armor, ignore it.
        if nat_no_armor_stack:
            nat_ac_base = None
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

    if isinstance(nat_ac_base, int):
        ac = max(ac, nat_ac_base)

    shield_entry = by_id.get(shield_item_id)
    shield_def = _item_def_for_inventory_entry(shield_entry) if shield_entry else None
    shield_equip = shield_def.equip if shield_def else None
    if shield_equip and shield_equip.grants_ac_bonus:
        ac += int(shield_equip.grants_ac_bonus)

    # Runtime AC bonus from race features (e.g., Tortle Shell Defense +4 AC)
    runtime = (race_features or {}).get("runtime") if isinstance(race_features, dict) else None
    ac_bonus = _safe_int(runtime.get("ac_bonus"), 0) if isinstance(runtime, dict) else 0
    if ac_bonus:
        ac += int(ac_bonus)

    rf_features = (race_features or {}).get("features") if isinstance(race_features, dict) else None
    carapace_cfg = rf_features.get("ac_bonus_if_no_heavy_armor") if isinstance(rf_features, dict) else None
    if isinstance(carapace_cfg, dict):
        armor_cat = equipped_armor_category(inventory=inventory, equip_map=equip_map)
        if armor_cat != "heavy":
            ac += _safe_int(carapace_cfg.get("ac_bonus"), 0)
    integrated_protection_cfg = rf_features.get("integrated_protection") if isinstance(rf_features, dict) else None
    if isinstance(integrated_protection_cfg, dict):
        ac += _safe_int(integrated_protection_cfg.get("ac_bonus"), 0)

    return _clamp(ac, 1, 50)
