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


def test_build_group_camp_result_prefers_safe_or_sheltered_rest_on_safe_node() -> None:
    result = session_state.build_group_camp_result(
        {"reason": "ночлег", "source": "test"},
        node_context={
            "node_summary": {
                "node_id": "chapel_village",
                "label": "Деревня у часовни",
                "zone_band": "safe",
                "settlement_kind": "village",
                "poi_kind": "chapel",
                "safe_rest_hint": True,
            }
        },
        available_services=[{"service_key": "safe_rest", "label": "Безопасный отдых"}],
        source="test",
    )

    assert result is not None
    assert result["result_type"] == "sheltered_rest"
    assert result["rest_quality"] == "sheltered"
    assert result["risk_band"] == "low"


def test_build_group_camp_result_prefers_uneasy_or_interrupted_rest_on_border_or_danger_node() -> None:
    result = session_state.build_group_camp_result(
        {"reason": "ночлег", "source": "test"},
        node_context={
            "node_summary": {
                "node_id": "ruined_settlement",
                "label": "Разрушенное поселение",
                "zone_band": "danger",
                "settlement_kind": "ruins",
                "safe_rest_hint": False,
            }
        },
        source="test",
    )

    assert result is not None
    assert result["result_type"] == "interrupted_rest"
    assert result["rest_quality"] == "interrupted"
    assert result["risk_band"] == "high"


def test_build_group_camp_result_active_blocking_event_worsens_outcome() -> None:
    result = session_state.build_group_camp_result(
        {"reason": "переждать", "source": "test"},
        node_context={
            "node_summary": {
                "node_id": "start_trakt",
                "label": "Стартовый тракт",
                "zone_band": "safe",
                "settlement_kind": "roadside",
                "safe_rest_hint": True,
            }
        },
        travel_event={
            "event_id": "evt-1",
            "event_key": "blocked_path",
            "event_type": "roadside_hook",
            "summary": "Путь заблокирован",
            "route_snapshot": {
                "allowed": True,
                "route_kind": "zone_move",
                "action_kind": "move",
                "target_label": "Лесной брод",
            },
            "source": "test",
            "active": True,
            "resolved": False,
        },
        source="test",
    )

    assert result is not None
    assert result["result_type"] == "interrupted_rest"
    assert any("blocked_route" in effect for effect in result["applied_effects"])


def test_resolve_group_camp_stores_canonical_result_and_exposes_current_result() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "chapel_village",
            "label": "Деревня у часовни",
        },
    )
    session_state.set_group_camp(sess, "main", reason="ночлег", source="test", requested_by=player_id)

    resolved, error = session_state.resolve_group_camp(sess, "main", player_id=player_id, source="test")

    assert error is None
    assert resolved is not None
    assert resolved["status"] == "idle"
    assert resolved["last_camp_result"]["result_type"] in {"safe_rest", "sheltered_rest"}
    assert session_state.get_current_group_last_camp_result(sess, player_id=player_id) == resolved["last_camp_result"]


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
    assert options[0]["route_id"] == "start_trakt->fortress_gate:move"
    assert options[0]["access_state"] == "open"
    assert options[0]["is_traversable"] is True
    assert options[0]["blocked"] is False

    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    updated_options = session_state.get_current_group_navigation_options(sess, player_id=player_id)

    assert [option["target_node_id"] for option in updated_options] == ["fortress_gate", "craft_town"]
    assert updated_options[1]["known"] is True
    assert updated_options[1]["revealed"] is False
    assert updated_options[1]["access_state"] == "open"
    assert updated_options[1]["is_traversable"] is True


def test_group_route_access_state_stores_reads_and_is_scoped_per_group() -> None:
    leader_id = uuid.uuid4()
    other_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [leader_id, other_id], "Стартовый тракт")
    session_state._split_group(sess, "main", [other_id], new_group_id="scout")

    stored = session_state.set_group_route_access_state(
        sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Путь к городку завален поваленными телегами.",
        block_reason="debris",
        source="test",
    )

    assert stored is not None
    assert session_state.get_group_route_access_state(sess, "main", "start_trakt->craft_town:move") == stored
    assert session_state.get_effective_group_route_access_state(
        sess,
        "main",
        route_id="start_trakt->craft_town:move",
    )["is_traversable"] is False
    assert session_state.get_group_route_access_state(sess, "scout", "start_trakt->craft_town:move") is None


def test_navigation_options_keep_blocked_revealed_route_visible_but_unavailable() -> None:
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
    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "craft_town", source="test")
    session_state.set_group_route_access_state(
        sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Путь к городку перекрыт.",
        block_reason="blocked_path",
        source="test",
    )

    options = session_state.get_current_group_navigation_options(sess, player_id=player_id)
    blocked_option = next(option for option in options if option["target_node_id"] == "craft_town")

    assert blocked_option["revealed"] is True
    assert blocked_option["blocked"] is True
    assert blocked_option["is_traversable"] is False
    assert blocked_option["access_state"] == "blocked"
    assert blocked_option["block_reason"] == "blocked_path"


def test_build_group_scout_result_reveals_authored_route_or_landmark() -> None:
    result = session_state.build_group_scout_result(
        node_context={
            "node_summary": {
                "node_id": "start_trakt",
                "label": "Стартовый тракт",
            }
        },
        scout_discoveries=[
            {
                "result_type": "route_revealed",
                "discovery_scope": "adjacent_route",
                "discovered_node_ids": ["craft_town"],
                "discovered_route_ids": ["start_trakt->craft_town"],
                "discovered_notes": ["С тракта замечается надёжный боковой путь к озёрному городку."],
            }
        ],
        fully_revealed_node_ids=["start_trakt", "fortress_gate"],
        source="test",
    )

    assert result is not None
    assert result["result_type"] == "route_revealed"
    assert result["discovery_scope"] == "adjacent_route"
    assert result["discovered_node_ids"] == ["craft_town"]
    assert result["reveal_applied"] is True


def test_build_group_scout_result_hidden_path_and_repeated_scout_no_new_findings() -> None:
    hidden_result = session_state.build_group_scout_result(
        node_context={
            "node_summary": {
                "node_id": "forest_road",
                "label": "Лесная дорога",
            }
        },
        scout_discoveries=[
            {
                "result_type": "hidden_path_revealed",
                "discovery_scope": "hidden_route",
                "discovered_node_ids": ["ruined_settlement"],
                "discovered_route_ids": ["forest_road->ruined_settlement"],
                "discovered_notes": ["В стороне от лесной дороги открывается старая тропа к разрушенному посёлку."],
            }
        ],
        fully_revealed_node_ids=["forest_road"],
        source="test",
    )
    repeated_result = session_state.build_group_scout_result(
        node_context={
            "node_summary": {
                "node_id": "forest_road",
                "label": "Лесная дорога",
            }
        },
        scout_discoveries=[
            {
                "result_type": "hidden_path_revealed",
                "discovery_scope": "hidden_route",
                "discovered_node_ids": ["ruined_settlement"],
                "discovered_route_ids": ["forest_road->ruined_settlement"],
                "discovered_notes": ["В стороне от лесной дороги открывается старая тропа к разрушенному посёлку."],
            }
        ],
        fully_revealed_node_ids=["forest_road", "ruined_settlement"],
        source="test",
    )

    assert hidden_result is not None
    assert hidden_result["result_type"] == "hidden_path_revealed"
    assert repeated_result is not None
    assert repeated_result["result_type"] == "no_new_findings"
    assert repeated_result["reveal_applied"] is False


def test_build_group_scout_result_can_return_local_clue_found() -> None:
    result = session_state.build_group_scout_result(
        node_context={
            "node_summary": {
                "node_id": "chapel_village",
                "label": "Часовенное село",
            }
        },
        node_detail={
            "node_id": "chapel_village",
            "travel_note": "Удобная пограничная остановка между берегом и лесными дорогами.",
        },
        scout_discoveries=[],
        fully_revealed_node_ids=["chapel_village"],
        source="test",
    )

    assert result is not None
    assert result["result_type"] == "local_clue_found"
    assert result["discovered_notes"] == ["Удобная пограничная остановка между берегом и лесными дорогами."]


def test_resolve_group_scout_stores_canonical_result_and_updates_navigation_visibility() -> None:
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

    before_options = session_state.get_current_group_navigation_options(sess, player_id=player_id)
    resolved, error = session_state.resolve_group_scout(sess, "main", player_id=player_id, source="test")
    after_options = session_state.get_current_group_navigation_options(sess, player_id=player_id)

    assert error is None
    assert resolved is not None
    assert session_state.get_current_group_last_scout_result(sess, player_id=player_id) == resolved["last_scout_result"]
    assert resolved["last_scout_result"]["result_type"] == "route_revealed"
    assert [option["target_node_id"] for option in before_options] == ["fortress_gate"]
    assert [option["target_node_id"] for option in after_options] == ["fortress_gate", "craft_town"]
    assert after_options[1]["revealed"] is True


def test_resolve_group_scout_reveal_scope_is_not_global_and_keeps_knowledge_reveal_split() -> None:
    leader_id = uuid.uuid4()
    other_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [leader_id, other_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    session_state._split_group(sess, "main", [other_id], new_group_id="scout")

    resolved, error = session_state.resolve_group_scout(sess, "main", player_id=leader_id, source="test")

    assert error is None
    assert resolved is not None
    assert session_state.is_player_node_revealed(sess, leader_id, "craft_town") is True
    assert session_state.is_player_node_revealed(sess, other_id, "craft_town") is False
    assert session_state.has_player_map_knowledge(sess, leader_id, "craft_town") is True
    assert session_state.get_player_map_knowledge(sess, leader_id)["craft_town"]["knowledge_kind"] == "known"


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


def test_execute_group_navigation_option_rejects_blocked_revealed_route_and_allows_cleared_route() -> None:
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
    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "craft_town", source="test")
    session_state.set_group_route_access_state(
        sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Путь к городку перекрыт.",
        block_reason="оползень",
        source="test",
    )

    blocked_updated, blocked_error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="craft_town",
        player_id=player_id,
        source="test",
    )

    assert blocked_updated is None
    assert blocked_error == "Маршрут к Озёрный городок сейчас заблокирован: оползень."

    session_state.set_group_route_access_state(
        sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="cleared",
        summary="Путь к городку снова проходим.",
        source="test",
    )
    cleared_updated, cleared_error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="craft_town",
        player_id=player_id,
        source="test",
    )

    assert cleared_error is None
    assert cleared_updated is not None
    assert cleared_updated["movement_intent"]["target_node_id"] == "craft_town"


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
            {"action_id": "navigate", "action_key": "navigate", "label": "Продолжить путь", "action_type": "action", "action_kind": "navigate", "interaction_kind": "context_action", "interaction_id": "navigate", "availability_status": "available", "status": "available", "available": True, "unavailable_reason": "", "unlock_hint": "", "satisfied_requirements": [], "missing_requirements": [], "source": "interaction_gating", "exhausted": False},
            {"action_id": "inspect", "action_key": "inspect", "label": "Осмотреться", "action_type": "action", "action_kind": "inspect", "interaction_kind": "context_action", "interaction_id": "inspect", "availability_status": "available", "status": "available", "available": True, "unavailable_reason": "", "unlock_hint": "", "satisfied_requirements": [], "missing_requirements": [], "source": "interaction_gating", "exhausted": False},
            {"action_id": "wait", "action_key": "wait", "label": "Подождать", "action_type": "action", "action_kind": "wait", "interaction_kind": "context_action", "interaction_id": "wait", "availability_status": "available", "status": "available", "available": True, "unavailable_reason": "", "unlock_hint": "", "satisfied_requirements": [], "missing_requirements": [], "source": "interaction_gating", "exhausted": False},
            {"action_id": "rest_hint", "action_key": "rest_hint", "label": "Есть место для передышки", "action_type": "hint", "action_kind": "rest_hint", "interaction_kind": "context_action", "interaction_id": "rest_hint", "availability_status": "unavailable", "status": "unavailable", "available": False, "unavailable_reason": "informational_only", "unlock_hint": "", "satisfied_requirements": [], "missing_requirements": [], "source": "interaction_gating", "exhausted": False},
            {"action_id": "trace_watchtower_bearing", "action_key": "trace_watchtower_bearing", "label": "Сверить береговой ориентир", "action_type": "action", "action_kind": "clue", "interaction_kind": "context_action", "interaction_id": "trace_watchtower_bearing", "availability_status": "locked", "status": "locked", "available": False, "unavailable_reason": "requires_node_state_flag", "unlock_hint": "Сначала получить береговую наводку при первом прибытии в городок.", "satisfied_requirements": [], "missing_requirements": ["node_state:craft_arrival_notice_taken", "first_visit_only"], "source": "registry", "one_shot": False, "exhausted": False},
        ],
        "available_services": [
            {
                "service_id": "craft_town:safe_rest",
                "service_key": "safe_rest",
                "label": "Безопасный отдых",
                "service_type": "rest",
                "service_kind": "rest",
                "summary": "Можно перевести дух и переждать путь в сравнительно безопасных условиях.",
                "source": "registry",
                "interaction_kind": "service",
                "interaction_id": "craft_town:safe_rest",
                "availability_status": "available",
                "available": True,
                "status": "available",
                "unavailable_reason": "",
                "unlock_hint": "",
                "satisfied_requirements": [],
                "missing_requirements": [],
                "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
            },
            {
                "service_id": "craft_town:resupply",
                "service_key": "resupply",
                "label": "Пополнение припасов",
                "service_type": "supplies",
                "service_kind": "supplies",
                "summary": "Здесь можно пополнить базовые дорожные запасы перед выходом.",
                "source": "registry",
                "interaction_kind": "service",
                "interaction_id": "craft_town:resupply",
                "availability_status": "available",
                "available": True,
                "status": "available",
                "unavailable_reason": "",
                "unlock_hint": "",
                "satisfied_requirements": [],
                "missing_requirements": [],
                "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
            },
            {
                "service_id": "craft_town_local_guidance",
                "service_key": "local_guidance",
                "label": "Местные указания",
                "service_type": "guidance",
                "service_kind": "guidance",
                "summary": "Здесь можно получить ориентиры, слухи и безопасные подсказки по ближайшим дорогам.",
                "source": "registry",
                "interaction_kind": "service",
                "interaction_id": "craft_town_local_guidance",
                "availability_status": "locked",
                "unavailable_reason": "requires_destination_event_id",
                "unlock_hint": "Сначала получить местную наводку при прибытии в городок.",
                "satisfied_requirements": [],
                "missing_requirements": ["destination_event:craft_town_arrival_notice", "destination_event_result:settlement_notice"],
                "status": "locked",
                "available": False,
                "one_shot": True,
                "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
            },
            {
                "service_id": "craft_town:healing_aid",
                "service_key": "healing_aid",
                "label": "Помощь с ранами",
                "service_type": "aid",
                "service_kind": "aid",
                "summary": "На месте можно получить перевязку, уход или базовую помощь после дороги.",
                "source": "registry",
                "interaction_kind": "service",
                "interaction_id": "craft_town:healing_aid",
                "availability_status": "available",
                "available": True,
                "status": "available",
                "unavailable_reason": "",
                "unlock_hint": "",
                "satisfied_requirements": [],
                "missing_requirements": [],
                "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
            },
        ],
        "service_actions": [
            {"action_key": "use_service", "label": "Воспользоваться услугой", "action_type": "action"},
        ],
        "current_node_progression_status": "locally_active",
        "current_node_progression_summary": "В Озёрный городок ещё есть доступные локальные действия или услуги.",
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
        service_id="craft_town:resupply",
        source="test",
    )

    assert [service["service_key"] for service in services] == [
        "safe_rest",
        "resupply",
        "local_guidance",
        "healing_aid",
    ]
    assert next(service for service in services if service["service_key"] == "local_guidance")["availability_status"] == "locked"
    assert error is None
    assert updated is not None
    assert session_state.get_current_group_last_service_result(sess, player_id=player_id) == {
        "result_id": updated["last_service_result"]["result_id"],
        "service_id": "craft_town:resupply",
        "service_key": "resupply",
        "service_label": "Пополнение припасов",
        "label": "Пополнение припасов",
        "result_type": "supplies_secured",
        "service_type": "supplies",
        "service_kind": "supplies",
        "summary": "Здесь можно пополнить базовые дорожные запасы перед выходом.",
        "result_summary": "Здесь можно собрать базовые припасы и привести снаряжение в порядок.",
        "node_id": "craft_town",
        "node_label": "Озёрный городок",
        "reveal_applied": False,
        "source": "test",
        "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
        "resolved_at": updated["last_service_result"]["resolved_at"],
    }
    assert session_state.get_current_group_service_states(sess, player_id=player_id) == [
        {
            "service_id": "craft_town:resupply",
            "status": "resolved",
            "result_type": "supplies_secured",
            "summary": "Здесь можно собрать базовые припасы и привести снаряжение в порядок.",
            "source": "test",
            "updated_at": updated["service_states"]["craft_town:resupply"]["updated_at"],
        }
    ]


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
        service_id="safe_rest",
        source="test",
    )

    assert updated is None
    assert error == "Эта услуга сейчас недоступна в текущем месте."


