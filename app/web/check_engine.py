from __future__ import annotations

import random
from typing import Optional, Protocol

from app.gm import checks as gm_checks


class _Rng(Protocol):
    def randint(self, a: int, b: int) -> int: ...


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
