from __future__ import annotations


def apply_long_rest(hp: int, hp_max: int, sta: int, sta_max: int) -> tuple[int, int]:
    hp_max_norm = max(1, int(hp_max))
    sta_max_norm = max(0, int(sta_max))
    return hp_max_norm, sta_max_norm


def apply_short_rest(hp: int, hp_max: int, sta: int, sta_max: int) -> tuple[int, int]:
    hp_max_norm = max(1, int(hp_max))
    hp_norm = max(0, min(int(hp), hp_max_norm))
    sta_norm = max(0, int(sta_max))
    return hp_norm, sta_norm