def test_resolve_group_service_can_reveal_and_update_node_state_with_already_used_repeat() -> None:
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
    session_state.record_group_node_visit(
        sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="settlement_arrival",
        summary="Группа прибыла в городок.",
    )
    session_state.resolve_group_destination_event(sess, "main", source="test")

    resolved, error = session_state.resolve_group_service(
        sess,
        "main",
        service_id="craft_town_local_guidance",
        player_id=player_id,
        source="test",
    )
    repeated, repeated_error = session_state.resolve_group_service(
        sess,
        "main",
        service_id="craft_town_local_guidance",
        player_id=player_id,
        source="test",
    )
    services_after = session_state.get_current_group_node_services(sess, player_id=player_id)

    assert error is None
    assert resolved is not None
    assert resolved["last_service_result"]["result_type"] == "guidance_received"
    assert resolved["last_service_result"]["reveal_applied"] is False
    assert session_state.is_player_node_revealed(sess, player_id, "watchtower") is True
    assert set(session_state.get_group_node_state(sess, "main", "craft_town")["state_flags"]) == {
        "craft_arrival_notice_taken",
        "craft_guidance_taken",
    }
    assert repeated_error is None
    assert repeated is not None
    assert repeated["last_service_result"]["result_type"] == "already_used"
    used_service = next(service for service in services_after if service["service_id"] == "craft_town_local_guidance")
    assert used_service["available"] is False
    assert used_service["status"] == "completed"
    assert used_service["unavailable_reason"] == "already_used"


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
        "action_id": "enter",
        "action_key": "enter",
        "label": "Войти",
        "action_type": "action",
        "action_kind": "enter",
        "interaction_kind": "context_action",
        "interaction_id": "enter",
        "availability_status": "available",
        "status": "available",
        "available": True,
        "unavailable_reason": "",
        "unlock_hint": "",
        "satisfied_requirements": [],
        "missing_requirements": [],
        "source": "interaction_gating",
        "exhausted": False,
    }


def test_local_interaction_gating_uses_node_state_destination_event_and_visit_history() -> None:
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

    actions_before = session_state.get_current_group_context_action_availability(sess, player_id=player_id)
    services_before = session_state.get_current_group_service_availability(sess, player_id=player_id)

    gated_action_before = next(item for item in actions_before if item["action_id"] == "trace_watchtower_bearing")
    gated_service_before = next(item for item in services_before if item["service_id"] == "craft_town_local_guidance")
    assert gated_action_before["availability_status"] == "locked"
    assert gated_service_before["availability_status"] == "locked"

    session_state.record_group_node_visit(
        sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="settlement_arrival",
        summary="Группа впервые прибыла в городок.",
    )
    session_state.resolve_group_destination_event(sess, "main", source="test")

    actions_after = session_state.get_current_group_context_action_availability(sess, player_id=player_id)
    services_after = session_state.get_current_group_service_availability(sess, player_id=player_id)

    gated_action_after = next(item for item in actions_after if item["action_id"] == "trace_watchtower_bearing")
    gated_service_after = next(item for item in services_after if item["service_id"] == "craft_town_local_guidance")
    assert gated_action_after["availability_status"] == "available"
    assert "node_state:craft_arrival_notice_taken" in gated_action_after["satisfied_requirements"]
    assert gated_service_after["availability_status"] == "available"
    assert "destination_event:craft_town_arrival_notice" in gated_service_after["satisfied_requirements"]


def test_local_interaction_gating_honors_return_visit_and_min_visit_count() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "chapel_village",
            "label": "Часовенное село",
        },
    )
    first_visit_actions = session_state.get_current_group_context_action_availability(sess, player_id=player_id)
    first_visit_services = session_state.get_current_group_service_availability(sess, player_id=player_id)
    assert next(item for item in first_visit_actions if item["action_id"] == "listen_chapel_watch")["availability_status"] == "locked"
    assert next(item for item in first_visit_services if item["service_id"] == "chapel_village_shrine_aid")["availability_status"] == "locked"

    session_state.record_group_node_visit(
        sess,
        "main",
        "chapel_village",
        node_label="Часовенное село",
        result_type="settlement_arrival",
        summary="Первый визит.",
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "chapel_village",
        node_label="Часовенное село",
        result_type="return_arrival",
        summary="Повторный визит.",
    )

    return_visit_actions = session_state.get_current_group_context_action_availability(sess, player_id=player_id)
    return_visit_services = session_state.get_current_group_service_availability(sess, player_id=player_id)
    assert next(item for item in return_visit_actions if item["action_id"] == "listen_chapel_watch")["availability_status"] == "available"
    assert next(item for item in return_visit_services if item["service_id"] == "chapel_village_shrine_aid")["availability_status"] == "available"

    session_state._set_group_map_position(
        sess,
        "main",
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    forest_services_before = session_state.get_current_group_service_availability(sess, player_id=player_id)
    assert next(item for item in forest_services_before if item["service_id"] == "forest_settlement_resupply")["availability_status"] == "locked"
    session_state.record_group_node_visit(
        sess,
        "main",
        "forest_settlement",
        node_label="Лесной посёлок",
        result_type="first_arrival",
        summary="Первый визит в лесной посёлок.",
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "forest_settlement",
        node_label="Лесной посёлок",
        result_type="return_arrival",
        summary="Второй визит в лесной посёлок.",
    )
    forest_services_after = session_state.get_current_group_service_availability(sess, player_id=player_id)
    assert next(item for item in forest_services_after if item["service_id"] == "forest_settlement_resupply")["availability_status"] == "available"


def test_local_interaction_gating_enforces_locked_execution_without_side_effects() -> None:
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

    action_updated, action_error = session_state.execute_current_group_context_action(
        sess,
        action_key="trace_watchtower_bearing",
        player_id=player_id,
        source="test",
    )
    service_updated, service_error = session_state.execute_current_group_service(
        sess,
        player_id=player_id,
        service_id="craft_town_local_guidance",
        source="test",
    )

    assert action_updated is None
    assert action_error == "Сначала получить береговую наводку при первом прибытии в городок."
    assert service_updated is None
    assert service_error == "Сначала получить местную наводку при прибытии в городок."
    assert session_state.get_current_group_last_context_action_result(sess, player_id=player_id) is None
    assert session_state.get_current_group_last_service_result(sess, player_id=player_id) is None


def test_local_interaction_surface_groups_available_and_locked_entries() -> None:
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

    surface = session_state.get_current_group_local_interaction_surface(sess, player_id=player_id)

    assert surface is not None
    assert surface["node_id"] == "craft_town"
    assert any(item["interaction_id"] == "navigate" for item in surface["available_actions"])
    assert any(item["interaction_id"] == "trace_watchtower_bearing" for item in surface["locked_actions"])
    assert any(item["interaction_id"] == "craft_town_local_guidance" for item in surface["locked_services"])


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


def test_resolve_group_context_action_stores_canonical_result_and_updates_route_access() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.set_group_route_access_state(
        sess,
        "main",
        "forest_road->ruined_settlement:move",
        access_state="blocked",
        summary="Старая дорога завалена.",
        block_reason="fallen_trees",
        source="test",
    )

    resolved, error = session_state.resolve_group_context_action(
        sess,
        "main",
        action_id="clear_old_road",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert resolved is not None
    assert resolved["last_context_action_result"]["result_type"] == "route_cleared"
    assert resolved["last_context_action_result"]["action_id"] == "clear_old_road"
    assert session_state.get_current_group_last_context_action_result(sess, player_id=player_id) == resolved["last_context_action_result"]
    assert session_state.get_group_route_access_state(sess, "main", "forest_road->ruined_settlement:move")["access_state"] == "cleared"
    assert session_state.get_current_group_context_action_states(sess, player_id=player_id) == [
        {
            "action_id": "clear_old_road",
            "status": "completed",
            "result_type": "route_cleared",
            "summary": "Группа убирает завал с лесной дороги и открывает устойчивый проход к разрушенному посёлку.",
            "source": "test",
            "updated_at": resolved["context_action_states"]["clear_old_road"]["updated_at"],
        }
    ]


def test_repeated_one_shot_context_action_returns_already_completed_and_context_marks_exhausted() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "chapel_village",
            "label": "Часовенное село",
        },
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "chapel_village",
        node_label="Часовенное село",
        result_type="settlement_arrival",
        summary="Первый визит.",
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "chapel_village",
        node_label="Часовенное село",
        result_type="return_arrival",
        summary="Повторный визит.",
    )

    first, first_error = session_state.resolve_group_context_action(
        sess,
        "main",
        action_id="listen_chapel_watch",
        player_id=player_id,
        source="test",
    )
    repeated, repeated_error = session_state.resolve_group_context_action(
        sess,
        "main",
        action_id="listen_chapel_watch",
        player_id=player_id,
        source="test",
    )
    context = session_state.get_current_group_node_context(sess, player_id=player_id)

    assert first_error is None
    assert first is not None
    assert first["last_context_action_result"]["result_type"] == "local_clue_found"
    assert repeated_error is None
    assert repeated is not None
    assert repeated["last_context_action_result"]["result_type"] == "already_completed"
    authored_action = next(action for action in context["contextual_actions"] if action["action_id"] == "listen_chapel_watch")
    assert authored_action["status"] == "completed"
    assert authored_action["available"] is False
    assert authored_action["exhausted"] is True


def test_context_action_can_keep_route_blocked_and_no_effect_is_explicit() -> None:
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

    blocked, blocked_error = session_state.resolve_group_context_action(
        sess,
        "main",
        action_id="shore_up_mine_path",
        player_id=player_id,
        source="test",
    )

    assert blocked_error is None
    assert blocked is not None
    assert blocked["last_context_action_result"]["result_type"] == "route_still_blocked"
    assert session_state.get_group_route_access_state(sess, "main", "ruined_settlement->mine_entrance:enter")["access_state"] == "blocked"

    no_effect_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        no_effect_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.set_group_route_access_state(
        no_effect_sess,
        "main",
        "forest_road->ruined_settlement:move",
        access_state="open",
        summary="Маршрут уже открыт.",
        source="test",
    )

    no_effect, no_effect_error = session_state.resolve_group_context_action(
        no_effect_sess,
        "main",
        action_id="clear_old_road",
        player_id=player_id,
        source="test",
    )

    assert no_effect_error is None
    assert no_effect is not None
    assert no_effect["last_context_action_result"]["result_type"] == "no_effect"


def test_group_node_state_storage_helpers_are_canonical_and_scoped_per_group() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [left_id, right_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    split_request = session_state.request_group_split("main", [str(right_id)], new_group_id="scouts")
    session_state.apply_group_split(sess, split_request)

    stored = session_state.set_group_node_state(
        sess,
        "main",
        "forest_road",
        state_flags=["old_road_cleared"],
        summary="Старая дорога расчищена.",
        source="test",
    )
    added = session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_road",
        state_flag="watch_post_checked",
        summary="Группа заодно проверила край дороги.",
        source="test",
    )

    assert stored is not None
    assert stored["node_id"] == "forest_road"
    assert session_state.get_group_node_state(sess, "main", "forest_road") == {
        "node_id": "forest_road",
        "state_flags": ["old_road_cleared", "watch_post_checked"],
        "summary": "Группа заодно проверила край дороги.",
        "source": "test",
        "updated_at": added["updated_at"],
    }
    assert session_state.has_group_node_state_flag(sess, "main", "forest_road", "old_road_cleared") is True
    assert session_state.has_group_node_state_flag(sess, "main", "forest_road", "watch_post_checked") is True
    assert session_state.get_group_node_state(sess, "scouts", "forest_road") is None


def test_contextual_action_updates_node_state_and_keeps_layers_separate() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.set_group_route_access_state(
        sess,
        "main",
        "forest_road->ruined_settlement:move",
        access_state="blocked",
        summary="Старая дорога завалена.",
        block_reason="fallen_trees",
        source="test",
    )

    resolved, error = session_state.resolve_group_context_action(
        sess,
        "main",
        action_id="clear_old_road",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert resolved is not None
    assert session_state.get_group_node_state(sess, "main", "forest_road") == {
        "node_id": "forest_road",
        "state_flags": ["old_road_cleared"],
        "summary": "На лесной дороге заметны следы недавней расчистки старого прохода.",
        "source": "test",
        "updated_at": resolved["node_states"]["forest_road"]["updated_at"],
    }
    assert session_state.get_group_route_access_state(sess, "main", "forest_road->ruined_settlement:move")["access_state"] == "cleared"
    assert resolved["context_action_states"]["clear_old_road"]["status"] == "completed"
    repeated, repeated_error = session_state.resolve_group_context_action(
        sess,
        "main",
        action_id="clear_old_road",
        player_id=player_id,
        source="test",
    )
    assert repeated_error is None
    assert repeated is not None
    assert repeated["last_context_action_result"]["result_type"] == "already_completed"
    assert session_state.get_group_node_state(sess, "main", "forest_road")["state_flags"] == ["old_road_cleared"]


def test_current_group_node_context_and_detail_reflect_node_state_overlays() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "chapel_village",
            "label": "Часовенное село",
        },
    )
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "chapel_village",
        state_flag="chapel_watch_clue_taken",
        summary="Дозорные уже поделились короткой наводкой.",
        source="test",
    )

    context = session_state.get_current_group_node_context(sess, player_id=player_id)
    detail = session_state.get_current_group_node_detail(sess, player_id=player_id)

    assert context is not None
    assert context["node_state_flags"] == ["chapel_watch_clue_taken"]
    assert context["state_notes"] == [
        "У часовни уже собраны местные подсказки, и дозорные узнают группу."
    ]
    assert detail is not None
    assert detail["node_state_flags"] == ["chapel_watch_clue_taken"]
    assert detail["state_notes"] == [
        "Разговор с дозорными оставил конкретную дорожную наводку, и местные уже не повторяют её как первую новость."
    ]


def test_inspect_current_group_node_reflects_changed_node_condition() -> None:
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
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "ruined_settlement",
        state_flag="mine_path_shored",
        summary="Подход к шахте укреплён, но ещё тревожит.",
        source="test",
    )

    inspected = session_state.inspect_current_group_node(sess, player_id=player_id, source="test")

    assert inspected is not None
    assert inspected["last_inspect_result"]["state_notes"] == [
        "У входа в шахту заметны новые подпорки и следы осмотра, но сам проход остаётся тревожно нестабильным."
    ]


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
    assert completed["last_arrival_result"]["result_type"] == "landmark_arrival"
    assert completed["last_arrival_result"]["visit_count"] == 1
    assert completed["route_traversal_states"]["start_trakt->fortress_gate:move"]["traversal_count"] == 1
    assert completed["node_visit_states"]["fortress_gate"]["visit_count"] == 1
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
    assert confirmed["last_arrival_result"]["node_id"] == "mine_entrance"
    assert confirmed["node_visit_states"]["mine_entrance"]["visit_count"] == 1
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


def test_build_group_travel_event_candidates_use_route_metadata() -> None:
    safe_candidates = session_state.build_group_travel_event_candidates(
        {
            "allowed": True,
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "Восточный берег",
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "eastern_bank",
                "label": "Восточный берег",
            },
            "traversal_kind": "road",
            "risk_band": "low",
            "terrain_hint": "open",
        },
        movement_mode="normal",
        source="test",
    )
    danger_candidates = session_state.build_group_travel_event_candidates(
        {
            "allowed": True,
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "Край болот",
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "marsh_edge",
                "label": "Край болот",
            },
            "traversal_kind": "marsh_path",
            "risk_band": "high",
            "terrain_hint": "marsh",
            "travel_tags": ["poor_visibility"],
        },
        movement_mode="cautious",
        travel_activity={"activity": "observe", "source": "test"},
        source="test",
    )

    assert [candidate["event_key"] for candidate in safe_candidates] == ["roadside_finding", "lost_traveler"]
    assert "blocked_path" in [candidate["event_key"] for candidate in danger_candidates]
    assert "ominous_quiet" in [candidate["event_key"] for candidate in danger_candidates]


def test_trigger_and_resolve_group_travel_event_update_state_honestly() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Стартовый тракт")

    started = session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "Край болот",
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "marsh_edge",
                "label": "Край болот",
                "zone_label": "Край болот",
                "area_label": "Край болот",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "marsh_edge",
                "label": "Край болот",
            },
            "next_zone_label": "Край болот",
            "traversal_kind": "marsh_path",
            "risk_band": "high",
            "terrain_hint": "marsh",
            "travel_tags": ["poor_visibility"],
        },
        movement_mode="cautious",
        source="test",
    )

    assert started is not None
    assert started["travel_event"]["event_key"] == "blocked_path"
    assert started["travel_event"]["active"] is True
    assert started["status"] == "paused_travel"
    assert started["travel_state"]["pause_reason"] == "route_blocked"
    assert started["travel_state"]["resume_allowed"] is False

    resolved, resolve_error = session_state.resolve_group_travel_event(
        sess,
        "main",
        resolution="resolve",
        player_id=player_id,
        source="test",
    )

    assert resolve_error is None
    assert resolved is not None
    assert resolved["status"] == "moving"
    assert resolved["travel_state"]["paused"] is False
    assert resolved["travel_event"]["event_key"] == "blocked_path"
    assert resolved["travel_event"]["active"] is False
    assert resolved["travel_event"]["resolved"] is True
    assert resolved["travel_event"]["resolution"] == "resolve"
    assert resolved["travel_event"]["source"] == "test"
    assert resolved["travel_event"]["route_snapshot"]["traversal_kind"] == "marsh_path"
    assert resolved["travel_event"]["route_snapshot"]["route_id"] == "стартовый тракт->marsh_edge:move"
    assert resolved["last_travel_event_outcome"]["event_key"] == "blocked_path"
    assert resolved["last_travel_event_outcome"]["outcome_type"] == "obstacle_cleared"
    assert resolved["last_travel_event_outcome"]["applied_effects"] == ["event_closed", "travel_resumed"]
    assert session_state.get_group_route_access_state(sess, "main", "стартовый тракт->marsh_edge:move") == {
        "route_id": "стартовый тракт->marsh_edge:move",
        "access_state": "cleared",
        "is_traversable": True,
        "summary": "Группа расчистила маршрут и может снова пройти этим путём.",
        "source": "test",
        "updated_at": resolved["route_access_states"]["стартовый тракт->marsh_edge:move"]["updated_at"],
    }


