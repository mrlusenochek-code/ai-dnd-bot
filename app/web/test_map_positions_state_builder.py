from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.web import state_builder


class _FakeScalarResult:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)


class _FakeExecuteResult:
    def __init__(self, items):
        self._items = list(items)

    def scalars(self):
        return _FakeScalarResult(self._items)


class _FakeDb:
    def __init__(self, responses):
        self._responses = list(responses)

    async def execute(self, _query):
        if not self._responses:
            raise AssertionError("unexpected execute call")
        return _FakeExecuteResult(self._responses.pop(0))


def test_build_state_includes_legacy_and_structured_positions(monkeypatch) -> None:
    player_id = uuid.uuid4()
    session_id = uuid.uuid4()
    char_id = uuid.uuid4()
    structured_position = {
        "v": 1,
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Старый подвал",
    }
    group_state = {
        "main": {
            "group_id": "main",
            "player_ids": [str(player_id)],
            "movement_mode": "normal",
            "current_map_position": structured_position,
            "area_label": "Старый подвал",
            "status": "idle",
        }
    }

    sess = SimpleNamespace(
        id=session_id,
        title="Campaign",
        is_active=False,
        is_paused=False,
        turn_index=0,
        current_player_id=None,
        turn_started_at=None,
        settings={},
    )
    sp = SimpleNamespace(player_id=player_id, join_order=1, is_admin=False, is_active=True)
    player = SimpleNamespace(id=player_id, display_name="Alice", web_user_id=42, telegram_user_id=None)
    char = SimpleNamespace(
        id=char_id,
        session_id=session_id,
        player_id=player_id,
        name="Рин",
        level=2,
        stats={},
        hp=10,
        hp_max=12,
        sta=5,
        sta_max=6,
    )

    async def fake_list_session_players(_db, _sess, active_only=False):
        assert active_only is False
        return [sp]

    monkeypatch.setattr(state_builder, "list_session_players", fake_list_session_players)
    monkeypatch.setattr(state_builder, "_get_kicked", lambda _sess: set())
    monkeypatch.setattr(state_builder, "_char_to_payload", lambda _char: {"name": _char.name} if _char else None)
    monkeypatch.setattr(state_builder, "_level_progress_payload", lambda _char: {"level": _char.level})
    monkeypatch.setattr(state_builder, "_skills_payload_for_character", lambda _char, _skills: [])
    monkeypatch.setattr(state_builder, "_player_uid", lambda _player: _player.web_user_id)
    monkeypatch.setattr(state_builder, "_get_ready_map", lambda _sess: {str(player_id): True})
    monkeypatch.setattr(state_builder, "_get_init_map", lambda _sess: {str(player_id): 7})
    monkeypatch.setattr(state_builder, "_get_last_seen_map", lambda _sess: {str(player_id): "2026-03-14T00:00:00"})
    monkeypatch.setattr(state_builder, "_initiative_fixed", lambda _sess: False)
    monkeypatch.setattr(state_builder, "_is_free_turns", lambda _sess: False)
    monkeypatch.setattr(state_builder, "_get_phase", lambda _sess: "turns")
    monkeypatch.setattr(state_builder, "_get_round_actions", lambda _sess: {})
    monkeypatch.setattr(state_builder, "_ready_active_players", lambda _sess, active_sps: active_sps)
    monkeypatch.setattr(state_builder, "_get_group_states", lambda _sess, _player_ids=None: group_state)
    monkeypatch.setattr(state_builder, "_get_pc_positions", lambda _sess: {str(player_id): "Старый подвал"})
    monkeypatch.setattr(state_builder, "_get_map_positions", lambda _sess: {str(player_id): structured_position})
    monkeypatch.setattr(state_builder, "_get_player_group_id", lambda _sess, _player_id, _player_ids=None: "main")
    monkeypatch.setattr(state_builder, "snapshot_combat_state", lambda _session_id: None)

    db = _FakeDb([[player], [char], [], []])
    payload = asyncio.run(state_builder.build_state(db, sess))

    assert payload["game"]["pc_positions"] == {"42": "Старый подвал"}
    assert payload["game"]["map_positions"] == {"42": structured_position}
    assert payload["game"]["groups"] == {
        "main": {
            "group_id": "main",
            "player_ids": [str(player_id)],
            "member_ids": [str(player_id)],
            "member_uids": [42],
            "current_map_position": structured_position,
            "area_label": "Старый подвал",
            "status": "idle",
            "movement_mode": "normal",
            "travel_activity": None,
            "travel_activity_summary": None,
            "wait_summary": None,
            "camp_summary": None,
            "movement_intent_summary": None,
            "travel_state": None,
            "travel_summary": None,
        }
    }
    assert payload["session"]["current_group_id"] is None
    assert payload["players"] == [
        {
            "id": str(player_id),
            "uid": 42,
            "name": "Alice",
            "order": 1,
            "is_admin": False,
            "is_current": False,
            "is_active": True,
            "is_ready": True,
            "initiative": 7,
            "last_seen": "2026-03-14T00:00:00",
            "char": {"name": "Рин", "level_progress": {"level": 2}, "skills": []},
            "has_character": True,
            "group_id": "main",
            "group_area_label": "Старый подвал",
            "group_map_position": structured_position,
            "zone": "Старый подвал",
            "map_position": structured_position,
        }
    ]


