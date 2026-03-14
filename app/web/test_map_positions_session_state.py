from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.web import session_state


def test_set_player_map_position_stores_structured_and_legacy_label() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})

    session_state._set_player_map_position(
        sess,
        player_id,
        {
            "map_level": "district",
            "node_type": "landmark",
            "node_id": "old-tavern-cellar",
            "label": "Старый подвал",
        },
    )

    assert sess.settings["map_positions"][str(player_id)] == {
        "v": 1,
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Старый подвал",
    }
    assert sess.settings["pc_positions"][str(player_id)] == "Старый подвал"


def test_map_position_area_label_returns_zone_label_for_zone_position() -> None:
    pos = {
        "map_level": "region",
        "node_type": "zone",
        "node_id": "центр-города",
        "label": "центр города",
    }

    assert session_state._map_position_area_label(pos) == "центр города"


def test_map_position_area_label_returns_parent_zone_for_landmark() -> None:
    pos = {
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "north-gate",
        "label": "Северные ворота",
        "area_label": "центр города",
    }

    assert session_state._map_position_area_label(pos) == "центр города"


def test_map_position_area_label_returns_parent_zone_for_interior_entry() -> None:
    pos = {
        "map_level": "interior",
        "node_type": "interior_entry",
        "node_id": "castle",
        "label": "замок",
        "area_label": "дорога к замку",
    }

    assert session_state._map_position_area_label(pos) == "дорога к замку"


def test_map_position_area_label_falls_back_when_parent_missing() -> None:
    pos = {
        "map_level": "interior",
        "node_type": "interior_entry",
        "node_id": "castle",
        "label": "замок",
    }

    assert session_state._map_position_area_label(pos) == "замок"


def test_apply_map_position_transition_moves_between_zones() -> None:
    current = {
        "map_level": "region",
        "node_type": "zone",
        "node_id": "таверна",
        "label": "таверна",
    }

    next_position, next_zone, ok, error = session_state._apply_map_position_transition(
        current,
        {
            "node_type": "zone",
            "node_id": "улица у таверны",
            "label": "улица у таверны",
            "zone_label": "улица у таверны",
        },
        "test_move",
    )

    assert ok is True
    assert error is None
    assert next_zone == "улица у таверны"
    assert next_position == {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": "улица у таверны",
        "label": "улица у таверны",
        "area_label": "улица у таверны",
    }


def test_apply_map_position_transition_moves_to_landmark_and_keeps_legacy_zone_label() -> None:
    current = {
        "map_level": "region",
        "node_type": "zone",
        "node_id": "центр города",
        "label": "центр города",
    }

    next_position, next_zone, ok, error = session_state._apply_map_position_transition(
        current,
        {
            "node_type": "landmark",
            "node_id": "ворота",
            "label": "Северные ворота",
            "zone_label": "Северные ворота",
        },
        "test_move",
    )

    assert ok is True
    assert error is None
    assert next_zone == "центр города"
    assert next_position == {
        "v": 1,
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "ворота",
        "label": "Северные ворота",
        "area_label": "центр города",
    }


def test_get_pc_positions_prefers_structured_map_positions() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "pc_positions": {str(player_id): "Устаревшая зона"},
            "map_positions": {
                str(player_id): {
                    "map_level": "landmark",
                    "node_type": "landmark",
                    "node_id": "north-gate",
                    "label": "Северные ворота",
                    "area_label": "центр города",
                }
            },
        }
    )

    assert session_state._get_pc_positions(sess) == {str(player_id): "центр города"}


def test_map_position_identity_equals_ignores_label_mismatch() -> None:
    left = {
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Старый подвал",
    }
    right = {
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Подвал таверны",
    }

    assert session_state._map_position_identity_equals(left, right) is True


def test_map_position_identity_equals_detects_different_node() -> None:
    left = {
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Старый подвал",
    }
    right = {
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "north-gate",
        "label": "Северные ворота",
    }

    assert session_state._map_position_identity_equals(left, right) is False


def test_same_player_map_position_falls_back_to_legacy_when_structured_absent() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "pc_positions": {
                str(left_id): "Таверна",
                str(right_id): "Таверна",
            }
        }
    )

    assert session_state._same_player_map_position(sess, left_id, right_id) is True


def test_same_player_map_position_legacy_fallback_does_not_read_pc_positions_helper(monkeypatch) -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "pc_positions": {
                str(left_id): "Таверна",
                str(right_id): "Таверна",
            }
        }
    )

    def _unexpected_read(_sess) -> dict[str, str]:
        raise AssertionError("_get_pc_positions should not be used by same-position fallback")

    monkeypatch.setattr(session_state, "_get_pc_positions", _unexpected_read)

    assert session_state._same_player_map_position(sess, left_id, right_id) is True


