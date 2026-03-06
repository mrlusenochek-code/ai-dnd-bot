import random

from app.web.check_engine import roll_check


def test_roll_check_normal_deterministic() -> None:
    rng = random.Random(0)
    a, b, r = roll_check("normal", rng=rng)
    assert (a, b, r) == (13, None, 13)


def test_roll_check_advantage_deterministic() -> None:
    rng = random.Random(0)
    a, b, r = roll_check("advantage", rng=rng)
    assert (a, b, r) == (13, 14, 14)


def test_roll_check_disadvantage_deterministic() -> None:
    rng = random.Random(0)
    a, b, r = roll_check("disadvantage", rng=rng)
    assert (a, b, r) == (13, 14, 13)