def test_trigger_non_blocking_event_and_ignore_event() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Стартовый тракт")

    started = session_state.start_group_travel(
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
            "source": "registry",
            "traversal_kind": "road",
            "risk_band": "low",
            "terrain_hint": "open",
        },
        source="test",
    )

    assert started is not None
    assert started["status"] == "moving"
    assert started["travel_event"]["event_key"] == "roadside_finding"
    assert started["travel_state"]["paused"] is False

    ignored, ignore_error = session_state.resolve_group_travel_event(
        sess,
        "main",
        resolution="ignore",
        player_id=player_id,
        source="test",
    )

    assert ignore_error is None
    assert ignored is not None
    assert ignored["status"] == "moving"
    assert ignored["travel_state"]["active"] is True
    assert ignored["travel_event"]["active"] is False
    assert ignored["travel_event"]["resolution"] == "ignore"
    assert ignored["last_travel_event_outcome"]["outcome_type"] == "ignored_event"
    assert ignored["last_travel_event_outcome"]["event_key"] == "roadside_finding"


def test_build_and_apply_group_travel_event_outcome_can_update_knowledge_and_reveal() -> None:
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

    event = {
        "event_id": "evt-signs",
        "event_key": "tracks_or_signs",
        "event_type": "roadside_hook",
        "summary": "На дороге видны старые зарубки и следы.",
        "route_snapshot": {
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
            "target_node_type": "landmark",
            "target_node_id": "watchtower",
        },
        "source": "travel",
        "active": True,
        "resolved": False,
    }

    outcome = session_state.build_group_travel_event_outcome(event, resolution="resolve", source="test")

    assert outcome is not None
    assert outcome["event_key"] == "tracks_or_signs"
    assert outcome["outcome_type"] == "route_hint"
    assert outcome["applied_effects"] == ["event_closed", "knowledge_updated", "node_revealed"]

    applied = session_state.apply_group_travel_event_outcome(
        sess,
        "main",
        outcome,
        player_id=player_id,
        source="test",
    )

    assert applied is not None
    assert session_state.get_current_group_last_travel_event_outcome(sess, player_id=player_id)["event_key"] == "tracks_or_signs"
    assert session_state.has_player_map_knowledge(sess, player_id, "watchtower") is True
    assert session_state.is_player_node_revealed(sess, player_id, "watchtower") is True


def test_apply_group_travel_event_outcome_route_still_blocked_updates_route_accessibility() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "marsh_edge",
            "label": "Край болот",
        },
    )

    applied = session_state.apply_group_travel_event_outcome(
        sess,
        "main",
        {
            "outcome_id": "out-blocked",
            "event_key": "blocked_path",
            "event_type": "roadside_hook",
            "outcome_type": "route_still_blocked",
            "summary": "Путь вязнет в болоте.",
            "result_summary": "Маршрут остаётся перекрыт.",
            "applied_effects": ["event_closed", "travel_interrupted"],
            "route_snapshot": {
                "allowed": True,
                "route_id": "marsh_edge->forgotten_shrine:move",
                "route_kind": "landmark_move",
                "action_kind": "move",
                "target_node_id": "forgotten_shrine",
                "target_label": "Забытое святилище",
            },
            "source": "test",
            "resolved_at": "2026-03-15T00:10:00+00:00",
        },
        player_id=player_id,
        source="test",
    )

    assert applied is not None
    assert session_state.get_group_route_access_state(sess, "main", "marsh_edge->forgotten_shrine:move") == {
        "route_id": "marsh_edge->forgotten_shrine:move",
        "access_state": "blocked",
        "is_traversable": False,
        "summary": "Маршрут остаётся заблокированным после попытки разобраться с преградой.",
        "block_reason": "route_blocked",
        "source": "test",
        "updated_at": applied["route_access_states"]["marsh_edge->forgotten_shrine:move"]["updated_at"],
    }


def test_resolve_group_travel_event_guidance_updates_only_target_knowledge() -> None:
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

    session_state.trigger_group_travel_event(
        sess,
        "main",
        event={
            "event_id": "evt-lost",
            "event_key": "lost_traveler",
            "event_type": "roadside_hook",
            "summary": "На тракте встречается заплутавший путник.",
            "route_snapshot": {
                "allowed": True,
                "route_kind": "zone_move",
                "action_kind": "move",
                "target_label": "Озёрный городок",
                "target_node": {
                    "map_level": "region",
                    "node_type": "zone",
                    "node_id": "craft_town",
                    "label": "Озёрный городок",
                },
                "target_node_type": "zone",
                "target_node_id": "craft_town",
            },
            "source": "travel",
            "active": True,
            "resolved": False,
        },
        source="test",
    )

    updated, error = session_state.resolve_group_travel_event(
        sess,
        "main",
        resolution="resolve",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert updated is not None
    assert updated["last_travel_event_outcome"]["outcome_type"] == "guidance_note"
    assert session_state.has_player_map_knowledge(sess, player_id, "craft_town") is True
    assert session_state.is_player_node_revealed(sess, player_id, "craft_town") is False


def test_group_map_intel_storage_recent_and_group_scope() -> None:
    player_id = uuid.uuid4()
    other_player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")
    groups = session_state._get_group_states(sess)
    groups["scout"] = {
        "group_id": "scout",
        "player_ids": [str(other_player_id)],
        "current_map_position": {
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
        "area_label": "Лесная дорога",
        "status": "idle",
        "movement_mode": "normal",
    }
    session_state._persist_group_states(sess, groups)

    first = session_state.add_group_map_intel_entry(
        sess,
        "main",
        session_state.build_group_map_intel_entry(
            entry_type="guidance",
            title="Дорожная наводка",
            summary="Группа получает наводку.",
            result_summary="Местные указывают безопасный береговой ориентир.",
            source_kind="service",
            source_id="craft_town_local_guidance",
            node_id="craft_town",
            node_label="Озёрный городок",
            related_node_ids=["watchtower"],
            related_route_ids=[],
            tags=["guidance", "craft_town"],
            dedupe_key="service|craft_town_local_guidance|guidance",
        ),
    )
    second = session_state.add_group_map_intel_entry(
        sess,
        "main",
        session_state.build_group_map_intel_entry(
            entry_type="warning",
            title="Предупреждение на дороге",
            summary="Группа отмечает риск.",
            result_summary="Лесная дорога к руинам пока остаётся рискованной.",
            source_kind="travel_event",
            source_id="evt-warning",
            node_id="forest_road",
            node_label="Лесная дорога",
            related_node_ids=[],
            related_route_ids=["forest_road->ruined_settlement:move"],
            tags=["warning", "road"],
            dedupe_key="travel_event|ominous_quiet|warning",
        ),
    )

    assert first is not None
    assert second is not None
    assert [entry["entry_type"] for entry in session_state.get_current_group_map_intel(sess, player_id=player_id)] == ["guidance", "warning"]
    assert [entry["entry_type"] for entry in session_state.get_current_group_recent_map_intel(sess, player_id=player_id, limit=1)] == ["warning"]
    assert session_state.get_current_group_map_intel(sess, group_id="scout") == []


def test_group_map_intel_dedupe_keeps_single_entry_per_dedupe_key() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")

    first = session_state.add_group_map_intel_entry(
        sess,
        "main",
        session_state.build_group_map_intel_entry(
            entry_type="clue",
            title="Локальная зацепка",
            summary="Группа находит зацепку.",
            result_summary="У часовни уже отмечена короткая дорожная наводка.",
            source_kind="context_action",
            source_id="listen_chapel_watch",
            node_id="chapel_village",
            node_label="Часовенное село",
            related_node_ids=[],
            related_route_ids=[],
            tags=["clue", "chapel"],
            dedupe_key="context_action|listen_chapel_watch|clue",
        ),
    )
    duplicate = session_state.add_group_map_intel_entry(
        sess,
        "main",
        session_state.build_group_map_intel_entry(
            entry_type="clue",
            title="Локальная зацепка",
            summary="Повтор той же зацепки.",
            result_summary="У часовни уже отмечена короткая дорожная наводка.",
            source_kind="context_action",
            source_id="listen_chapel_watch",
            node_id="chapel_village",
            node_label="Часовенное село",
            related_node_ids=[],
            related_route_ids=[],
            tags=["clue", "chapel"],
            dedupe_key="context_action|listen_chapel_watch|clue",
        ),
    )

    assert first is not None
    assert duplicate == first
    assert len(session_state.get_current_group_map_intel(sess, player_id=player_id)) == 1


def test_existing_outcomes_write_map_intel_entries() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})

    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    session_state.resolve_group_scout(sess, "main", player_id=player_id, source="test")
    scout_entries = session_state.get_current_group_map_intel(sess, player_id=player_id)
    assert scout_entries[-1]["source_kind"] == "scout"
    assert scout_entries[-1]["entry_type"] == "route_hint"

    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="settlement_arrival",
        summary="Группа прибыла в городок.",
    )
    session_state.resolve_group_destination_event(sess, "main", source="test")
    session_state.resolve_group_service(sess, "main", service_id="craft_town_local_guidance", player_id=player_id, source="test")
    service_entries = session_state.get_current_group_map_intel(sess, player_id=player_id)
    assert service_entries[-1]["source_kind"] == "service"
    assert service_entries[-1]["entry_type"] == "guidance"

    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "chapel_village", "label": "Часовенное село"},
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "chapel_village",
        node_label="Часовенное село",
        result_type="settlement_arrival",
        summary="Первый визит.",
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "chapel_village",
        node_label="Часовенное село",
        result_type="return_arrival",
        summary="Повторный визит.",
    )
    session_state.resolve_group_context_action(sess, "main", action_id="listen_chapel_watch", player_id=player_id, source="test")
    action_entries = session_state.get_current_group_map_intel(sess, player_id=player_id)
    assert action_entries[-1]["source_kind"] == "context_action"
    assert action_entries[-1]["entry_type"] == "clue"

    outcome = session_state.build_group_travel_event_outcome(
        {
            "event_id": "evt-route",
            "event_key": "tracks_or_signs",
            "event_type": "roadside_hook",
            "summary": "На дороге замечены следы и старые знаки.",
            "route_snapshot": {
                "allowed": True,
                "route_id": "start_trakt->craft_town:move",
                "route_kind": "zone_move",
                "action_kind": "move",
                "target_label": "Озёрный городок",
                "target_node_id": "craft_town",
                "target_node_type": "zone",
            },
            "source": "travel",
            "active": True,
            "resolved": False,
        },
        resolution="resolve",
        source="test",
    )
    assert outcome is not None
    session_state.apply_group_travel_event_outcome(sess, "main", outcome, player_id=player_id, source="test")
    event_entries = session_state.get_current_group_map_intel(sess, player_id=player_id)
    assert event_entries[-1]["source_kind"] == "travel_event"
    assert event_entries[-1]["entry_type"] == "route_hint"


def test_group_visit_history_storage_helpers_are_canonical_and_scoped_per_group() -> None:
    player_id = uuid.uuid4()
    other_player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    groups = session_state._get_group_states(sess)
    groups["scout"] = {
        "group_id": "scout",
        "player_ids": [str(other_player_id)],
        "current_map_position": {"v": 1, "map_level": "region", "node_type": "zone", "node_id": "forest_road", "label": "Лесная дорога"},
        "area_label": "Лесная дорога",
        "status": "idle",
        "movement_mode": "normal",
    }
    session_state._persist_group_states(sess, groups)

    route_state = session_state.record_group_route_traversal(
        sess,
        "main",
        "start_trakt->fortress_gate:move",
        summary="Группа проходит к воротам крепости.",
        traversed_at="2026-03-15T00:00:00+00:00",
    )
    node_state = session_state.record_group_node_visit(
        sess,
        "main",
        "fortress_gate",
        node_label="Ворота крепости",
        result_type="landmark_arrival",
        summary="Группа впервые достигает ворот крепости.",
        visited_at="2026-03-15T00:00:10+00:00",
    )

    assert route_state == {
        "route_id": "start_trakt->fortress_gate:move",
        "traversal_count": 1,
        "first_traversed_at": "2026-03-15T00:00:00+00:00",
        "last_traversed_at": "2026-03-15T00:00:00+00:00",
        "summary": "Группа проходит к воротам крепости.",
    }
    assert node_state == {
        "node_id": "fortress_gate",
        "node_label": "Ворота крепости",
        "visit_count": 1,
        "first_visited_at": "2026-03-15T00:00:10+00:00",
        "last_visited_at": "2026-03-15T00:00:10+00:00",
        "last_result_type": "landmark_arrival",
        "summary": "Группа впервые достигает ворот крепости.",
    }
    assert session_state.get_current_group_current_node_visit_state(sess, player_id=player_id) is None
    assert session_state.get_current_group_node_visit_states(sess, player_id=player_id) == [node_state]
    assert session_state.get_current_group_route_traversal_states(sess, player_id=player_id) == [route_state]
    assert session_state.get_current_group_node_visit_states(sess, group_id="scout") == []
    assert session_state.get_current_group_route_traversal_states(sess, group_id="scout") == []


def test_complete_group_travel_records_first_and_return_arrival_history() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )

    route = {
        "allowed": True,
        "route_id": "start_trakt->craft_town:move",
        "route_kind": "zone_move",
        "action_kind": "move",
        "target_label": "Озёрный городок",
        "target_node_id": "craft_town",
        "target_node": {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
            "zone_label": "Озёрный городок",
            "area_label": "Озёрный городок",
        },
        "next_map_position": {
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
            "area_label": "Озёрный городок",
        },
        "next_zone_label": "Озёрный городок",
        "source": "registry",
    }

    session_state.start_group_travel(sess, "main", route, source="test")
    first = session_state.complete_group_travel(sess, "main", player_id=player_id, source="test")

    groups = session_state._get_group_states(sess)
    groups["main"]["current_map_position"] = {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": "start_trakt",
        "label": "Стартовый тракт",
        "area_label": "Стартовый тракт",
    }
    groups["main"]["area_label"] = "Стартовый тракт"
    session_state._persist_group_states(sess, groups)
    session_state.start_group_travel(sess, "main", route, source="test")
    second = session_state.complete_group_travel(sess, "main", player_id=player_id, source="test")

    assert first is not None
    assert first["last_arrival_result"]["result_type"] == "settlement_arrival"
    assert first["last_arrival_result"]["first_visit"] is True
    assert first["last_arrival_result"]["visit_count"] == 1
    assert second is not None
    assert second["last_arrival_result"]["result_type"] == "return_arrival"
    assert second["last_arrival_result"]["first_visit"] is False
    assert second["last_arrival_result"]["visit_count"] == 2
    assert second["node_visit_states"]["craft_town"]["visit_count"] == 2
    assert second["route_traversal_states"]["start_trakt->craft_town:move"]["traversal_count"] == 2
    assert session_state.get_current_group_current_node_visit_state(sess, player_id=player_id)["node_id"] == "craft_town"
    context = session_state.get_current_group_node_context(sess, player_id=player_id)
    assert context["visit_count"] == 2
    assert context["current_node_visit_state"]["visit_count"] == 2


def test_failed_or_blocked_travel_does_not_create_false_arrival_history() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.set_group_route_access_state(
        sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Путь перекрыт.",
        block_reason="blocked_path",
        source="test",
    )

    updated, error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="craft_town",
        player_id=player_id,
        group_id="main",
        source="test",
    )

    assert updated is None
    assert error == "Маршрут к Озёрный городок сейчас заблокирован: blocked_path."
    assert session_state.get_current_group_last_arrival_result(sess, player_id=player_id) is None
    assert session_state.get_current_group_node_visit_states(sess, player_id=player_id) == []
    assert session_state.get_current_group_route_traversal_states(sess, player_id=player_id) == []


