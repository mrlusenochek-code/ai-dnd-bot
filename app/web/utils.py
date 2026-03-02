import re
from typing import Any


def as_int(s: Any, default: int = 0) -> int:
    try:
        return int(s)
    except Exception:
        return default


def _clamp(n: int, low: int, high: int) -> int:
    return max(low, min(high, n))


def _short_text(text: str, limit: int) -> str:
    txt = str(text or "").strip()
    if len(txt) <= limit:
        return txt
    return txt[:limit].rstrip() + "..."


def _slugify_inventory_id(raw: Any, fallback_name: str, index: int) -> str:
    src = str(raw or fallback_name or "").strip().lower()
    src = re.sub(r"[^a-z0-9]+", "-", src)
    src = src.strip("-")
    if src:
        return src[:40]
    return f"item-{max(1, index)}"
