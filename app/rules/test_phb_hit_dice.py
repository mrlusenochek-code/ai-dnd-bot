import random

from app.rules.phb_rest import (
    apply_short_rest_spend_hd,
    long_rest_recover_hit_dice,
    roll_hit_die,
)


def test_roll_hit_die_uses_die_and_con_mod_with_min_zero() -> None:
    rng = random.Random(0)
    assert roll_hit_die(hit_die=8, con_mod=2, rng=rng) == 9

    rng = random.Random(0)
    assert roll_hit_die(hit_die=6, con_mod=-10, rng=rng) == 0


def test_apply_short_rest_spend_hd_spends_one_and_heals_without_overflow() -> None:
    rng = random.Random(0)
    hp_after, remaining_after, heals = apply_short_rest_spend_hd(
        hp=5,
        hp_max=10,
        hit_die=8,
        hit_dice_remaining=3,
        con_mod=0,
        spend=1,
        rng=rng,
    )
    assert remaining_after == 2
    assert 5 < hp_after <= 10
    assert heals == [7]


def test_apply_short_rest_spend_hd_caps_hp_to_hp_max() -> None:
    rng = random.Random(0)
    hp_after, remaining_after, heals = apply_short_rest_spend_hd(
        hp=9,
        hp_max=10,
        hit_die=8,
        hit_dice_remaining=2,
        con_mod=2,
        spend=2,
        rng=rng,
    )
    assert hp_after == 10
    assert remaining_after == 0
    assert heals == [9, 9]


def test_long_rest_recover_hit_dice_minimum_one_and_floor_half() -> None:
    assert long_rest_recover_hit_dice(hit_dice_max=1, hit_dice_remaining=0) == 1
    assert long_rest_recover_hit_dice(hit_dice_max=5, hit_dice_remaining=0) == 2
    assert long_rest_recover_hit_dice(hit_dice_max=6, hit_dice_remaining=1) == 4