def test_build_state_exports_current_player_group_id(monkeypatch) -> None:
    player_id = uuid.uuid4()
    session_id = uuid.uuid4()
    sess = SimpleNamespace(
        id=session_id,
        title="Campaign",
        is_active=True,
        is_paused=False,
        turn_index=1,
        current_player_id=player_id,
        turn_started_at=None,
        settings={},
    )
    sp = SimpleNamespace(player_id=player_id, join_order=1, is_admin=False, is_active=True)
    player = SimpleNamespace(id=player_id, display_name="Alice", web_user_id=42, telegram_user_id=None)
    group_state = {
        "main": {
            "group_id": "main",
            "player_ids": [str(player_id)],
            "movement_mode": "normal",
            "current_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "camp",
                "label": "camp",
            },
            "area_label": "camp",
            "status": "idle",
        }
    }

    async def fake_list_session_players(_db, _sess, active_only=False):
        assert active_only is False
        return [sp]

    monkeypatch.setattr(state_builder, "list_session_players", fake_list_session_players)
    monkeypatch.setattr(state_builder, "_get_kicked", lambda _sess: set())
    monkeypatch.setattr(state_builder, "_char_to_payload", lambda _char: None)
    monkeypatch.setattr(state_builder, "_player_uid", lambda _player: _player.web_user_id if _player else None)
    monkeypatch.setattr(state_builder, "_get_ready_map", lambda _sess: {str(player_id): True})
    monkeypatch.setattr(state_builder, "_get_init_map", lambda _sess: {})
    monkeypatch.setattr(state_builder, "_get_last_seen_map", lambda _sess: {})
    monkeypatch.setattr(state_builder, "_initiative_fixed", lambda _sess: False)
    monkeypatch.setattr(state_builder, "_is_free_turns", lambda _sess: False)
    monkeypatch.setattr(state_builder, "_get_phase", lambda _sess: "turns")
    monkeypatch.setattr(state_builder, "_get_round_actions", lambda _sess: {})
    monkeypatch.setattr(state_builder, "_ready_active_players", lambda _sess, active_sps: active_sps)
    monkeypatch.setattr(state_builder, "_get_group_states", lambda _sess, _player_ids=None: group_state)
    monkeypatch.setattr(state_builder, "_get_pc_positions", lambda _sess: {str(player_id): "camp"})
    monkeypatch.setattr(state_builder, "_get_map_positions", lambda _sess: {str(player_id): group_state["main"]["current_map_position"]})
    monkeypatch.setattr(state_builder, "_get_player_group_id", lambda _sess, _player_id, _player_ids=None: "main")
    monkeypatch.setattr(state_builder, "snapshot_combat_state", lambda _session_id: None)

    db = _FakeDb([[player], [], [], []])
    payload = asyncio.run(state_builder.build_state(db, sess))

    assert payload["session"]["current_group_id"] == "main"


