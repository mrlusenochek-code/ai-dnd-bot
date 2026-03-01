from dataclasses import dataclass
from typing import Any

from app.web import server


@dataclass
class _FakeCharacter:
    hp: int
    is_alive: bool
    stats: dict[str, Any]


def test_compute_robbed_removals_is_deterministic_and_skips_quest_items() -> None:
    inv = [
        {"id": "zeta", "name": "Zeta item", "qty": 1, "def": "longsword"},
        {"id": "alpha", "name": "Quest key", "qty": 1, "def": "quest_key"},
        {"id": "beta", "name": "Beta item", "qty": 1, "def": "dagger"},
        {"id": "gamma", "name": "No def item", "qty": 1},
    ]

    removals_first = server._compute_robbed_removals(inv, max_take=2)
    removals_second = server._compute_robbed_removals(inv, max_take=2)

    assert removals_first == ["beta", "gamma"]
    assert removals_second == removals_first


def test_revive_characters_to_1hp_only_for_zero_or_negative_hp() -> None:
    alive = _FakeCharacter(hp=5, is_alive=True, stats={})
    downed = _FakeCharacter(hp=0, is_alive=False, stats={})
    dead = _FakeCharacter(hp=-3, is_alive=False, stats={})

    changed = server._revive_characters_to_1hp([alive, downed, dead])

    assert changed is True
    assert alive.hp == 5
    assert alive.is_alive is True
    assert downed.hp == 1
    assert downed.is_alive is True
    assert dead.hp == 1
    assert dead.is_alive is True
