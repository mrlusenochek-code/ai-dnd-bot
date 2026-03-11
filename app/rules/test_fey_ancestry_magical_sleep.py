from __future__ import annotations

from types import SimpleNamespace

from app.combat.live_actions import _has_magical_sleep_immunity


def test_fey_ancestry_grants_magical_sleep_immunity() -> None:
    actor = SimpleNamespace(
        race_features={
            "features": {
                "fey_ancestry": {
                    "type": "fey_ancestry",
                    "immune_to_magical_sleep": True,
                }
            },
            "immunities": {"conditions": ["magic_sleep"]},
            "runtime": {},
        }
    )

    assert _has_magical_sleep_immunity(actor) is True


def test_actor_without_fey_ancestry_has_no_magical_sleep_immunity() -> None:
    actor = SimpleNamespace(race_features={"features": {}, "immunities": {"conditions": []}, "runtime": {}})
    assert _has_magical_sleep_immunity(actor) is False


def test_warforged_magical_sleep_immunity_uses_same_guard() -> None:
    actor = SimpleNamespace(
        race_features={
            "features": {
                "constructed_resilience": {
                    "cannot_be_magically_slept": True,
                }
            },
            "immunities": {"conditions": ["magic_sleep"]},
            "runtime": {},
        }
    )

    assert _has_magical_sleep_immunity(actor) is True
