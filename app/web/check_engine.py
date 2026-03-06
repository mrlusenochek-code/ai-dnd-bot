from __future__ import annotations

import random
from typing import Any, Optional, Protocol

from app.gm import checks as gm_checks


class _Rng(Protocol):
    def randint(self, a: int, b: int) -> int: ...


def _as_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def roll_check(mode: str, *, rng: Optional[_Rng] = None) -> tuple[int, Optional[int], int]:
    """
    PHB: d20 roll with (dis)advantage.
    Returns: (roll_a, roll_b_or_none, chosen_roll)
    """
    r = rng or random
    normalized = gm_checks._normalize_check_mode(mode)

    if normalized == "advantage":
        r1 = r.randint(1, 20)
        r2 = r.randint(1, 20)
        return r1, r2, max(r1, r2)

    if normalized == "disadvantage":
        r1 = r.randint(1, 20)
        r2 = r.randint(1, 20)
        return r1, r2, min(r1, r2)

    x = r.randint(1, 20)
    return x, None, x


def build_check_result(
    check: dict[str, Any],
    *,
    mod: int,
    roll_a: int,
    roll_b: Optional[int],
    roll: int,
) -> dict[str, Any]:
    dc = max(0, _as_int(check.get("dc"), 0))
    total = roll + mod
    name = gm_checks._normalize_check_name(check.get("name"))
    result: dict[str, Any] = {
        "actor_uid": _as_int(check.get("actor_uid"), 0),
        "kind": gm_checks._check_kind_for_name(check.get("kind"), name),
        "name": name,
        "dc": dc,
        "roll": roll,
        "mod": mod,
        "total": total,
        "success": total >= dc if dc > 0 else True,
        "mode": gm_checks._normalize_check_mode(check.get("mode")),
    }
    if roll_b is not None:
        result["roll_a"] = roll_a
        result["roll_b"] = roll_b
    if check.get("reason"):
        result["reason"] = str(check.get("reason"))
    return result