def test_get_player_position_context_prefers_structured_and_exposes_zone_label() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "pc_positions": {str(player_id): "Устаревшая зона"},
            "map_positions": {
                str(player_id): {
                    "map_level": "district",
                    "node_type": "landmark",
                    "node_id": "old-tavern-cellar",
                    "label": "Старый подвал",
                    "area_label": "Таверна",
                }
            },
        }
    )

    assert session_state._get_player_position_context(sess, player_id) == {
        "group_id": "main",
        "zone_label": "Таверна",
        "map_position": {
            "v": 1,
            "map_level": "district",
            "node_type": "landmark",
            "node_id": "old-tavern-cellar",
            "label": "Старый подвал",
            "area_label": "Таверна",
        },
    }


def test_get_player_position_context_falls_back_to_legacy_zone() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={"pc_positions": {str(player_id): "Таверна"}})

    assert session_state._get_player_position_context(sess, player_id) == {
        "group_id": "main",
        "zone_label": "Таверна",
        "map_position": {
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "Таверна",
            "label": "Таверна",
        },
    }


def test_clear_player_map_position_removes_structured_and_legacy_entries() -> None:
    player_id = uuid.uuid4()
    other_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "pc_positions": {
                str(player_id): "Старый подвал",
                str(other_id): "Рынок",
            },
            "map_positions": {
                str(player_id): {
                    "map_level": "district",
                    "node_type": "landmark",
                    "node_id": "old-tavern-cellar",
                    "label": "Старый подвал",
                },
                str(other_id): {
                    "map_level": "region",
                    "node_type": "zone",
                    "node_id": "market",
                    "label": "Рынок",
                },
            },
        }
    )

    session_state._clear_player_map_position(sess, player_id)

    assert str(player_id) not in sess.settings["pc_positions"]
    assert str(player_id) not in sess.settings["map_positions"]
    assert str(other_id) in sess.settings["pc_positions"]
    assert str(other_id) in sess.settings["map_positions"]


def test_initialize_default_group_creates_main_group_for_all_players() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})

    groups = session_state._initialize_default_group(
        sess,
        [left_id, right_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "camp-square",
            "label": "Площадь лагеря",
        },
    )

    assert groups == {
        "main": {
            "group_id": "main",
            "player_ids": [str(left_id), str(right_id)],
            "current_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "camp-square",
                "label": "Площадь лагеря",
            },
            "area_label": "Площадь лагеря",
            "status": "idle",
            "movement_mode": "normal",
        }
    }


def test_get_player_group_id_resolves_membership_from_group_state() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [left_id, right_id], "Таверна")

    assert session_state._get_player_group_id(sess, left_id) == "main"
    assert session_state._get_player_group_id(sess, right_id) == "main"


def test_set_group_map_position_updates_all_member_mirrors() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [left_id, right_id], "Таверна")

    session_state._set_group_map_position(
        sess,
        "main",
        {
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "north-gate",
            "label": "Северные ворота",
            "area_label": "центр города",
        },
    )

    groups = session_state._get_group_states(sess)
    assert groups["main"]["current_map_position"] == {
        "v": 1,
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "north-gate",
        "label": "Северные ворота",
        "area_label": "центр города",
    }
    assert sess.settings["map_positions"][str(left_id)] == groups["main"]["current_map_position"]
    assert sess.settings["map_positions"][str(right_id)] == groups["main"]["current_map_position"]
    assert sess.settings["pc_positions"][str(left_id)] == "центр города"
    assert sess.settings["pc_positions"][str(right_id)] == "центр города"


def test_split_group_creates_second_group_with_shared_position() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    third_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [left_id, right_id, third_id], "Таверна")

    new_group = session_state._split_group(sess, "main", [third_id], new_group_id="scout")

    assert new_group == {
        "group_id": "scout",
        "player_ids": [str(third_id)],
        "current_map_position": {
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "Таверна",
            "label": "Таверна",
        },
        "area_label": "Таверна",
        "status": "idle",
    }
    groups = session_state._get_group_states(sess)
    assert groups["main"]["player_ids"] == [str(left_id), str(right_id)]
    assert groups["main"]["status"] == "idle"
    assert session_state._get_player_group_id(sess, third_id) == "scout"


def test_merge_groups_rejoins_colocated_groups_and_keeps_positions_consistent() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [left_id, right_id], "Таверна")
    session_state._split_group(sess, "main", [right_id], new_group_id="scout")

    merged = session_state._merge_groups(sess, "main", "scout")

    assert merged is not None
    assert session_state._get_group_states(sess) == {
        "main": {
            "group_id": "main",
            "player_ids": [str(left_id), str(right_id)],
            "current_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "Таверна",
                "label": "Таверна",
            },
            "area_label": "Таверна",
            "status": "idle",
            "movement_mode": "normal",
        }
    }
    assert session_state._get_map_positions(sess)[str(left_id)] == session_state._get_map_positions(sess)[str(right_id)]


def test_set_group_wait_creates_group_wait_state() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")

    updated = session_state.set_group_wait(
        sess,
        "main",
        reason="ждём разведчика",
        source="test",
        requested_by=player_id,
    )

    assert updated is not None
    assert updated["status"] == "waiting"
    assert updated["wait_state"] == {
        "reason": "ждём разведчика",
        "source": "test",
        "requested_by": str(player_id),
    }
    assert session_state._get_group_states(sess)["main"]["status"] == "waiting"


