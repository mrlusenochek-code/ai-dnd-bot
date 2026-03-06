from __future__ import annotations

from typing import Any

from app.combat.state import upsert_pc
from app.rules.derived_stats import compute_ac
from app.rules.phb_math import ability_mod_from_stat100


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
        level = _safe_int(getattr(ch, "level", 1), 1)
        speed = _safe_int(getattr(ch, "speed_ft", 30), 30)

        stats = getattr(ch, "stats", {})
        dex_default = 50
        stats_payload: dict[str, int] | None = None
        inventory_payload: list[dict[str, Any]] | None = None
        equip_payload: dict[str, str] | None = None
        if isinstance(stats, dict):
            inventory_raw = stats.get("_inv", [])
            inventory = inventory_raw if isinstance(inventory_raw, list) else []
            inventory_payload = inventory if isinstance(inventory_raw, list) else None
            equip_raw = stats.get("_equip", {})
            equip_map = equip_raw if isinstance(equip_raw, dict) else {}
            equip_payload = equip_raw if isinstance(equip_raw, dict) else None

            stats_payload = {}
            for key in ("str", "dex", "con", "int", "wis", "cha"):
                value = stats.get(key)
                if isinstance(value, int):
                    stats_payload[key] = value

            ac = compute_ac(stats=stats, inventory=inventory, equip_map=equip_map)
        else:
            dex = dex_default
            ac = 10 + ability_mod_from_stat100(dex)

        upsert_pc(
            session_id,
            pc_key=f"pc_{uid}",
            name=name,
            hp=hp,
            hp_max=hp_max,
            ac=ac,
            initiative=0,
            level=level,
            speed_ft=speed,
            stats=stats_payload,
            inventory=inventory_payload,
            equip=equip_payload,
        )
