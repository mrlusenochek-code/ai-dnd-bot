from app.rules.phb_rest import sync_hit_dice_on_level_change


def test_sync_hit_dice_level_up_adds_one_when_pool_empty() -> None:
    hd_max, hd_rem = sync_hit_dice_on_level_change(
        old_level=1,
        new_level=2,
        hit_dice_max=1,
        hit_dice_remaining=0,
    )
    assert hd_max == 2
    assert hd_rem == 1


def test_sync_hit_dice_level_up_adds_one_when_pool_has_one() -> None:
    hd_max, hd_rem = sync_hit_dice_on_level_change(
        old_level=1,
        new_level=2,
        hit_dice_max=1,
        hit_dice_remaining=1,
    )
    assert hd_max == 2
    assert hd_rem == 2


def test_sync_hit_dice_same_level_keeps_values() -> None:
    hd_max, hd_rem = sync_hit_dice_on_level_change(
        old_level=5,
        new_level=5,
        hit_dice_max=5,
        hit_dice_remaining=3,
    )
    assert hd_max == 5
    assert hd_rem == 3


def test_sync_hit_dice_level_down_clamps_remaining() -> None:
    hd_max, hd_rem = sync_hit_dice_on_level_change(
        old_level=5,
        new_level=3,
        hit_dice_max=5,
        hit_dice_remaining=5,
    )
    assert hd_max == 3
    assert hd_rem == 3


def test_sync_hit_dice_new_level_zero_normalizes_to_one() -> None:
    hd_max, hd_rem = sync_hit_dice_on_level_change(
        old_level=1,
        new_level=0,
        hit_dice_max=1,
        hit_dice_remaining=1,
    )
    assert hd_max == 1
    assert hd_rem == 1
