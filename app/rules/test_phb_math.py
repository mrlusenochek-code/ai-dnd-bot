import pytest

from app.rules.phb_math import ability_mod_from_stat100


@pytest.mark.parametrize(
    ("stat", "expected_mod"),
    [
        (0, -4),
        (30, -2),
        (50, 0),
        (70, 2),
        (100, 5),
    ],
)
def test_ability_mod_from_stat100_phb_mapping(stat: int, expected_mod: int) -> None:
    assert ability_mod_from_stat100(stat) == expected_mod
