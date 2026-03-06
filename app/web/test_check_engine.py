import random

from app.web.check_engine import build_check_result, roll_check


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


def test_build_check_result_success_by_dc() -> None:
    check = {"actor_uid": 7, "kind": "skill", "name": "perception", "dc": 15, "mode": "normal"}

    success = build_check_result(check, mod=3, roll_a=14, roll_b=None, roll=14)
    assert success["total"] == 17
    assert success["success"] is True

    fail = build_check_result(check, mod=3, roll_a=10, roll_b=None, roll=10)
    assert fail["total"] == 13
    assert fail["success"] is False

    no_dc = build_check_result({**check, "dc": 0}, mod=3, roll_a=1, roll_b=None, roll=1)
    assert no_dc["success"] is True


def test_build_check_result_includes_roll_pair_when_present() -> None:
    res = build_check_result(
        {"actor_uid": 1, "kind": "skill", "name": "stealth", "dc": 12, "mode": "advantage"},
        mod=2,
        roll_a=5,
        roll_b=17,
        roll=17,
    )
    assert res["roll_a"] == 5
    assert res["roll_b"] == 17
