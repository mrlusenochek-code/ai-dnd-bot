from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class LootDrop:
    item_def: str
    chance: float
    qty: int = 1


@dataclass(frozen=True)
class LootTable:
    drops: tuple[LootDrop, ...]


DEFAULT_LOOT_TABLE = LootTable(
    drops=(
        LootDrop(item_def="healing_potion", chance=0.30, qty=1),
        LootDrop(item_def="silver_ring", chance=0.15, qty=1),
        LootDrop(item_def="quest_key", chance=0.60, qty=1),
    )
)


ENEMY_LOOT_TABLES: dict[str, LootTable] = {
    "band1": LootTable(
        drops=(
            LootDrop(item_def="dagger", chance=0.45, qty=1),
            LootDrop(item_def="longsword", chance=0.35, qty=1),
            LootDrop(item_def="healing_potion", chance=0.40, qty=1),
            LootDrop(item_def="silver_ring", chance=0.10, qty=1),
        )
    )
}


def roll_loot(enemy_id: str, rng: Random | None = None) -> list[dict]:
    random_source = rng or Random()
    table = ENEMY_LOOT_TABLES.get(enemy_id, DEFAULT_LOOT_TABLE)
    loot: list[dict] = []

    for drop in table.drops:
        if random_source.random() < drop.chance:
            loot.append({"def": drop.item_def, "qty": drop.qty})

    return loot
