from __future__ import annotations

from types import SimpleNamespace

from app.combat.live_actions import _has_magical_sleep_immunity


def test_reborn_deathless_nature_grants_magical_sleep_immunity() -> None:
    actor = SimpleNamespace(
        race_features={
            "features": {
                "deathless_nature": {
                    "type": "deathless_nature",
                    "cannot_be_magically_slept": True,
                    "no_need": ["eat", "drink", "breathe", "sleep"],
                }
            },
            "immunities": {"conditions": ["magic_sleep"]},
            "needs": {"no_need": ["eat", "drink", "breathe", "sleep"]},
            "runtime": {},
        }
    )

    assert _has_magical_sleep_immunity(actor) is True
    assert set(actor.race_features["needs"]["no_need"]) == {"eat", "drink", "breathe", "sleep"}


def test_reborn_uses_same_magical_sleep_guard_as_existing_traits() -> None:
    actor = SimpleNamespace(race_features={"features": {}, "immunities": {"conditions": []}, "runtime": {}})
    assert _has_magical_sleep_immunity(actor) is False
