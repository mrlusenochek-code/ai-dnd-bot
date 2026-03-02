import re
from typing import Any, Optional

from app.db.models import Character
from app.rules.equipment_slots import EquipmentSlot, EQUIPMENT_SLOT_ORDER, slot_label_ru
from app.rules.item_catalog import ITEMS
from app.rules.items import ItemDef
from app.web.utils import as_int, _clamp, _short_text, _slugify_inventory_id


def _normalize_inventory_def(raw_def: Any) -> Optional[str]:
    value = str(raw_def or "").strip()[:60]
    if not value:
        return None
    if not re.fullmatch(r"[a-z0-9_]+", value):
        return None
    return value


def _normalize_inventory_item(raw_item: Any, index: int) -> Optional[dict[str, Any]]:
    if isinstance(raw_item, str):
        name = raw_item.strip()
        qty = 1
        item_id_raw = ""
        tags_raw = None
        notes_raw = ""
        def_raw = None
    elif isinstance(raw_item, dict):
        name = str(raw_item.get("name") or "").strip()
        qty = _clamp(as_int(raw_item.get("qty"), 1), 1, 99)
        item_id_raw = str(raw_item.get("id") or "").strip()
        tags_raw = raw_item.get("tags")
        notes_raw = str(raw_item.get("notes") or "").strip()
        def_raw = raw_item.get("def")
    else:
        return None

    if not name:
        return None

    item: dict[str, Any] = {
        "id": _slugify_inventory_id(item_id_raw, name, index),
        "name": name[:80],
        "qty": _clamp(as_int(qty, 1), 1, 99),
    }

    if isinstance(tags_raw, list):
        tags: list[str] = []
        for tag in tags_raw:
            t = str(tag or "").strip()
            if t:
                tags.append(t[:30])
            if len(tags) >= 8:
                break
        if tags:
            item["tags"] = tags

    notes = str(notes_raw or "").strip()[:200]
    if notes:
        item["notes"] = notes

    item_def = _normalize_inventory_def(def_raw)
    if item_def:
        item["def"] = item_def

    return item


def _parse_inventory_text(raw_text: Any) -> list[dict[str, Any]]:
    text = str(raw_text or "")
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        ln = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(line or "").strip())
        if not ln:
            continue
        qty = 1
        name = ln
        m_tail = re.match(r"^(.*?)\s*[xх*]\s*(\d{1,2})\s*$", ln, flags=re.IGNORECASE)
        if m_tail:
            name = m_tail.group(1).strip()
            qty = _clamp(as_int(m_tail.group(2), 1), 1, 99)
        else:
            m_head = re.match(r"^(\d{1,2})\s*[xх*]?\s+(.+?)\s*$", ln, flags=re.IGNORECASE)
            if m_head:
                qty = _clamp(as_int(m_head.group(1), 1), 1, 99)
                name = m_head.group(2).strip()
        if name:
            items.append({"name": name, "qty": qty})
    return items


def _normalize_inventory_payload(inventory_raw: Any, inventory_text_raw: Any) -> list[dict[str, Any]]:
    source_items: list[Any]
    if isinstance(inventory_raw, list):
        source_items = inventory_raw
    elif str(inventory_text_raw or "").strip():
        source_items = _parse_inventory_text(inventory_text_raw)
    else:
        source_items = []

    out: list[dict[str, Any]] = []
    for idx, raw_item in enumerate(source_items, start=1):
        normalized = _normalize_inventory_item(raw_item, idx)
        if normalized:
            out.append(normalized)
        if len(out) >= 60:
            break
    return out


def _character_inventory_from_stats(stats_raw: Any) -> list[dict[str, Any]]:
    if not isinstance(stats_raw, dict):
        return []
    raw = stats_raw.get("_inv")
    return raw if isinstance(raw, list) else []