def test_set_group_camp_creates_group_camp_state() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")

    updated = session_state.set_group_camp(
        sess,
        "main",
        reason="ночёвка у ворот",
        source="test",
        requested_by=player_id,
    )

    assert updated is not None
    assert updated["status"] == "camping"
    assert updated["camp_state"] == {
        "reason": "ночёвка у ворот",
        "source": "test",
        "requested_by": str(player_id),
    }
    assert session_state._get_group_states(sess)["main"]["status"] == "camping"


def test_request_and_apply_group_split_creates_two_valid_groups() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    third_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [left_id, right_id, third_id], "Таверна")
    request = session_state.request_group_split(
        "main",
        [third_id],
        new_group_id="scout",
        source="test",
        requested_by=left_id,
    )

    created = session_state.apply_group_split(sess, request)

    assert created is not None
    assert created["group_id"] == "scout"
    groups = session_state._get_group_states(sess)
    assert set(groups.keys()) == {"main", "scout"}
    assert groups["main"]["player_ids"] == [str(left_id), str(right_id)]
    assert groups["scout"]["player_ids"] == [str(third_id)]
    assert groups["main"]["current_map_position"] == groups["scout"]["current_map_position"]


def test_request_and_apply_group_merge_rejoins_colocated_groups() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [left_id, right_id], "Таверна")
    session_state._split_group(sess, "main", [right_id], new_group_id="scout")
    session_state.set_group_wait(sess, "scout", reason="держим точку", source="test", requested_by=right_id)
    request = session_state.request_group_merge(
        "main",
        "scout",
        source="test",
        requested_by=left_id,
    )

    merged = session_state.apply_group_merge(sess, request)

    assert merged is not None
    assert merged["status"] == "waiting"
    assert merged["wait_state"] == {
        "reason": "держим точку",
        "source": "test",
        "requested_by": str(right_id),
    }
    assert session_state._get_group_states(sess)["main"]["player_ids"] == [str(left_id), str(right_id)]


def test_set_group_movement_intent_stores_canonical_structured_target() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")

    updated = session_state.set_group_movement_intent(
        sess,
        "main",
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "north-gate",
            "label": "Северные ворота",
            "zone_label": "Таверна",
            "area_label": "Таверна",
        },
        source="test",
        movement_mode="travel",
    )

    assert updated is not None
    assert updated["status"] == "moving_intent"
    assert updated["movement_mode"] == "normal"
    assert updated["movement_intent"] == {
        "target_label": "Северные ворота",
        "movement_mode": "normal",
        "movement_kind": "move",
        "action_kind": "move",
        "source": "test",
        "active": True,
        "allowed": True,
        "target_node": {
            "v": 1,
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "north-gate",
            "label": "Северные ворота",
            "zone_label": "Таверна",
            "area_label": "Таверна",
        },
        "target_node_type": "landmark",
        "target_node_id": "north-gate",
    }


def test_clear_group_movement_intent_clears_intent_and_restores_idle() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")
    session_state.set_group_movement_intent(sess, "main", target_node="центр города", source="test")

    updated = session_state.clear_group_movement_intent(sess, "main")

    assert updated is not None
    assert updated["status"] == "idle"
    assert "movement_intent" not in updated
    assert "movement_intent" not in session_state._get_group_states(sess)["main"]


def test_group_enter_target_produces_expected_structured_target_semantics() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")

    updated = session_state.maybe_apply_group_enter_target(
        sess,
        "main",
        {
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "замок",
            "label": "замок",
            "zone_label": "Таверна",
            "area_label": "Таверна",
        },
        source="test",
    )

    assert updated is not None
    assert updated["status"] == "paused_travel"
    assert updated["current_map_position"] == {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": "Таверна",
        "label": "Таверна",
    }
    assert updated["movement_intent"]["target_node_type"] == "interior_entry"
    assert updated["movement_intent"]["target_node_id"] == "замок"
    assert updated["movement_intent"]["movement_mode"] == "normal"
    assert updated["movement_intent"]["movement_kind"] == "enter"
    assert updated["movement_intent"]["action_kind"] == "enter"
    assert updated["movement_intent"]["allowed"] is True
    assert updated["travel_state"]["active"] is True
    assert updated["status"] == "paused_travel"
    assert updated["travel_state"]["route_summary"]["route_kind"] == "enter"
    assert updated["travel_state"]["started_from"]["node_id"] == "Таверна"
    assert updated["travel_state"]["paused"] is True
    assert updated["travel_state"]["pause_reason"] == "target_requires_enter"
    assert updated["travel_state"]["pause_details"] == {"target_node_type": "interior_entry"}
    assert sess.settings["pc_positions"][str(player_id)] == "Таверна"


def test_set_and_get_group_movement_mode() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")

    updated = session_state.set_group_movement_mode(sess, "main", "cautious")

    assert updated is not None
    assert updated["movement_mode"] == "cautious"
    assert session_state.get_group_movement_mode(sess, "main") == "cautious"


