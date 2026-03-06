from __future__ import annotations

import random


def _clamp_int(v: int, low: int, high: int) -> int:
    return max(low, min(high, int(v)))


def long_rest_recover_hit_dice(hit_dice_max: int, hit_dice_remaining: int) -> int:
    hd_max = max(1, int(hit_dice_max))
    hd_remaining = _clamp_int(hit_dice_remaining, 0, hd_max)
    recovered = max(1, hd_max // 2)
    return min(hd_max, hd_remaining + recovered)


def roll_hit_die(hit_die: int, con_mod: int, *, rng: random.Random | None = None) -> int:
    roller = rng or random
    die_size = max(1, int(hit_die))
    raw_roll = int(roller.randint(1, die_size))
    return max(0, raw_roll + int(con_mod))


def apply_short_rest_spend_hd(
    *,
    hp: int,
    hp_max: int,
    hit_die: int,
    hit_dice_remaining: int,
    con_mod: int,
    spend: int,
    rng: random.Random | None = None,
) -> tuple[int, int, list[int]]:
    hp_max_norm = max(1, int(hp_max))
    hp_after = _clamp_int(hp, 0, hp_max_norm)
    hd_remaining = max(0, int(hit_dice_remaining))
    spend_norm = _clamp_int(spend, 0, hd_remaining)
    heals: list[int] = []

    for _ in range(spend_norm):
        heal = roll_hit_die(hit_die=hit_die, con_mod=con_mod, rng=rng)
        heals.append(heal)
        hp_after = min(hp_max_norm, hp_after + heal)

    return hp_after, hd_remaining - spend_norm, heals


def apply_long_rest(hp: int, hp_max: int, sta: int, sta_max: int) -> tuple[int, int]:
    hp_max_norm = max(1, int(hp_max))
    sta_max_norm = max(0, int(sta_max))
    return hp_max_norm, sta_max_norm


def apply_short_rest(hp: int, hp_max: int, sta: int, sta_max: int) -> tuple[int, int]:
    hp_max_norm = max(1, int(hp_max))
    hp_norm = max(0, min(int(hp), hp_max_norm))
    sta_norm = max(0, int(sta_max))
    return hp_norm, sta_norm
