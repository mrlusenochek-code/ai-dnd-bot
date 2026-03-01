import asyncio
from dataclasses import dataclass
from typing import Any

from app.web import server


@dataclass
class _FakeCharacter:
    stats: dict[str, Any]


@dataclass
class _FakeSession:
    settings: dict[str, Any]


def test_equip_blocks_same_wear_group(monkeypatch) -> None:
    leather_id = "leather_item"
    chain_id = "chain_item"
    inv = [
        {"id": leather_id, "name": "Кожаная броня", "def": "leather_armor", "qty": 1},
        {"id": chain_id, "name": "Кольчуга", "def": "chain_mail", "qty": 1},
    ]
    stats = server._put_character_inventory_into_stats({}, inv)
    stats = server._put_character_equip_into_stats(stats, {})
    ch = _FakeCharacter(stats=stats)

    async def _fake_load_actor_context(_db, _sess):
        return {}, {1: ch}, {}

    monkeypatch.setattr(server, "_load_actor_context", _fake_load_actor_context)

    sess = _FakeSession(settings={})
    commands = [
        {"op": "equip", "uid": 1, "name": "Кожаная броня", "slot": "body"},
        {"op": "equip", "uid": 1, "name": "Кольчуга", "slot": "body"},
    ]
    asyncio.run(server._apply_inventory_machine_commands(None, sess, commands))

    equip_map = server._character_equip_from_stats(ch.stats)
    assert equip_map.get("body") == leather_id