def test_set_and_clear_group_travel_activity_preserves_assigned_actor() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")

    updated = session_state.set_group_travel_activity(
        sess,
        "main",
        activity="observe",
        assigned_actor_id=player_id,
        source="test",
    )

    assert updated is not None
    assert session_state.get_group_travel_activity(sess, "main") == {
        "activity": "observe",
        "assigned_actor_id": str(player_id),
        "source": "test",
    }

    cleared = session_state.clear_group_travel_activity(sess, "main")

    assert cleared is not None
    assert session_state.get_group_travel_activity(sess, "main") is None


def test_movement_intent_inherits_group_mode_and_activity() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")
    session_state.set_group_movement_mode(sess, "main", "fast")
    session_state.set_group_travel_activity(sess, "main", activity="navigate", assigned_actor_id=player_id, source="test")

    updated = session_state.apply_group_move_target(
        sess,
        "main",
        {
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "ворота",
            "label": "ворота",
            "zone_label": "центр города",
            "area_label": "центр города",
        },
        source="test",
    )

    assert updated is not None
    assert updated["movement_intent"]["movement_mode"] == "fast"
    assert updated["movement_intent"]["action_kind"] == "move"
    assert updated["movement_intent"]["route_source"] == "fallback"
    assert updated["movement_intent"]["traversal_kind"] == "approach"
    assert updated["movement_intent"]["risk_band"] == "medium"
    assert updated["movement_intent"]["terrain_hint"] == "mixed"
    assert updated["travel_state"]["movement_mode"] == "fast"
    assert updated["current_map_position"]["node_id"] == "центр города"
    assert updated["movement_intent"]["travel_activity"] == {
        "activity": "navigate",
        "assigned_actor_id": str(player_id),
        "source": "test",
    }
    assert updated["travel_state"]["travel_activity"] == {
        "activity": "navigate",
        "assigned_actor_id": str(player_id),
        "source": "test",
    }
    assert updated["travel_state"]["paused"] is False


def test_start_complete_and_interrupt_group_travel_manage_position_and_status() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")

    started = session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "ворота",
            "target_node": {
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "zone_label": "центр города",
                "area_label": "центр города",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "area_label": "центр города",
            },
            "next_zone_label": "центр города",
        },
        source="test",
    )

    assert started is not None
    assert started["status"] == "moving"
    assert started["current_map_position"]["node_id"] == "центр города"
    assert started["travel_state"]["active"] is True
    assert started["travel_state"]["phase"] == "in_transit"
    assert started["travel_state"]["route_summary"]["route_kind"] == "landmark_move"
    assert started["travel_state"]["paused"] is False

    advanced = session_state.advance_group_travel(sess, "main")

    assert advanced is not None
    assert advanced["travel_state"]["progress_step"] == 1
    assert advanced["status"] == "moving"

    completed = session_state.complete_group_travel(sess, "main")

    assert completed is not None
    assert completed["status"] == "idle"
    assert completed["current_map_position"]["node_id"] == "ворота"
    assert "travel_state" not in completed
    assert "movement_intent" not in completed

    restarted = session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "enter_location",
            "action_kind": "enter",
            "target_label": "замок",
            "target_node": {
                "map_level": "interior",
                "node_type": "interior_entry",
                "node_id": "замок",
                "label": "замок",
                "zone_label": "центр города",
                "area_label": "центр города",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "interior",
                "node_type": "interior_entry",
                "node_id": "замок",
                "label": "замок",
                "area_label": "центр города",
            },
            "next_zone_label": "центр города",
        },
        source="test",
    )

    assert restarted is not None
    assert restarted["status"] == "paused_travel"
    assert restarted["travel_state"]["pause_reason"] == "target_requires_enter"
    resumed = session_state.resume_group_travel(sess, "main")

    assert resumed is not None
    assert resumed["status"] == "moving"
    assert resumed["travel_state"]["paused"] is False
    interrupted = session_state.interrupt_group_travel(sess, "main")

    assert interrupted is not None
    assert interrupted["status"] == "idle"
    assert interrupted["current_map_position"]["node_id"] == "ворота"
    assert "travel_state" not in interrupted
    assert "movement_intent" not in interrupted


def test_player_map_knowledge_grant_get_has_and_upgrade_cleanly() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    seeded = session_state.get_player_map_knowledge(sess, player_id)

    assert seeded["start_trakt"]["knowledge_kind"] == "known"
    assert session_state.has_player_map_knowledge(sess, player_id, "start_trakt") is True
    assert session_state.has_player_map_knowledge(sess, player_id, "fortress_gate") is True
    assert session_state.has_player_map_knowledge(sess, player_id, "eastern_bank") is False

    session_state.grant_player_map_knowledge(sess, player_id, "eastern_bank", knowledge_kind="known", source="test")
    session_state.grant_player_map_knowledge(sess, player_id, "eastern_bank", knowledge_kind="discovered", source="travel")
    session_state.maybe_mark_player_node_visited(sess, player_id, "eastern_bank", source="arrival")

    knowledge = session_state.get_player_map_knowledge(sess, player_id)

    assert knowledge["eastern_bank"]["knowledge_kind"] == "visited"
    assert knowledge["eastern_bank"]["source"] == "arrival"
    assert session_state.has_player_map_knowledge(sess, player_id, "eastern_bank", minimum_kind="discovered") is True
    assert session_state.has_player_map_knowledge(sess, player_id, "eastern_bank", minimum_kind="visited") is True


