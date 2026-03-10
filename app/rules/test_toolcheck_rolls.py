from __future__ import annotations

from app.web.check_engine import build_check_result, roll_check
from app.web import ws_handlers


class _FixedRng:
    def __init__(self, values: list[int]) -> None:
        self._values = list(values)

    def randint(self, _a: int, _b: int) -> int:
        return self._values.pop(0)


def test_toolcheck_normal_roll_uses_single_d20_and_dc() -> None:
    rng = _FixedRng([14])
    roll_a, roll_b, roll = roll_check("normal", rng=rng)
    result = build_check_result(
        {"actor_uid": 1, "kind": "tool", "name": "thieves_tools", "dc": 12, "mode": "normal"},
        mod=0,
        roll_a=roll_a,
        roll_b=roll_b,
        roll=roll,
    )

    assert result["kind"] == "tool"
    assert result["roll"] == 14
    assert result["mod"] == 0
    assert result["total"] == 14
    assert result["success"] is True


def test_toolcheck_advantage_picks_higher_roll() -> None:
    rng = _FixedRng([7, 15])
    roll_a, roll_b, roll = roll_check("advantage", rng=rng)

    assert (roll_a, roll_b, roll) == (7, 15, 15)
    assert ws_handlers._format_d20_roll("advantage", roll_a, roll_b, roll) == "adv d20(7, 15) -> 15"


def test_toolcheck_disadvantage_picks_lower_roll_and_fails_dc() -> None:
    rng = _FixedRng([17, 4])
    roll_a, roll_b, roll = roll_check("disadvantage", rng=rng)
    result = build_check_result(
        {"actor_uid": 1, "kind": "tool", "name": "alchemists_supplies", "dc": 10, "mode": "disadvantage"},
        mod=0,
        roll_a=roll_a,
        roll_b=roll_b,
        roll=roll,
    )

    assert (roll_a, roll_b, roll) == (17, 4, 4)
    assert result["total"] == 4
    assert result["success"] is False
    assert ws_handlers._format_d20_roll("disadvantage", roll_a, roll_b, roll) == "dis d20(17, 4) -> 4"
