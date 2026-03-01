from __future__ import annotations

from typing import Any

from app.combat.state import upsert_pc
from app.rules.derived_stats import compute_ac


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def sync_pcs_from_chars(session_id: str, chars_by_uid: dict[int, Any]) -> None:
    for uid, ch in (chars_by_uid or {}).items():
        name_raw = getattr(ch, "name", "")
        name = str(name_raw).strip() if str(name_raw or "").strip() else f"PC {uid}"

        hp = _safe_int(getattr(ch, "hp", 0), 0)
        hp_max_raw = _safe_int(getattr(ch, "hp_max", hp), hp)
        hp_max = max(0, hp_max_raw)
        hp = _clamp(hp, 0, hp_max)

        stats = getattr(ch, "stats", {})
        dex_default = 50
        if isinstance(stats, dict):
            inventory = stats.get("_inv", [])
            if not isinstance(inventory, list):
                inventory = []
            equip_map = stats.get("_equip", {})
            if not isinstance(equip_map, dict):
                equip_map = {}
            ac = compute_ac(stats=stats, inventory=inventory, equip_map=equip_map)
        else:
            dex = dex_default
            ac = _clamp(12 + int((dex - 50) // 20), 10, 18)

        upsert_pc(
            session_id,
            pc_key=f"pc_{uid}",
            name=name,
            hp=hp,
            hp_max=hp_max,
            ac=ac,
            initiative=0,
        )