def test_player_map_reveal_storage_is_separate_and_seeded_from_current_static_position() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    revealed_node_ids = session_state.get_player_revealed_node_ids(sess, player_id)

    assert "start_trakt" in revealed_node_ids
    assert "fortress_gate" in revealed_node_ids
    assert "eastern_bank" not in revealed_node_ids
    assert len(revealed_node_ids) == len(set(revealed_node_ids))
    assert session_state.is_player_node_revealed(sess, player_id, "start_trakt") is True
    assert session_state.is_player_node_revealed(sess, player_id, "eastern_bank") is False

    session_state.reveal_player_map_node(sess, player_id, "eastern_bank", source="test")
    session_state.reveal_player_map_node(sess, player_id, "eastern_bank", source="test")

    updated_revealed = session_state.get_player_revealed_node_ids(sess, player_id)

    assert "eastern_bank" in updated_revealed
    assert len(updated_revealed) == len(set(updated_revealed))
    assert session_state.has_player_map_knowledge(sess, player_id, "eastern_bank") is True


def test_get_current_group_navigation_options_respects_known_and_revealed_nodes() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    options = session_state.get_current_group_navigation_options(sess, player_id=player_id)

    assert [option["target_node_id"] for option in options] == ["fortress_gate"]
    assert options[0]["revealed"] is True

    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    updated_options = session_state.get_current_group_navigation_options(sess, player_id=player_id)

    assert [option["target_node_id"] for option in updated_options] == ["fortress_gate", "craft_town"]
    assert updated_options[1]["known"] is True
    assert updated_options[1]["revealed"] is False


def test_execute_group_navigation_option_runs_existing_travel_flow_and_errors_cleanly() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    updated, error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="fortress_gate",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert updated is not None
    assert updated["movement_intent"]["target_node_id"] == "fortress_gate"
    assert updated["travel_state"]["route_summary"]["source"] == "registry"

    invalid_updated, invalid_error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="missing_node",
        player_id=player_id,
        source="test",
    )

    assert invalid_updated is None
    assert invalid_error == "Неизвестная navigation цель группы."

    session_state.grant_player_map_knowledge(sess, player_id, "watchtower", knowledge_kind="known", source="test")
    unavailable_updated, unavailable_error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="watchtower",
        player_id=player_id,
        source="test",
    )

    assert unavailable_updated is None
    assert unavailable_error == "Эта navigation цель сейчас недоступна из текущей точки."


def test_get_current_group_node_context_returns_node_summary_and_contextual_actions() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
    )

    context = session_state.get_current_group_node_context(sess, player_id=player_id)

    assert context == {
        "node_summary": {
            "node_id": "craft_town",
            "label": "Озёрный городок",
            "node_type": "zone",
            "area_label": "Озёрный городок",
            "zone_band": "safe",
            "settlement_kind": "town",
            "environment_hint": "lakeshore",
            "safe_rest_hint": True,
            "detail_summary": "Здесь легко пополнить припасы, переждать дорогу и собрать слухи о ближних тропах.",
        },
        "contextual_actions": [
            {"action_key": "navigate", "label": "Продолжить путь", "action_type": "action"},
            {"action_key": "inspect", "label": "Осмотреться", "action_type": "action"},
            {"action_key": "wait", "label": "Подождать", "action_type": "action"},
            {"action_key": "rest_hint", "label": "Есть место для передышки", "action_type": "hint"},
        ],
        "available_services": [
            {
                "service_key": "safe_rest",
                "label": "Безопасный отдых",
                "service_type": "rest",
                "summary": "Можно перевести дух и переждать путь в сравнительно безопасных условиях.",
                "source": "registry",
                "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
            },
            {
                "service_key": "resupply",
                "label": "Пополнение припасов",
                "service_type": "supplies",
                "summary": "Здесь можно пополнить базовые дорожные запасы перед выходом.",
                "source": "registry",
                "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
            },
            {
                "service_key": "local_guidance",
                "label": "Местные указания",
                "service_type": "guidance",
                "summary": "Здесь можно получить ориентиры, слухи и безопасные подсказки по ближайшим дорогам.",
                "source": "registry",
                "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
            },
            {
                "service_key": "healing_aid",
                "label": "Помощь с ранами",
                "service_type": "aid",
                "summary": "На месте можно получить перевязку, уход или базовую помощь после дороги.",
                "source": "registry",
                "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
            },
        ],
        "service_actions": [
            {"action_key": "use_service", "label": "Воспользоваться услугой", "action_type": "action"},
        ],
    }


