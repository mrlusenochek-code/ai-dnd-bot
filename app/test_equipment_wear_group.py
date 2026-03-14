import asyncio
import uuid
from dataclasses import dataclass
from typing import Any
from types import SimpleNamespace

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


def test_inventory_transfer_allows_same_structured_position_with_different_labels(monkeypatch) -> None:
    from_player_id = uuid.uuid4()
    to_player_id = uuid.uuid4()
    from_ch = _FakeCharacter(stats=server._put_character_inventory_into_stats({}, [{"name": "Факел", "qty": 1}]))
    to_ch = _FakeCharacter(stats=server._put_character_inventory_into_stats({}, []))
    from_sp = SimpleNamespace(player_id=from_player_id, join_order=1)
    to_sp = SimpleNamespace(player_id=to_player_id, join_order=2)

    async def _fake_load_actor_context(_db, _sess):
        return {
            1: (from_sp, SimpleNamespace(display_name="A")),
            2: (to_sp, SimpleNamespace(display_name="B")),
        }, {1: from_ch, 2: to_ch}, {}

    monkeypatch.setattr(server, "_load_actor_context", _fake_load_actor_context)

    sess = _FakeSession(
        settings={
            "map_positions": {
                str(from_player_id): {
                    "map_level": "district",
                    "node_type": "landmark",
                    "node_id": "old-tavern-cellar",
                    "label": "Старый подвал",
                },
                str(to_player_id): {
                    "map_level": "district",
                    "node_type": "landmark",
                    "node_id": "old-tavern-cellar",
                    "label": "Подвал таверны",
                },
            }
        }
    )
    commands = [{"op": "transfer", "from_uid": 1, "to_uid": 2, "name": "Факел", "qty": 1}]

    asyncio.run(server._apply_inventory_machine_commands(None, sess, commands))

    from_inventory = server._character_inventory_from_stats(from_ch.stats)
    to_inventory = server._character_inventory_from_stats(to_ch.stats)
    assert from_inventory == []
    assert len(to_inventory) == 1
    assert to_inventory[0]["name"] == "Факел"
    assert int(to_inventory[0]["qty"]) == 1