def test_build_group_node_entry_result_supports_authored_and_state_sensitive_overlays() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
    )

    first_entry = session_state.build_group_node_entry_result(
        current_map_position={"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
        node_visit_state={
            "node_id": "craft_town",
            "node_label": "Озёрный городок",
            "visit_count": 1,
            "first_visited_at": "2026-03-15T00:00:00+00:00",
            "last_visited_at": "2026-03-15T00:00:00+00:00",
            "last_result_type": "settlement_arrival",
            "summary": "Первое прибытие в городок.",
        },
        source="test",
    )
    return_entry = session_state.build_group_node_entry_result(
        current_map_position={"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
        node_visit_state={
            "node_id": "craft_town",
            "node_label": "Озёрный городок",
            "visit_count": 2,
            "first_visited_at": "2026-03-15T00:00:00+00:00",
            "last_visited_at": "2026-03-15T01:00:00+00:00",
            "last_result_type": "return_arrival",
            "summary": "Возвращение в городок.",
        },
        source="test",
    )
    landmark_entry = session_state.build_group_node_entry_result(
        current_map_position={"map_level": "landmark", "node_type": "landmark", "node_id": "fortress_gate", "label": "Ворота крепости"},
        node_visit_state={
            "node_id": "fortress_gate",
            "node_label": "Ворота крепости",
            "visit_count": 1,
            "first_visited_at": "2026-03-15T00:00:00+00:00",
            "last_visited_at": "2026-03-15T00:00:00+00:00",
            "last_result_type": "landmark_arrival",
            "summary": "Первый подход к воротам.",
        },
        source="test",
    )
    changed_entry = session_state.build_group_node_entry_result(
        current_map_position={"map_level": "region", "node_type": "zone", "node_id": "forest_road", "label": "Лесная дорога"},
        node_visit_state={
            "node_id": "forest_road",
            "node_label": "Лесная дорога",
            "visit_count": 2,
            "first_visited_at": "2026-03-15T00:00:00+00:00",
            "last_visited_at": "2026-03-15T02:00:00+00:00",
            "last_result_type": "return_arrival",
            "summary": "Возвращение на дорогу.",
        },
        node_state={
            "node_id": "forest_road",
            "state_flags": ["old_road_cleared"],
            "summary": "Проход был расчищен.",
            "source": "test",
            "updated_at": "2026-03-15T01:00:00+00:00",
        },
        source="test",
    )
    quiet_entry = session_state.build_group_node_entry_result(
        current_map_position={"map_level": "region", "node_type": "zone", "node_id": "road_hamlet", "label": "Дорожный хутор"},
        node_visit_state={
            "node_id": "road_hamlet",
            "node_label": "Дорожный хутор",
            "visit_count": 1,
            "first_visited_at": "2026-03-15T00:00:00+00:00",
            "last_visited_at": "2026-03-15T00:00:00+00:00",
            "last_result_type": "first_arrival",
            "summary": "Первое прибытие в хутор.",
        },
        source="test",
    )

    assert first_entry["result_type"] == "settlement_welcome"
    assert first_entry["title"] == "Озёрный городок принимает путников"
    assert first_entry["first_visit"] is True
    assert return_entry["result_type"] == "return_entry"
    assert return_entry["title"] == "Возвращение в Озёрный городок"
    assert return_entry["first_visit"] is False
    assert landmark_entry["result_type"] == "landmark_reached"
    assert landmark_entry["title"] == "Ворота крепости достигнуты"
    assert changed_entry["result_type"] == "changed_place"
    assert changed_entry["title"] == "Лесная дорога изменилась"
    assert changed_entry["node_state_flags"] == ["old_road_cleared"]
    assert quiet_entry["result_type"] == "quiet_entry"
    assert quiet_entry["title"] == "Дорожный хутор на пути"


def test_successful_arrival_creates_node_entry_and_failed_travel_does_not() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "craft_town", source="test")

    started, error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="craft_town",
        player_id=player_id,
        group_id="main",
        source="test",
    )

    assert started is not None
    assert error is None
    updated = session_state.complete_group_travel(sess, "main", player_id=player_id, source="test")
    assert updated is not None
    assert updated["last_arrival_result"]["node_id"] == "craft_town"
    assert updated["last_node_entry_result"]["node_id"] == "craft_town"
    assert updated["last_node_entry_result"]["result_type"] == "settlement_welcome"
    assert updated["node_entry_states"]["craft_town"]["entry_count"] == 1
    assert session_state.get_current_group_last_node_entry_result(sess, player_id=player_id)["result_type"] == "settlement_welcome"
    assert session_state.get_current_group_current_node_entry_state(sess, player_id=player_id)["entry_count"] == 1
    context = session_state.get_current_group_node_context(sess, player_id=player_id)
    assert context["current_entry_type"] == "settlement_welcome"
    assert context["current_entry_note"] == "Городок встречает группу как новый спокойный узел пути у воды."

    blocked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        blocked_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    session_state.grant_player_map_knowledge(blocked_sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(blocked_sess, player_id, "craft_town", source="test")
    session_state.set_group_route_access_state(
        blocked_sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Путь перекрыт.",
        block_reason="blocked_path",
        source="test",
    )

    blocked_updated, blocked_error = session_state.execute_group_navigation_option(
        blocked_sess,
        target_node_id="craft_town",
        player_id=player_id,
        group_id="main",
        source="test",
    )

    assert blocked_updated is None
    assert blocked_error == "Маршрут к Озёрный городок сейчас заблокирован: blocked_path."
    assert session_state.get_current_group_last_node_entry_result(blocked_sess, player_id=player_id) is None
    assert session_state.get_current_group_current_node_entry_state(blocked_sess, player_id=player_id) is None


def test_confirm_group_enter_creates_node_entry_result() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "ruined_settlement", "label": "Разрушенный посёлок"},
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

    confirmed = session_state.confirm_group_enter(sess, "main", player_id=player_id, source="test")

    assert confirmed is not None
    assert confirmed["last_arrival_result"]["node_id"] == "mine_entrance"
    assert confirmed["last_node_entry_result"]["node_id"] == "mine_entrance"
    assert confirmed["last_node_entry_result"]["result_type"] == "landmark_reached"
    assert session_state.get_current_group_node_entry_states(sess, player_id=player_id) == [
        confirmed["node_entry_states"]["mine_entrance"]
    ]


def test_build_group_destination_event_result_supports_authored_warning_changed_and_repeat_semantics() -> None:
    craft_first = session_state.build_group_destination_event_result(
        current_map_position={"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
        node_visit_state={
            "node_id": "craft_town",
            "node_label": "Озёрный городок",
            "visit_count": 1,
            "first_visited_at": "2026-03-15T00:00:00+00:00",
            "last_visited_at": "2026-03-15T00:00:00+00:00",
            "last_result_type": "settlement_arrival",
            "summary": "Первое прибытие в городок.",
        },
        source="test",
    )
    repeated = session_state.build_group_destination_event_result(
        current_map_position={"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
        node_visit_state={
            "node_id": "craft_town",
            "node_label": "Озёрный городок",
            "visit_count": 2,
            "first_visited_at": "2026-03-15T00:00:00+00:00",
            "last_visited_at": "2026-03-15T01:00:00+00:00",
            "last_result_type": "return_arrival",
            "summary": "Возвращение в городок.",
        },
        prior_destination_event_state={
            "event_id": "craft_town_arrival_notice",
            "node_id": "craft_town",
            "status": "completed",
            "result_type": "settlement_notice",
            "summary": "Первое прибытие уже было отмечено.",
            "source": "test",
            "updated_at": "2026-03-15T00:00:10+00:00",
        },
        source="test",
    )
    warning = session_state.build_group_destination_event_result(
        current_map_position={"map_level": "interior", "node_type": "interior_entry", "node_id": "mine_entrance", "label": "Шахтный вход"},
        node_visit_state={
            "node_id": "mine_entrance",
            "node_label": "Шахтный вход",
            "visit_count": 1,
            "first_visited_at": "2026-03-15T00:00:00+00:00",
            "last_visited_at": "2026-03-15T00:00:00+00:00",
            "last_result_type": "landmark_arrival",
            "summary": "Первое прибытие к шахте.",
        },
        source="test",
    )
    changed = session_state.build_group_destination_event_result(
        current_map_position={"map_level": "region", "node_type": "zone", "node_id": "ruined_settlement", "label": "Разрушенный посёлок"},
        node_visit_state={
            "node_id": "ruined_settlement",
            "node_label": "Разрушенный посёлок",
            "visit_count": 2,
            "first_visited_at": "2026-03-15T00:00:00+00:00",
            "last_visited_at": "2026-03-15T02:00:00+00:00",
            "last_result_type": "return_arrival",
            "summary": "Возвращение к руинам.",
        },
        node_state={
            "node_id": "ruined_settlement",
            "state_flags": ["mine_path_shored"],
            "summary": "У шахтного подхода есть свежие подпорки.",
            "source": "test",
            "updated_at": "2026-03-15T01:00:00+00:00",
        },
        source="test",
    )
    no_event = session_state.build_group_destination_event_result(
        current_map_position={"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
        node_visit_state={
            "node_id": "start_trakt",
            "node_label": "Стартовый тракт",
            "visit_count": 1,
            "first_visited_at": "2026-03-15T00:00:00+00:00",
            "last_visited_at": "2026-03-15T00:00:00+00:00",
            "last_result_type": "first_arrival",
            "summary": "Первое прибытие на тракт.",
        },
        source="test",
    )

    assert craft_first["result_type"] == "settlement_notice"
    assert craft_first["event_id"] == "craft_town_arrival_notice"
    assert repeated["result_type"] == "already_resolved"
    assert warning["result_type"] == "local_warning"
    assert changed["result_type"] == "changed_place_notice"
    assert no_event["result_type"] == "no_event"


def test_successful_arrival_creates_destination_event_and_integrates_with_helpers() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "craft_town", source="test")

    started, error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="craft_town",
        player_id=player_id,
        group_id="main",
        source="test",
    )

    assert started is not None
    assert error is None
    completed = session_state.complete_group_travel(sess, "main", player_id=player_id, source="test")

    assert completed is not None
    assert completed["last_arrival_result"]["node_id"] == "craft_town"
    assert completed["last_node_entry_result"]["node_id"] == "craft_town"
    assert completed["last_destination_event_result"]["event_id"] == "craft_town_arrival_notice"
    assert completed["last_destination_event_result"]["result_type"] == "settlement_notice"
    assert session_state.is_player_node_revealed(sess, player_id, "watchtower") is True
    assert session_state.get_group_node_state(sess, "main", "craft_town")["state_flags"] == ["craft_arrival_notice_taken"]
    intel_entries = session_state.get_current_group_map_intel(sess, player_id=player_id)
    assert intel_entries[-1]["source_kind"] == "destination_event"
    assert intel_entries[-1]["source_id"] == "craft_town_arrival_notice"
    assert session_state.get_current_group_last_destination_event_result(sess, player_id=player_id)["result_type"] == "settlement_notice"
    assert session_state.get_current_group_current_node_destination_event_state(sess, player_id=player_id)["event_id"] == "craft_town_arrival_notice"
    context = session_state.get_current_group_node_context(sess, player_id=player_id)
    assert context["current_destination_event_type"] == "settlement_notice"


def test_failed_or_blocked_travel_does_not_create_false_destination_event_result() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "craft_town", source="test")
    session_state.set_group_route_access_state(
        sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Путь перекрыт.",
        block_reason="blocked_path",
        source="test",
    )

    updated, error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="craft_town",
        player_id=player_id,
        group_id="main",
        source="test",
    )

    assert updated is None
    assert error == "Маршрут к Озёрный городок сейчас заблокирован: blocked_path."
    assert session_state.get_current_group_last_destination_event_result(sess, player_id=player_id) is None
    assert session_state.get_current_group_current_node_destination_event_state(sess, player_id=player_id) is None


def test_group_route_planning_builds_reachable_destinations_and_frontiers() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_road", "label": "Лесная дорога"},
    )
    session_state.grant_player_map_knowledge(sess, player_id, "road_hamlet", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "road_hamlet", source="test")
    session_state.grant_player_map_knowledge(sess, player_id, "mine_entrance", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "mine_entrance", source="test")
    session_state.set_group_route_access_state(
        sess,
        "main",
        "forest_road->mine_entrance:enter",
        access_state="blocked",
        summary="Вход в шахту завален.",
        block_reason="blocked_path",
        source="test",
    )

    reachable = session_state.get_group_reachable_destinations(sess, "main")
    frontiers = session_state.get_group_route_frontiers(sess, "main")
    planning = session_state.get_current_group_route_planning(sess, player_id=player_id)

    assert [item["target_node_id"] for item in reachable] == ["road_hamlet"]
    assert reachable[0]["path_node_ids"] == ["forest_road", "road_hamlet"]
    assert reachable[0]["path_route_ids"] == ["forest_road->road_hamlet:move"]
    assert reachable[0]["plan_status"] == "reachable"
    assert any(
        item["route_id"] == "forest_road->mine_entrance:enter" and item["frontier_type"] == "blocked_route"
        for item in frontiers
    )
    assert any(item["frontier_type"] == "unrevealed_branch" for item in frontiers)
    assert planning["reachable_destinations"] == reachable
    assert planning["route_frontiers"] == frontiers


def test_group_route_plan_to_node_returns_current_reachable_blocked_and_unrevealed() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_road", "label": "Лесная дорога"},
    )
    session_state.grant_player_map_knowledge(sess, player_id, "road_hamlet", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "road_hamlet", source="test")
    session_state.grant_player_map_knowledge(sess, player_id, "mine_entrance", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "mine_entrance", source="test")
    session_state.grant_player_map_knowledge(sess, player_id, "watchtower", knowledge_kind="known", source="test")
    session_state.set_group_route_access_state(
        sess,
        "main",
        "forest_road->mine_entrance:enter",
        access_state="blocked",
        summary="Вход в шахту завален.",
        block_reason="blocked_path",
        source="test",
    )

    current_plan = session_state.get_group_route_plan_to_node(sess, "main", "forest_road")
    reachable_plan = session_state.get_group_route_plan_to_node(sess, "main", "road_hamlet")
    blocked_plan = session_state.get_group_route_plan_to_node(sess, "main", "mine_entrance")
    unrevealed_plan = session_state.get_group_route_plan_to_node(sess, "main", "watchtower")
    unknown_plan = session_state.get_group_route_plan_to_node(sess, "main", "missing_node")

    assert current_plan is not None
    assert current_plan["plan_status"] == "current_location"
    assert current_plan["reachable"] is True
    assert reachable_plan is not None
    assert reachable_plan["plan_status"] == "reachable"
    assert reachable_plan["path_route_ids"] == ["forest_road->road_hamlet:move"]
    assert blocked_plan is not None
    assert blocked_plan["plan_status"] == "blocked"
    assert blocked_plan["blocked_route_id"] == "forest_road->mine_entrance:enter"
    assert blocked_plan["blocked_reason"] == "blocked_path"
    assert unrevealed_plan is not None
    assert unrevealed_plan["plan_status"] == "unrevealed"
    assert unrevealed_plan["target_known"] is True
    assert unrevealed_plan["target_revealed"] is False
    assert unknown_plan is not None
    assert unknown_plan["plan_status"] == "unknown"


def test_group_journey_target_set_advance_and_clear_are_canonical() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    for node_id in ("craft_town", "fortress_gate"):
        session_state.grant_player_map_knowledge(sess, player_id, node_id, knowledge_kind="known", source="test")
        session_state.reveal_player_map_node(sess, player_id, node_id, source="test")

    planned, planned_error = session_state.set_group_journey_target(
        sess,
        "main",
        "fortress_gate",
        player_id=player_id,
        source="test",
    )

    assert planned_error is None
    assert planned is not None
    assert planned["active_journey"]["journey_status"] == "planned"
    assert planned["active_journey"]["target_node_id"] == "fortress_gate"
    assert planned["active_journey"]["next_route_id"] == "start_trakt->fortress_gate:move"
    assert planned["last_journey_result"]["result_type"] == "journey_planned"

    advanced, advanced_error = session_state.advance_group_journey(
        sess,
        "main",
        player_id=player_id,
        source="test",
    )

    assert advanced_error is None
    assert advanced is not None
    assert advanced["current_map_position"]["node_id"] == "fortress_gate"
    assert advanced["active_journey"]["journey_status"] == "arrived"
    assert advanced["last_journey_result"]["result_type"] == "journey_arrived"
    assert advanced["last_arrival_result"]["node_id"] == "fortress_gate"
    assert advanced["node_visit_states"]["fortress_gate"]["visit_count"] == 1
    assert advanced["route_traversal_states"]["start_trakt->fortress_gate:move"]["traversal_count"] == 1
    assert session_state.get_current_group_journey_state(sess, player_id=player_id)["journey_status"] == "arrived"
    assert session_state.get_current_group_last_journey_result(sess, player_id=player_id)["result_type"] == "journey_arrived"

    cleared = session_state.clear_group_journey(sess, "main", source="test")

    assert cleared is not None
    assert "active_journey" not in cleared
    assert cleared["last_journey_result"]["result_type"] == "journey_cleared"


def test_group_journey_rejects_current_location_and_unrevealed_targets_and_blocks_mid_journey() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    same_place, same_place_error = session_state.set_group_journey_target(
        sess,
        "main",
        "start_trakt",
        player_id=player_id,
        source="test",
    )
    session_state.grant_player_map_knowledge(sess, player_id, "watchtower", knowledge_kind="known", source="test")
    unrevealed, unrevealed_error = session_state.set_group_journey_target(
        sess,
        "main",
        "watchtower",
        player_id=player_id,
        source="test",
    )

    assert same_place is not None
    assert same_place_error == "Группа уже находится в точке Стартовый тракт."
    assert "active_journey" not in same_place
    assert unrevealed is not None
    assert unrevealed_error == "Точка Сторожевая башня ещё не раскрыта для текущей группы."
    assert "active_journey" not in unrevealed

    for node_id in ("craft_town", "fortress_gate"):
        session_state.grant_player_map_knowledge(sess, player_id, node_id, knowledge_kind="known", source="test")
        session_state.reveal_player_map_node(sess, player_id, node_id, source="test")
    planned, planned_error = session_state.set_group_journey_target(
        sess,
        "main",
        "craft_town",
        player_id=player_id,
        source="test",
    )
    assert planned_error is None
    assert planned is not None

    session_state.set_group_route_access_state(
        sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Путь перекрыт.",
        block_reason="blocked_path",
        source="test",
    )
    session_state.set_group_route_access_state(
        sess,
        "main",
        "fortress_gate->craft_town:move",
        access_state="blocked",
        summary="Обход к городку тоже закрыт.",
        block_reason="fortress_lockdown",
        source="test",
    )

    blocked, blocked_error = session_state.advance_group_journey(
        sess,
        "main",
        player_id=player_id,
        source="test",
    )

    assert blocked is not None
    assert blocked_error == "Путь к Озёрный городок упирается в заблокированный маршрут."
    assert blocked["active_journey"]["journey_status"] == "blocked"
    assert blocked["last_journey_result"]["result_type"] == "journey_blocked"
    assert session_state.get_current_group_last_arrival_result(sess, player_id=player_id) is None
    assert session_state.get_current_group_route_traversal_states(sess, player_id=player_id) == []


def test_group_exploration_leads_reflect_active_journey_and_primary_preference() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    for node_id in ("fortress_gate",):
        session_state.grant_player_map_knowledge(sess, player_id, node_id, knowledge_kind="known", source="test")
        session_state.reveal_player_map_node(sess, player_id, node_id, source="test")
    session_state.set_group_journey_target(sess, "main", "fortress_gate", player_id=player_id, source="test")

    leads = session_state.get_current_group_exploration_leads(sess, player_id=player_id)
    primary = session_state.get_current_group_primary_exploration_lead(sess, player_id=player_id)

    assert leads
    assert leads[0]["lead_type"] == "active_journey"
    assert leads[0]["priority_band"] == "high"
    assert leads[0]["suggested_command"] == "group continue"
    assert primary == leads[0]

    session_state.advance_group_journey(sess, "main", player_id=player_id, source="test")
    arrived_primary = session_state.get_current_group_primary_exploration_lead(sess, player_id=player_id)
    assert arrived_primary is not None
    assert arrived_primary["lead_type"] == "active_journey"
    assert arrived_primary["suggested_command"] == "group stop"