def test_inspect_current_group_node_stores_canonical_inspect_result_and_updates_knowledge() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
    )

    inspected = session_state.inspect_current_group_node(sess, player_id=player_id, source="test")

    assert inspected is not None
    assert session_state.get_current_group_last_inspect_result(sess, player_id=player_id) == {
        "node_id": "craft_town",
        "label": "Озёрный городок",
        "node_type": "zone",
        "inspect_summary": "Здесь легко пополнить припасы, переждать дорогу и собрать слухи о ближних тропах.",
        "short_description": "Небольшой ремесленный городок у воды с пристанью, мастерскими и постоялым двором.",
        "travel_note": "Самая надёжная безопасная точка региона перед выходом в пограничные земли.",
        "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
        "source": "test",
        "inspected_at": inspected["last_inspect_result"]["inspected_at"],
    }
    assert session_state.get_player_map_knowledge(sess, player_id)["craft_town"]["knowledge_kind"] == "discovered"
    assert session_state.is_player_node_revealed(sess, player_id, "craft_town") is True


def test_get_current_group_node_services_and_execute_service_store_result() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
    )

    services = session_state.get_current_group_node_services(sess, player_id=player_id)
    updated, error = session_state.execute_current_group_service(
        sess,
        player_id=player_id,
        service_key="resupply",
        source="test",
    )

    assert [service["service_key"] for service in services] == [
        "safe_rest",
        "resupply",
        "local_guidance",
        "healing_aid",
    ]
    assert error is None
    assert updated is not None
    assert session_state.get_current_group_last_service_result(sess, player_id=player_id) == {
        "service_key": "resupply",
        "label": "Пополнение припасов",
        "service_type": "supplies",
        "summary": "Здесь можно пополнить базовые дорожные запасы перед выходом.",
        "result_summary": "Здесь можно собрать базовые припасы и привести снаряжение в порядок.",
        "node_id": "craft_town",
        "node_label": "Озёрный городок",
        "source": "test",
        "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
        "used_at": updated["last_service_result"]["used_at"],
    }


def test_execute_current_group_service_rejects_unavailable_service_cleanly() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "ruined_settlement",
            "label": "Разрушенный посёлок",
        },
    )

    updated, error = session_state.execute_current_group_service(
        sess,
        player_id=player_id,
        service_key="safe_rest",
        source="test",
    )

    assert updated is None
    assert error == "Эта услуга сейчас недоступна в текущем месте."


def test_get_current_group_node_context_adds_enter_for_paused_target_requires_enter() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "ruined_settlement",
            "label": "Разрушенный посёлок",
        },
    )
    session_state.maybe_apply_group_enter_target(
        sess,
        "main",
        {
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Разрушенный посёлок",
            "area_label": "Разрушенный посёлок",
        },
        source="test",
    )

    context = session_state.get_current_group_node_context(sess, player_id=player_id)

    assert context is not None
    assert context["contextual_actions"][0] == {
        "action_key": "enter",
        "label": "Войти",
        "action_type": "action",
    }


def test_execute_current_group_context_action_supports_wait_camp_inspect_enter_and_navigate() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    waited, wait_error = session_state.execute_current_group_context_action(
        sess,
        action_key="wait",
        player_id=player_id,
        payload={"reason": "держим точку"},
        source="test",
    )
    assert wait_error is None
    assert waited is not None
    assert waited["status"] == "waiting"
    assert waited["wait_state"]["reason"] == "держим точку"

    session_state.clear_group_movement_intent(sess, "main")
    session_state._clear_group_activity_state(session_state._get_group_states(sess)["main"], status="idle")

    camped, camp_error = session_state.execute_current_group_context_action(
        sess,
        action_key="camp",
        player_id=player_id,
        payload={"reason": "ночлег"},
        source="test",
    )
    assert camp_error is None
    assert camped is not None
    assert camped["status"] == "camping"
    assert camped["camp_state"]["reason"] == "ночлег"

    session_state._clear_group_activity_state(session_state._get_group_states(sess)["main"], status="idle")
    session_state.grant_player_map_knowledge(sess, player_id, "start_trakt", knowledge_kind="known", source="seed")
    inspected, inspect_error = session_state.execute_current_group_context_action(
        sess,
        action_key="inspect",
        player_id=player_id,
        source="test",
    )
    assert inspect_error is None
    assert inspected is not None
    assert session_state.get_player_map_knowledge(sess, player_id)["start_trakt"]["knowledge_kind"] == "discovered"
    assert inspected["last_inspect_result"]["node_id"] == "start_trakt"
    assert inspected["last_inspect_result"]["inspect_summary"] == "По тракту удобно держать путь к воротам крепости и к озёрному городку."

    navigated, navigate_error = session_state.execute_current_group_context_action(
        sess,
        action_key="navigate",
        player_id=player_id,
        payload={"target_node_id": "fortress_gate"},
        source="test",
    )
    assert navigate_error is None
    assert navigated is not None
    assert navigated["movement_intent"]["target_node_id"] == "fortress_gate"
    assert navigated["travel_state"]["active"] is True

    paused_enter_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        paused_enter_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "ruined_settlement",
            "label": "Разрушенный посёлок",
        },
    )
    session_state.maybe_apply_group_enter_target(
        paused_enter_sess,
        "main",
        {
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Разрушенный посёлок",
            "area_label": "Разрушенный посёлок",
        },
        source="test",
    )

    entered, enter_error = session_state.execute_current_group_context_action(
        paused_enter_sess,
        action_key="enter",
        player_id=player_id,
        source="test",
    )
    assert enter_error is None
    assert entered is not None
    assert entered["status"] == "idle"
    assert entered["current_map_position"]["node_id"] == "mine_entrance"


