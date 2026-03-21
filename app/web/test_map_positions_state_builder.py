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
    monkeypatch.setattr(state_builder, "get_player_known_node_ids", lambda _sess, _player_id: [])
    monkeypatch.setattr(state_builder, "get_player_revealed_node_ids", lambda _sess, _player_id: [])
    monkeypatch.setattr(state_builder, "get_current_group_node_context", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_detail", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_inspect_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_services", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_service_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_service_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_service_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_service_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_travel_event", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_camp_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_scout_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_context_action_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_route_access_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_context_action_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_node_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_current_node_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_travel_event_outcome", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_map_intel", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_recent_map_intel", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_arrival_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_node_entry_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_node_entry_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_entry_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_destination_event_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_node_destination_event_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_destination_event_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_destination_event_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_node_destination_event_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_destination_event_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_current_node_visit_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_visit_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_route_traversal_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_journey_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_journey_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_exploration_leads", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_primary_exploration_lead", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_local_interaction_surface", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_node_progress", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_region_exploration_summary", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_region_frontier_summary", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_region_gateways", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_primary_region_gateway", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_region_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_discovered_regions", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_discovered_region_summaries", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_region_entry_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_region_onboarding_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_region_onboarding_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_region_world_overview", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_primary_region_focus", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_primary_region_focus_plan", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_region_target_options", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_region_transition_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_region_transition_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(
        state_builder,
        "get_current_group_route_planning",
        lambda _sess, player_id=None: {"reachable_destinations": [], "route_frontiers": []},
    )
    monkeypatch.setattr(state_builder, "get_current_group_navigation_options", lambda _sess, player_id=None: [])
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
            "last_camp_result_summary": None,
            "route_access_states": None,
            "last_scout_result_summary": None,
            "last_context_action_result_summary": None,
            "last_node_entry_result_summary": None,
            "last_destination_event_result_summary": None,
            "last_region_entry_result_summary": None,
            "active_journey_summary": None,
            "last_journey_result_summary": None,
            "context_action_states": None,
            "node_entry_states": None,
            "destination_event_states": None,
            "node_states": None,
            "last_service_result_summary": None,
            "service_states": None,
            "map_intel_count": 0,
            "discovered_region_count": 0,
            "visited_node_count": 0,
            "traversed_route_count": 0,
            "movement_intent_summary": None,
            "travel_state": None,
            "travel_summary": None,
            "travel_event_summary": None,
            "last_travel_event_outcome_summary": None,
            "pause_reason": None,
            "pause_details": None,
            "available_resolutions": None,
            "last_resolution_summary": None,
        }
    }
    assert payload["game"]["current_group_node_context"] is None
    assert payload["game"]["current_group_node_detail"] is None
    assert payload["game"]["current_group_last_inspect_result"] is None
    assert payload["game"]["current_group_node_services"] == []
    assert payload["game"]["current_group_last_service_result"] is None
    assert payload["game"]["current_group_service_states"] == []
    assert payload["game"]["current_group_travel_event"] is None
    assert payload["game"]["current_group_last_camp_result"] is None
    assert payload["game"]["current_group_last_scout_result"] is None
    assert payload["game"]["current_group_last_context_action_result"] is None
    assert payload["game"]["current_group_route_access_states"] == []
    assert payload["game"]["current_group_context_action_states"] == []
    assert payload["game"]["current_group_node_states"] == []
    assert payload["game"]["current_group_current_node_state"] is None
    assert payload["game"]["current_group_last_travel_event_outcome"] is None
    assert payload["game"]["current_group_map_intel"] == []
    assert payload["game"]["current_group_recent_map_intel"] == []
    assert payload["game"]["current_group_last_arrival_result"] is None
    assert payload["game"]["current_group_last_node_entry_result"] is None
    assert payload["game"]["current_group_current_node_entry_state"] is None
    assert payload["game"]["current_group_node_entry_states"] == []
    assert payload["game"]["current_group_last_destination_event_result"] is None
    assert payload["game"]["current_group_current_node_destination_event_state"] is None
    assert payload["game"]["current_group_destination_event_states"] == []
    assert payload["game"]["current_group_current_node_visit_state"] is None
    assert payload["game"]["current_group_node_visit_states"] == []
    assert payload["game"]["current_group_route_traversal_states"] == []
    assert payload["game"]["current_group_active_journey"] is None
    assert payload["game"]["current_group_last_journey_result"] is None
    assert payload["game"]["current_group_route_planning"] == {"reachable_destinations": [], "route_frontiers": []}
    assert payload["game"]["current_group_reachable_destinations"] == []
    assert payload["game"]["current_group_route_frontiers"] == []
    assert payload["game"]["current_group_exploration_leads"] == []
    assert payload["game"]["current_group_primary_exploration_lead"] is None
    assert payload["game"]["current_group_local_interaction_surface"] is None
    assert payload["game"]["current_group_current_node_progress"] is None
    assert payload["game"]["current_group_region_exploration_summary"] is None
    assert payload["game"]["current_group_region_frontier_summary"] is None
    assert payload["game"]["current_group_region_gateways"] == []
    assert payload["game"]["current_group_primary_region_gateway"] is None
    assert payload["game"]["current_group_current_region_state"] is None
    assert payload["game"]["current_group_discovered_regions"] == []
    assert payload["game"]["current_group_discovered_region_summaries"] == []
    assert payload["game"]["current_group_last_region_entry_result"] is None
    assert payload["game"]["current_group_last_region_onboarding_result"] is None
    assert payload["game"]["current_group_region_onboarding_states"] == []
    assert payload["game"]["current_group_region_world_overview"] is None
    assert payload["game"]["current_group_primary_region_focus"] is None
    assert payload["game"]["current_group_primary_region_focus_plan"] is None
    assert payload["game"]["current_group_region_target_options"] is None
    assert payload["game"]["current_group_last_region_transition_result"] is None
    assert payload["game"]["current_group_region_transition_state"] is None
    assert payload["game"]["current_group_navigation_options"] == []
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
            "known_node_ids": [],
            "revealed_node_ids": [],
        }
    ]