def test_group_node_progress_summary_supports_new_active_partial_changed_resolved_and_quiet_states() -> None:
    player_id = uuid.uuid4()

    quiet_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        quiet_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    quiet_progress = session_state.get_current_group_current_node_progress(quiet_sess, player_id=player_id)
    assert quiet_progress is not None
    assert quiet_progress["progression_status"] == "quiet_location"

    active_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        active_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
    )
    session_state.record_group_node_visit(
        active_sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="first_arrival",
        summary="Первый визит.",
    )
    active_progress = session_state.get_current_group_current_node_progress(active_sess, player_id=player_id)
    assert active_progress is not None
    assert active_progress["progression_status"] == "locally_active"
    assert active_progress["available_service_count"] >= 1

    new_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        new_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
    )
    session_state.record_group_node_visit(
        new_sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="first_arrival",
        summary="Первый визит.",
    )
    session_state.resolve_group_node_entry(new_sess, "main", source="test")
    session_state.resolve_group_destination_event(new_sess, "main", source="test")
    new_progress = session_state.get_current_group_current_node_progress(new_sess, player_id=player_id)
    assert new_progress is not None
    assert new_progress["progression_status"] == "newly_arrived"

    partial_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        partial_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
    )
    session_state.record_group_node_visit(
        partial_sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="first_arrival",
        summary="Первый визит.",
    )
    session_state.record_group_node_visit(
        partial_sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="return_arrival",
        summary="Повторный визит.",
    )
    session_state.execute_current_group_service(
        partial_sess,
        player_id=player_id,
        service_id="craft_town:resupply",
        source="test",
    )
    partial_progress = session_state.get_current_group_current_node_progress(partial_sess, player_id=player_id)
    assert partial_progress is not None
    assert partial_progress["progression_status"] == "partially_resolved"
    assert partial_progress["completed_service_count"] >= 1
    assert partial_progress["available_service_count"] >= 1

    resolved_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        resolved_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_road", "label": "Лесная дорога"},
    )
    session_state.record_group_node_visit(
        resolved_sess,
        "main",
        "forest_road",
        node_label="Лесная дорога",
        result_type="landmark_arrival",
        summary="Первый визит.",
    )
    session_state.resolve_group_context_action(
        resolved_sess,
        "main",
        action_id="clear_old_road",
        player_id=player_id,
        source="test",
    )
    resolved_progress = session_state.get_current_group_current_node_progress(resolved_sess, player_id=player_id)
    assert resolved_progress is not None
    assert resolved_progress["progression_status"] == "locally_resolved"

    changed_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        changed_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "ruined_settlement", "label": "Разрушенный посёлок"},
    )
    session_state.record_group_node_visit(
        changed_sess,
        "main",
        "ruined_settlement",
        node_label="Разрушенный посёлок",
        result_type="first_arrival",
        summary="Первый визит.",
    )
    session_state.record_group_node_visit(
        changed_sess,
        "main",
        "ruined_settlement",
        node_label="Разрушенный посёлок",
        result_type="return_arrival",
        summary="Повторный визит.",
    )
    session_state.add_group_node_state_flag(
        changed_sess,
        "main",
        "ruined_settlement",
        state_flag="mine_path_shored",
        summary="Место выглядит иначе после укрепления подступа.",
        source="test",
    )
    session_state.resolve_group_destination_event(changed_sess, "main", source="test")
    changed_progress = session_state.get_current_group_current_node_progress(changed_sess, player_id=player_id)
    assert changed_progress is not None
    assert changed_progress["progression_status"] == "revisit_changed"


def test_current_group_node_context_and_exploration_leads_reflect_node_progress() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="first_arrival",
        summary="Первый визит.",
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="return_arrival",
        summary="Повторный визит.",
    )
    session_state.execute_current_group_service(
        sess,
        player_id=player_id,
        service_id="craft_town:resupply",
        source="test",
    )

    context = session_state.get_current_group_node_context(sess, player_id=player_id)
    leads = session_state.get_current_group_exploration_leads(sess, player_id=player_id)

    assert context is not None
    assert context["current_node_progression_status"] == "partially_resolved"
    assert "локальных возможностей" in context["current_node_progression_summary"]
    assert any(lead["lead_type"] == "local_opportunity" for lead in leads)

    quiet_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        quiet_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    quiet_leads = session_state.get_current_group_exploration_leads(quiet_sess, player_id=player_id)
    assert all(lead["lead_type"] != "local_opportunity" for lead in quiet_leads)


def test_group_exploration_leads_synthesize_intel_reachable_and_blocked_frontiers_without_duplicates() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    for node_id in ("fortress_gate", "craft_town"):
        session_state.grant_player_map_knowledge(sess, player_id, node_id, knowledge_kind="known", source="test")
        session_state.reveal_player_map_node(sess, player_id, node_id, source="test")
    session_state.set_group_route_access_state(
        sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Путь перекрыт.",
        block_reason="blocked_path",
        source="test",
    )
    first_entry = session_state.add_group_map_intel_entry(
        sess,
        "main",
        session_state.build_group_map_intel_entry(
            entry_type="route_hint",
            title="Зацепка к крепости",
            summary="На тракте найден знак к воротам крепости.",
            result_summary="Старый указатель явно ведёт к воротам крепости.",
            source_kind="travel_event",
            source_id="hint-1",
            node_id="start_trakt",
            node_label="Стартовый тракт",
            related_node_ids=["fortress_gate"],
            related_route_ids=["start_trakt->fortress_gate:move"],
            tags=["fortress", "hint"],
            dedupe_key="hint|fortress_gate",
            discovered_at="2026-03-15T00:00:00+00:00",
        ),
    )
    duplicate_entry = session_state.add_group_map_intel_entry(
        sess,
        "main",
        session_state.build_group_map_intel_entry(
            entry_type="route_hint",
            title="Дублирующая зацепка к крепости",
            summary="Повторный знак к тем же воротам.",
            result_summary="Та же дорога снова указывает к воротам крепости.",
            source_kind="travel_event",
            source_id="hint-2",
            node_id="start_trakt",
            node_label="Стартовый тракт",
            related_node_ids=["fortress_gate"],
            related_route_ids=["start_trakt->fortress_gate:move"],
            tags=["fortress", "hint"],
            dedupe_key="hint|fortress_gate",
            discovered_at="2026-03-15T00:05:00+00:00",
        ),
    )

    leads = session_state.get_group_exploration_leads(sess, "main")

    assert first_entry == duplicate_entry
    assert sum(1 for lead in leads if lead["lead_type"] == "intel_target" and lead["target_node_id"] == "fortress_gate") == 1
    assert any(lead["lead_type"] == "unvisited_reachable" and lead["target_node_id"] == "fortress_gate" for lead in leads)
    blocked_frontier = next(lead for lead in leads if lead["lead_type"] == "blocked_frontier")
    assert blocked_frontier["target_node_id"] == "craft_town"
    assert blocked_frontier["blocked_reason"] == "blocked_path"


def test_group_exploration_leads_include_local_opportunities_only_when_available() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
    )

    leads_before = session_state.get_group_exploration_leads(sess, "main")
    local_lead = next((lead for lead in leads_before if lead["lead_type"] == "local_opportunity"), None)
    assert local_lead is not None
    assert local_lead["source_kind"] in {"service", "context_action"}
    assert local_lead["suggested_command"] in {"group service craft_town:safe_rest", "group service craft_town:resupply", "group service craft_town_local_guidance", "group action clear_old_road"}

    session_state.resolve_group_service(sess, "main", service_id="craft_town_local_guidance", player_id=player_id, source="test")
    leads_after = session_state.get_group_exploration_leads(sess, "main")
    assert not any(
        lead["lead_type"] == "local_opportunity"
        and lead["source_kind"] == "service"
        and lead["source_ref"] == "craft_town_local_guidance"
        for lead in leads_after
    )


def test_group_region_exploration_summary_supports_quiet_active_expanding_blocked_and_saturated_states() -> None:
    player_id = uuid.uuid4()

    quiet_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        quiet_sess,
        [player_id],
        {"map_level": "region", "node_type": "landmark", "node_id": "mine_entrance", "label": "Шахтный вход"},
    )
    quiet_summary = session_state.get_current_group_region_exploration_summary(quiet_sess, player_id=player_id)
    assert quiet_summary is not None
    assert quiet_summary["progression_status"] == "region_quiet"

    frontier_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        frontier_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    active_summary = session_state.get_current_group_region_exploration_summary(frontier_sess, player_id=player_id)
    assert active_summary is not None
    assert active_summary["progression_status"] == "newly_opened_region"

    session_state.grant_player_map_knowledge(frontier_sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(frontier_sess, player_id, "craft_town", source="test")
    expanding_summary = session_state.get_current_group_region_exploration_summary(frontier_sess, player_id=player_id)
    assert expanding_summary is not None
    assert expanding_summary["progression_status"] == "expanding_routes"

    session_state.set_group_route_access_state(
        frontier_sess,
        "main",
        "start_trakt->fortress_gate:move",
        access_state="blocked",
        summary="Подход к воротам перекрыт.",
        block_reason="blocked_path",
        source="test",
    )
    session_state.set_group_route_access_state(
        frontier_sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Дорога к городку перекрыта.",
        block_reason="washout",
        source="test",
    )
    blocked_summary = session_state.get_current_group_region_exploration_summary(frontier_sess, player_id=player_id)
    assert blocked_summary is not None
    assert blocked_summary["progression_status"] == "blocked_progress"

    saturated_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        saturated_sess,
        [player_id],
        {"map_level": "region", "node_type": "landmark", "node_id": "mine_entrance", "label": "Шахтный вход"},
    )
    session_state.record_group_node_visit(
        saturated_sess,
        "main",
        "mine_entrance",
        node_label="Шахтный вход",
        result_type="landmark_arrival",
        summary="Первый визит.",
    )
    saturated_summary = session_state.get_current_group_region_exploration_summary(saturated_sess, player_id=player_id)
    assert saturated_summary is not None
    assert saturated_summary["progression_status"] == "locally_saturated"


def test_group_region_frontier_summary_counts_reachable_blocked_and_unresolved_nodes() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"},
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="first_arrival",
        summary="Первый визит.",
    )
    session_state.execute_current_group_service(
        sess,
        player_id=player_id,
        service_id="craft_town:resupply",
        source="test",
    )
    session_state.grant_player_map_knowledge(sess, player_id, "fortress_gate", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "fortress_gate", source="test")
    session_state.set_group_route_access_state(
        sess,
        "main",
        "craft_town->fortress_gate:move",
        access_state="blocked",
        summary="Путь перекрыт.",
        block_reason="blocked_path",
        source="test",
    )

    frontier = session_state.get_current_group_region_frontier_summary(sess, player_id=player_id)

    assert frontier is not None
    assert frontier["blocked_frontiers"]
    assert frontier["reachable_unvisited_nodes"] == []
    assert frontier["unresolved_local_nodes"]
    assert frontier["unresolved_local_nodes"][0]["node_id"] == "craft_town"


def test_group_region_gateways_support_unavailable_locked_open_blocked_and_future_stub_states() -> None:
    player_id = uuid.uuid4()

    hidden_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        hidden_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    assert session_state.get_current_group_region_gateways(hidden_sess, player_id=player_id) == []
    assert session_state.get_current_group_primary_region_gateway(hidden_sess, player_id=player_id) is None

    fortress_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        fortress_sess,
        [player_id],
        {"map_level": "region", "node_type": "landmark", "node_id": "fortress_gate", "label": "Ворота крепости"},
    )
    locked_gateway = session_state.get_current_group_region_gateways(fortress_sess, player_id=player_id)
    assert len(locked_gateway) == 1
    assert locked_gateway[0]["gateway_status"] == "locked"
    assert locked_gateway[0]["gateway_id"] == "fortress_gate_western_road"

    session_state.record_group_node_visit(
        fortress_sess,
        "main",
        "fortress_gate",
        node_label="Ворота крепости",
        result_type="landmark_arrival",
        summary="Первый визит.",
    )
    session_state.resolve_group_destination_event(fortress_sess, "main", source="test")
    open_gateway = session_state.get_current_group_region_gateways(fortress_sess, player_id=player_id)
    assert open_gateway[0]["gateway_status"] == "open"
    assert session_state.get_current_group_primary_region_gateway(fortress_sess, player_id=player_id)["gateway_id"] == "fortress_gate_western_road"

    session_state.set_group_route_access_state(
        fortress_sess,
        "main",
        "start_trakt->fortress_gate:move",
        access_state="blocked",
        summary="Подход к воротам перекрыт.",
        block_reason="gate_blocked",
        source="test",
    )
    blocked_gateway = session_state.get_current_group_region_gateways(fortress_sess, player_id=player_id)
    assert blocked_gateway[0]["gateway_status"] == "blocked"
    assert blocked_gateway[0]["blocked_reason"] == "gate_blocked"

    shrine_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        shrine_sess,
        [player_id],
        {"map_level": "region", "node_type": "landmark", "node_id": "forgotten_shrine", "label": "Забытое святилище"},
    )
    future_gateway = session_state.get_current_group_region_gateways(shrine_sess, player_id=player_id)
    assert len(future_gateway) == 1
    assert future_gateway[0]["gateway_status"] == "future_stub"
    assert future_gateway[0]["future_stub"] is True


def test_group_region_gateways_honor_node_state_and_visit_requirements() -> None:
    player_id = uuid.uuid4()

    forest_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        forest_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    locked_forest_gateway = session_state.get_current_group_region_gateways(forest_sess, player_id=player_id)
    assert len(locked_forest_gateway) == 1
    assert locked_forest_gateway[0]["gateway_status"] == "locked"
    session_state.add_group_node_state_flag(
        forest_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    open_forest_gateway = session_state.get_current_group_region_gateways(forest_sess, player_id=player_id)
    assert open_forest_gateway[0]["gateway_status"] == "open"
    assert open_forest_gateway[0]["gateway_id"] == "forest_settlement_northwatch"

    marsh_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        marsh_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "marsh_edge", "label": "Край болот"},
    )
    locked_marsh_gateway = session_state.get_current_group_region_gateways(marsh_sess, player_id=player_id)
    assert len(locked_marsh_gateway) == 1
    assert locked_marsh_gateway[0]["gateway_status"] == "locked"
    session_state.record_group_node_visit(
        marsh_sess,
        "main",
        "marsh_edge",
        node_label="Край болот",
        result_type="first_arrival",
        summary="Первый визит.",
    )
    still_locked_gateway = session_state.get_current_group_region_gateways(marsh_sess, player_id=player_id)
    assert still_locked_gateway[0]["gateway_status"] == "locked"
    session_state.record_group_node_visit(
        marsh_sess,
        "main",
        "marsh_edge",
        node_label="Край болот",
        result_type="return_arrival",
        summary="Повторный визит.",
    )
    open_marsh_gateway = session_state.get_current_group_region_gateways(marsh_sess, player_id=player_id)
    assert open_marsh_gateway[0]["gateway_status"] == "open"
    assert open_marsh_gateway[0]["gateway_id"] == "marsh_edge_deep_marsh"


def test_group_region_transition_completes_and_reuses_arrival_pipeline() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )

    updated, error = session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert updated is not None
    assert updated["current_map_position"]["node_id"] == "northwatch_outpost"
    assert updated["last_region_transition_result"]["result_type"] == "region_transition_completed"
    assert updated["last_region_transition_result"]["transition_status"] == "completed"
    assert session_state.get_current_group_last_arrival_result(sess, player_id=player_id)["node_id"] == "northwatch_outpost"
    assert session_state.get_current_group_last_node_entry_result(sess, player_id=player_id)["node_id"] == "northwatch_outpost"
    assert session_state.get_current_group_current_node_visit_state(sess, player_id=player_id)["node_id"] == "northwatch_outpost"
    assert session_state.get_current_group_region_transition_state(sess, player_id=player_id)["last_gateway_id"] == "forest_settlement_northwatch"


def test_group_region_transition_handles_invalid_blocked_locked_and_future_stub_without_fake_move() -> None:
    player_id = uuid.uuid4()

    invalid_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        invalid_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    invalid_before = session_state.get_current_group_current_node_visit_state(invalid_sess, player_id=player_id)
    invalid_updated, invalid_error = session_state.resolve_group_region_transition(
        invalid_sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="test",
    )
    assert invalid_error is not None
    assert invalid_updated is not None
    assert invalid_updated["current_map_position"]["node_id"] == "start_trakt"
    assert invalid_updated["last_region_transition_result"]["result_type"] == "region_transition_invalid"
    assert session_state.get_current_group_current_node_visit_state(invalid_sess, player_id=player_id) == invalid_before

    blocked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        blocked_sess,
        [player_id],
        {"map_level": "region", "node_type": "landmark", "node_id": "fortress_gate", "label": "Ворота крепости"},
    )
    session_state.record_group_node_visit(
        blocked_sess,
        "main",
        "fortress_gate",
        node_label="Ворота крепости",
        result_type="landmark_arrival",
        summary="Первый визит.",
    )
    session_state.resolve_group_destination_event(blocked_sess, "main", source="test")
    session_state.set_group_route_access_state(
        blocked_sess,
        "main",
        "start_trakt->fortress_gate:move",
        access_state="blocked",
        summary="Подход перекрыт.",
        block_reason="gate_blocked",
        source="test",
    )
    blocked_updated, blocked_error = session_state.resolve_group_region_transition(
        blocked_sess,
        "main",
        "fortress_gate_western_road",
        player_id=player_id,
        source="test",
    )
    assert blocked_error == "Выход сейчас заблокирован."
    assert blocked_updated["current_map_position"]["node_id"] == "fortress_gate"
    assert blocked_updated["last_region_transition_result"]["result_type"] == "region_transition_blocked"

    locked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        locked_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    locked_updated, locked_error = session_state.resolve_group_region_transition(
        locked_sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="test",
    )
    assert locked_error == "Выход пока закрыт условиями этого узла."
    assert locked_updated["last_region_transition_result"]["result_type"] == "region_transition_locked"
    assert session_state.get_current_group_last_arrival_result(locked_sess, player_id=player_id) is None

    future_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        future_sess,
        [player_id],
        {"map_level": "region", "node_type": "landmark", "node_id": "forgotten_shrine", "label": "Забытое святилище"},
    )
    future_updated, future_error = session_state.resolve_group_region_transition(
        future_sess,
        "main",
        "forgotten_shrine_sunken_reaches",
        player_id=player_id,
        source="test",
    )
    assert future_error == "Этот выход пока существует только как future stub."
    assert future_updated["last_region_transition_result"]["result_type"] == "region_transition_future_stub"
    assert future_updated["current_map_position"]["node_id"] == "forgotten_shrine"