def test_execute_current_group_context_action_rejects_unavailable_and_hint_only_actions() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
    )

    hint_updated, hint_error = session_state.execute_current_group_context_action(
        sess,
        action_key="rest_hint",
        player_id=player_id,
        source="test",
    )
    unavailable_updated, unavailable_error = session_state.execute_current_group_context_action(
        sess,
        action_key="camp",
        player_id=player_id,
        source="test",
    )

    assert hint_updated is None
    assert hint_error == "Это contextual действие доступно только как подсказка."
    assert unavailable_updated is None
    assert unavailable_error == "Это contextual действие сейчас недоступно."


def test_pause_resume_and_evaluate_group_travel_preserve_mode_and_activity() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")
    session_state.set_group_movement_mode(sess, "main", "cautious")
    session_state.set_group_travel_activity(sess, "main", activity="observe", assigned_actor_id=player_id, source="test")
    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "ворота",
            "target_node": {
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "zone_label": "центр города",
                "area_label": "центр города",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "area_label": "центр города",
            },
            "next_zone_label": "центр города",
        },
        source="test",
    )

    paused = session_state.pause_group_travel(
        sess,
        "main",
        reason="route_blocked",
        pause_details={"blocker": "оползень"},
        resume_allowed=True,
    )

    assert paused is not None
    assert paused["status"] == "paused_travel"
    assert paused["travel_state"]["paused"] is True
    assert paused["travel_state"]["pause_reason"] == "route_blocked"
    assert paused["travel_state"]["pause_details"] == {"blocker": "оползень"}
    assert paused["travel_state"]["movement_mode"] == "cautious"
    assert paused["travel_state"]["travel_activity"] == {
        "activity": "observe",
        "assigned_actor_id": str(player_id),
        "source": "test",
    }

    resumed = session_state.resume_group_travel(sess, "main")

    assert resumed is not None
    assert resumed["status"] == "moving"
    assert resumed["travel_state"]["paused"] is False
    assert resumed["travel_state"]["movement_mode"] == "cautious"
    assert resumed["travel_state"]["travel_activity"] == {
        "activity": "observe",
        "assigned_actor_id": str(player_id),
        "source": "test",
    }

    evaluated_poi = session_state.evaluate_group_travel_pause(
        sess,
        "main",
        pause_details={"pause_hint": "inspection_required"},
    )

    assert evaluated_poi is not None
    assert evaluated_poi["travel_state"]["pause_reason"] == "point_of_interest_reached"
    assert evaluated_poi["travel_state"]["pause_details"] == {"pause_hint": "inspection_required"}

    resumed_again = session_state.resume_group_travel(sess, "main")
    assert resumed_again is not None

    evaluated_event = session_state.evaluate_group_travel_pause(
        sess,
        "main",
        pause_reason="event_pending",
        pause_details={"event_id": "poi-1"},
    )

    assert evaluated_event is not None
    assert evaluated_event["travel_state"]["pause_reason"] == "event_pending"
    assert evaluated_event["travel_state"]["pause_details"] == {"event_id": "poi-1"}


