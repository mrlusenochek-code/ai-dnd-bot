import pytest

from app.web.ws_checks import _skill_bonus_from_rank_and_level


@pytest.mark.parametrize(
    ("level", "rank", "expected"),
    [
        (1, 0, 0),
        (1, 1, 2),
        (5, 1, 3),
        (5, 4, 6),
    ],
)
def test_skill_bonus_from_rank_and_level_uses_phb_proficiency(level: int, rank: int, expected: int) -> None:
    assert _skill_bonus_from_rank_and_level(rank, level) == expected