def test_group_region_residency_tracks_current_region_and_same_region_refresh_without_fake_discovery() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )

    current_region = session_state.get_current_group_current_region_state(sess, player_id=player_id)
    assert current_region == {
        "region_id": "starter_frontier",
        "region_label": "Стартовое пограничье",
        "current_node_id": "start_trakt",
        "visit_count": 1,
        "source": "region_residency",
        "entered_at": current_region["entered_at"],
    }
    first_entry = session_state.get_current_group_last_region_entry_result(sess, player_id=player_id)
    assert first_entry["result_type"] == "first_region_entry"
    assert first_entry["region_id"] == "starter_frontier"
    assert first_entry["anchor_node_id"] == "start_trakt"
    assert first_entry["visit_count"] == 1

    group_states = session_state._get_group_states(sess)
    group = group_states["main"]
    group["current_map_position"] = session_state._normalize_map_position(
        {"map_level": "region", "node_type": "zone", "node_id": "craft_town", "label": "Озёрный городок"}
    )
    group["area_label"] = "Озёрный городок"
    session_state._persist_group_states(sess, group_states)

    refreshed_region = session_state.get_current_group_current_region_state(sess, player_id=player_id)
    assert refreshed_region["region_id"] == "starter_frontier"
    assert refreshed_region["current_node_id"] == "craft_town"
    assert refreshed_region["visit_count"] == 1

    discovered_regions = session_state.get_current_group_discovered_regions(sess, player_id=player_id)
    assert discovered_regions == [
        {
            "region_id": "starter_frontier",
            "region_label": "Стартовое пограничье",
            "visit_count": 1,
            "first_entered_at": discovered_regions[0]["first_entered_at"],
            "last_entered_at": discovered_regions[0]["last_entered_at"],
            "first_anchor_node_id": "start_trakt",
            "last_anchor_node_id": "craft_town",
            "summary": "Группа впервые входит в регион Стартовое пограничье.",
        }
    ]
    assert session_state.get_current_group_last_region_entry_result(sess, player_id=player_id)["result_type"] == "first_region_entry"


def test_group_region_onboarding_applies_anchor_reveal_and_repeat_is_idempotent() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )

    current_region = session_state.get_current_group_current_region_state(sess, player_id=player_id)
    onboarding = session_state.get_current_group_last_region_onboarding_result(sess, player_id=player_id)

    assert current_region["region_id"] == "starter_frontier"
    assert onboarding["result_type"] == "anchor_reveal_applied"
    assert onboarding["region_id"] == "starter_frontier"
    assert onboarding["anchor_node_id"] == "start_trakt"
    assert onboarding["revealed_node_ids"] == ["craft_town", "fortress_gate"]
    assert onboarding["revealed_route_ids"] == ["start_trakt->craft_town:move", "start_trakt->fortress_gate:move"]
    assert onboarding["onboarding_applied"] is True
    assert set(session_state.get_player_revealed_node_ids(sess, player_id)) >= {"start_trakt", "craft_town", "fortress_gate"}

    map_intel = session_state.get_current_group_map_intel(sess, player_id=player_id)
    assert any(entry["source_kind"] == "region_onboarding" and entry["source_id"] == "starter_frontier" for entry in map_intel)

    repeated = session_state.resolve_group_region_onboarding(
        sess,
        "main",
        current_region_state=current_region,
        source="test",
    )
    assert repeated["result_type"] == "repeat_region_onboarding"
    assert repeated["revealed_node_ids"] == ["craft_town", "fortress_gate"]
    assert repeated["onboarding_applied"] is False
    assert len(session_state.get_current_group_region_onboarding_states(sess, player_id=player_id)) == 1


def test_group_region_onboarding_supports_quiet_and_unavailable_results() -> None:
    player_id = uuid.uuid4()
    quiet_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        quiet_sess,
        [player_id],
        {"map_level": "region", "node_type": "watch", "node_id": "western_road_watch", "label": "Западный дозор"},
    )

    current_region = session_state.resolve_group_region_residency(quiet_sess, "main", source="test", persist_result=True)
    quiet_result = session_state.get_current_group_last_region_onboarding_result(quiet_sess, player_id=player_id)
    assert current_region["region_id"] == "western_road"
    assert quiet_result["result_type"] == "quiet_region_onboarding"
    assert quiet_result["revealed_node_ids"] == []
    assert quiet_result["revealed_route_ids"] == []

    unavailable_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(unavailable_sess, [player_id], "Таверна")
    unavailable = session_state.resolve_group_region_onboarding(unavailable_sess, "main", source="test")
    assert unavailable["result_type"] == "region_onboarding_unavailable"
    assert unavailable["region_id"] == "unknown_region"


def test_group_region_transition_triggers_region_onboarding_without_fake_reapply_on_same_region_refresh() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )

    updated, error = session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="region_transition",
    )

    assert error is None
    assert updated is not None
    onboarding = session_state.get_current_group_last_region_onboarding_result(sess, player_id=player_id)
    assert onboarding["region_id"] == "northwatch_frontier"
    assert onboarding["result_type"] == "anchor_reveal_applied"
    assert onboarding["anchor_node_id"] == "northwatch_outpost"
    assert onboarding["revealed_route_ids"] == ["forest_settlement->old_fortress_edge:move"]
    assert any(entry["region_id"] == "northwatch_frontier" for entry in session_state.get_current_group_region_onboarding_states(sess, player_id=player_id))

    group_states = session_state._get_group_states(sess)
    group = group_states["main"]
    group["current_map_position"] = session_state._normalize_map_position(
        {"map_level": "region", "node_type": "landmark", "node_id": "old_fortress_edge", "label": "Край старой крепости"}
    )
    group["area_label"] = "Край старой крепости"
    session_state._persist_group_states(sess, group_states)

    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    repeated = session_state.resolve_group_region_onboarding(sess, "main", source="test")
    assert repeated["result_type"] == "repeat_region_onboarding"
    assert len(session_state.get_current_group_region_onboarding_states(sess, player_id=player_id)) == 2


def test_group_discovered_region_summaries_support_current_blocked_region() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    group_states = session_state._get_group_states(sess)
    group = group_states["main"]
    group["current_region_state"]["visit_count"] = 2
    group["discovered_regions"]["starter_frontier"]["visit_count"] = 2
    session_state._persist_group_states(sess, group_states)
    session_state.set_group_route_access_state(
        sess,
        "main",
        route_id="start_trakt->craft_town:move",
        access_state="blocked",
        summary="Выход к городку перекрыт.",
        block_reason="Завал на тракте.",
        source="test",
    )
    session_state.set_group_route_access_state(
        sess,
        "main",
        route_id="start_trakt->fortress_gate:move",
        access_state="blocked",
        summary="К крепости не пройти.",
        block_reason="Подъезд к крепости перекрыт.",
        source="test",
    )

    summaries = session_state.get_current_group_discovered_region_summaries(sess, player_id=player_id)

    assert summaries[0]["region_id"] == "starter_frontier"
    assert summaries[0]["region_status"] == "current_blocked_region"
    assert summaries[0]["blocked_frontier_count"] >= 1
    focus = session_state.get_current_group_primary_region_focus(sess, player_id=player_id)
    assert focus["region_status"] == "current_blocked_region"


def test_group_region_world_overview_synthesizes_current_and_non_current_discovered_regions() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    updated, error = session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="region_transition",
    )
    assert error is None
    assert updated is not None
    session_state.set_group_route_access_state(
        sess,
        "main",
        route_id="forest_settlement->old_fortress_edge:move",
        access_state="blocked",
        summary="Дальний путь к северному рубежу снова затянут туманом.",
        block_reason="Опасный проход снова перекрыт.",
        source="test",
    )

    summaries = session_state.get_current_group_discovered_region_summaries(sess, player_id=player_id)
    overview = session_state.get_current_group_region_world_overview(sess, player_id=player_id)
    focus = session_state.get_current_group_primary_region_focus(sess, player_id=player_id)

    assert [item["region_id"] for item in summaries] == ["northwatch_frontier", "starter_frontier"]
    assert summaries[0]["region_status"] == "newly_onboarded_region"
    assert summaries[1]["region_status"] == "blocked_region"
    assert overview["discovered_region_count"] == 2
    assert overview["active_region_count"] == 1
    assert overview["blocked_region_count"] == 1
    assert overview["primary_region_focus"]["region_id"] == "northwatch_frontier"
    assert focus["region_id"] == "northwatch_frontier"


def test_group_region_target_plan_supports_current_ready_and_approach_states() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    current_region = session_state.get_current_group_region_target_plan(
        sess,
        player_id=player_id,
        target_region_id="starter_frontier",
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    assert current_region is not None
    assert current_region["plan_status"] == "current_region"
    assert current_region["reachable"] is True

    session_state.reveal_player_map_node(sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    approach = session_state.get_current_group_region_target_plan(
        sess,
        player_id=player_id,
        target_region_id="northwatch_frontier",
    )
    assert approach is not None
    assert approach["plan_status"] == "approach_gateway"
    assert approach["gateway_id"] == "forest_settlement_northwatch"
    assert approach["reachable"] is True
    assert approach["path_node_ids"] == ["forest_road", "forest_settlement"]
    assert approach["suggested_command"] == "group go forest_settlement"

    ready_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        ready_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.get_current_group_current_region_state(ready_sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        ready_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    ready = session_state.get_current_group_region_target_plan(
        ready_sess,
        player_id=player_id,
        target_region_id="northwatch_frontier",
    )
    assert ready is not None
    assert ready["plan_status"] == "gateway_ready"
    assert ready["suggested_command"] == "group exit forest_settlement_northwatch"

def test_group_region_target_plan_supports_blocked_locked_future_and_undiscovered_states() -> None:
    player_id = uuid.uuid4()

    blocked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        blocked_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.get_current_group_current_region_state(blocked_sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        blocked_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.set_group_route_access_state(
        blocked_sess,
        "main",
        route_id="forest_settlement->old_fortress_edge:move",
        access_state="blocked",
        summary="Проход к северному рубежу закрыт.",
        block_reason="Завал на дальнем тракте.",
        source="test",
    )
    blocked = session_state.get_current_group_region_target_plan(
        blocked_sess,
        player_id=player_id,
        target_region_id="northwatch_frontier",
    )
    assert blocked is not None
    assert blocked["plan_status"] == "gateway_blocked"
    assert blocked["blocked_reason"] == "Завал на дальнем тракте."

    locked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        locked_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "landmark",
            "node_id": "fortress_gate",
            "label": "Ворота крепости",
        },
    )
    session_state.get_current_group_current_region_state(locked_sess, player_id=player_id)
    locked = session_state.get_current_group_region_target_plan(
        locked_sess,
        player_id=player_id,
        target_region_id="western_road",
    )
    assert locked is not None
    assert locked["plan_status"] == "gateway_locked"

    future_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        future_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "landmark",
            "node_id": "forgotten_shrine",
            "label": "Забытое святилище",
        },
    )
    session_state.get_current_group_current_region_state(future_sess, player_id=player_id)
    future = session_state.get_current_group_region_target_plan(
        future_sess,
        player_id=player_id,
        target_region_id="sunken_reaches",
    )
    assert future is not None
    assert future["plan_status"] == "gateway_future_stub"

    undiscovered = session_state.get_current_group_region_target_plan(
        future_sess,
        player_id=player_id,
        target_region_id="missing_region",
    )
    assert undiscovered is not None
    assert undiscovered["plan_status"] == "target_region_undiscovered"


def test_group_region_target_plan_supports_unavailable_state_for_known_region_without_gateway_guidance(monkeypatch) -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    monkeypatch.setattr(
        session_state,
        "_normalize_group_discovered_region_map",
        lambda _raw: {
            "starter_frontier": {
                "region_id": "starter_frontier",
                "region_label": "Стартовое пограничье",
                "visit_count": 1,
                "summary": "Группа уже знает стартовый регион.",
            },
            "mystic_delta": {
                "region_id": "mystic_delta",
                "region_label": "Туманный предел",
                "visit_count": 1,
                "summary": "Группа знает о Туманном пределе, но не имеет прямого выхода.",
            },
        },
    )
    monkeypatch.setattr(session_state, "get_static_region_gateways", lambda **_kwargs: [])

    unavailable = session_state.get_current_group_region_target_plan(
        sess,
        player_id=player_id,
        target_region_id="mystic_delta",
    )

    assert unavailable is not None
    assert unavailable["plan_status"] == "target_region_unavailable"


def test_group_primary_region_focus_plan_and_target_options_are_canonical_and_separate() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    assert session_state.get_current_group_primary_region_focus_plan(empty_sess, player_id=player_id) is None

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="region_transition",
    )

    focus_plan = session_state.get_current_group_primary_region_focus_plan(sess, player_id=player_id)
    options = session_state.get_current_group_region_target_options(sess, player_id=player_id)
    overview = session_state.get_current_group_region_world_overview(sess, player_id=player_id)

    assert focus_plan is not None
    assert focus_plan["target_region_id"] == "northwatch_frontier"
    assert focus_plan["plan_status"] == "current_region"
    assert options is not None
    assert options["primary_region_focus_plan"]["target_region_id"] == "northwatch_frontier"
    assert [item["target_region_id"] for item in options["target_region_plans"]] == [
        "northwatch_frontier",
        "starter_frontier",
    ]
    assert overview is not None
    assert "primary_region_focus" in overview


def test_group_known_region_route_supports_current_direct_multi_undiscovered_and_disconnected() -> None:
    player_id = uuid.uuid4()
    current_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        current_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_road", "label": "Лесная дорога"},
    )
    session_state.get_current_group_current_region_state(current_sess, player_id=player_id)
    current_route = session_state.get_current_group_known_region_route(
        current_sess,
        player_id=player_id,
        target_region_id="starter_frontier",
    )
    assert current_route is not None
    assert current_route["route_status"] == "current_region"

    direct_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        direct_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_road", "label": "Лесная дорога"},
    )
    session_state.get_current_group_current_region_state(direct_sess, player_id=player_id)
    session_state.reveal_player_map_node(direct_sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        direct_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.record_group_gateway_traversal(
        direct_sess,
        "main",
        gateway_id="forest_settlement_northwatch",
        gateway_label="Выход к северному рубежу",
        source_region_id="starter_frontier",
        source_region_label="Стартовое пограничье",
        target_region_id="northwatch_frontier",
        target_region_label="Северный рубеж",
        source="test",
    )
    groups = session_state._get_group_states(direct_sess)
    group = groups["main"]
    group["discovered_regions"]["northwatch_frontier"] = {
        "region_id": "northwatch_frontier",
        "region_label": "Северный рубеж",
        "visit_count": 1,
        "first_entered_at": "2025-01-02T00:00:00+00:00",
        "last_entered_at": "2025-01-02T00:00:00+00:00",
        "first_anchor_node_id": "northwatch_outpost",
        "last_anchor_node_id": "northwatch_outpost",
        "summary": "Группа ранее входила в регион Северный рубеж.",
    }
    session_state._persist_group_states(direct_sess, groups)
    session_state._sync_group_position_mirrors(direct_sess, group)
    direct_route = session_state.get_current_group_known_region_route(
        direct_sess,
        player_id=player_id,
        target_region_id="northwatch_frontier",
    )
    assert direct_route is not None
    assert direct_route["route_status"] == "direct_route"
    assert direct_route["region_path_ids"] == ["starter_frontier", "northwatch_frontier"]
    assert direct_route["next_gateway_id"] == "forest_settlement_northwatch"

    multi_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        multi_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_road", "label": "Лесная дорога"},
    )
    session_state.get_current_group_current_region_state(multi_sess, player_id=player_id)
    session_state.reveal_player_map_node(multi_sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        multi_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.record_group_gateway_traversal(
        multi_sess,
        "main",
        gateway_id="forest_settlement_northwatch",
        gateway_label="Выход к северному рубежу",
        source_region_id="starter_frontier",
        source_region_label="Стартовое пограничье",
        target_region_id="northwatch_frontier",
        target_region_label="Северный рубеж",
        source="test",
    )
    groups = session_state._get_group_states(multi_sess)
    group = groups["main"]
    group["discovered_regions"]["northwatch_frontier"] = {
        "region_id": "northwatch_frontier",
        "region_label": "Северный рубеж",
        "visit_count": 1,
        "first_entered_at": "2025-01-02T00:00:00+00:00",
        "last_entered_at": "2025-01-02T00:00:00+00:00",
        "first_anchor_node_id": "northwatch_outpost",
        "last_anchor_node_id": "northwatch_outpost",
        "summary": "Группа ранее входила в регион Северный рубеж.",
    }
    group["discovered_regions"]["western_road"] = {
        "region_id": "western_road",
        "region_label": "Западный тракт",
        "visit_count": 1,
        "first_entered_at": "2025-01-03T00:00:00+00:00",
        "last_entered_at": "2025-01-03T00:00:00+00:00",
        "first_anchor_node_id": "old_western_mile",
        "last_anchor_node_id": "old_western_mile",
        "summary": "Группа ранее входила в регион Западный тракт.",
    }
    group["region_link_states"]["region-link:northwatch_frontier::western_road"] = {
        "link_id": "region-link:northwatch_frontier::western_road",
        "region_a_id": "northwatch_frontier",
        "region_a_label": "Северный рубеж",
        "region_b_id": "western_road",
        "region_b_label": "Западный тракт",
        "gateway_ids": ["northwatch_western_stub"],
        "traversal_count": 1,
        "first_discovered_at": "2025-01-03T00:00:00+00:00",
        "last_traversed_at": "2025-01-03T00:00:00+00:00",
        "summary": "Связь между Северным рубежом и Западным трактом уже подтверждена.",
    }
    session_state._persist_group_states(multi_sess, groups)
    session_state._sync_group_position_mirrors(multi_sess, group)
    multi_route = session_state.get_current_group_known_region_route(
        multi_sess,
        player_id=player_id,
        target_region_id="western_road",
    )
    assert multi_route is not None
    assert multi_route["route_status"] == "multi_region_route"
    assert multi_route["region_path_ids"] == ["starter_frontier", "northwatch_frontier", "western_road"]
    assert multi_route["next_gateway_id"] == "forest_settlement_northwatch"

    undiscovered_route = session_state.get_current_group_known_region_route(
        multi_sess,
        player_id=player_id,
        target_region_id="missing_region",
    )
    assert undiscovered_route is not None
    assert undiscovered_route["route_status"] == "target_region_undiscovered"

    disconnected_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        disconnected_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_road", "label": "Лесная дорога"},
    )
    session_state.get_current_group_current_region_state(disconnected_sess, player_id=player_id)
    groups = session_state._get_group_states(disconnected_sess)
    group = groups["main"]
    group["discovered_regions"]["mystic_delta"] = {
        "region_id": "mystic_delta",
        "region_label": "Мистическая дельта",
        "visit_count": 1,
        "first_entered_at": "2025-01-04T00:00:00+00:00",
        "last_entered_at": "2025-01-04T00:00:00+00:00",
        "first_anchor_node_id": "delta_edge",
        "last_anchor_node_id": "delta_edge",
        "summary": "Группа помнит Мистическую дельту как отдельный регион.",
    }
    session_state._persist_group_states(disconnected_sess, groups)
    session_state._sync_group_position_mirrors(disconnected_sess, group)
    disconnected_route = session_state.get_current_group_known_region_route(
        disconnected_sess,
        player_id=player_id,
        target_region_id="mystic_delta",
    )
    assert disconnected_route is not None
    assert disconnected_route["route_status"] == "no_known_route"