def test_confirm_inspect_bypass_and_resolve_group_travel_pause() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")

    entered = session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "enter_location",
            "action_kind": "enter",
            "target_label": "замок",
            "target_node": {
                "map_level": "interior",
                "node_type": "interior_entry",
                "node_id": "замок",
                "label": "замок",
                "zone_label": "центр города",
                "area_label": "центр города",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "interior",
                "node_type": "interior_entry",
                "node_id": "замок",
                "label": "замок",
                "area_label": "центр города",
            },
            "next_zone_label": "центр города",
        },
        source="test",
    )

    assert entered is not None
    assert entered["status"] == "paused_travel"
    confirmed = session_state.confirm_group_enter(sess, "main", source="test")

    assert confirmed is not None
    assert confirmed["status"] == "idle"
    assert confirmed["current_map_position"]["node_id"] == "замок"
    assert confirmed["last_travel_resolution"] == {
        "resolution_kind": "confirm_enter",
        "pause_reason": "target_requires_enter",
        "target_label": "замок",
        "source": "test",
        "details": {"confirmed": True},
    }

    poi = session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "ворота",
            "target_node": {
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "zone_label": "центр города",
                "area_label": "центр города",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "area_label": "центр города",
            },
            "next_zone_label": "центр города",
            "pause_hint": "inspection_required",
        },
        source="test",
    )

    assert poi is not None
    assert poi["status"] == "paused_travel"
    inspected = session_state.inspect_group_travel_target(sess, "main", source="test")

    assert inspected is not None
    assert inspected["status"] == "idle"
    assert inspected["current_map_position"]["node_id"] == "замок"
    assert inspected["last_travel_resolution"] == {
        "resolution_kind": "inspect_target",
        "pause_reason": "point_of_interest_reached",
        "target_label": "ворота",
        "source": "test",
        "details": {"inspected": True},
    }
    assert inspected["last_inspect_result"]["node_id"] == "ворота"
    assert inspected["last_inspect_result"]["inspect_summary"] == "ворота"

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "лесная тропа",
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "лесная тропа",
                "label": "лесная тропа",
                "zone_label": "лесная тропа",
                "area_label": "лесная тропа",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "лесная тропа",
                "label": "лесная тропа",
            },
            "next_zone_label": "лесная тропа",
        },
        source="test",
    )
    session_state.pause_group_travel(sess, "main", reason="route_blocked", pause_details={"blocker": "оползень"})
    bypassed = session_state.bypass_group_travel_pause(sess, "main", source="test")

    assert bypassed is not None
    assert bypassed["status"] == "idle"
    assert bypassed["current_map_position"]["node_id"] == "замок"
    assert bypassed["last_travel_resolution"] == {
        "resolution_kind": "bypass",
        "pause_reason": "route_blocked",
        "target_label": "лесная тропа",
        "source": "test",
        "details": {"bypassed": True},
    }


def test_complete_inspect_and_confirm_enter_update_player_map_knowledge() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "Ворота крепости",
            "target_node": {
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "fortress_gate",
                "label": "Ворота крепости",
                "zone_label": "Стартовый тракт",
                "area_label": "Стартовый тракт",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "fortress_gate",
                "label": "Ворота крепости",
                "area_label": "Стартовый тракт",
            },
            "next_zone_label": "Стартовый тракт",
        },
        source="test",
    )
    completed = session_state.complete_group_travel(sess, "main", player_id=player_id, source="test")

    assert completed is not None
    assert session_state.get_player_map_knowledge(sess, player_id)["fortress_gate"]["knowledge_kind"] == "visited"
    assert session_state.is_player_node_revealed(sess, player_id, "fortress_gate") is True

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "Сторожевая башня",
            "target_node": {
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "watchtower",
                "label": "Сторожевая башня",
                "zone_label": "Восточный берег",
                "area_label": "Восточный берег",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "watchtower",
                "label": "Сторожевая башня",
                "area_label": "Восточный берег",
            },
            "next_zone_label": "Восточный берег",
            "pause_hint": "inspection_required",
        },
        source="test",
    )
    inspected = session_state.inspect_group_travel_target(sess, "main", player_id=player_id, source="test")

    assert inspected is not None
    assert session_state.get_player_map_knowledge(sess, player_id)["watchtower"]["knowledge_kind"] == "discovered"
    assert session_state.is_player_node_revealed(sess, player_id, "watchtower") is True
    assert inspected["last_inspect_result"]["node_id"] == "watchtower"

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "enter_location",
            "action_kind": "enter",
            "target_label": "Шахтный вход",
            "target_node": {
                "map_level": "interior",
                "node_type": "interior_entry",
                "node_id": "mine_entrance",
                "label": "Шахтный вход",
                "zone_label": "Лесная дорога",
                "area_label": "Лесная дорога",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "interior",
                "node_type": "interior_entry",
                "node_id": "mine_entrance",
                "label": "Шахтный вход",
                "area_label": "Лесная дорога",
            },
            "next_zone_label": "Лесная дорога",
        },
        source="test",
    )
    confirmed = session_state.confirm_group_enter(sess, "main", player_id=player_id, source="test")

    assert confirmed is not None
    assert session_state.get_player_map_knowledge(sess, player_id)["mine_entrance"]["knowledge_kind"] == "visited"
    assert session_state.is_player_node_revealed(sess, player_id, "mine_entrance") is True

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "старая башня",
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "старая башня",
                "label": "старая башня",
                "zone_label": "старая башня",
                "area_label": "старая башня",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "старая башня",
                "label": "старая башня",
            },
            "next_zone_label": "старая башня",
        },
        source="test",
    )
    session_state.pause_group_travel(sess, "main", reason="event_pending", pause_details={"event_id": "poi-1"})
    resolved = session_state.resolve_group_travel_pause(sess, "main", source="test")

    assert resolved is not None
    assert resolved["status"] == "moving"
    assert resolved["travel_state"]["paused"] is False
    assert resolved["last_travel_resolution"] == {
        "resolution_kind": "resolve_pause",
        "pause_reason": "event_pending",
        "target_label": "старая башня",
        "source": "test",
        "details": {"resolved": True},
    }
