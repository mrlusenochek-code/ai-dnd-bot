from dataclasses import dataclass
from typing import Any

from app.web import server


@dataclass
class _FakeCharacter:
    stats: dict[str, Any]


def test_inv_add_on_character_keeps_def_on_stack_update() -> None:
    ch = _FakeCharacter(stats={})

    changed_first = server._inv_add_on_character(ch, name="Кинжал", qty=1, item_def="dagger")
    assert changed_first is True

    inv_first = server._character_inventory_from_stats(ch.stats)
    assert len(inv_first) == 1
    assert inv_first[0]["def"] == "dagger"
    assert inv_first[0]["qty"] == 1

    changed_second = server._inv_add_on_character(ch, name="Кинжал", qty=2, item_def="dagger")
    assert changed_second is True

    inv_second = server._character_inventory_from_stats(ch.stats)
    assert len(inv_second) == 1
    assert inv_second[0]["def"] == "dagger"
    assert inv_second[0]["qty"] == 3
