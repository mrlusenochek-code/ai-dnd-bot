from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.web import ws_handlers


def test_build_player_action_position_payload_contains_zone_and_map_positions() -> None:
    player_id = uuid.uuid4()
    before = {
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Старый подвал",
    }
    after = {
        "map_level": "region",
        "node_type": "zone",
        "node_id": "улица у таверны",
        "label": "улица у таверны",
    }
    sess = SimpleNamespace(settings={"map_positions": {str(player_id): before}})

    payload = ws_handlers._build_player_action_position_payload(
        sess,
        player_id,
        zone_after="улица у таверны",
        map_position_after=after,
    )

    assert payload == {
        "zone_before": "Старый подвал",
        "zone_after": "улица у таверны",
        "map_position_before": {
            "v": 1,
            "map_level": "district",
            "node_type": "landmark",
            "node_id": "old-tavern-cellar",
            "label": "Старый подвал",
        },
        "map_position_after": after,
    }


def test_build_player_action_position_payload_uses_position_context_helper(monkeypatch) -> None:
    player_id = uuid.uuid4()
    calls: list[uuid.UUID] = []

    def fake_context(_sess, pid):
        calls.append(pid)
        return {
            "zone_label": "Старый подвал",
            "map_position": {
                "v": 1,
                "map_level": "district",
                "node_type": "landmark",
                "node_id": "old-tavern-cellar",
                "label": "Старый подвал",
            },
        }

    monkeypatch.setattr(ws_handlers, "_get_player_position_context", fake_context)
    sess = SimpleNamespace(settings={})

    payload = ws_handlers._build_player_action_position_payload(sess, player_id)

    assert calls == [player_id]
    assert payload["zone_before"] == "Старый подвал"
    assert payload["zone_after"] == "Старый подвал"
    assert payload["map_position_before"]["node_id"] == "old-tavern-cellar"