def test_build_state_exports_group_activity_summaries(monkeypatch) -> None:
    player_id = uuid.uuid4()
    session_id = uuid.uuid4()
    group_position = {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": "camp",
        "label": "camp",
    }
    sess = SimpleNamespace(
        id=session_id,
        title="Campaign",
        is_active=False,
        is_paused=False,
        turn_index=0,
        current_player_id=None,
        turn_started_at=None,
        settings={},
    )
    sp = SimpleNamespace(player_id=player_id, join_order=1, is_admin=False, is_active=True)
    player = SimpleNamespace(id=player_id, display_name="Alice", web_user_id=42, telegram_user_id=None)
    group_state = {
        "main": {
            "group_id": "main",
            "player_ids": [str(player_id)],
            "current_map_position": group_position,
            "area_label": "camp",
            "status": "moving",
            "movement_mode": "cautious",
            "travel_activity": {
                "activity": "navigate",
                "assigned_actor_id": str(player_id),
                "source": "test",
            },
            "wait_state": {
                "reason": "ждём остальных",
                "source": "test",
            },
            "camp_state": {
                "reason": "ночлег",
                "source": "test",
            },
            "movement_intent": {
                "target_label": "Северные ворота",
                "target_node": {
                    "v": 1,
                    "map_level": "landmark",
                    "node_type": "landmark",
                    "node_id": "north-gate",
                    "label": "Северные ворота",
                    "zone_label": "camp",
                    "area_label": "camp",
                },
                "movement_mode": "cautious",
                "movement_kind": "move",
                "action_kind": "move",
                "route_kind": "landmark_move",
                "allowed": True,
                "travel_activity": {
                    "activity": "navigate",
                    "assigned_actor_id": str(player_id),
                    "source": "test",
                },
                "source": "test",
                "active": True,
                "target_node_type": "landmark",
                "target_node_id": "north-gate",
            },
            "travel_state": {
                "active": True,
                "phase": "in_transit",
                "route_summary": {
                    "allowed": True,
                    "route_kind": "landmark_move",
                    "action_kind": "move",
                    "target_label": "Северные ворота",
                    "target_node": {
                        "v": 1,
                        "map_level": "landmark",
                        "node_type": "landmark",
                        "node_id": "north-gate",
                        "label": "Северные ворота",
                        "zone_label": "camp",
                        "area_label": "camp",
                    },
                    "target_node_type": "landmark",
                    "target_node_id": "north-gate",
                    "next_map_position": {
                        "v": 1,
                        "map_level": "landmark",
                        "node_type": "landmark",
                        "node_id": "north-gate",
                        "label": "Северные ворота",
                        "area_label": "camp",
                    },
                    "next_zone_label": "camp",
                },
                "started_from": group_position,
                "target_node": {
                    "v": 1,
                    "map_level": "landmark",
                    "node_type": "landmark",
                    "node_id": "north-gate",
                    "label": "Северные ворота",
                    "zone_label": "camp",
                    "area_label": "camp",
                },
                "progress_kind": "route",
                "progress_step": 1,
                "movement_mode": "cautious",
                "travel_activity": {
                    "activity": "navigate",
                    "assigned_actor_id": str(player_id),
                    "source": "test",
                },
            },
        }
    }

    async def fake_list_session_players(_db, _sess, active_only=False):
        assert active_only is False
        return [sp]

    monkeypatch.setattr(state_builder, "list_session_players", fake_list_session_players)
    monkeypatch.setattr(state_builder, "_get_kicked", lambda _sess: set())
    monkeypatch.setattr(state_builder, "_char_to_payload", lambda _char: None)
    monkeypatch.setattr(state_builder, "_player_uid", lambda _player: _player.web_user_id if _player else None)
    monkeypatch.setattr(state_builder, "_get_ready_map", lambda _sess: {str(player_id): True})
    monkeypatch.setattr(state_builder, "_get_init_map", lambda _sess: {})
    monkeypatch.setattr(state_builder, "_get_last_seen_map", lambda _sess: {})
    monkeypatch.setattr(state_builder, "_initiative_fixed", lambda _sess: False)
    monkeypatch.setattr(state_builder, "_is_free_turns", lambda _sess: False)
    monkeypatch.setattr(state_builder, "_get_phase", lambda _sess: "turns")
    monkeypatch.setattr(state_builder, "_get_round_actions", lambda _sess: {})
    monkeypatch.setattr(state_builder, "_ready_active_players", lambda _sess, active_sps: active_sps)
    monkeypatch.setattr(state_builder, "_get_group_states", lambda _sess, _player_ids=None: group_state)
    monkeypatch.setattr(state_builder, "_get_pc_positions", lambda _sess: {str(player_id): "camp"})
    monkeypatch.setattr(state_builder, "_get_map_positions", lambda _sess: {str(player_id): group_position})
    monkeypatch.setattr(state_builder, "_get_player_group_id", lambda _sess, _player_id, _player_ids=None: "main")
    monkeypatch.setattr(state_builder, "snapshot_combat_state", lambda _session_id: None)

    db = _FakeDb([[player], [], [], []])
    payload = asyncio.run(state_builder.build_state(db, sess))

    assert payload["game"]["groups"]["main"]["status"] == "moving"
    assert payload["game"]["groups"]["main"]["movement_mode"] == "cautious"
    assert payload["game"]["groups"]["main"]["travel_activity_summary"] == {
        "activity": "navigate",
        "assigned_actor_id": str(player_id),
        "source": "test",
    }
    assert payload["game"]["groups"]["main"]["wait_summary"] == {
        "reason": "ждём остальных",
        "source": "test",
    }
    assert payload["game"]["groups"]["main"]["camp_summary"] == {
        "reason": "ночлег",
        "source": "test",
    }
    assert payload["game"]["groups"]["main"]["movement_intent_summary"] == {
        "target_label": "Северные ворота",
        "target_node": {
            "v": 1,
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "north-gate",
            "label": "Северные ворота",
            "zone_label": "camp",
            "area_label": "camp",
        },
        "movement_mode": "cautious",
        "movement_kind": "move",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "allowed": True,
        "travel_activity": {
            "activity": "navigate",
            "assigned_actor_id": str(player_id),
            "source": "test",
        },
        "source": "test",
        "active": True,
        "target_node_type": "landmark",
        "target_node_id": "north-gate",
    }
    assert payload["game"]["groups"]["main"]["travel_state"] == {
        "active": True,
        "phase": "in_transit",
        "route_summary": {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "Северные ворота",
            "target_node": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "north-gate",
                "label": "Северные ворота",
                "zone_label": "camp",
                "area_label": "camp",
            },
            "target_node_type": "landmark",
            "target_node_id": "north-gate",
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "north-gate",
                "label": "Северные ворота",
                "area_label": "camp",
            },
            "next_zone_label": "camp",
        },
        "started_from": {
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "camp",
            "label": "camp",
        },
        "target_node": {
            "v": 1,
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "north-gate",
            "label": "Северные ворота",
            "zone_label": "camp",
            "area_label": "camp",
        },
        "progress_kind": "route",
        "progress_step": 1,
        "movement_mode": "cautious",
        "travel_activity": {
            "activity": "navigate",
            "assigned_actor_id": str(player_id),
            "source": "test",
        },
    }
    assert payload["game"]["groups"]["main"]["travel_summary"] == {
        "active": True,
        "phase": "in_transit",
        "progress_kind": "route",
        "progress_step": 1,
        "movement_mode": "cautious",
        "route_summary": {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "Северные ворота",
            "target_node": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "north-gate",
                "label": "Северные ворота",
                "zone_label": "camp",
                "area_label": "camp",
            },
            "target_node_type": "landmark",
            "target_node_id": "north-gate",
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "north-gate",
                "label": "Северные ворота",
                "area_label": "camp",
            },
            "next_zone_label": "camp",
        },
        "started_from": {
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "camp",
            "label": "camp",
        },
        "target_node": {
            "v": 1,
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "north-gate",
            "label": "Северные ворота",
            "zone_label": "camp",
            "area_label": "camp",
        },
        "travel_activity": {
            "activity": "navigate",
            "assigned_actor_id": str(player_id),
            "source": "test",
        },
    }
