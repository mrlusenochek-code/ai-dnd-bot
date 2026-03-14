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


def test_infer_action_position_update_returns_zone_move_via_canonical_transition() -> None:
    current_position = {
        "v": 1,
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Старый подвал",
    }

    next_zone, next_map_position = ws_handlers._infer_action_position_update(
        current_position,
        "Старый подвал",
        "выхожу на улицу",
    )

    assert next_zone == "улица у таверны"
    assert next_map_position == {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": "улица у таверны",
        "label": "улица у таверны",
    }


def test_infer_action_position_update_returns_landmark_node_for_landmark_move() -> None:
    current_position = {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": "центр города",
        "label": "центр города",
    }

    next_zone, next_map_position = ws_handlers._infer_action_position_update(
        current_position,
        "центр города",
        "иду к воротам",
    )

    assert next_zone == "ворота"
    assert next_map_position == {
        "v": 1,
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "ворота",
        "label": "ворота",
    }


def test_apply_player_action_position_update_updates_structured_and_legacy_state() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "map_positions": {
                str(player_id): {
                    "map_level": "district",
                    "node_type": "landmark",
                    "node_id": "old-tavern-cellar",
                    "label": "Старый подвал",
                }
            }
        }
    )

    payload = ws_handlers._apply_player_action_position_update(sess, player_id, "выхожу на улицу")

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
        "map_position_after": {
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "улица у таверны",
            "label": "улица у таверны",
        },
    }
    assert sess.settings["map_positions"][str(player_id)] == payload["map_position_after"]
    assert sess.settings["pc_positions"][str(player_id)] == "улица у таверны"


def test_apply_player_action_position_update_preserves_narrative_zone_inference() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "map_positions": {
                str(player_id): {
                    "map_level": "region",
                    "node_type": "zone",
                    "node_id": "таверна",
                    "label": "таверна",
                }
            }
        }
    )

    payload = ws_handlers._apply_player_action_position_update(sess, player_id, "захожу в замок")

    assert payload["zone_before"] == "таверна"
    assert payload["zone_after"] == "замок"
    assert payload["map_position_after"] == {
        "v": 1,
        "map_level": "interior",
        "node_type": "interior_entry",
        "node_id": "замок",
        "label": "замок",
    }


def test_apply_player_action_position_update_emits_structured_landmark_payload() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "map_positions": {
                str(player_id): {
                    "map_level": "region",
                    "node_type": "zone",
                    "node_id": "центр города",
                    "label": "центр города",
                }
            }
        }
    )

    payload = ws_handlers._apply_player_action_position_update(sess, player_id, "иду к воротам")

    assert payload["zone_before"] == "центр города"
    assert payload["zone_after"] == "ворота"
    assert payload["map_position_before"] == {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": "центр города",
        "label": "центр города",
    }
    assert payload["map_position_after"] == {
        "v": 1,
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "ворота",
        "label": "ворота",
    }
    assert sess.settings["pc_positions"][str(player_id)] == "ворота"
