import random

from app.rules.loot_tables import roll_loot


def test_roll_loot_band1_is_deterministic_with_seeded_rng() -> None:
    rng = random.Random(123)

    first = roll_loot("band1", rng=rng)
    second = roll_loot("band1", rng=rng)

    assert first == [
        {"def": "dagger", "qty": 1},
        {"def": "longsword", "qty": 1},
    ]
    assert second == [
        {"def": "longsword", "qty": 1},
    ]