def test_group_known_region_route_reflects_next_gateway_statuses_and_primary_route() -> None:
    player_id = uuid.uuid4()
    blocked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        blocked_sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_road", "label": "Лесная дорога"},
    )
    session_state.get_current_group_current_region_state(blocked_sess, player_id=player_id)
    session_state.record_group_gateway_traversal(
        blocked_sess,
        "main",
        gateway_id="forest_settlement_northwatch",
        gateway_label="Выход к северному рубежу",
        source_region_id="starter_frontier",
        source_region_label="Стартовое пограничье",
        target_region_id="northwatch_frontier",
        target_region_label="Северный рубеж",
        source="test",
    )
    groups = session_state._get_group_states(blocked_sess)
    group = groups["main"]
    group["discovered_regions"]["northwatch_frontier"] = {
        "region_id": "northwatch_frontier",
        "region_label": "Северный рубеж",
        "visit_count": 1,
        "first_entered_at": "2025-01-02T00:00:00+00:00",
        "last_entered_at": "2025-01-02T00:00:00+00:00",
        "first_anchor_node_id": "northwatch_outpost",
        "last_anchor_node_id": "northwatch_outpost",
        "summary": "Группа ранее входила в регион Северный рубеж.",
    }
    session_state._persist_group_states(blocked_sess, groups)
    session_state._sync_group_position_mirrors(blocked_sess, group)
    session_state.set_group_route_access_state(
        blocked_sess,
        "main",
        route_id="forest_settlement->old_fortress_edge:move",
        access_state="blocked",
        summary="Проход к северному рубежу закрыт.",
        block_reason="Завал на дальнем тракте.",
        source="test",
    )
    blocked_route = session_state.get_current_group_known_region_route(
        blocked_sess,
        player_id=player_id,
        target_region_id="northwatch_frontier",
    )
    assert blocked_route is not None
    assert blocked_route["route_status"] == "blocked_next_gateway"

    locked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        locked_sess,
        [player_id],
        {"map_level": "region", "node_type": "landmark", "node_id": "fortress_gate", "label": "Ворота крепости"},
    )
    session_state.get_current_group_current_region_state(locked_sess, player_id=player_id)
    session_state.record_group_gateway_traversal(
        locked_sess,
        "main",
        gateway_id="fortress_gate_western_road",
        gateway_label="Западные ворота",
        source_region_id="starter_frontier",
        source_region_label="Стартовое пограничье",
        target_region_id="western_road",
        target_region_label="Западный тракт",
        source="test",
    )
    groups = session_state._get_group_states(locked_sess)
    group = groups["main"]
    group["discovered_regions"]["western_road"] = {
        "region_id": "western_road",
        "region_label": "Западный тракт",
        "visit_count": 1,
        "first_entered_at": "2025-01-03T00:00:00+00:00",
        "last_entered_at": "2025-01-03T00:00:00+00:00",
        "first_anchor_node_id": "old_western_mile",
        "last_anchor_node_id": "old_western_mile",
        "summary": "Группа ранее входила в регион Западный тракт.",
    }
    session_state._persist_group_states(locked_sess, groups)
    session_state._sync_group_position_mirrors(locked_sess, group)
    locked_route = session_state.get_current_group_known_region_route(
        locked_sess,
        player_id=player_id,
        target_region_id="western_road",
    )
    assert locked_route is not None
    assert locked_route["route_status"] == "locked_next_gateway"

    future_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        future_sess,
        [player_id],
        {"map_level": "region", "node_type": "landmark", "node_id": "forgotten_shrine", "label": "Забытое святилище"},
    )
    session_state.get_current_group_current_region_state(future_sess, player_id=player_id)
    session_state.record_group_gateway_traversal(
        future_sess,
        "main",
        gateway_id="forgotten_shrine_sunken_reaches",
        gateway_label="Провал к затопленным пределам",
        source_region_id="starter_frontier",
        source_region_label="Стартовое пограничье",
        target_region_id="sunken_reaches",
        target_region_label="Затопленные пределы",
        source="test",
    )
    groups = session_state._get_group_states(future_sess)
    group = groups["main"]
    group["discovered_regions"]["sunken_reaches"] = {
        "region_id": "sunken_reaches",
        "region_label": "Затопленные пределы",
        "visit_count": 1,
        "first_entered_at": "2025-01-04T00:00:00+00:00",
        "last_entered_at": "2025-01-04T00:00:00+00:00",
        "first_anchor_node_id": "sunken_shore",
        "last_anchor_node_id": "sunken_shore",
        "summary": "Группа ранее входила в Затопленные пределы.",
    }
    session_state._persist_group_states(future_sess, groups)
    session_state._sync_group_position_mirrors(future_sess, group)
    future_route = session_state.get_current_group_known_region_route(
        future_sess,
        player_id=player_id,
        target_region_id="sunken_reaches",
    )
    assert future_route is not None
    assert future_route["route_status"] == "future_stub_next_gateway"

    assert session_state.get_current_group_primary_region_route(SimpleNamespace(settings={}), player_id=player_id) is None
    primary_route = session_state.get_current_group_primary_region_route(blocked_sess, player_id=player_id)
    assert primary_route is not None
    options = session_state.get_current_group_known_region_route_options(blocked_sess, player_id=player_id)
    assert options is not None
    assert options["primary_region_route"] is not None
    assert options["primary_region_route"]["target_region_id"] == primary_route["target_region_id"]


def test_group_region_pursuit_set_links_existing_journey_and_clear_stops_it() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.reveal_player_map_node(sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )

    updated, error = session_state.set_group_region_pursuit(
        sess,
        "main",
        "northwatch_frontier",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert updated is not None
    pursuit = session_state.get_current_group_region_pursuit(sess, player_id=player_id)
    journey = session_state.get_current_group_journey_state(sess, player_id=player_id)
    result = session_state.get_current_group_last_region_pursuit_result(sess, player_id=player_id)

    assert pursuit is not None
    assert pursuit["pursuit_status"] == "pursuing_gateway"
    assert pursuit["guidance_status"] == "approach_gateway"
    assert pursuit["gateway_source_node_id"] == "forest_settlement"
    assert journey is not None
    assert pursuit["linked_journey_id"] == journey["journey_id"]
    assert journey["target_node_id"] == "forest_settlement"
    assert result is not None
    assert result["result_type"] == "region_pursuit_set"

    cleared = session_state.clear_group_region_pursuit(sess, "main", source="test")
    assert cleared is not None
    assert session_state.get_current_group_region_pursuit(sess, player_id=player_id) is None
    assert session_state.get_current_group_journey_state(sess, player_id=player_id) is None
    cleared_result = session_state.get_current_group_last_region_pursuit_result(sess, player_id=player_id)
    assert cleared_result is not None
    assert cleared_result["result_type"] == "region_pursuit_cleared"


def test_group_region_pursuit_supports_ready_blocked_locked_future_and_unavailable_statuses() -> None:
    player_id = uuid.uuid4()

    ready_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        ready_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.get_current_group_current_region_state(ready_sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        ready_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    ready_updated, ready_error = session_state.set_group_region_pursuit(
        ready_sess,
        "main",
        "northwatch_frontier",
        player_id=player_id,
        source="test",
    )
    assert ready_error is None
    assert ready_updated is not None
    assert session_state.get_current_group_region_pursuit(ready_sess, player_id=player_id)["pursuit_status"] == "gateway_ready"
    assert session_state.get_current_group_last_region_pursuit_result(ready_sess, player_id=player_id)["result_type"] == "region_pursuit_gateway_ready"

    blocked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        blocked_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.get_current_group_current_region_state(blocked_sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        blocked_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.set_group_route_access_state(
        blocked_sess,
        "main",
        route_id="forest_settlement->old_fortress_edge:move",
        access_state="blocked",
        summary="Проход к северному рубежу закрыт.",
        block_reason="Завал на дальнем тракте.",
        source="test",
    )
    session_state.set_group_region_pursuit(
        blocked_sess,
        "main",
        "northwatch_frontier",
        player_id=player_id,
        source="test",
    )
    assert session_state.get_current_group_region_pursuit(blocked_sess, player_id=player_id)["pursuit_status"] == "blocked"
    assert session_state.get_current_group_last_region_pursuit_result(blocked_sess, player_id=player_id)["result_type"] == "region_pursuit_blocked"

    locked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        locked_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "landmark",
            "node_id": "fortress_gate",
            "label": "Ворота крепости",
        },
    )
    session_state.get_current_group_current_region_state(locked_sess, player_id=player_id)
    session_state.set_group_region_pursuit(
        locked_sess,
        "main",
        "western_road",
        player_id=player_id,
        source="test",
    )
    assert session_state.get_current_group_region_pursuit(locked_sess, player_id=player_id)["pursuit_status"] == "locked"
    assert session_state.get_current_group_last_region_pursuit_result(locked_sess, player_id=player_id)["result_type"] == "region_pursuit_locked"

    future_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        future_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "landmark",
            "node_id": "forgotten_shrine",
            "label": "Забытое святилище",
        },
    )
    session_state.get_current_group_current_region_state(future_sess, player_id=player_id)
    session_state.set_group_region_pursuit(
        future_sess,
        "main",
        "sunken_reaches",
        player_id=player_id,
        source="test",
    )
    assert session_state.get_current_group_region_pursuit(future_sess, player_id=player_id)["pursuit_status"] == "future_stub"
    assert session_state.get_current_group_last_region_pursuit_result(future_sess, player_id=player_id)["result_type"] == "region_pursuit_future_stub"

    unavailable_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        unavailable_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(unavailable_sess, player_id=player_id)
    session_state.set_group_region_pursuit(
        unavailable_sess,
        "main",
        "missing_region",
        player_id=player_id,
        source="test",
    )
    assert session_state.get_current_group_region_pursuit(unavailable_sess, player_id=player_id)["pursuit_status"] == "unavailable"
    assert session_state.get_current_group_last_region_pursuit_result(unavailable_sess, player_id=player_id)["result_type"] == "region_pursuit_unavailable"


