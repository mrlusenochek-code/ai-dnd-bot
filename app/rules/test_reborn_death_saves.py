from __future__ import annotations

from types import SimpleNamespace

from app.combat.live_actions import _has_death_save_advantage


def test_reborn_deathless_nature_grants_death_save_advantage() -> None:
    actor = SimpleNamespace(
        side="pc",
        race_features={
            "features": {
                "deathless_nature": {
                    "type": "deathless_nature",
                    "advantage_on_saves": ["disease", "poisoned", "death_saves"],
                }
            },
            "saves": {"advantage_conditions": ["death_saves"]},
        },
    )

    assert _has_death_save_advantage(actor) is True


def test_non_reborn_has_no_death_save_advantage() -> None:
    actor = SimpleNamespace(side="pc", race_features={"features": {}, "saves": {}})
    assert _has_death_save_advantage(actor) is False