def test_build_state_exports_region_residency_payloads(monkeypatch) -> None:
    player_id = uuid.uuid4()
    session_id = uuid.uuid4()
    structured_position = {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": "northwatch_outpost",
        "label": "Северный рубеж",
        "area_label": "Северный рубеж",
    }
    sp = SimpleNamespace(player_id=player_id, join_order=1, is_admin=False, is_active=True)
    player = SimpleNamespace(id=player_id, display_name="Alice", web_user_id=42, telegram_user_id=None)
    group_state = {
        "main": {
            "group_id": "main",
            "player_ids": [str(player_id)],
            "movement_mode": "normal",
            "current_map_position": structured_position,
            "area_label": "Северный рубеж",
            "status": "idle",
            "current_region_state": {
                "region_id": "northwatch_frontier",
                "region_label": "Северный рубеж",
                "current_node_id": "northwatch_outpost",
                "entered_at": "2025-01-02T00:00:00+00:00",
                "visit_count": 1,
                "source": "region_transition",
            },
            "discovered_regions": {
                "starter_frontier": {
                    "region_id": "starter_frontier",
                    "region_label": "Стартовое пограничье",
                    "visit_count": 1,
                    "first_entered_at": "2025-01-01T00:00:00+00:00",
                    "last_entered_at": "2025-01-01T00:00:00+00:00",
                    "first_anchor_node_id": "start_trakt",
                    "last_anchor_node_id": "start_trakt",
                    "summary": "Группа впервые входит в регион Стартовое пограничье.",
                },
                "northwatch_frontier": {
                    "region_id": "northwatch_frontier",
                    "region_label": "Северный рубеж",
                    "visit_count": 1,
                    "first_entered_at": "2025-01-02T00:00:00+00:00",
                    "last_entered_at": "2025-01-02T00:00:00+00:00",
                    "first_anchor_node_id": "northwatch_outpost",
                    "last_anchor_node_id": "northwatch_outpost",
                    "summary": "Группа впервые входит в регион Северный рубеж.",
                },
            },
            "last_region_entry_result": {
                "result_id": "region-entry-2",
                "result_type": "region_transition_entry",
                "summary": "Группа переходит в регион Северный рубеж через frontier gateway.",
                "result_summary": "Группа переходит в регион Северный рубеж через frontier gateway.",
                "region_id": "northwatch_frontier",
                "region_label": "Северный рубеж",
                "anchor_node_id": "northwatch_outpost",
                "first_region_visit": True,
                "visit_count": 1,
                "source": "region_transition",
                "resolved_at": "2025-01-02T00:00:00+00:00",
            },
        }
    }
    sess = SimpleNamespace(
        id=session_id,
        title="Campaign",
        is_active=False,
        is_paused=False,
        turn_index=0,
        current_player_id=player_id,
        turn_started_at=None,
        settings={
            "ready": {str(player_id): True},
            "initiative": {str(player_id): 7},
            "group_states": group_state,
            "pc_positions": {str(player_id): "Северный рубеж"},
            "map_positions": {str(player_id): structured_position},
        },
    )

    monkeypatch.setattr(state_builder, "get_session_lock", lambda _session_id: None)
    async def _list_players(_db, _session_id, active_only=False):
        return [sp]

    monkeypatch.setattr(state_builder, "list_session_players", _list_players)
    monkeypatch.setattr(state_builder, "snapshot_combat_state", lambda _session_id: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_context", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_detail", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_inspect_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_services", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_service_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_service_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_travel_event", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_camp_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_scout_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_context_action_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_route_access_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_context_action_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_node_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_current_node_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_travel_event_outcome", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_map_intel", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_recent_map_intel", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_arrival_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_node_entry_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_node_entry_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_entry_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_destination_event_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_node_destination_event_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_destination_event_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_current_node_visit_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_visit_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_route_traversal_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_journey_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_journey_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_route_planning", lambda _sess, player_id=None: {"reachable_destinations": [], "route_frontiers": []})
    monkeypatch.setattr(state_builder, "get_current_group_exploration_leads", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_primary_exploration_lead", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_local_interaction_surface", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_node_progress", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_region_exploration_summary", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_region_frontier_summary", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_region_gateways", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_primary_region_gateway", lambda _sess, player_id=None: None)
    monkeypatch.setattr(
        state_builder,
        "get_current_group_current_region_state",
        lambda _sess, player_id=None: {
            "region_id": "northwatch_frontier",
            "region_label": "Северный рубеж",
            "current_node_id": "northwatch_outpost",
            "entered_at": "2025-01-02T00:00:00+00:00",
            "visit_count": 1,
            "source": "region_transition",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_discovered_regions",
        lambda _sess, player_id=None: [
            {
                "region_id": "starter_frontier",
                "region_label": "Стартовое пограничье",
                "visit_count": 1,
                "first_entered_at": "2025-01-01T00:00:00+00:00",
                "last_entered_at": "2025-01-01T00:00:00+00:00",
                "first_anchor_node_id": "start_trakt",
                "last_anchor_node_id": "start_trakt",
                "summary": "Группа впервые входит в регион Стартовое пограничье.",
            },
            {
                "region_id": "northwatch_frontier",
                "region_label": "Северный рубеж",
                "visit_count": 1,
                "first_entered_at": "2025-01-02T00:00:00+00:00",
                "last_entered_at": "2025-01-02T00:00:00+00:00",
                "first_anchor_node_id": "northwatch_outpost",
                "last_anchor_node_id": "northwatch_outpost",
                "summary": "Группа впервые входит в регион Северный рубеж.",
            },
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_discovered_region_summaries",
        lambda _sess, player_id=None: [
            {
                "region_id": "northwatch_frontier",
                "region_label": "Северный рубеж",
                "region_status": "newly_onboarded_region",
                "summary": "Северный рубеж только что закреплён как новый регион и пока остаётся свежим стартовым плацдармом.",
                "current_region": True,
                "visit_count": 1,
                "first_entered_at": "2025-01-02T00:00:00+00:00",
                "last_entered_at": "2025-01-02T00:00:00+00:00",
                "revealed_node_count": 1,
                "visited_node_count": 1,
                "unresolved_local_node_count": 0,
                "blocked_frontier_count": 0,
                "reachable_unvisited_count": 0,
                "onboarding_status": "applied",
                "primary_frontier": None,
                "source": "region_world_overview",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_region_entry_result",
        lambda _sess, player_id=None: {
            "result_id": "region-entry-2",
            "result_type": "region_transition_entry",
            "summary": "Группа переходит в регион Северный рубеж через frontier gateway.",
            "result_summary": "Группа переходит в регион Северный рубеж через frontier gateway.",
            "region_id": "northwatch_frontier",
            "region_label": "Северный рубеж",
            "anchor_node_id": "northwatch_outpost",
            "first_region_visit": True,
            "visit_count": 1,
            "source": "region_transition",
            "resolved_at": "2025-01-02T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_region_onboarding_result",
        lambda _sess, player_id=None: {
            "result_id": "region-onboarding-2",
            "result_type": "anchor_reveal_applied",
            "summary": "Северный рубеж раскрывает ближайшие дозорные тропы вокруг заставы.",
            "result_summary": "Северный рубеж раскрывает ближайшие дозорные тропы вокруг заставы.",
            "region_id": "northwatch_frontier",
            "region_label": "Северный рубеж",
            "anchor_node_id": "northwatch_outpost",
            "revealed_node_ids": ["old_fortress_edge"],
            "revealed_route_ids": ["forest_settlement->old_fortress_edge:move"],
            "onboarding_applied": True,
            "source": "region_transition",
            "resolved_at": "2025-01-02T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_region_onboarding_states",
        lambda _sess, player_id=None: [
            {
                "region_id": "northwatch_frontier",
                "region_label": "Северный рубеж",
                "status": "applied",
                "summary": "Северный рубеж раскрывает ближайшие дозорные тропы вокруг заставы.",
                "revealed_node_ids": ["old_fortress_edge"],
                "revealed_route_ids": ["forest_settlement->old_fortress_edge:move"],
                "updated_at": "2025-01-02T00:00:00+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_region_world_overview",
        lambda _sess, player_id=None: {
            "current_region_id": "northwatch_frontier",
            "current_region_label": "Северный рубеж",
            "discovered_region_count": 1,
            "active_region_count": 1,
            "blocked_region_count": 0,
            "saturated_region_count": 0,
            "quiet_region_count": 0,
            "primary_region_focus": {
                "region_id": "northwatch_frontier",
                "region_label": "Северный рубеж",
                "region_status": "newly_onboarded_region",
            },
            "region_summaries": [
                {
                    "region_id": "northwatch_frontier",
                    "region_label": "Северный рубеж",
                    "region_status": "newly_onboarded_region",
                    "summary": "Северный рубеж только что закреплён как новый регион и пока остаётся свежим стартовым плацдармом.",
                    "current_region": True,
                    "visit_count": 1,
                    "first_entered_at": "2025-01-02T00:00:00+00:00",
                    "last_entered_at": "2025-01-02T00:00:00+00:00",
                    "revealed_node_count": 1,
                    "visited_node_count": 1,
                    "unresolved_local_node_count": 0,
                    "blocked_frontier_count": 0,
                    "reachable_unvisited_count": 0,
                    "onboarding_status": "applied",
                    "primary_frontier": None,
                    "source": "region_world_overview",
                }
            ],
            "summary": "Группа видит 1 открытых регионов: 1 активных, 0 упёршихся в блоки, 0 в основном выработанных и 0 тихих.",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_primary_region_focus",
        lambda _sess, player_id=None: {
            "region_id": "northwatch_frontier",
            "region_label": "Северный рубеж",
            "region_status": "newly_onboarded_region",
            "summary": "Северный рубеж только что закреплён как новый регион и пока остаётся свежим стартовым плацдармом.",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_primary_region_focus_plan",
        lambda _sess, player_id=None: {
            "target_region_id": "northwatch_frontier",
            "target_region_label": "Северный рубеж",
            "plan_status": "current_region",
            "summary": "Группа уже находится в регионе Северный рубеж.",
            "current_region_id": "northwatch_frontier",
            "current_region_label": "Северный рубеж",
            "gateway_id": "",
            "gateway_label": "",
            "gateway_status": "",
            "gateway_source_node_id": "",
            "gateway_source_node_label": "",
            "path_node_ids": ["northwatch_outpost"],
            "path_route_ids": [],
            "path_step_count": 0,
            "reachable": True,
            "blocked_reason": "",
            "suggested_command": "",
            "source": "region_target_guidance",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_region_target_options",
        lambda _sess, player_id=None: {
            "current_region_id": "northwatch_frontier",
            "current_region_label": "Северный рубеж",
            "primary_region_focus_plan": {
                "target_region_id": "northwatch_frontier",
                "target_region_label": "Северный рубеж",
                "plan_status": "current_region",
                "summary": "Группа уже находится в регионе Северный рубеж.",
                "current_region_id": "northwatch_frontier",
                "current_region_label": "Северный рубеж",
                "gateway_id": "",
                "gateway_label": "",
                "gateway_status": "",
                "gateway_source_node_id": "",
                "gateway_source_node_label": "",
                "path_node_ids": ["northwatch_outpost"],
                "path_route_ids": [],
                "path_step_count": 0,
                "reachable": True,
                "blocked_reason": "",
                "suggested_command": "",
                "source": "region_target_guidance",
            },
            "target_region_plans": [
                {
                    "target_region_id": "northwatch_frontier",
                    "target_region_label": "Северный рубеж",
                    "plan_status": "current_region",
                    "summary": "Группа уже находится в регионе Северный рубеж.",
                    "current_region_id": "northwatch_frontier",
                    "current_region_label": "Северный рубеж",
                    "gateway_id": "",
                    "gateway_label": "",
                    "gateway_status": "",
                    "gateway_source_node_id": "",
                    "gateway_source_node_label": "",
                    "path_node_ids": ["northwatch_outpost"],
                    "path_route_ids": [],
                    "path_step_count": 0,
                    "reachable": True,
                    "blocked_reason": "",
                    "suggested_command": "",
                    "source": "region_target_guidance",
                }
            ],
            "summary": "Из региона Северный рубеж собрано 1 canonical target-region plan(s).",
        },
    )
    monkeypatch.setattr(state_builder, "get_current_group_last_region_transition_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_region_transition_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_navigation_options", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "_group_discovered_region_count", lambda _group: 2)
    monkeypatch.setattr(
        state_builder,
        "_group_last_region_entry_result_summary",
        lambda _group: {
            "result_id": "region-entry-2",
            "result_type": "region_transition_entry",
            "summary": "Группа переходит в регион Северный рубеж через frontier gateway.",
            "result_summary": "Группа переходит в регион Северный рубеж через frontier gateway.",
            "region_id": "northwatch_frontier",
            "region_label": "Северный рубеж",
            "anchor_node_id": "northwatch_outpost",
            "first_region_visit": True,
            "visit_count": 1,
            "source": "region_transition",
            "resolved_at": "2025-01-02T00:00:00+00:00",
        },
    )
    db = _FakeDb([[player], [], [], []])
    payload = asyncio.run(state_builder.build_state(db, sess))

    assert payload["game"]["current_group_current_region_state"]["region_id"] == "northwatch_frontier"
    assert [item["region_id"] for item in payload["game"]["current_group_discovered_regions"]] == [
        "starter_frontier",
        "northwatch_frontier",
    ]
    assert payload["game"]["current_group_last_region_entry_result"]["result_type"] == "region_transition_entry"
    assert payload["game"]["current_group_discovered_region_summaries"][0]["region_id"] == "northwatch_frontier"
    assert payload["game"]["current_group_last_region_onboarding_result"]["result_type"] == "anchor_reveal_applied"
    assert payload["game"]["current_group_region_onboarding_states"][0]["region_id"] == "northwatch_frontier"
    assert payload["game"]["current_group_region_world_overview"]["current_region_id"] == "northwatch_frontier"
    assert payload["game"]["current_group_primary_region_focus"]["region_status"] == "newly_onboarded_region"
    assert payload["game"]["current_group_primary_region_focus_plan"]["target_region_id"] == "northwatch_frontier"
    assert payload["game"]["current_group_region_target_options"]["current_region_id"] == "northwatch_frontier"


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
            "last_node_entry_result": {
                "result_id": "entry-1",
                "result_type": "changed_place",
                "title": "Стартовый тракт изменился",
                "summary": "На входе в тракт заметны следы недавних перемен.",
                "result_summary": "Тракт встречает группу заметными следами недавней расчистки и выглядит иначе, чем прежде.",
                "node_id": "start_trakt",
                "node_label": "Стартовый тракт",
                "visit_count": 1,
                "first_visit": True,
                "node_state_flags": ["old_road_cleared"],
                "applied_effects": ["visit_count:1", "entry_type:changed_place", "node_state_flags:old_road_cleared"],
                "source": "test",
                "resolved_at": "2026-03-14T00:04:10+00:00",
            },
            "node_entry_states": {
                "start_trakt": {
                    "node_id": "start_trakt",
                    "node_label": "Стартовый тракт",
                    "entry_count": 1,
                    "last_entry_type": "changed_place",
                    "summary": "Текущий вход в тракт отмечен как изменившееся место.",
                    "source": "test",
                    "updated_at": "2026-03-14T00:04:11+00:00",
                }
            },
            "last_destination_event_result": {
                "result_id": "dest-1",
                "event_id": "craft_town_arrival_notice",
                "event_label": "Береговая наводка у городка",
                "result_type": "settlement_notice",
                "title": "У причала быстро находят ориентиры",
                "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
                "result_summary": "Озёрный городок встречает группу короткой береговой наводкой и подсказывает, где проще держать следующий ход.",
                "node_id": "start_trakt",
                "node_label": "Стартовый тракт",
                "visit_count": 1,
                "first_visit": True,
                "applied_effects": ["destination_notice:craft_town", "visit_count:1", "destination_event:settlement_notice"],
                "source": "test",
                "resolved_at": "2026-03-14T00:04:12+00:00",
            },
            "destination_event_states": {
                "start_trakt": {
                    "event_id": "craft_town_arrival_notice",
                    "node_id": "start_trakt",
                    "status": "completed",
                    "result_type": "settlement_notice",
                    "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
                    "source": "test",
                    "updated_at": "2026-03-14T00:04:13+00:00",
                }
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
    monkeypatch.setattr(state_builder, "_get_map_positions", lambda _sess: {str(player_id): group_state["main"]["current_map_position"]})
    monkeypatch.setattr(state_builder, "_get_player_group_id", lambda _sess, _player_id, _player_ids=None: "main")
    monkeypatch.setattr(state_builder, "get_player_known_node_ids", lambda _sess, _player_id: ["start_trakt"])
    monkeypatch.setattr(state_builder, "get_player_revealed_node_ids", lambda _sess, _player_id: ["start_trakt", "fortress_gate"])
    monkeypatch.setattr(
        state_builder,
        "get_current_group_node_context",
        lambda _sess, player_id=None: {
            "node_summary": {
                "node_id": "start_trakt",
                "label": "Стартовый тракт",
                "node_type": "zone",
                "area_label": "Стартовый тракт",
                "zone_band": "safe",
                "settlement_kind": "roadside",
                "environment_hint": "roadland",
                "safe_rest_hint": True,
            },
            "node_state_flags": ["old_road_cleared"],
            "state_notes": ["У старой дороги видны следы недавней расчистки, и проход к руинам читается увереннее."],
            "contextual_actions": [
                {"action_id": "navigate", "action_key": "navigate", "label": "Продолжить путь", "action_type": "action", "action_kind": "navigate", "status": "available", "available": True, "exhausted": False},
                {"action_id": "inspect", "action_key": "inspect", "label": "Осмотреться", "action_type": "action", "action_kind": "inspect", "status": "available", "available": True, "exhausted": False},
                {"action_id": "wait", "action_key": "wait", "label": "Подождать", "action_type": "action", "action_kind": "wait", "status": "available", "available": True, "exhausted": False},
                {"action_id": "camp", "action_key": "camp", "label": "Разбить лагерь", "action_type": "action", "action_kind": "camp", "status": "available", "available": True, "exhausted": False},
                {"action_id": "rest_hint", "action_key": "rest_hint", "label": "Есть место для передышки", "action_type": "hint", "action_kind": "rest_hint", "status": "available", "available": False, "exhausted": False},
            ],
            "available_services": [
                {
                    "service_id": "start_trakt:safe_rest",
                    "service_key": "safe_rest",
                    "label": "Безопасный отдых",
                    "service_type": "rest",
                    "service_kind": "rest",
                    "summary": "Можно перевести дух и переждать путь в сравнительно безопасных условиях.",
                    "source": "registry",
                    "available": True,
                    "status": "available",
                    "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
                }
            ],
            "service_actions": [
                {"action_key": "use_service", "label": "Воспользоваться услугой", "action_type": "action"},
            ],
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_node_detail",
        lambda _sess, player_id=None: {
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
            "node_type": "zone",
            "area_label": "Стартовый тракт",
            "short_description": "Широкий тракт у стартового лагеря, где сходятся безопасные дороги региона.",
            "inspect_summary": "По тракту удобно держать путь к воротам крепости и к озёрному городку.",
            "travel_note": "Хороший ориентир для сбора группы и спокойного перехода.",
            "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
            "node_state_flags": ["old_road_cleared"],
            "state_notes": ["Сломанные ветви и свежие борозды в грязи показывают, что завал уже разбирали совсем недавно."],
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_inspect_result",
        lambda _sess, player_id=None: {
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
            "node_type": "zone",
            "inspect_summary": "По тракту удобно держать путь к воротам крепости и к озёрному городку.",
            "short_description": "Широкий тракт у стартового лагеря, где сходятся безопасные дороги региона.",
            "travel_note": "Хороший ориентир для сбора группы и спокойного перехода.",
            "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
            "state_notes": ["Сломанные ветви и свежие борозды в грязи показывают, что завал уже разбирали совсем недавно."],
            "source": "test",
            "inspected_at": "2026-03-14T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_node_services",
        lambda _sess, player_id=None: [
            {
                "service_id": "start_trakt:safe_rest",
                "service_key": "safe_rest",
                "label": "Безопасный отдых",
                "service_type": "rest",
                "service_kind": "rest",
                "summary": "Можно перевести дух и переждать путь в сравнительно безопасных условиях.",
                "source": "registry",
                "available": True,
                "status": "available",
                "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_service_result",
        lambda _sess, player_id=None: {
            "result_id": "service-out-1",
            "service_id": "start_trakt:safe_rest",
            "service_key": "safe_rest",
            "service_label": "Безопасный отдых",
            "label": "Безопасный отдых",
            "result_type": "lodging_received",
            "service_type": "rest",
            "service_kind": "rest",
            "summary": "Можно перевести дух и переждать путь в сравнительно безопасных условиях.",
            "result_summary": "Место подходит для короткой передышки без немедленной дорожной угрозы.",
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "applied_effects": ["lodging_received"],
            "discovered_notes": [],
            "reveal_applied": False,
            "source": "test",
            "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
            "resolved_at": "2026-03-14T00:05:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_service_states",
        lambda _sess, player_id=None: [
            {
                "service_id": "start_trakt:safe_rest",
                "status": "resolved",
                "result_type": "lodging_received",
                "summary": "Место подходит для короткой передышки без немедленной дорожной угрозы.",
                "source": "test",
                "updated_at": "2026-03-14T00:05:10+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_travel_event",
        lambda _sess, player_id=None: {
            "event_id": "evt-road",
            "event_key": "roadside_finding",
            "event_type": "roadside_hook",
            "summary": "У обочины лежит приметная дорожная находка.",
            "route_snapshot": {
                "allowed": True,
                "route_kind": "zone_move",
                "action_kind": "move",
                "target_label": "Восточный берег",
            },
            "source": "travel",
            "active": True,
            "resolved": False,
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_camp_result",
        lambda _sess, player_id=None: {
            "result_id": "camp-out-1",
            "result_type": "sheltered_rest",
            "summary": "У часовни есть укрытие для спокойной стоянки.",
            "result_summary": "Группа устраивается в укрытии и получает спокойную передышку.",
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "rest_quality": "sheltered",
            "risk_band": "low",
            "source": "test",
            "applied_effects": ["rest_quality:sheltered", "safety_note:shelter_found"],
            "resolved_at": "2026-03-14T00:07:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_scout_result",
        lambda _sess, player_id=None: {
            "result_id": "scout-out-1",
            "result_type": "route_revealed",
            "summary": "Разведка у тракта приносит новый маршрутный результат.",
            "result_summary": "Разведка проясняет соседний маршрут и добавляет новый понятный выход из текущей точки.",
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "discovery_scope": "adjacent_route",
            "discovered_node_ids": ["craft_town"],
            "discovered_route_ids": ["start_trakt->craft_town"],
            "discovered_notes": ["С тракта замечается надёжный боковой путь к озёрному городку."],
            "reveal_applied": True,
            "source": "test",
            "resolved_at": "2026-03-14T00:08:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_context_action_result",
        lambda _sess, player_id=None: {
            "result_id": "ctx-out-1",
            "action_id": "clear_old_road",
            "action_label": "Расчистить старую дорогу",
            "result_type": "route_cleared",
            "summary": "Разобрать завал и вернуть проход к разрушенному посёлку.",
            "result_summary": "Группа убирает завал с лесной дороги и открывает устойчивый проход к разрушенному посёлку.",
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "applied_effects": ["route_access:cleared"],
            "source": "test",
            "resolved_at": "2026-03-14T00:09:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_route_access_states",
        lambda _sess, player_id=None: [
            {
                "route_id": "start_trakt->craft_town:move",
                "access_state": "blocked",
                "is_traversable": False,
                "summary": "Путь к городку перекрыт.",
                "block_reason": "blocked_path",
                "source": "test",
                "updated_at": "2026-03-15T00:09:00+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_context_action_states",
        lambda _sess, player_id=None: [
            {
                "action_id": "clear_old_road",
                "status": "completed",
                "result_type": "route_cleared",
                "summary": "Группа убирает завал с лесной дороги и открывает устойчивый проход к разрушенному посёлку.",
                "source": "test",
                "updated_at": "2026-03-15T00:09:30+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_node_states",
        lambda _sess, player_id=None: [
            {
                "node_id": "start_trakt",
                "state_flags": ["old_road_cleared"],
                "summary": "На лесной дороге заметны следы недавней расчистки старого прохода.",
                "source": "test",
                "updated_at": "2026-03-15T00:09:45+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_current_node_state",
        lambda _sess, player_id=None: {
            "node_id": "start_trakt",
            "state_flags": ["old_road_cleared"],
            "summary": "На лесной дороге заметны следы недавней расчистки старого прохода.",
            "source": "test",
            "updated_at": "2026-03-15T00:09:45+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_travel_event_outcome",
        lambda _sess, player_id=None: {
            "outcome_id": "out-road",
            "event_key": "roadside_finding",
            "event_type": "roadside_hook",
            "outcome_type": "finding_note",
            "summary": "У обочины лежит приметная дорожная находка.",
            "result_summary": "Группа отмечает дорожную примету и получает полезную заметку о ближайшем пути.",
            "applied_effects": ["event_closed", "travel_hint_recorded"],
            "source": "travel",
            "resolved_at": "2026-03-14T00:10:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_map_intel",
        lambda _sess, player_id=None: [
            {
                "entry_id": "intel-1",
                "entry_type": "route_hint",
                "title": "Разведка у Стартового тракта",
                "summary": "Разведка у Стартового тракта приносит новый маршрутный результат.",
                "result_summary": "С тракта замечается надёжный боковой путь к озёрному городку.",
                "source_kind": "scout",
                "source_id": "scout-out-1",
                "node_id": "start_trakt",
                "node_label": "Стартовый тракт",
                "related_node_ids": ["craft_town"],
                "related_route_ids": ["start_trakt->craft_town"],
                "tags": ["route_hint", "start_trakt", "craft_town"],
                "dedupe_key": "scout|start_trakt|route_revealed|craft_town|start_trakt->craft_town|route",
                "discovered_at": "2026-03-14T00:08:00+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_recent_map_intel",
        lambda _sess, player_id=None: [
            {
                "entry_id": "intel-1",
                "entry_type": "route_hint",
                "title": "Разведка у Стартового тракта",
                "summary": "Разведка у Стартового тракта приносит новый маршрутный результат.",
                "result_summary": "С тракта замечается надёжный боковой путь к озёрному городку.",
                "source_kind": "scout",
                "source_id": "scout-out-1",
                "node_id": "start_trakt",
                "node_label": "Стартовый тракт",
                "related_node_ids": ["craft_town"],
                "related_route_ids": ["start_trakt->craft_town"],
                "tags": ["route_hint", "start_trakt", "craft_town"],
                "dedupe_key": "scout|start_trakt|route_revealed|craft_town|start_trakt->craft_town|route",
                "discovered_at": "2026-03-14T00:08:00+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_arrival_result",
        lambda _sess, player_id=None: {
            "result_id": "arrival-1",
            "result_type": "first_arrival",
            "summary": "Группа прибывает в Стартовый тракт.",
            "result_summary": "Это первое фактическое прибытие группы в данную точку карты.",
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "route_id": "camp->start_trakt:move",
            "first_visit": True,
            "visit_count": 1,
            "source": "test",
            "applied_effects": ["visit_count:1", "visit:first_time"],
            "resolved_at": "2026-03-14T00:04:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_node_entry_result",
        lambda _sess, player_id=None: {
            "result_id": "entry-1",
            "result_type": "changed_place",
            "title": "Стартовый тракт изменился",
            "summary": "На входе в тракт заметны следы недавних перемен.",
            "result_summary": "Тракт встречает группу заметными следами недавней расчистки и выглядит иначе, чем прежде.",
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "visit_count": 1,
            "first_visit": True,
            "node_state_flags": ["old_road_cleared"],
            "applied_effects": ["visit_count:1", "entry_type:changed_place", "node_state_flags:old_road_cleared"],
            "source": "test",
            "resolved_at": "2026-03-14T00:04:10+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_current_node_entry_state",
        lambda _sess, player_id=None: {
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "entry_count": 1,
            "last_entry_type": "changed_place",
            "summary": "Текущий вход в тракт отмечен как изменившееся место.",
            "source": "test",
            "updated_at": "2026-03-14T00:04:11+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_node_entry_states",
        lambda _sess, player_id=None: [
            {
                "node_id": "start_trakt",
                "node_label": "Стартовый тракт",
                "entry_count": 1,
                "last_entry_type": "changed_place",
                "summary": "Текущий вход в тракт отмечен как изменившееся место.",
                "source": "test",
                "updated_at": "2026-03-14T00:04:11+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_destination_event_result",
        lambda _sess, player_id=None: {
            "result_id": "dest-1",
            "event_id": "craft_town_arrival_notice",
            "event_label": "Береговая наводка у городка",
            "result_type": "settlement_notice",
            "title": "У причала быстро находят ориентиры",
            "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
            "result_summary": "Озёрный городок встречает группу короткой береговой наводкой и подсказывает, где проще держать следующий ход.",
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "visit_count": 1,
            "first_visit": True,
            "applied_effects": ["destination_notice:craft_town", "visit_count:1", "destination_event:settlement_notice"],
            "source": "test",
            "resolved_at": "2026-03-14T00:04:12+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_current_node_destination_event_state",
        lambda _sess, player_id=None: {
            "event_id": "craft_town_arrival_notice",
            "node_id": "start_trakt",
            "status": "completed",
            "result_type": "settlement_notice",
            "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
            "source": "test",
            "updated_at": "2026-03-14T00:04:13+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_destination_event_states",
        lambda _sess, player_id=None: [
            {
                "event_id": "craft_town_arrival_notice",
                "node_id": "start_trakt",
                "status": "completed",
                "result_type": "settlement_notice",
                "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
                "source": "test",
                "updated_at": "2026-03-14T00:04:13+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_current_node_visit_state",
        lambda _sess, player_id=None: {
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "visit_count": 1,
            "first_visited_at": "2026-03-14T00:04:00+00:00",
            "last_visited_at": "2026-03-14T00:04:00+00:00",
            "last_result_type": "first_arrival",
            "summary": "Группа впервые достигает Стартового тракта.",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_node_visit_states",
        lambda _sess, player_id=None: [
            {
                "node_id": "start_trakt",
                "node_label": "Стартовый тракт",
                "visit_count": 1,
                "first_visited_at": "2026-03-14T00:04:00+00:00",
                "last_visited_at": "2026-03-14T00:04:00+00:00",
                "last_result_type": "first_arrival",
                "summary": "Группа впервые достигает Стартового тракта.",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_route_traversal_states",
        lambda _sess, player_id=None: [
            {
                "route_id": "camp->start_trakt:move",
                "traversal_count": 1,
                "first_traversed_at": "2026-03-14T00:04:00+00:00",
                "last_traversed_at": "2026-03-14T00:04:00+00:00",
                "summary": "Группа проходит маршрутом к Стартовому тракту.",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_journey_state",
        lambda _sess, player_id=None: {
            "journey_id": "journey-1",
            "target_node_id": "fortress_gate",
            "target_node_label": "Ворота крепости",
            "journey_status": "in_progress",
            "path_node_ids": ["start_trakt", "fortress_gate"],
            "path_route_ids": ["start_trakt->fortress_gate:move"],
            "next_node_id": "fortress_gate",
            "next_route_id": "start_trakt->fortress_gate:move",
            "completed_step_count": 0,
            "total_step_count": 1,
            "source": "test",
            "created_at": "2026-03-14T00:03:00+00:00",
            "updated_at": "2026-03-14T00:03:10+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_journey_result",
        lambda _sess, player_id=None: {
            "result_id": "journey-res-1",
            "result_type": "journey_advanced",
            "summary": "Группа продвигается к Воротам крепости.",
            "result_summary": "Путешествие к Воротам крепости продвинулось на один переход.",
            "journey_id": "journey-1",
            "target_node_id": "fortress_gate",
            "target_node_label": "Ворота крепости",
            "next_node_id": "fortress_gate",
            "next_route_id": "start_trakt->fortress_gate:move",
            "completed_step_count": 0,
            "total_step_count": 1,
            "source": "test",
            "resolved_at": "2026-03-14T00:03:10+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_exploration_leads",
        lambda _sess, player_id=None: [
            {
                "lead_id": "active_journey:journey-1",
                "lead_type": "active_journey",
                "priority_band": "high",
                "title": "Активный путь: Ворота крепости",
                "summary": "У группы есть in_progress journey к Ворота крепости (0/1 шагов).",
                "target_node_id": "fortress_gate",
                "target_node_label": "Ворота крепости",
                "route_id": "start_trakt->fortress_gate:move",
                "source_kind": "journey",
                "source_ref": "journey-1",
                "reachable": True,
                "blocked": False,
                "blocked_reason": "",
                "first_unvisited": "fortress_gate",
                "has_active_journey": True,
                "suggested_command": "group continue",
                "tags": ["journey", "in_progress"],
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_primary_exploration_lead",
        lambda _sess, player_id=None: {
            "lead_id": "active_journey:journey-1",
            "lead_type": "active_journey",
            "priority_band": "high",
            "title": "Активный путь: Ворота крепости",
            "summary": "У группы есть in_progress journey к Ворота крепости (0/1 шагов).",
            "target_node_id": "fortress_gate",
            "target_node_label": "Ворота крепости",
            "route_id": "start_trakt->fortress_gate:move",
            "source_kind": "journey",
            "source_ref": "journey-1",
            "reachable": True,
            "blocked": False,
            "blocked_reason": "",
            "first_unvisited": "fortress_gate",
            "has_active_journey": True,
            "suggested_command": "group continue",
            "tags": ["journey", "in_progress"],
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_local_interaction_surface",
        lambda _sess, player_id=None: {
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "available_actions": [
                {
                    "action_id": "navigate",
                    "availability_status": "available",
                    "available": True,
                }
            ],
            "locked_actions": [
                {
                    "action_id": "rest_hint",
                    "availability_status": "unavailable",
                    "available": False,
                }
            ],
            "available_services": [
                {
                    "service_id": "start_trakt:safe_rest",
                    "availability_status": "available",
                    "available": True,
                }
            ],
            "locked_services": [],
            "summary": "У Стартового тракта доступно 1 действий и 1 услуг; ограничено 1 действий и 0 услуг.",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_current_node_progress",
        lambda _sess, player_id=None: {
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "progression_status": "partially_resolved",
            "summary": "В Стартовом тракте часть локальных возможностей уже закрыта, но остаётся активный местный контент.",
            "visit_count": 2,
            "first_visit": False,
            "has_node_entry": True,
            "has_destination_event": True,
            "available_action_count": 1,
            "locked_action_count": 1,
            "completed_action_count": 1,
            "available_service_count": 1,
            "locked_service_count": 0,
            "completed_service_count": 1,
            "node_state_flags": ["old_road_cleared"],
            "unresolved_local_opportunities": ["Продолжить путь", "Безопасный отдых"],
            "source": "node_progression",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_region_exploration_summary",
        lambda _sess, player_id=None: {
            "region_id": "region",
            "region_label": "Стартовый тракт",
            "progression_status": "active_frontier",
            "summary": "У группы остаются достижимые непосещённые точки, так что frontier региона ещё активен.",
            "current_node_id": "start_trakt",
            "current_node_label": "Стартовый тракт",
            "revealed_node_count": 3,
            "visited_node_count": 2,
            "reachable_unvisited_count": 1,
            "blocked_frontier_count": 1,
            "quiet_node_count": 0,
            "active_local_node_count": 1,
            "locally_resolved_node_count": 1,
            "current_primary_frontier": {
                "target_node_id": "fortress_gate",
                "target_node_label": "Ворота крепости",
                "plan_status": "reachable",
            },
            "current_primary_lead": {
                "lead_id": "active_journey:journey-1",
                "lead_type": "active_journey",
                "title": "Активный путь: Ворота крепости",
            },
            "source": "region_exploration",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_region_frontier_summary",
        lambda _sess, player_id=None: {
            "blocked_frontiers": [
                {
                    "from_node_id": "start_trakt",
                    "to_node_id": "craft_town",
                    "route_id": "start_trakt->craft_town:move",
                    "frontier_type": "blocked_route",
                    "summary": "Маршрут видим, но заблокирован.",
                }
            ],
            "reachable_unvisited_nodes": [
                {
                    "target_node_id": "fortress_gate",
                    "target_node_label": "Ворота крепости",
                    "plan_status": "reachable",
                    "summary": "До Ворот крепости есть полностью открытый и проходимый путь.",
                }
            ],
            "unresolved_local_nodes": [
                {
                    "node_id": "start_trakt",
                    "node_label": "Стартовый тракт",
                    "progression_status": "partially_resolved",
                    "summary": "В Стартовом тракте часть локальных возможностей уже закрыта, но остаётся активный местный контент.",
                }
            ],
            "summary": "У группы 1 достижимых непосещённых точек, 1 заблокированных frontier-веток и 1 локально незавершённых узлов.",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_region_gateways",
        lambda _sess, player_id=None: [
            {
                "gateway_id": "forest_settlement_northwatch",
                "gateway_label": "Выход к северному рубежу",
                "gateway_status": "open",
                "summary": "Лесной посёлок выводит к региону Северный рубеж.",
                "source_node_id": "forest_settlement",
                "source_node_label": "Лесной посёлок",
                "route_id": "forest_settlement->old_fortress_edge:move",
                "target_region_id": "northwatch_frontier",
                "target_region_label": "Северный рубеж",
                "target_anchor_node_id": "northwatch_outpost",
                "reachable": True,
                "blocked": False,
                "locked": False,
                "blocked_reason": "",
                "unlock_hint": "Сначала собрать лесные припасы перед дальним выходом к северному рубежу.",
                "future_stub": False,
                "source": "region_gateway",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_primary_region_gateway",
        lambda _sess, player_id=None: {
            "gateway_id": "forest_settlement_northwatch",
            "gateway_label": "Выход к северному рубежу",
            "gateway_status": "open",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_current_region_state",
        lambda _sess, player_id=None: {
            "region_id": "starter_frontier",
            "region_label": "Стартовое пограничье",
            "current_node_id": "start_trakt",
            "entered_at": "2025-01-01T00:00:00+00:00",
            "visit_count": 1,
            "source": "region_residency",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_discovered_regions",
        lambda _sess, player_id=None: [
            {
                "region_id": "starter_frontier",
                "region_label": "Стартовое пограничье",
                "visit_count": 1,
                "first_entered_at": "2025-01-01T00:00:00+00:00",
                "last_entered_at": "2025-01-01T00:00:00+00:00",
                "first_anchor_node_id": "start_trakt",
                "last_anchor_node_id": "start_trakt",
                "summary": "Группа впервые входит в регион Стартовое пограничье.",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_discovered_region_summaries",
        lambda _sess, player_id=None: [
            {
                "region_id": "starter_frontier",
                "region_label": "Стартовое пограничье",
                "region_status": "current_active_region",
                "summary": "Стартовое пограничье остаётся основным рабочим frontier-регионом группы.",
                "current_region": True,
                "visit_count": 1,
                "first_entered_at": "2025-01-01T00:00:00+00:00",
                "last_entered_at": "2025-01-01T00:00:00+00:00",
                "revealed_node_count": 2,
                "visited_node_count": 1,
                "unresolved_local_node_count": 1,
                "blocked_frontier_count": 0,
                "reachable_unvisited_count": 1,
                "onboarding_status": "applied",
                "primary_frontier": {
                    "target_node_id": "craft_town",
                    "target_node_label": "Озёрный городок",
                    "plan_status": "reachable",
                },
                "source": "region_world_overview",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_region_entry_result",
        lambda _sess, player_id=None: {
            "result_id": "region-entry-1",
            "result_type": "first_region_entry",
            "summary": "Группа впервые закрепляется в регионе Стартовое пограничье.",
            "result_summary": "Группа впервые закрепляется в регионе Стартовое пограничье.",
            "region_id": "starter_frontier",
            "region_label": "Стартовое пограничье",
            "anchor_node_id": "start_trakt",
            "first_region_visit": True,
            "visit_count": 1,
            "source": "region_residency",
            "resolved_at": "2025-01-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_region_onboarding_result",
        lambda _sess, player_id=None: {
            "result_id": "region-onboarding-1",
            "result_type": "anchor_reveal_applied",
            "summary": "Стартовое пограничье открывает опорные пути вокруг стартового тракта.",
            "result_summary": "Стартовое пограничье открывает опорные пути вокруг стартового тракта.",
            "region_id": "starter_frontier",
            "region_label": "Стартовое пограничье",
            "anchor_node_id": "start_trakt",
            "revealed_node_ids": ["craft_town", "fortress_gate"],
            "revealed_route_ids": ["start_trakt->craft_town:move", "start_trakt->fortress_gate:move"],
            "onboarding_applied": True,
            "source": "region_residency",
            "resolved_at": "2025-01-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_region_onboarding_states",
        lambda _sess, player_id=None: [
            {
                "region_id": "starter_frontier",
                "region_label": "Стартовое пограничье",
                "status": "applied",
                "summary": "Стартовое пограничье открывает опорные пути вокруг стартового тракта.",
                "revealed_node_ids": ["craft_town", "fortress_gate"],
                "revealed_route_ids": ["start_trakt->craft_town:move", "start_trakt->fortress_gate:move"],
                "updated_at": "2025-01-01T00:00:00+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_region_world_overview",
        lambda _sess, player_id=None: {
            "current_region_id": "starter_frontier",
            "current_region_label": "Стартовое пограничье",
            "discovered_region_count": 1,
            "active_region_count": 1,
            "blocked_region_count": 0,
            "saturated_region_count": 0,
            "quiet_region_count": 0,
            "primary_region_focus": {
                "region_id": "starter_frontier",
                "region_label": "Стартовое пограничье",
                "region_status": "current_active_region",
                "summary": "Стартовое пограничье остаётся основным рабочим frontier-регионом группы.",
            },
            "region_summaries": [
                {
                    "region_id": "starter_frontier",
                    "region_label": "Стартовое пограничье",
                    "region_status": "current_active_region",
                    "summary": "Стартовое пограничье остаётся основным рабочим frontier-регионом группы.",
                    "current_region": True,
                    "visit_count": 1,
                    "first_entered_at": "2025-01-01T00:00:00+00:00",
                    "last_entered_at": "2025-01-01T00:00:00+00:00",
                    "revealed_node_count": 2,
                    "visited_node_count": 1,
                    "unresolved_local_node_count": 1,
                    "blocked_frontier_count": 0,
                    "reachable_unvisited_count": 1,
                    "onboarding_status": "applied",
                    "primary_frontier": {
                        "target_node_id": "craft_town",
                        "target_node_label": "Озёрный городок",
                        "plan_status": "reachable",
                    },
                    "source": "region_world_overview",
                }
            ],
            "summary": "Группа видит 1 открытых регионов: 1 активных, 0 упёршихся в блоки, 0 в основном выработанных и 0 тихих.",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_primary_region_focus",
        lambda _sess, player_id=None: {
            "region_id": "starter_frontier",
            "region_label": "Стартовое пограничье",
            "region_status": "current_active_region",
            "summary": "Стартовое пограничье остаётся основным рабочим frontier-регионом группы.",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_primary_region_focus_plan",
        lambda _sess, player_id=None: {
            "target_region_id": "starter_frontier",
            "target_region_label": "Стартовое пограничье",
            "plan_status": "current_region",
            "summary": "Группа уже находится в регионе Стартовое пограничье.",
            "current_region_id": "starter_frontier",
            "current_region_label": "Стартовое пограничье",
            "gateway_id": "",
            "gateway_label": "",
            "gateway_status": "",
            "gateway_source_node_id": "",
            "gateway_source_node_label": "",
            "path_node_ids": ["start_trakt"],
            "path_route_ids": [],
            "path_step_count": 0,
            "reachable": True,
            "blocked_reason": "",
            "suggested_command": "",
            "source": "region_target_guidance",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_region_target_options",
        lambda _sess, player_id=None: {
            "current_region_id": "starter_frontier",
            "current_region_label": "Стартовое пограничье",
            "primary_region_focus_plan": {
                "target_region_id": "starter_frontier",
                "target_region_label": "Стартовое пограничье",
                "plan_status": "current_region",
                "summary": "Группа уже находится в регионе Стартовое пограничье.",
                "current_region_id": "starter_frontier",
                "current_region_label": "Стартовое пограничье",
                "gateway_id": "",
                "gateway_label": "",
                "gateway_status": "",
                "gateway_source_node_id": "",
                "gateway_source_node_label": "",
                "path_node_ids": ["start_trakt"],
                "path_route_ids": [],
                "path_step_count": 0,
                "reachable": True,
                "blocked_reason": "",
                "suggested_command": "",
                "source": "region_target_guidance",
            },
            "target_region_plans": [
                {
                    "target_region_id": "starter_frontier",
                    "target_region_label": "Стартовое пограничье",
                    "plan_status": "current_region",
                    "summary": "Группа уже находится в регионе Стартовое пограничье.",
                    "current_region_id": "starter_frontier",
                    "current_region_label": "Стартовое пограничье",
                    "gateway_id": "",
                    "gateway_label": "",
                    "gateway_status": "",
                    "gateway_source_node_id": "",
                    "gateway_source_node_label": "",
                    "path_node_ids": ["start_trakt"],
                    "path_route_ids": [],
                    "path_step_count": 0,
                    "reachable": True,
                    "blocked_reason": "",
                    "suggested_command": "",
                    "source": "region_target_guidance",
                }
            ],
            "summary": "Из региона Стартовое пограничье собрано 1 canonical target-region plan(s).",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_last_region_transition_result",
        lambda _sess, player_id=None: {
            "result_id": "transition-1",
            "gateway_id": "forest_settlement_northwatch",
            "gateway_label": "Выход к северному рубежу",
            "result_type": "region_transition_completed",
            "summary": "Группа проходит через Выход к северному рубежу и выходит в регион Северный рубеж.",
            "result_summary": "Группа проходит через Выход к северному рубежу и выходит в регион Северный рубеж.",
            "source_region_id": "region",
            "source_region_label": "Лесной посёлок",
            "source_node_id": "forest_settlement",
            "target_region_id": "northwatch_frontier",
            "target_region_label": "Северный рубеж",
            "target_anchor_node_id": "northwatch_outpost",
            "transition_status": "completed",
            "applied_effects": ["region_transition:completed", "target_region:northwatch_frontier", "target_anchor:northwatch_outpost"],
            "source": "region_transition",
            "resolved_at": "2025-01-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_region_transition_state",
        lambda _sess, player_id=None: {
            "last_gateway_id": "forest_settlement_northwatch",
            "last_result_type": "region_transition_completed",
            "summary": "Группа проходит через Выход к северному рубежу и выходит в регион Северный рубеж.",
            "updated_at": "2025-01-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_route_planning",
        lambda _sess, player_id=None: {
            "reachable_destinations": [
                {
                    "target_node_id": "fortress_gate",
                    "target_node_label": "Ворота крепости",
                    "plan_status": "reachable",
                    "path_node_ids": ["start_trakt", "fortress_gate"],
                    "path_route_ids": ["start_trakt->fortress_gate:move"],
                    "step_count": 1,
                    "reachable": True,
                    "blocked_route_id": "",
                    "blocked_reason": "",
                    "first_unvisited": "fortress_gate",
                    "target_known": True,
                    "target_revealed": True,
                    "summary": "До Ворот крепости есть полностью открытый и проходимый путь.",
                }
            ],
            "route_frontiers": [
                {
                    "from_node_id": "start_trakt",
                    "to_node_id": "craft_town",
                    "route_id": "start_trakt->craft_town:move",
                    "frontier_type": "blocked_route",
                    "summary": "Маршрут start_trakt->craft_town:move видим, но сейчас заблокирован для группы.",
                }
            ],
        },
    )
    monkeypatch.setattr(
        state_builder,
        "get_current_group_navigation_options",
        lambda _sess, player_id=None: [
            {
                "route_id": "start_trakt->fortress_gate:move",
                "target_node_id": "fortress_gate",
                "target_label": "Ворота крепости",
                "target_node_type": "landmark",
                "action_kind": "move",
                "route_kind": "landmark_move",
                "traversal_kind": "gate_approach",
                "risk_band": "low",
                "terrain_hint": "fortified",
                "travel_tags": ["fortified"],
                "source": "registry",
                "known": True,
                "revealed": True,
                "visible": True,
                "access_state": "open",
                "is_traversable": True,
                "blocked": False,
            }
        ],
    )
    monkeypatch.setattr(state_builder, "snapshot_combat_state", lambda _session_id: None)

    db = _FakeDb([[player], [], [], []])
    payload = asyncio.run(state_builder.build_state(db, sess))

    assert payload["session"]["current_group_id"] == "main"
    assert payload["game"]["current_group_node_context"] == {
        "node_summary": {
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
            "node_type": "zone",
            "area_label": "Стартовый тракт",
            "zone_band": "safe",
            "settlement_kind": "roadside",
            "environment_hint": "roadland",
            "safe_rest_hint": True,
        },
        "node_state_flags": ["old_road_cleared"],
        "state_notes": ["У старой дороги видны следы недавней расчистки, и проход к руинам читается увереннее."],
        "contextual_actions": [
            {"action_id": "navigate", "action_key": "navigate", "label": "Продолжить путь", "action_type": "action", "action_kind": "navigate", "status": "available", "available": True, "exhausted": False},
            {"action_id": "inspect", "action_key": "inspect", "label": "Осмотреться", "action_type": "action", "action_kind": "inspect", "status": "available", "available": True, "exhausted": False},
            {"action_id": "wait", "action_key": "wait", "label": "Подождать", "action_type": "action", "action_kind": "wait", "status": "available", "available": True, "exhausted": False},
            {"action_id": "camp", "action_key": "camp", "label": "Разбить лагерь", "action_type": "action", "action_kind": "camp", "status": "available", "available": True, "exhausted": False},
            {"action_id": "rest_hint", "action_key": "rest_hint", "label": "Есть место для передышки", "action_type": "hint", "action_kind": "rest_hint", "status": "available", "available": False, "exhausted": False},
        ],
        "available_services": [
            {
                "service_id": "start_trakt:safe_rest",
                "service_key": "safe_rest",
                "label": "Безопасный отдых",
                "service_type": "rest",
                "service_kind": "rest",
                "summary": "Можно перевести дух и переждать путь в сравнительно безопасных условиях.",
                "source": "registry",
                "available": True,
                "status": "available",
                "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
            }
        ],
        "service_actions": [
            {"action_key": "use_service", "label": "Воспользоваться услугой", "action_type": "action"},
        ],
    }
    assert payload["game"]["current_group_node_detail"] == {
        "node_id": "start_trakt",
        "label": "Стартовый тракт",
        "node_type": "zone",
        "area_label": "Стартовый тракт",
        "short_description": "Широкий тракт у стартового лагеря, где сходятся безопасные дороги региона.",
        "inspect_summary": "По тракту удобно держать путь к воротам крепости и к озёрному городку.",
        "travel_note": "Хороший ориентир для сбора группы и спокойного перехода.",
        "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
        "node_state_flags": ["old_road_cleared"],
        "state_notes": ["Сломанные ветви и свежие борозды в грязи показывают, что завал уже разбирали совсем недавно."],
    }
    assert payload["game"]["current_group_last_inspect_result"] == {
        "node_id": "start_trakt",
        "label": "Стартовый тракт",
        "node_type": "zone",
        "inspect_summary": "По тракту удобно держать путь к воротам крепости и к озёрному городку.",
        "short_description": "Широкий тракт у стартового лагеря, где сходятся безопасные дороги региона.",
        "travel_note": "Хороший ориентир для сбора группы и спокойного перехода.",
        "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
        "state_notes": ["Сломанные ветви и свежие борозды в грязи показывают, что завал уже разбирали совсем недавно."],
        "source": "test",
        "inspected_at": "2026-03-14T00:00:00+00:00",
    }
    assert payload["game"]["current_group_node_services"] == [
        {
            "service_id": "start_trakt:safe_rest",
            "service_key": "safe_rest",
            "label": "Безопасный отдых",
            "service_type": "rest",
            "service_kind": "rest",
            "summary": "Можно перевести дух и переждать путь в сравнительно безопасных условиях.",
            "source": "registry",
            "available": True,
            "status": "available",
            "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
        }
    ]
    assert payload["game"]["current_group_last_service_result"] == {
        "result_id": "service-out-1",
        "service_id": "start_trakt:safe_rest",
        "service_key": "safe_rest",
        "service_label": "Безопасный отдых",
        "label": "Безопасный отдых",
        "result_type": "lodging_received",
        "service_type": "rest",
        "service_kind": "rest",
        "summary": "Можно перевести дух и переждать путь в сравнительно безопасных условиях.",
        "result_summary": "Место подходит для короткой передышки без немедленной дорожной угрозы.",
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "applied_effects": ["lodging_received"],
        "discovered_notes": [],
        "reveal_applied": False,
        "source": "test",
        "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
        "resolved_at": "2026-03-14T00:05:00+00:00",
    }
    assert payload["game"]["current_group_service_states"] == [
        {
            "service_id": "start_trakt:safe_rest",
            "status": "resolved",
            "result_type": "lodging_received",
            "summary": "Место подходит для короткой передышки без немедленной дорожной угрозы.",
            "source": "test",
            "updated_at": "2026-03-14T00:05:10+00:00",
        }
    ]
    assert payload["game"]["current_group_travel_event"] == {
        "event_id": "evt-road",
        "event_key": "roadside_finding",
        "event_type": "roadside_hook",
        "summary": "У обочины лежит приметная дорожная находка.",
        "route_snapshot": {
            "allowed": True,
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "Восточный берег",
        },
        "source": "travel",
        "active": True,
        "resolved": False,
    }
    assert payload["game"]["current_group_last_camp_result"] == {
        "result_id": "camp-out-1",
        "result_type": "sheltered_rest",
        "summary": "У часовни есть укрытие для спокойной стоянки.",
        "result_summary": "Группа устраивается в укрытии и получает спокойную передышку.",
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "rest_quality": "sheltered",
        "risk_band": "low",
        "source": "test",
        "applied_effects": ["rest_quality:sheltered", "safety_note:shelter_found"],
        "resolved_at": "2026-03-14T00:07:00+00:00",
    }
    assert payload["game"]["current_group_last_scout_result"] == {
        "result_id": "scout-out-1",
        "result_type": "route_revealed",
        "summary": "Разведка у тракта приносит новый маршрутный результат.",
        "result_summary": "Разведка проясняет соседний маршрут и добавляет новый понятный выход из текущей точки.",
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "discovery_scope": "adjacent_route",
        "discovered_node_ids": ["craft_town"],
        "discovered_route_ids": ["start_trakt->craft_town"],
        "discovered_notes": ["С тракта замечается надёжный боковой путь к озёрному городку."],
        "reveal_applied": True,
        "source": "test",
        "resolved_at": "2026-03-14T00:08:00+00:00",
    }
    assert payload["game"]["current_group_last_context_action_result"] == {
        "result_id": "ctx-out-1",
        "action_id": "clear_old_road",
        "action_label": "Расчистить старую дорогу",
        "result_type": "route_cleared",
        "summary": "Разобрать завал и вернуть проход к разрушенному посёлку.",
        "result_summary": "Группа убирает завал с лесной дороги и открывает устойчивый проход к разрушенному посёлку.",
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "applied_effects": ["route_access:cleared"],
        "source": "test",
        "resolved_at": "2026-03-14T00:09:00+00:00",
    }
    assert payload["game"]["current_group_route_access_states"] == [
        {
            "route_id": "start_trakt->craft_town:move",
            "access_state": "blocked",
            "is_traversable": False,
            "summary": "Путь к городку перекрыт.",
            "block_reason": "blocked_path",
            "source": "test",
            "updated_at": "2026-03-15T00:09:00+00:00",
        }
    ]
    assert payload["game"]["current_group_context_action_states"] == [
        {
            "action_id": "clear_old_road",
            "status": "completed",
            "result_type": "route_cleared",
            "summary": "Группа убирает завал с лесной дороги и открывает устойчивый проход к разрушенному посёлку.",
            "source": "test",
            "updated_at": "2026-03-15T00:09:30+00:00",
        }
    ]
    assert payload["game"]["current_group_node_states"] == [
        {
            "node_id": "start_trakt",
            "state_flags": ["old_road_cleared"],
            "summary": "На лесной дороге заметны следы недавней расчистки старого прохода.",
            "source": "test",
            "updated_at": "2026-03-15T00:09:45+00:00",
        }
    ]
    assert payload["game"]["current_group_current_node_state"] == {
        "node_id": "start_trakt",
        "state_flags": ["old_road_cleared"],
        "summary": "На лесной дороге заметны следы недавней расчистки старого прохода.",
        "source": "test",
        "updated_at": "2026-03-15T00:09:45+00:00",
    }
    assert payload["game"]["current_group_last_travel_event_outcome"] == {
        "outcome_id": "out-road",
        "event_key": "roadside_finding",
        "event_type": "roadside_hook",
        "outcome_type": "finding_note",
        "summary": "У обочины лежит приметная дорожная находка.",
        "result_summary": "Группа отмечает дорожную примету и получает полезную заметку о ближайшем пути.",
        "applied_effects": ["event_closed", "travel_hint_recorded"],
        "source": "travel",
        "resolved_at": "2026-03-14T00:10:00+00:00",
    }
    assert payload["game"]["current_group_map_intel"] == [
        {
            "entry_id": "intel-1",
            "entry_type": "route_hint",
            "title": "Разведка у Стартового тракта",
            "summary": "Разведка у Стартового тракта приносит новый маршрутный результат.",
            "result_summary": "С тракта замечается надёжный боковой путь к озёрному городку.",
            "source_kind": "scout",
            "source_id": "scout-out-1",
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "related_node_ids": ["craft_town"],
            "related_route_ids": ["start_trakt->craft_town"],
            "tags": ["route_hint", "start_trakt", "craft_town"],
            "dedupe_key": "scout|start_trakt|route_revealed|craft_town|start_trakt->craft_town|route",
            "discovered_at": "2026-03-14T00:08:00+00:00",
        }
    ]
    assert payload["game"]["current_group_recent_map_intel"] == payload["game"]["current_group_map_intel"]
    assert payload["game"]["current_group_last_arrival_result"] == {
        "result_id": "arrival-1",
        "result_type": "first_arrival",
        "summary": "Группа прибывает в Стартовый тракт.",
        "result_summary": "Это первое фактическое прибытие группы в данную точку карты.",
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "route_id": "camp->start_trakt:move",
        "first_visit": True,
        "visit_count": 1,
        "source": "test",
        "applied_effects": ["visit_count:1", "visit:first_time"],
        "resolved_at": "2026-03-14T00:04:00+00:00",
    }
    assert payload["game"]["current_group_last_node_entry_result"] == {
        "result_id": "entry-1",
        "result_type": "changed_place",
        "title": "Стартовый тракт изменился",
        "summary": "На входе в тракт заметны следы недавних перемен.",
        "result_summary": "Тракт встречает группу заметными следами недавней расчистки и выглядит иначе, чем прежде.",
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "visit_count": 1,
        "first_visit": True,
        "node_state_flags": ["old_road_cleared"],
        "applied_effects": ["visit_count:1", "entry_type:changed_place", "node_state_flags:old_road_cleared"],
        "source": "test",
        "resolved_at": "2026-03-14T00:04:10+00:00",
    }
    assert payload["game"]["current_group_current_node_entry_state"] == {
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "entry_count": 1,
        "last_entry_type": "changed_place",
        "summary": "Текущий вход в тракт отмечен как изменившееся место.",
        "source": "test",
        "updated_at": "2026-03-14T00:04:11+00:00",
    }
    assert payload["game"]["current_group_node_entry_states"] == [
        {
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "entry_count": 1,
            "last_entry_type": "changed_place",
            "summary": "Текущий вход в тракт отмечен как изменившееся место.",
            "source": "test",
            "updated_at": "2026-03-14T00:04:11+00:00",
        }
    ]
    assert payload["game"]["current_group_last_destination_event_result"] == {
        "result_id": "dest-1",
        "event_id": "craft_town_arrival_notice",
        "event_label": "Береговая наводка у городка",
        "result_type": "settlement_notice",
        "title": "У причала быстро находят ориентиры",
        "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
        "result_summary": "Озёрный городок встречает группу короткой береговой наводкой и подсказывает, где проще держать следующий ход.",
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "visit_count": 1,
        "first_visit": True,
        "applied_effects": ["destination_notice:craft_town", "visit_count:1", "destination_event:settlement_notice"],
        "source": "test",
        "resolved_at": "2026-03-14T00:04:12+00:00",
    }
    assert payload["game"]["current_group_current_node_destination_event_state"] == {
        "event_id": "craft_town_arrival_notice",
        "node_id": "start_trakt",
        "status": "completed",
        "result_type": "settlement_notice",
        "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
        "source": "test",
        "updated_at": "2026-03-14T00:04:13+00:00",
    }
    assert payload["game"]["current_group_destination_event_states"] == [
        {
            "event_id": "craft_town_arrival_notice",
            "node_id": "start_trakt",
            "status": "completed",
            "result_type": "settlement_notice",
            "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
            "source": "test",
            "updated_at": "2026-03-14T00:04:13+00:00",
        }
    ]
    assert payload["game"]["current_group_current_node_visit_state"] == {
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "visit_count": 1,
        "first_visited_at": "2026-03-14T00:04:00+00:00",
        "last_visited_at": "2026-03-14T00:04:00+00:00",
        "last_result_type": "first_arrival",
        "summary": "Группа впервые достигает Стартового тракта.",
    }
    assert payload["game"]["current_group_node_visit_states"] == [
        {
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "visit_count": 1,
            "first_visited_at": "2026-03-14T00:04:00+00:00",
            "last_visited_at": "2026-03-14T00:04:00+00:00",
            "last_result_type": "first_arrival",
            "summary": "Группа впервые достигает Стартового тракта.",
        }
    ]
    assert payload["game"]["current_group_route_traversal_states"] == [
        {
            "route_id": "camp->start_trakt:move",
            "traversal_count": 1,
            "first_traversed_at": "2026-03-14T00:04:00+00:00",
            "last_traversed_at": "2026-03-14T00:04:00+00:00",
            "summary": "Группа проходит маршрутом к Стартовому тракту.",
        }
    ]
    assert payload["game"]["current_group_active_journey"] == {
        "journey_id": "journey-1",
        "target_node_id": "fortress_gate",
        "target_node_label": "Ворота крепости",
        "journey_status": "in_progress",
        "path_node_ids": ["start_trakt", "fortress_gate"],
        "path_route_ids": ["start_trakt->fortress_gate:move"],
        "next_node_id": "fortress_gate",
        "next_route_id": "start_trakt->fortress_gate:move",
        "completed_step_count": 0,
        "total_step_count": 1,
        "source": "test",
        "created_at": "2026-03-14T00:03:00+00:00",
        "updated_at": "2026-03-14T00:03:10+00:00",
    }
    assert payload["game"]["current_group_last_journey_result"] == {
        "result_id": "journey-res-1",
        "result_type": "journey_advanced",
        "summary": "Группа продвигается к Воротам крепости.",
        "result_summary": "Путешествие к Воротам крепости продвинулось на один переход.",
        "journey_id": "journey-1",
        "target_node_id": "fortress_gate",
        "target_node_label": "Ворота крепости",
        "next_node_id": "fortress_gate",
        "next_route_id": "start_trakt->fortress_gate:move",
        "completed_step_count": 0,
        "total_step_count": 1,
        "source": "test",
        "resolved_at": "2026-03-14T00:03:10+00:00",
    }
    assert payload["game"]["current_group_route_planning"] == {
        "reachable_destinations": [
            {
                "target_node_id": "fortress_gate",
                "target_node_label": "Ворота крепости",
                "plan_status": "reachable",
                "path_node_ids": ["start_trakt", "fortress_gate"],
                "path_route_ids": ["start_trakt->fortress_gate:move"],
                "step_count": 1,
                "reachable": True,
                "blocked_route_id": "",
                "blocked_reason": "",
                "first_unvisited": "fortress_gate",
                "target_known": True,
                "target_revealed": True,
                "summary": "До Ворот крепости есть полностью открытый и проходимый путь.",
            }
        ],
        "route_frontiers": [
            {
                "from_node_id": "start_trakt",
                "to_node_id": "craft_town",
                "route_id": "start_trakt->craft_town:move",
                "frontier_type": "blocked_route",
                "summary": "Маршрут start_trakt->craft_town:move видим, но сейчас заблокирован для группы.",
            }
        ],
    }
    assert payload["game"]["current_group_reachable_destinations"] == payload["game"]["current_group_route_planning"]["reachable_destinations"]
    assert payload["game"]["current_group_route_frontiers"] == payload["game"]["current_group_route_planning"]["route_frontiers"]
    assert payload["game"]["current_group_exploration_leads"] == [
        {
            "lead_id": "active_journey:journey-1",
            "lead_type": "active_journey",
            "priority_band": "high",
            "title": "Активный путь: Ворота крепости",
            "summary": "У группы есть in_progress journey к Ворота крепости (0/1 шагов).",
            "target_node_id": "fortress_gate",
            "target_node_label": "Ворота крепости",
            "route_id": "start_trakt->fortress_gate:move",
            "source_kind": "journey",
            "source_ref": "journey-1",
            "reachable": True,
            "blocked": False,
            "blocked_reason": "",
            "first_unvisited": "fortress_gate",
            "has_active_journey": True,
            "suggested_command": "group continue",
            "tags": ["journey", "in_progress"],
        }
    ]
    assert payload["game"]["current_group_primary_exploration_lead"] == payload["game"]["current_group_exploration_leads"][0]
    assert payload["game"]["current_group_local_interaction_surface"] == {
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "available_actions": [
            {
                "action_id": "navigate",
                "availability_status": "available",
                "available": True,
            }
        ],
        "locked_actions": [
            {
                "action_id": "rest_hint",
                "availability_status": "unavailable",
                "available": False,
            }
        ],
        "available_services": [
            {
                "service_id": "start_trakt:safe_rest",
                "availability_status": "available",
                "available": True,
            }
        ],
        "locked_services": [],
        "summary": "У Стартового тракта доступно 1 действий и 1 услуг; ограничено 1 действий и 0 услуг.",
    }
    assert payload["game"]["current_group_current_node_progress"] == {
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "progression_status": "partially_resolved",
        "summary": "В Стартовом тракте часть локальных возможностей уже закрыта, но остаётся активный местный контент.",
        "visit_count": 2,
        "first_visit": False,
        "has_node_entry": True,
        "has_destination_event": True,
        "available_action_count": 1,
        "locked_action_count": 1,
        "completed_action_count": 1,
        "available_service_count": 1,
        "locked_service_count": 0,
        "completed_service_count": 1,
        "node_state_flags": ["old_road_cleared"],
        "unresolved_local_opportunities": ["Продолжить путь", "Безопасный отдых"],
        "source": "node_progression",
    }
    assert payload["game"]["current_group_region_exploration_summary"] == {
        "region_id": "region",
        "region_label": "Стартовый тракт",
        "progression_status": "active_frontier",
        "summary": "У группы остаются достижимые непосещённые точки, так что frontier региона ещё активен.",
        "current_node_id": "start_trakt",
        "current_node_label": "Стартовый тракт",
        "revealed_node_count": 3,
        "visited_node_count": 2,
        "reachable_unvisited_count": 1,
        "blocked_frontier_count": 1,
        "quiet_node_count": 0,
        "active_local_node_count": 1,
        "locally_resolved_node_count": 1,
        "current_primary_frontier": {
            "target_node_id": "fortress_gate",
            "target_node_label": "Ворота крепости",
            "plan_status": "reachable",
        },
        "current_primary_lead": {
            "lead_id": "active_journey:journey-1",
            "lead_type": "active_journey",
            "title": "Активный путь: Ворота крепости",
        },
        "source": "region_exploration",
    }
    assert payload["game"]["current_group_region_frontier_summary"] == {
        "blocked_frontiers": [
            {
                "from_node_id": "start_trakt",
                "to_node_id": "craft_town",
                "route_id": "start_trakt->craft_town:move",
                "frontier_type": "blocked_route",
                "summary": "Маршрут видим, но заблокирован.",
            }
        ],
        "reachable_unvisited_nodes": [
            {
                "target_node_id": "fortress_gate",
                "target_node_label": "Ворота крепости",
                "plan_status": "reachable",
                "summary": "До Ворот крепости есть полностью открытый и проходимый путь.",
            }
        ],
        "unresolved_local_nodes": [
            {
                "node_id": "start_trakt",
                "node_label": "Стартовый тракт",
                "progression_status": "partially_resolved",
                "summary": "В Стартовом тракте часть локальных возможностей уже закрыта, но остаётся активный местный контент.",
            }
        ],
        "summary": "У группы 1 достижимых непосещённых точек, 1 заблокированных frontier-веток и 1 локально незавершённых узлов.",
    }
    assert payload["game"]["current_group_region_gateways"] == [
        {
            "gateway_id": "forest_settlement_northwatch",
            "gateway_label": "Выход к северному рубежу",
            "gateway_status": "open",
            "summary": "Лесной посёлок выводит к региону Северный рубеж.",
            "source_node_id": "forest_settlement",
            "source_node_label": "Лесной посёлок",
            "route_id": "forest_settlement->old_fortress_edge:move",
            "target_region_id": "northwatch_frontier",
            "target_region_label": "Северный рубеж",
            "target_anchor_node_id": "northwatch_outpost",
            "reachable": True,
            "blocked": False,
            "locked": False,
            "blocked_reason": "",
            "unlock_hint": "Сначала собрать лесные припасы перед дальним выходом к северному рубежу.",
            "future_stub": False,
            "source": "region_gateway",
        }
    ]
    assert payload["game"]["current_group_primary_region_gateway"] == {
        "gateway_id": "forest_settlement_northwatch",
        "gateway_label": "Выход к северному рубежу",
        "gateway_status": "open",
    }
    assert payload["game"]["current_group_current_region_state"] == {
        "region_id": "starter_frontier",
        "region_label": "Стартовое пограничье",
        "current_node_id": "start_trakt",
        "entered_at": "2025-01-01T00:00:00+00:00",
        "visit_count": 1,
        "source": "region_residency",
    }
    assert payload["game"]["current_group_discovered_regions"] == [
        {
            "region_id": "starter_frontier",
            "region_label": "Стартовое пограничье",
            "visit_count": 1,
            "first_entered_at": "2025-01-01T00:00:00+00:00",
            "last_entered_at": "2025-01-01T00:00:00+00:00",
            "first_anchor_node_id": "start_trakt",
            "last_anchor_node_id": "start_trakt",
            "summary": "Группа впервые входит в регион Стартовое пограничье.",
        }
    ]
    assert payload["game"]["current_group_discovered_region_summaries"] == [
        {
            "region_id": "starter_frontier",
            "region_label": "Стартовое пограничье",
            "region_status": "current_active_region",
            "summary": "Стартовое пограничье остаётся основным рабочим frontier-регионом группы.",
            "current_region": True,
            "visit_count": 1,
            "first_entered_at": "2025-01-01T00:00:00+00:00",
            "last_entered_at": "2025-01-01T00:00:00+00:00",
            "revealed_node_count": 2,
            "visited_node_count": 1,
            "unresolved_local_node_count": 1,
            "blocked_frontier_count": 0,
            "reachable_unvisited_count": 1,
            "onboarding_status": "applied",
            "primary_frontier": {
                "target_node_id": "craft_town",
                "target_node_label": "Озёрный городок",
                "plan_status": "reachable",
            },
            "source": "region_world_overview",
        }
    ]
    assert payload["game"]["current_group_last_region_entry_result"] == {
        "result_id": "region-entry-1",
        "result_type": "first_region_entry",
        "summary": "Группа впервые закрепляется в регионе Стартовое пограничье.",
        "result_summary": "Группа впервые закрепляется в регионе Стартовое пограничье.",
        "region_id": "starter_frontier",
        "region_label": "Стартовое пограничье",
        "anchor_node_id": "start_trakt",
        "first_region_visit": True,
        "visit_count": 1,
        "source": "region_residency",
        "resolved_at": "2025-01-01T00:00:00+00:00",
    }
    assert payload["game"]["current_group_last_region_onboarding_result"] == {
        "result_id": "region-onboarding-1",
        "result_type": "anchor_reveal_applied",
        "summary": "Стартовое пограничье открывает опорные пути вокруг стартового тракта.",
        "result_summary": "Стартовое пограничье открывает опорные пути вокруг стартового тракта.",
        "region_id": "starter_frontier",
        "region_label": "Стартовое пограничье",
        "anchor_node_id": "start_trakt",
        "revealed_node_ids": ["craft_town", "fortress_gate"],
        "revealed_route_ids": ["start_trakt->craft_town:move", "start_trakt->fortress_gate:move"],
        "onboarding_applied": True,
        "source": "region_residency",
        "resolved_at": "2025-01-01T00:00:00+00:00",
    }
    assert payload["game"]["current_group_region_onboarding_states"] == [
        {
            "region_id": "starter_frontier",
            "region_label": "Стартовое пограничье",
            "status": "applied",
            "summary": "Стартовое пограничье открывает опорные пути вокруг стартового тракта.",
            "revealed_node_ids": ["craft_town", "fortress_gate"],
            "revealed_route_ids": ["start_trakt->craft_town:move", "start_trakt->fortress_gate:move"],
            "updated_at": "2025-01-01T00:00:00+00:00",
        }
    ]
    assert payload["game"]["current_group_region_world_overview"] == {
        "current_region_id": "starter_frontier",
        "current_region_label": "Стартовое пограничье",
        "discovered_region_count": 1,
        "active_region_count": 1,
        "blocked_region_count": 0,
        "saturated_region_count": 0,
        "quiet_region_count": 0,
        "primary_region_focus": {
            "region_id": "starter_frontier",
            "region_label": "Стартовое пограничье",
            "region_status": "current_active_region",
            "summary": "Стартовое пограничье остаётся основным рабочим frontier-регионом группы.",
        },
        "region_summaries": [
            {
                "region_id": "starter_frontier",
                "region_label": "Стартовое пограничье",
                "region_status": "current_active_region",
                "summary": "Стартовое пограничье остаётся основным рабочим frontier-регионом группы.",
                "current_region": True,
                "visit_count": 1,
                "first_entered_at": "2025-01-01T00:00:00+00:00",
                "last_entered_at": "2025-01-01T00:00:00+00:00",
                "revealed_node_count": 2,
                "visited_node_count": 1,
                "unresolved_local_node_count": 1,
                "blocked_frontier_count": 0,
                "reachable_unvisited_count": 1,
                "onboarding_status": "applied",
                "primary_frontier": {
                    "target_node_id": "craft_town",
                    "target_node_label": "Озёрный городок",
                    "plan_status": "reachable",
                },
                "source": "region_world_overview",
            }
        ],
        "summary": "Группа видит 1 открытых регионов: 1 активных, 0 упёршихся в блоки, 0 в основном выработанных и 0 тихих.",
    }
    assert payload["game"]["current_group_primary_region_focus"] == {
        "region_id": "starter_frontier",
        "region_label": "Стартовое пограничье",
        "region_status": "current_active_region",
        "summary": "Стартовое пограничье остаётся основным рабочим frontier-регионом группы.",
    }
    assert payload["game"]["current_group_primary_region_focus_plan"] == {
        "target_region_id": "starter_frontier",
        "target_region_label": "Стартовое пограничье",
        "plan_status": "current_region",
        "summary": "Группа уже находится в регионе Стартовое пограничье.",
        "current_region_id": "starter_frontier",
        "current_region_label": "Стартовое пограничье",
        "gateway_id": "",
        "gateway_label": "",
        "gateway_status": "",
        "gateway_source_node_id": "",
        "gateway_source_node_label": "",
        "path_node_ids": ["start_trakt"],
        "path_route_ids": [],
        "path_step_count": 0,
        "reachable": True,
        "blocked_reason": "",
        "suggested_command": "",
        "source": "region_target_guidance",
    }
    assert payload["game"]["current_group_region_target_options"] == {
        "current_region_id": "starter_frontier",
        "current_region_label": "Стартовое пограничье",
        "primary_region_focus_plan": {
            "target_region_id": "starter_frontier",
            "target_region_label": "Стартовое пограничье",
            "plan_status": "current_region",
            "summary": "Группа уже находится в регионе Стартовое пограничье.",
            "current_region_id": "starter_frontier",
            "current_region_label": "Стартовое пограничье",
            "gateway_id": "",
            "gateway_label": "",
            "gateway_status": "",
            "gateway_source_node_id": "",
            "gateway_source_node_label": "",
            "path_node_ids": ["start_trakt"],
            "path_route_ids": [],
            "path_step_count": 0,
            "reachable": True,
            "blocked_reason": "",
            "suggested_command": "",
            "source": "region_target_guidance",
        },
        "target_region_plans": [
            {
                "target_region_id": "starter_frontier",
                "target_region_label": "Стартовое пограничье",
                "plan_status": "current_region",
                "summary": "Группа уже находится в регионе Стартовое пограничье.",
                "current_region_id": "starter_frontier",
                "current_region_label": "Стартовое пограничье",
                "gateway_id": "",
                "gateway_label": "",
                "gateway_status": "",
                "gateway_source_node_id": "",
                "gateway_source_node_label": "",
                "path_node_ids": ["start_trakt"],
                "path_route_ids": [],
                "path_step_count": 0,
                "reachable": True,
                "blocked_reason": "",
                "suggested_command": "",
                "source": "region_target_guidance",
            }
        ],
        "summary": "Из региона Стартовое пограничье собрано 1 canonical target-region plan(s).",
    }
    assert payload["game"]["current_group_last_region_transition_result"] == {
        "result_id": "transition-1",
        "gateway_id": "forest_settlement_northwatch",
        "gateway_label": "Выход к северному рубежу",
        "result_type": "region_transition_completed",
        "summary": "Группа проходит через Выход к северному рубежу и выходит в регион Северный рубеж.",
        "result_summary": "Группа проходит через Выход к северному рубежу и выходит в регион Северный рубеж.",
        "source_region_id": "region",
        "source_region_label": "Лесной посёлок",
        "source_node_id": "forest_settlement",
        "target_region_id": "northwatch_frontier",
        "target_region_label": "Северный рубеж",
        "target_anchor_node_id": "northwatch_outpost",
        "transition_status": "completed",
        "applied_effects": ["region_transition:completed", "target_region:northwatch_frontier", "target_anchor:northwatch_outpost"],
        "source": "region_transition",
        "resolved_at": "2025-01-01T00:00:00+00:00",
    }
    assert payload["game"]["current_group_region_transition_state"] == {
        "last_gateway_id": "forest_settlement_northwatch",
        "last_result_type": "region_transition_completed",
        "summary": "Группа проходит через Выход к северному рубежу и выходит в регион Северный рубеж.",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }
    assert payload["game"]["current_group_navigation_options"] == [
        {
            "route_id": "start_trakt->fortress_gate:move",
            "target_node_id": "fortress_gate",
            "target_label": "Ворота крепости",
            "target_node_type": "landmark",
            "action_kind": "move",
            "route_kind": "landmark_move",
            "traversal_kind": "gate_approach",
            "risk_band": "low",
            "terrain_hint": "fortified",
            "travel_tags": ["fortified"],
            "source": "registry",
            "known": True,
            "revealed": True,
            "visible": True,
            "access_state": "open",
            "is_traversable": True,
            "blocked": False,
        }
    ]
    assert payload["game"]["groups"]["main"]["map_intel_count"] == 0
    assert payload["game"]["groups"]["main"]["visited_node_count"] == 0
    assert payload["game"]["groups"]["main"]["traversed_route_count"] == 0
    assert payload["game"]["groups"]["main"]["last_node_entry_result_summary"] == {
        "result_id": "entry-1",
        "result_type": "changed_place",
        "title": "Стартовый тракт изменился",
        "summary": "На входе в тракт заметны следы недавних перемен.",
        "result_summary": "Тракт встречает группу заметными следами недавней расчистки и выглядит иначе, чем прежде.",
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "visit_count": 1,
        "first_visit": True,
        "node_state_flags": ["old_road_cleared"],
        "applied_effects": ["visit_count:1", "entry_type:changed_place", "node_state_flags:old_road_cleared"],
        "source": "test",
        "resolved_at": "2026-03-14T00:04:10+00:00",
    }
    assert payload["game"]["groups"]["main"]["node_entry_states"] == [
        {
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "entry_count": 1,
            "last_entry_type": "changed_place",
            "summary": "Текущий вход в тракт отмечен как изменившееся место.",
            "source": "test",
            "updated_at": "2026-03-14T00:04:11+00:00",
        }
    ]
    assert payload["game"]["groups"]["main"]["last_destination_event_result_summary"] == {
        "result_id": "dest-1",
        "event_id": "craft_town_arrival_notice",
        "event_label": "Береговая наводка у городка",
        "result_type": "settlement_notice",
        "title": "У причала быстро находят ориентиры",
        "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
        "result_summary": "Озёрный городок встречает группу короткой береговой наводкой и подсказывает, где проще держать следующий ход.",
        "node_id": "start_trakt",
        "node_label": "Стартовый тракт",
        "visit_count": 1,
        "first_visit": True,
        "applied_effects": ["destination_notice:craft_town", "visit_count:1", "destination_event:settlement_notice"],
        "source": "test",
        "resolved_at": "2026-03-14T00:04:12+00:00",
    }
    assert payload["game"]["groups"]["main"]["destination_event_states"] == [
        {
            "event_id": "craft_town_arrival_notice",
            "node_id": "start_trakt",
            "status": "completed",
            "result_type": "settlement_notice",
            "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
            "source": "test",
            "updated_at": "2026-03-14T00:04:13+00:00",
        }
    ]


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
            "last_camp_result": {
                "result_id": "camp-out-2",
                "result_type": "uneasy_rest",
                "summary": "Лагерь у лагеря остаётся настороженным.",
                "result_summary": "Группа отдыхает вполглаза и не получает полной безопасности.",
                "node_id": "camp",
                "node_label": "camp",
                "rest_quality": "uneasy",
                "risk_band": "medium",
                "source": "test",
                "applied_effects": ["rest_quality:uneasy", "safety_note:border_watch"],
                "resolved_at": "2026-03-14T00:06:00+00:00",
            },
            "last_scout_result": {
                "result_id": "scout-out-2",
                "result_type": "local_clue_found",
                "summary": "Разведка у лагеря даёт локальную зацепку.",
                "result_summary": "Нового выхода разведка не открывает, но место даёт полезную локальную подсказку.",
                "node_id": "camp",
                "node_label": "camp",
                "discovery_scope": "local_area",
                "discovered_node_ids": [],
                "discovered_route_ids": [],
                "discovered_notes": ["Лагерь остаётся удобной точкой сбора перед выходом."],
                "reveal_applied": False,
                "source": "test",
                "resolved_at": "2026-03-14T00:07:00+00:00",
            },
            "last_context_action_result": {
                "result_id": "ctx-out-2",
                "action_id": "clear_old_road",
                "action_label": "Расчистить старую дорогу",
                "result_type": "route_cleared",
                "summary": "Разобрать завал и вернуть проход к северным воротам.",
                "result_summary": "Группа очищает локальный завал и фиксирует новый проходимый подход.",
                "node_id": "camp",
                "node_label": "camp",
                "applied_effects": ["route_access:cleared"],
                "source": "test",
                "resolved_at": "2026-03-14T00:07:30+00:00",
            },
            "context_action_states": {
                "clear_old_road": {
                    "action_id": "clear_old_road",
                    "status": "completed",
                    "result_type": "route_cleared",
                    "summary": "Группа очищает локальный завал и фиксирует новый проходимый подход.",
                    "source": "test",
                    "updated_at": "2026-03-14T00:07:31+00:00",
                }
            },
            "node_states": {
                "camp": {
                    "node_id": "camp",
                    "state_flags": ["camp_watch_checked"],
                    "summary": "Лагерная точка уже осмотрена и отмечена для следующего сбора.",
                    "source": "test",
                    "updated_at": "2026-03-14T00:07:32+00:00",
                }
            },
            "route_access_states": {
                "camp->north-gate:move": {
                    "route_id": "camp->north-gate:move",
                    "access_state": "cleared",
                    "is_traversable": True,
                    "summary": "Подход к северным воротам снова открыт.",
                    "source": "test",
                    "updated_at": "2026-03-15T00:06:00+00:00",
                }
            },
            "map_intel_entries": [
                {
                    "entry_id": "intel-camp-1",
                    "entry_type": "clue",
                    "title": "Лагерная заметка",
                    "summary": "Лагерь остаётся удобной точкой сбора.",
                    "result_summary": "Лагерь остаётся удобной точкой сбора перед выходом.",
                    "source_kind": "scout",
                    "source_id": "scout-out-2",
                    "node_id": "camp",
                    "node_label": "camp",
                    "related_node_ids": [],
                    "related_route_ids": [],
                    "tags": ["clue", "camp"],
                    "dedupe_key": "scout|camp|local_clue",
                    "discovered_at": "2026-03-14T00:07:00+00:00",
                }
            ],
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
                "route_source": "registry",
                "traversal_kind": "gate_approach",
                "risk_band": "low",
                "terrain_hint": "fortified",
                "travel_tags": ["fortified"],
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
                    "source": "registry",
                    "traversal_kind": "gate_approach",
                    "risk_band": "low",
                    "terrain_hint": "fortified",
                    "travel_tags": ["fortified"],
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
                "paused": False,
                "resume_allowed": True,
                "travel_activity": {
                    "activity": "navigate",
                    "assigned_actor_id": str(player_id),
                    "source": "test",
                },
            },
            "travel_event": {
                "event_id": "evt-road",
                "event_key": "roadside_finding",
                "event_type": "roadside_hook",
                "summary": "У обочины лежит приметная дорожная находка.",
                "route_snapshot": {
                    "allowed": True,
                    "route_kind": "landmark_move",
                    "action_kind": "move",
                    "target_label": "Северные ворота",
                    "target_node_type": "landmark",
                    "target_node_id": "north-gate",
                },
                "source": "travel",
                "active": True,
                "resolved": False,
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
    monkeypatch.setattr(state_builder, "get_player_known_node_ids", lambda _sess, _player_id: ["camp", "north-gate"])
    monkeypatch.setattr(state_builder, "get_player_revealed_node_ids", lambda _sess, _player_id: ["camp"])
    monkeypatch.setattr(state_builder, "get_current_group_node_context", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_detail", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_inspect_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_services", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_service_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_service_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_travel_event", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_camp_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_scout_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_context_action_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_route_access_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_context_action_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_node_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_current_node_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_travel_event_outcome", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_map_intel", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_recent_map_intel", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_arrival_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_node_entry_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_node_entry_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_entry_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_destination_event_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_node_destination_event_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_destination_event_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_current_node_visit_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_visit_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_route_traversal_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(
        state_builder,
        "get_current_group_route_planning",
        lambda _sess, player_id=None: {"reachable_destinations": [], "route_frontiers": []},
    )
    monkeypatch.setattr(state_builder, "get_current_group_navigation_options", lambda _sess, player_id=None: [])
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
    assert payload["game"]["groups"]["main"]["last_camp_result_summary"] == {
        "result_id": "camp-out-2",
        "result_type": "uneasy_rest",
        "summary": "Лагерь у лагеря остаётся настороженным.",
        "result_summary": "Группа отдыхает вполглаза и не получает полной безопасности.",
        "node_id": "camp",
        "node_label": "camp",
        "rest_quality": "uneasy",
        "risk_band": "medium",
        "source": "test",
        "applied_effects": ["rest_quality:uneasy", "safety_note:border_watch"],
        "resolved_at": "2026-03-14T00:06:00+00:00",
    }
    assert payload["game"]["groups"]["main"]["last_scout_result_summary"] == {
        "result_id": "scout-out-2",
        "result_type": "local_clue_found",
        "summary": "Разведка у лагеря даёт локальную зацепку.",
        "result_summary": "Нового выхода разведка не открывает, но место даёт полезную локальную подсказку.",
        "node_id": "camp",
        "node_label": "camp",
        "discovery_scope": "local_area",
        "discovered_node_ids": [],
        "discovered_route_ids": [],
        "discovered_notes": ["Лагерь остаётся удобной точкой сбора перед выходом."],
        "reveal_applied": False,
        "source": "test",
        "resolved_at": "2026-03-14T00:07:00+00:00",
    }
    assert payload["game"]["groups"]["main"]["last_context_action_result_summary"] == {
        "result_id": "ctx-out-2",
        "action_id": "clear_old_road",
        "action_label": "Расчистить старую дорогу",
        "result_type": "route_cleared",
        "summary": "Разобрать завал и вернуть проход к северным воротам.",
        "result_summary": "Группа очищает локальный завал и фиксирует новый проходимый подход.",
        "node_id": "camp",
        "node_label": "camp",
        "applied_effects": ["route_access:cleared"],
        "source": "test",
        "resolved_at": "2026-03-14T00:07:30+00:00",
    }
    assert payload["game"]["groups"]["main"]["context_action_states"] == [
        {
            "action_id": "clear_old_road",
            "status": "completed",
            "result_type": "route_cleared",
            "summary": "Группа очищает локальный завал и фиксирует новый проходимый подход.",
            "source": "test",
            "updated_at": "2026-03-14T00:07:31+00:00",
        }
    ]
    assert payload["game"]["groups"]["main"]["node_states"] == [
        {
            "node_id": "camp",
            "state_flags": ["camp_watch_checked"],
            "summary": "Лагерная точка уже осмотрена и отмечена для следующего сбора.",
            "source": "test",
            "updated_at": "2026-03-14T00:07:32+00:00",
        }
    ]
    assert payload["game"]["groups"]["main"]["route_access_states"] == [
        {
            "route_id": "camp->north-gate:move",
            "access_state": "cleared",
            "is_traversable": True,
            "summary": "Подход к северным воротам снова открыт.",
            "source": "test",
            "updated_at": "2026-03-15T00:06:00+00:00",
        }
    ]
    assert payload["game"]["groups"]["main"]["map_intel_count"] == 1
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
        "route_source": "registry",
        "traversal_kind": "gate_approach",
        "risk_band": "low",
        "terrain_hint": "fortified",
        "travel_tags": ["fortified"],
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
            "source": "registry",
            "traversal_kind": "gate_approach",
            "risk_band": "low",
            "terrain_hint": "fortified",
            "travel_tags": ["fortified"],
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
        "paused": False,
        "resume_allowed": True,
        "travel_activity": {
            "activity": "navigate",
            "assigned_actor_id": str(player_id),
            "source": "test",
        },
    }
    assert payload["players"][0]["known_node_ids"] == ["camp", "north-gate"]
    assert payload["players"][0]["revealed_node_ids"] == ["camp"]
    assert payload["game"]["groups"]["main"]["travel_summary"] == {
        "active": True,
        "phase": "in_transit",
        "progress_kind": "route",
        "progress_step": 1,
        "movement_mode": "cautious",
        "paused": False,
        "resume_allowed": True,
        "route_summary": {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "source": "registry",
            "traversal_kind": "gate_approach",
            "risk_band": "low",
            "terrain_hint": "fortified",
            "travel_tags": ["fortified"],
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
    assert payload["game"]["groups"]["main"]["travel_event_summary"] == {
        "event_id": "evt-road",
        "event_key": "roadside_finding",
        "event_type": "roadside_hook",
        "summary": "У обочины лежит приметная дорожная находка.",
        "route_snapshot": {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "Северные ворота",
            "target_node_type": "landmark",
            "target_node_id": "north-gate",
        },
        "source": "travel",
        "active": True,
        "resolved": False,
    }
    assert payload["game"]["groups"]["main"]["last_travel_event_outcome_summary"] is None
    assert payload["game"]["groups"]["main"]["visited_node_count"] == 0
    assert payload["game"]["groups"]["main"]["traversed_route_count"] == 0
    assert payload["game"]["groups"]["main"]["available_resolutions"] is None
    assert payload["game"]["groups"]["main"]["last_resolution_summary"] is None


def test_build_state_exports_paused_travel_status_and_pause_reason(monkeypatch) -> None:
    session_id = "sess-1"
    player_id = uuid.uuid4()
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
            "status": "paused_travel",
            "movement_mode": "normal",
            "movement_intent": {
                "target_label": "замок",
                "target_node": {
                    "v": 1,
                    "map_level": "interior",
                    "node_type": "interior_entry",
                    "node_id": "castle",
                    "label": "замок",
                    "zone_label": "camp",
                    "area_label": "camp",
                },
                "movement_mode": "normal",
                "movement_kind": "enter",
                "action_kind": "enter",
                "route_kind": "enter_location",
                "allowed": True,
                "source": "test",
                "active": True,
                "target_node_type": "interior_entry",
                "target_node_id": "castle",
            },
            "travel_state": {
                "active": True,
                "phase": "paused",
                "route_summary": {
                    "allowed": True,
                    "route_kind": "enter_location",
                    "action_kind": "enter",
                    "target_label": "замок",
                    "target_node": {
                        "v": 1,
                        "map_level": "interior",
                        "node_type": "interior_entry",
                        "node_id": "castle",
                        "label": "замок",
                        "zone_label": "camp",
                        "area_label": "camp",
                    },
                    "target_node_type": "interior_entry",
                    "target_node_id": "castle",
                    "next_map_position": {
                        "v": 1,
                        "map_level": "interior",
                        "node_type": "interior_entry",
                        "node_id": "castle",
                        "label": "замок",
                        "area_label": "camp",
                    },
                    "next_zone_label": "camp",
                },
                "started_from": group_position,
                "target_node": {
                    "v": 1,
                    "map_level": "interior",
                    "node_type": "interior_entry",
                    "node_id": "castle",
                    "label": "замок",
                    "zone_label": "camp",
                    "area_label": "camp",
                },
                "progress_kind": "route",
                "progress_step": 0,
                "movement_mode": "normal",
                "paused": True,
                "pause_reason": "target_requires_enter",
                "pause_details": {"target_node_type": "interior_entry"},
                "resume_allowed": True,
            },
            "last_travel_resolution": {
                "resolution_kind": "inspect_target",
                "pause_reason": "point_of_interest_reached",
                "target_label": "старые ворота",
                "source": "test",
                "details": {"inspected": True},
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
    monkeypatch.setattr(state_builder, "get_current_group_node_context", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_detail", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_inspect_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_services", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_service_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_travel_event", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_travel_event_outcome", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_map_intel", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_recent_map_intel", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_last_arrival_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_last_node_entry_result", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_current_node_entry_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_entry_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_current_node_visit_state", lambda _sess, player_id=None: None)
    monkeypatch.setattr(state_builder, "get_current_group_node_visit_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(state_builder, "get_current_group_route_traversal_states", lambda _sess, player_id=None: [])
    monkeypatch.setattr(
        state_builder,
        "get_current_group_route_planning",
        lambda _sess, player_id=None: {"reachable_destinations": [], "route_frontiers": []},
    )
    monkeypatch.setattr(state_builder, "snapshot_combat_state", lambda _session_id: None)

    db = _FakeDb([[player], [], [], []])
    payload = asyncio.run(state_builder.build_state(db, sess))

    assert payload["game"]["groups"]["main"]["status"] == "paused_travel"
    assert payload["game"]["groups"]["main"]["travel_state"]["paused"] is True
    assert payload["game"]["groups"]["main"]["travel_state"]["pause_reason"] == "target_requires_enter"
    assert payload["game"]["groups"]["main"]["travel_summary"]["paused"] is True
    assert payload["game"]["groups"]["main"]["travel_summary"]["pause_reason"] == "target_requires_enter"
    assert payload["game"]["groups"]["main"]["travel_summary"]["pause_details"] == {"target_node_type": "interior_entry"}
    assert payload["game"]["groups"]["main"]["travel_event_summary"] is None
    assert payload["game"]["groups"]["main"]["last_travel_event_outcome_summary"] is None
    assert payload["game"]["groups"]["main"]["visited_node_count"] == 0
    assert payload["game"]["groups"]["main"]["traversed_route_count"] == 0
    assert payload["game"]["groups"]["main"]["pause_reason"] == "target_requires_enter"
    assert payload["game"]["groups"]["main"]["pause_details"] == {"target_node_type": "interior_entry"}
    assert payload["game"]["groups"]["main"]["available_resolutions"] == [
        {"resolution": "confirm_enter", "label": "confirm_enter"},
        {"resolution": "resume", "label": "resume"},
        {"resolution": "interrupt", "label": "interrupt"},
    ]
    assert payload["game"]["groups"]["main"]["last_resolution_summary"] == {
        "resolution_kind": "inspect_target",
        "pause_reason": "point_of_interest_reached",
        "target_label": "старые ворота",
        "source": "test",
        "details": {"inspected": True},
    }