def test_advance_group_region_pursuit_advances_one_journey_leg_and_marks_gateway_ready() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.reveal_player_map_node(sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.set_group_region_pursuit(
        sess,
        "main",
        "northwatch_frontier",
        player_id=player_id,
        source="test",
    )

    updated, error = session_state.advance_group_region_pursuit(
        sess,
        "main",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert updated is not None
    pursuit = session_state.get_current_group_region_pursuit(sess, player_id=player_id)
    journey = session_state.get_current_group_journey_state(sess, player_id=player_id)
    step_result = session_state.get_current_group_last_region_pursuit_step_result(sess, player_id=player_id)
    journey_result = session_state.get_current_group_last_journey_result(sess, player_id=player_id)
    assert pursuit is not None
    assert pursuit["pursuit_status"] == "gateway_ready"
    assert journey is not None
    assert journey["journey_status"] == "arrived"
    assert journey_result is not None
    assert journey_result["result_type"] == "journey_arrived"
    assert step_result is not None
    assert step_result["result_type"] == "region_pursuit_step_gateway_ready"
    assert step_result["step_kind"] == "journey_leg"
    assert step_result["linked_journey_id"] == journey["journey_id"]


def test_advance_group_region_pursuit_executes_gateway_cross_and_clears_pursuit_on_success() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.set_group_region_pursuit(
        sess,
        "main",
        "northwatch_frontier",
        player_id=player_id,
        source="test",
    )

    updated, error = session_state.advance_group_region_pursuit(
        sess,
        "main",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert updated is not None
    assert session_state.get_current_group_region_pursuit(sess, player_id=player_id) is None
    current_region = session_state.get_current_group_current_region_state(sess, player_id=player_id)
    transition_result = session_state.get_current_group_last_region_transition_result(sess, player_id=player_id)
    pursuit_result = session_state.get_current_group_last_region_pursuit_result(sess, player_id=player_id)
    step_result = session_state.get_current_group_last_region_pursuit_step_result(sess, player_id=player_id)
    assert current_region is not None
    assert current_region["region_id"] == "northwatch_frontier"
    assert transition_result is not None
    assert transition_result["result_type"] == "region_transition_completed"
    assert pursuit_result is not None
    assert pursuit_result["result_type"] == "region_pursuit_gateway_ready"
    assert step_result is not None
    assert step_result["result_type"] == "region_pursuit_step_transitioned"
    assert step_result["step_kind"] == "gateway_cross"


def test_advance_group_region_pursuit_returns_honest_no_step_results_for_blocked_and_missing_pursuit() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )

    empty_updated, empty_error = session_state.advance_group_region_pursuit(
        empty_sess,
        "main",
        player_id=player_id,
        source="test",
    )

    assert "нет активного region pursuit" in str(empty_error)
    assert empty_updated is not None
    empty_step = session_state.get_current_group_last_region_pursuit_step_result(empty_sess, player_id=player_id)
    assert empty_step is not None
    assert empty_step["result_type"] == "region_pursuit_step_invalid"
    assert empty_step["step_kind"] == "no_step"

    blocked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        blocked_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.get_current_group_current_region_state(blocked_sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        blocked_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.set_group_route_access_state(
        blocked_sess,
        "main",
        route_id="forest_settlement->old_fortress_edge:move",
        access_state="blocked",
        summary="Проход к северному рубежу закрыт.",
        block_reason="Завал на дальнем тракте.",
        source="test",
    )
    session_state.set_group_region_pursuit(
        blocked_sess,
        "main",
        "northwatch_frontier",
        player_id=player_id,
        source="test",
    )

    blocked_updated, blocked_error = session_state.advance_group_region_pursuit(
        blocked_sess,
        "main",
        player_id=player_id,
        source="test",
    )

    assert blocked_error is None
    assert blocked_updated is not None
    blocked_step = session_state.get_current_group_last_region_pursuit_step_result(blocked_sess, player_id=player_id)
    assert blocked_step is not None
    assert blocked_step["result_type"] == "region_pursuit_step_blocked"
    assert blocked_step["step_kind"] == "no_step"


def test_set_group_multi_region_pursuit_maps_direct_and_multihop_routes_cleanly() -> None:
    player_id = uuid.uuid4()

    direct_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        direct_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(direct_sess, player_id=player_id)
    session_state.reveal_player_map_node(direct_sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        direct_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.record_group_gateway_traversal(
        direct_sess,
        "main",
        gateway_id="forest_settlement_northwatch",
        gateway_label="Выход к северному рубежу",
        source_region_id="starter_frontier",
        source_region_label="Стартовое пограничье",
        target_region_id="northwatch_frontier",
        target_region_label="Северный рубеж",
        source="test",
    )
    groups = session_state._get_group_states(direct_sess)
    group = groups["main"]
    group["discovered_regions"]["northwatch_frontier"] = {
        "region_id": "northwatch_frontier",
        "region_label": "Северный рубеж",
        "visit_count": 1,
        "first_entered_at": "2025-01-02T00:00:00+00:00",
        "last_entered_at": "2025-01-02T00:00:00+00:00",
        "first_anchor_node_id": "northwatch_outpost",
        "last_anchor_node_id": "northwatch_outpost",
        "summary": "Группа ранее входила в регион Северный рубеж.",
    }
    session_state._persist_group_states(direct_sess, groups)
    session_state._sync_group_position_mirrors(direct_sess, group)

    updated, error = session_state.set_group_multi_region_pursuit(
        direct_sess,
        "main",
        "northwatch_frontier",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert updated is not None
    pursuit = session_state.get_current_group_multi_region_pursuit(direct_sess, player_id=player_id)
    journey = session_state.get_current_group_journey_state(direct_sess, player_id=player_id)
    result = session_state.get_current_group_last_multi_region_pursuit_result(direct_sess, player_id=player_id)
    assert pursuit is None
    direct_pursuit = session_state.get_current_group_region_pursuit(direct_sess, player_id=player_id)
    direct_result = session_state.get_current_group_last_region_pursuit_result(direct_sess, player_id=player_id)
    assert direct_pursuit is not None
    assert direct_pursuit["pursuit_scope"] == "direct_region"
    assert journey is not None
    assert direct_pursuit["linked_journey_id"] == journey["journey_id"]
    assert direct_result is not None
    assert direct_result["result_type"] == "region_pursuit_set"
    assert result is None

    multi_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        multi_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(multi_sess, player_id=player_id)
    session_state.reveal_player_map_node(multi_sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        multi_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.record_group_gateway_traversal(
        multi_sess,
        "main",
        gateway_id="forest_settlement_northwatch",
        gateway_label="Выход к северному рубежу",
        source_region_id="starter_frontier",
        source_region_label="Стартовое пограничье",
        target_region_id="northwatch_frontier",
        target_region_label="Северный рубеж",
        source="test",
    )
    groups = session_state._get_group_states(multi_sess)
    group = groups["main"]
    group["discovered_regions"]["northwatch_frontier"] = {
        "region_id": "northwatch_frontier",
        "region_label": "Северный рубеж",
        "visit_count": 1,
        "first_entered_at": "2025-01-02T00:00:00+00:00",
        "last_entered_at": "2025-01-02T00:00:00+00:00",
        "first_anchor_node_id": "northwatch_outpost",
        "last_anchor_node_id": "northwatch_outpost",
        "summary": "Группа ранее входила в регион Северный рубеж.",
    }
    group["discovered_regions"]["western_road"] = {
        "region_id": "western_road",
        "region_label": "Западный тракт",
        "visit_count": 1,
        "first_entered_at": "2025-01-03T00:00:00+00:00",
        "last_entered_at": "2025-01-03T00:00:00+00:00",
        "first_anchor_node_id": "old_western_mile",
        "last_anchor_node_id": "old_western_mile",
        "summary": "Группа ранее входила в регион Западный тракт.",
    }
    group["region_link_states"]["region-link:northwatch_frontier::western_road"] = {
        "link_id": "region-link:northwatch_frontier::western_road",
        "region_a_id": "northwatch_frontier",
        "region_a_label": "Северный рубеж",
        "region_b_id": "western_road",
        "region_b_label": "Западный тракт",
        "gateway_ids": ["northwatch_western_stub"],
        "traversal_count": 1,
        "first_discovered_at": "2025-01-03T00:00:00+00:00",
        "last_traversed_at": "2025-01-03T00:00:00+00:00",
        "summary": "Связь между Северным рубежом и Западным трактом уже подтверждена.",
    }
    session_state._persist_group_states(multi_sess, groups)
    session_state._sync_group_position_mirrors(multi_sess, group)

    updated, error = session_state.set_group_multi_region_pursuit(
        multi_sess,
        "main",
        "western_road",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert updated is not None
    multi_pursuit = session_state.get_current_group_multi_region_pursuit(multi_sess, player_id=player_id)
    multi_result = session_state.get_current_group_last_multi_region_pursuit_result(multi_sess, player_id=player_id)
    multi_journey = session_state.get_current_group_journey_state(multi_sess, player_id=player_id)
    assert multi_pursuit is not None
    assert multi_pursuit["pursuit_scope"] == "known_multi_region"
    assert multi_pursuit["target_region_id"] == "western_road"
    assert multi_pursuit["target_region_path_ids"] == ["starter_frontier", "northwatch_frontier", "western_road"]
    assert multi_pursuit["current_hop_region_id"] == "starter_frontier"
    assert multi_pursuit["next_hop_region_id"] == "northwatch_frontier"
    assert multi_pursuit["known_route_status"] == "multi_region_route"
    assert multi_pursuit["pursuit_status"] == "pursuing_gateway"
    assert multi_journey is not None
    assert multi_pursuit["linked_journey_id"] == multi_journey["journey_id"]
    assert multi_result is not None
    assert multi_result["result_type"] in {"region_pursuit_multihop_set", "region_pursuit_multihop_updated"}
    assert multi_result["next_hop_region_id"] == "northwatch_frontier"


def test_set_group_multi_region_pursuit_supports_blocked_and_unavailable_routes() -> None:
    player_id = uuid.uuid4()

    blocked_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        blocked_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(blocked_sess, player_id=player_id)
    session_state.reveal_player_map_node(blocked_sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        blocked_sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.record_group_gateway_traversal(
        blocked_sess,
        "main",
        gateway_id="forest_settlement_northwatch",
        gateway_label="Выход к северному рубежу",
        source_region_id="starter_frontier",
        source_region_label="Стартовое пограничье",
        target_region_id="northwatch_frontier",
        target_region_label="Северный рубеж",
        source="test",
    )
    groups = session_state._get_group_states(blocked_sess)
    group = groups["main"]
    group["discovered_regions"]["northwatch_frontier"] = {
        "region_id": "northwatch_frontier",
        "region_label": "Северный рубеж",
        "visit_count": 1,
        "first_entered_at": "2025-01-02T00:00:00+00:00",
        "last_entered_at": "2025-01-02T00:00:00+00:00",
        "first_anchor_node_id": "northwatch_outpost",
        "last_anchor_node_id": "northwatch_outpost",
        "summary": "Группа ранее входила в регион Северный рубеж.",
    }
    session_state._persist_group_states(blocked_sess, groups)
    session_state._sync_group_position_mirrors(blocked_sess, group)
    session_state.set_group_route_access_state(
        blocked_sess,
        "main",
        route_id="forest_settlement->old_fortress_edge:move",
        access_state="blocked",
        summary="Проход к северному рубежу закрыт.",
        block_reason="Завал на дальнем тракте.",
        source="test",
    )

    updated, error = session_state.set_group_multi_region_pursuit(
        blocked_sess,
        "main",
        "northwatch_frontier",
        player_id=player_id,
        source="test",
    )

    assert error is None
    assert updated is not None
    blocked_pursuit = session_state.get_current_group_region_pursuit(blocked_sess, player_id=player_id)
    blocked_result = session_state.get_current_group_last_region_pursuit_result(blocked_sess, player_id=player_id)
    assert blocked_pursuit is not None
    assert blocked_pursuit["pursuit_status"] == "blocked"
    assert blocked_result is not None
    assert blocked_result["result_type"] == "region_pursuit_blocked"

    unavailable_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        unavailable_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(unavailable_sess, player_id=player_id)

    unavailable_updated, unavailable_error = session_state.set_group_multi_region_pursuit(
        unavailable_sess,
        "main",
        "missing_region",
        player_id=player_id,
        source="test",
    )

    assert unavailable_error is None
    assert unavailable_updated is not None
    unavailable_pursuit = session_state.get_current_group_region_pursuit(unavailable_sess, player_id=player_id)
    unavailable_result = session_state.get_current_group_last_region_pursuit_result(unavailable_sess, player_id=player_id)
    assert unavailable_pursuit is not None
    assert unavailable_pursuit["pursuit_status"] == "unavailable"
    assert unavailable_result is not None
    assert unavailable_result["result_type"] == "region_pursuit_unavailable"


def test_multi_region_pursuit_syncs_after_transition_and_clears_on_target_reached() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    groups = session_state._get_group_states(sess)
    group = groups["main"]
    group.setdefault("region_link_states", {})
    group["discovered_regions"]["northwatch_frontier"] = {
        "region_id": "northwatch_frontier",
        "region_label": "Северный рубеж",
        "visit_count": 1,
        "first_entered_at": "2025-01-02T00:00:00+00:00",
        "last_entered_at": "2025-01-02T00:00:00+00:00",
        "first_anchor_node_id": "northwatch_outpost",
        "last_anchor_node_id": "northwatch_outpost",
        "summary": "Группа ранее входила в регион Северный рубеж.",
    }
    group["discovered_regions"]["western_road"] = {
        "region_id": "western_road",
        "region_label": "Западный тракт",
        "visit_count": 1,
        "first_entered_at": "2025-01-03T00:00:00+00:00",
        "last_entered_at": "2025-01-03T00:00:00+00:00",
        "first_anchor_node_id": "old_western_mile",
        "last_anchor_node_id": "old_western_mile",
        "summary": "Группа ранее входила в регион Западный тракт.",
    }
    group["region_link_states"]["region-link:northwatch_frontier::starter_frontier"] = {
        "link_id": "region-link:northwatch_frontier::starter_frontier",
        "region_a_id": "northwatch_frontier",
        "region_a_label": "Северный рубеж",
        "region_b_id": "starter_frontier",
        "region_b_label": "Стартовое пограничье",
        "gateway_ids": ["forest_settlement_northwatch"],
        "traversal_count": 1,
        "first_discovered_at": "2025-01-02T00:00:00+00:00",
        "last_traversed_at": "2025-01-02T00:00:00+00:00",
        "summary": "Связь между Стартовым пограничьем и Северным рубежом подтверждена.",
    }
    group["region_link_states"]["region-link:northwatch_frontier::western_road"] = {
        "link_id": "region-link:northwatch_frontier::western_road",
        "region_a_id": "northwatch_frontier",
        "region_a_label": "Северный рубеж",
        "region_b_id": "western_road",
        "region_b_label": "Западный тракт",
        "gateway_ids": ["northwatch_western_stub"],
        "traversal_count": 1,
        "first_discovered_at": "2025-01-03T00:00:00+00:00",
        "last_traversed_at": "2025-01-03T00:00:00+00:00",
        "summary": "Связь между Северным рубежом и Западным трактом подтверждена.",
    }
    session_state._persist_group_states(sess, groups)
    session_state._sync_group_position_mirrors(sess, group)

    updated, error = session_state.set_group_multi_region_pursuit(
        sess,
        "main",
        "western_road",
        player_id=player_id,
        source="test",
    )
    assert error is None
    assert updated is not None

    updated, error = session_state.advance_group_region_pursuit(
        sess,
        "main",
        player_id=player_id,
        source="test",
    )
    assert error is None
    assert updated is not None

    refreshed = session_state.get_current_group_multi_region_pursuit(sess, player_id=player_id)
    transition_result = session_state.get_current_group_last_region_transition_result(sess, player_id=player_id)
    assert transition_result is not None
    assert transition_result["result_type"] == "region_transition_completed"
    assert refreshed is not None
    assert refreshed["pursuit_scope"] == "known_multi_region"
    assert refreshed["target_region_id"] == "western_road"
    assert refreshed["current_hop_region_id"] == "northwatch_frontier"
    assert refreshed["next_hop_region_id"] == "western_road"
    assert refreshed["known_route_status"] in {"direct_route", "locked_next_gateway"}

    groups = session_state._get_group_states(sess)
    group = groups["main"]
    group["current_map_position"] = {
        "map_level": "region",
        "node_type": "gateway",
        "node_id": "fortress_gate",
        "label": "Ворота крепости",
    }
    session_state._persist_group_states(sess, groups)
    session_state._sync_group_position_mirrors(sess, group)

    updated, error = session_state.advance_group_region_pursuit(
        sess,
        "main",
        player_id=player_id,
        source="test",
    )
    assert error is None
    assert updated is not None
    assert session_state.get_current_group_multi_region_pursuit(sess, player_id=player_id) is not None

    groups = session_state._get_group_states(sess)
    group = groups["main"]
    group["current_map_position"] = {
        "map_level": "region",
        "node_type": "zone",
        "node_id": "old_western_mile",
        "label": "Старая западная миля",
    }
    group["current_region_state"] = {
        "region_id": "western_road",
        "region_label": "Западный тракт",
        "current_node_id": "old_western_mile",
        "current_node_label": "Старая западная миля",
        "entered_at": "2025-01-03T00:00:00+00:00",
        "visit_count": 2,
        "source": "region_residency",
    }
    session_state._persist_group_states(sess, groups)
    session_state._sync_group_position_mirrors(sess, group)

    assert session_state.sync_group_multi_region_pursuit(sess, "main", source="test") is None
    assert session_state.get_current_group_multi_region_pursuit(sess, player_id=player_id) is None
    assert session_state.get_current_group_region_pursuit(sess, player_id=player_id) is None
    last_result = session_state.get_current_group_last_region_pursuit_result(sess, player_id=player_id)
    assert last_result is not None
    assert last_result["result_type"] == "region_pursuit_cleared"

def test_group_region_transition_updates_region_residency_history() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )

    updated, error = session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="region_transition",
    )

    assert error is None
    assert updated is not None
    current_region = session_state.get_current_group_current_region_state(sess, player_id=player_id)
    assert current_region["region_id"] == "northwatch_frontier"
    assert current_region["region_label"] == "Северный рубеж"
    assert current_region["current_node_id"] == "northwatch_outpost"
    assert current_region["visit_count"] == 1
    discovered_regions = session_state.get_current_group_discovered_regions(sess, player_id=player_id)
    assert [item["region_id"] for item in discovered_regions] == ["starter_frontier", "northwatch_frontier"]
    assert session_state.get_current_group_last_region_entry_result(sess, player_id=player_id)["result_type"] == "region_transition_entry"
    assert session_state.get_current_group_last_region_onboarding_result(sess, player_id=player_id)["region_id"] == "northwatch_frontier"


def test_failed_region_transition_does_not_create_fake_discovered_region() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)

    updated, error = session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="test",
    )

    assert error == "Выход пока закрыт условиями этого узла."
    assert updated is not None
    discovered_regions = session_state.get_current_group_discovered_regions(sess, player_id=player_id)
    assert [item["region_id"] for item in discovered_regions] == ["starter_frontier"]


def test_successful_region_transition_records_gateway_history_and_region_link() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )

    updated, error = session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="region_transition",
    )

    assert error is None
    assert updated is not None
    crossings = session_state.get_current_group_gateway_traversal_states(sess, player_id=player_id)
    links = session_state.get_current_group_region_link_states(sess, player_id=player_id)
    result = session_state.get_current_group_last_region_link_result(sess, player_id=player_id)
    assert len(crossings) == 1
    assert crossings[0]["gateway_id"] == "forest_settlement_northwatch"
    assert crossings[0]["traversal_count"] == 1
    assert len(links) == 1
    assert links[0]["link_id"] == "region-link:northwatch_frontier::starter_frontier"
    assert links[0]["gateway_ids"] == ["forest_settlement_northwatch"]
    assert links[0]["traversal_count"] == 1
    assert result is not None
    assert result["result_type"] == "first_region_link_discovered"


def test_repeated_gateway_crossing_updates_counts_without_duplicate_region_link() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="region_transition",
    )
    groups = session_state._get_group_states(sess)
    group = groups["main"]
    group["current_map_position"] = {
        "map_level": "region",
        "node_type": "zone",
        "node_id": "forest_settlement",
        "label": "Лесной посёлок",
        "area_label": "Лесной посёлок",
    }
    group["area_label"] = "Лесной посёлок"
    group["current_region_state"] = {
        "region_id": "starter_frontier",
        "region_label": "Стартовое пограничье",
        "current_node_id": "forest_settlement",
        "visit_count": 2,
        "entered_at": "2025-01-02T00:00:00+00:00",
        "source": "region_transition",
    }
    session_state._persist_group_states(sess, groups)
    session_state._sync_group_position_mirrors(sess, group)

    updated, error = session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="region_transition",
    )

    assert error is None
    assert updated is not None
    crossings = session_state.get_current_group_gateway_traversal_states(sess, player_id=player_id)
    links = session_state.get_current_group_region_link_states(sess, player_id=player_id)
    result = session_state.get_current_group_last_region_link_result(sess, player_id=player_id)
    assert len(crossings) == 1
    assert crossings[0]["traversal_count"] == 2
    assert len(links) == 1
    assert links[0]["link_id"] == "region-link:northwatch_frontier::starter_frontier"
    assert links[0]["traversal_count"] == 2
    assert result is not None
    assert result["result_type"] == "repeated_gateway_crossing"
    assert result["traversal_count"] == 2


def test_failed_region_transition_does_not_create_fake_gateway_history_or_region_link() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "forest_settlement", "label": "Лесной посёлок"},
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.set_group_route_access_state(
        sess,
        "main",
        route_id="forest_settlement->old_fortress_edge:move",
        access_state="blocked",
        summary="Проход к северному рубежу закрыт.",
        block_reason="Завал на дальнем тракте.",
        source="test",
    )
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )

    updated, error = session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="region_transition",
    )

    assert "заблокирован" in str(error)
    assert updated is not None
    assert session_state.get_current_group_gateway_traversal_states(sess, player_id=player_id) == []
    assert session_state.get_current_group_region_link_states(sess, player_id=player_id) == []
    assert session_state.get_current_group_last_region_link_result(sess, player_id=player_id) is None
    assert session_state.get_current_group_last_region_onboarding_result(sess, player_id=player_id)["region_id"] == "starter_frontier"
