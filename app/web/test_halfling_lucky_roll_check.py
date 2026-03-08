from __future__ import annotations

from app.web.check_engine import roll_check


class _RngMock:
    def __init__(self, values: list[int]) -> None:
        self._values = list(values)

    def randint(self, _a: int, _b: int) -> int:
        if not self._values:
            raise AssertionError("No more RNG values")
        return self._values.pop(0)


def test_roll_check_lucky_normal_rerolls_one() -> None:
    rng = _RngMock([1, 13])
    ra, rb, roll = roll_check("normal", rng=rng, reroll_ones=True)
    assert ra == 13
    assert rb is None
    assert roll == 13


def test_roll_check_lucky_disadvantage_rerolls_selected_one() -> None:
    rng = _RngMock([1, 20, 15])
    ra, rb, roll = roll_check("disadvantage", rng=rng, reroll_ones=True)
    assert rb is not None
    assert roll != 1
    assert roll == 15