def _put_character_inventory_into_stats(stats_raw: Any, inventory: list[dict[str, Any]]) -> dict[str, Any]:
    stats = dict(stats_raw) if isinstance(stats_raw, dict) else {}
    stats["_inv"] = list(inventory) if isinstance(inventory, list) else []
    return stats


def _character_equip_from_stats(stats_raw: Any) -> dict[str, str]:
    if not isinstance(stats_raw, dict):
        return {}
    raw = stats_raw.get("_equip")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for slot_raw, item_id_raw in raw.items():
        slot_value = str(slot_raw or "").strip().lower()
        item_id = str(item_id_raw or "").strip().lower()
        if not slot_value or not item_id:
            continue
        try:
            slot = EquipmentSlot(slot_value)
        except Exception:
            continue
        out[slot.value] = item_id
    return out


def _put_character_equip_into_stats(stats_raw: Any, equip_map: dict[str, str]) -> dict[str, Any]:
    stats = dict(stats_raw) if isinstance(stats_raw, dict) else {}
    normalized: dict[str, str] = {}
    if isinstance(equip_map, dict):
        for slot_raw, item_id_raw in equip_map.items():
            slot_value = str(slot_raw or "").strip().lower()
            item_id = str(item_id_raw or "").strip().lower()
            if not slot_value or not item_id:
                continue
            try:
                slot = EquipmentSlot(slot_value)
            except Exception:
                continue
            normalized[slot.value] = item_id
    stats["_equip"] = normalized
    return stats


def _equip_state_line(ch: Optional[Character]) -> str:
    if not ch:
        return "ничего"
    equip = _character_equip_from_stats(ch.stats)
    if not equip:
        return "ничего"
    inv = _character_inventory_from_stats(ch.stats)
    by_id: dict[str, dict[str, Any]] = {}
    for entry in inv:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip().lower()
        if not entry_id:
            continue
        by_id[entry_id] = entry
    parts: list[str] = []
    for slot in EQUIPMENT_SLOT_ORDER:
        item_id = str(equip.get(slot.value) or "").strip().lower()
        if not item_id:
            continue
        item_entry = by_id.get(item_id)
        item_name = str((item_entry or {}).get("name") or item_id).strip()
        if not item_name:
            continue
        parts.append(f"{slot_label_ru(slot)}: {item_name}")
    return "; ".join(parts) if parts else "ничего"


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


def _equipped_wear_groups(inv: list[dict[str, Any]], equip_map: dict[str, str]) -> dict[str, str]:
    by_id: dict[str, dict[str, Any]] = {}
    for entry in inv:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip().lower()
        if not entry_id:
            continue
        by_id[entry_id] = entry
    out: dict[str, str] = {}
    for equipped_item_id in equip_map.values():
        item_id = str(equipped_item_id or "").strip().lower()
        if not item_id:
            continue
        entry = by_id.get(item_id)
        if not entry:
            continue
        item_def = _item_def_for_inventory_entry(entry)
        wear_group = str(((item_def.equip.wear_group if item_def and item_def.equip else None) or "")).strip().lower()
        if wear_group in ("", "weapon", "ring"):
            continue
        if wear_group not in out:
            out[wear_group] = item_id
    return out


def _find_inventory_item_index(inv: list[dict[str, Any]], name_or_id: str) -> Optional[int]:
    needle_name = str(name_or_id or "").strip().lower()
    if not needle_name:
        return None
    needle_id = _slugify_inventory_id(name_or_id, name_or_id, 1)
    for idx, raw_item in enumerate(inv):
        if not isinstance(raw_item, dict):
            continue
        item_name = str(raw_item.get("name") or "").strip().lower()
        item_id = str(raw_item.get("id") or "").strip().lower()
        if item_name == needle_name or item_id == needle_id:
            return idx
    return None


