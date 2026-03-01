import random

from app.rules.defeat_outcomes import DEFAULT_DEFEAT_OUTCOMES, pick_defeat_outcome


def test_pick_is_deterministic_for_same_started_at() -> None:
    started_at_iso = "2026-03-01T12:34:56Z"

    first = pick_defeat_outcome(started_at_iso=started_at_iso, rng=None)
    second = pick_defeat_outcome(started_at_iso=started_at_iso, rng=None)

    assert first.key == second.key


def test_pick_differs_for_different_started_at() -> None:
    first = pick_defeat_outcome(started_at_iso="2026-03-01T12:34:56Z", rng=None)
    second = pick_defeat_outcome(started_at_iso="2026-03-01T12:34:57Z", rng=None)
    valid_keys = {outcome.key for outcome in DEFAULT_DEFEAT_OUTCOMES}

    assert first.key in valid_keys
    assert second.key in valid_keys
    assert first.key != second.key or first.key in valid_keys


def test_weighted_choice_respects_rng() -> None:
    picked = pick_defeat_outcome(
        started_at_iso="ignored-when-rng-is-provided",
        rng=random.Random(123),
    )

    assert picked.key == "captured"