def _inv_add_on_character(
    ch: Character,
    *,
    name: str,
    qty: int,
    tags: Optional[list[str]] = None,
    notes: Optional[str] = None,
    item_def: str | None = None,
) -> bool:
    inv_raw = _character_inventory_from_stats(ch.stats)
    inv: list[dict[str, Any]] = [dict(x) for x in inv_raw if isinstance(x, dict)]
    idx = _find_inventory_item_index(inv, name)
    changed = False
    if idx is not None:
        item = dict(inv[idx])
        cur_qty = _clamp(as_int(item.get("qty"), 1), 1, 99)
        next_qty = _clamp(cur_qty + _clamp(as_int(qty, 1), 1, 99), 1, 99)
        if next_qty != cur_qty:
            item["qty"] = next_qty
            changed = True
        if tags is not None:
            item["tags"] = tags
            changed = True
        if notes:
            item["notes"] = str(notes).strip()[:200]
            changed = True
        if item_def is not None:
            normalized_item_def = _normalize_inventory_def(item_def)
            if normalized_item_def and str(item.get("def") or "") != normalized_item_def:
                item["def"] = normalized_item_def
                changed = True
        inv[idx] = item
    else:
        normalized = _normalize_inventory_item(
            {
                "id": _slugify_inventory_id("", name, len(inv) + 1),
                "name": name,
                "qty": qty,
                "tags": tags,
                "notes": notes or "",
                "def": item_def,
            },
            len(inv) + 1,
        )
        if normalized:
            inv.append(normalized)
            changed = True
    if changed:
        ch.stats = _put_character_inventory_into_stats(ch.stats, inv)
    return changed


def _inv_remove_on_character(ch: Character, *, name: str, qty: int) -> tuple[bool, int, Optional[dict[str, Any]]]:
    inv_raw = _character_inventory_from_stats(ch.stats)
    inv: list[dict[str, Any]] = [dict(x) for x in inv_raw if isinstance(x, dict)]
    idx = _find_inventory_item_index(inv, name)
    if idx is None:
        return False, 0, None
    item = dict(inv[idx])
    cur_qty = _clamp(as_int(item.get("qty"), 1), 1, 99)
    take = min(cur_qty, _clamp(as_int(qty, 1), 1, 99))
    next_qty = cur_qty - take
    removed_item_id = str(item.get("id") or "").strip().lower()
    if next_qty <= 0:
        inv.pop(idx)
    else:
        item["qty"] = next_qty
        inv[idx] = item
    stats_next = _put_character_inventory_into_stats(ch.stats, inv)
    if next_qty <= 0 and removed_item_id:
        equip_map = _character_equip_from_stats(stats_next)
        equip_changed = False
        for slot_key, equipped_item_id in list(equip_map.items()):
            if str(equipped_item_id or "").strip().lower() == removed_item_id:
                equip_map.pop(slot_key, None)
                equip_changed = True
        if equip_changed:
            stats_next = _put_character_equip_into_stats(stats_next, equip_map)
    ch.stats = stats_next
    removed_item = dict(item)
    removed_item["qty"] = take
    return True, take, removed_item


def _inventory_state_line(ch: Optional[Character]) -> str:
    if not ch:
        return "пусто"
    inv = _character_inventory_from_stats(ch.stats)
    parts: list[str] = []
    for item in inv:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        qty = _clamp(as_int(item.get("qty"), 1), 1, 99)
        parts.append(f"{name} x{qty}" if qty > 1 else name)
        if len(parts) >= 20:
            break
    return "; ".join(parts) if parts else "пусто"


def _inventory_prompt_line(stats_raw: Any, max_len: int = 150) -> str:
    inv = _character_inventory_from_stats(stats_raw)
    if not inv:
        return ""
    parts: list[str] = []
    for item in inv:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        qty = _clamp(as_int(item.get("qty"), 1), 1, 99)
        parts.append(f"{name} x{qty}" if qty > 1 else name)
        if len(parts) >= 12:
            break
    if not parts:
        return ""
    return _short_text("inventory: " + "; ".join(parts), max(120, min(160, max_len)))
