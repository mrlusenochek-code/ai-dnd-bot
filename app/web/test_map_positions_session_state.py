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
        "source": "test",
        "active": True,
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
    assert updated["current_map_position"] == {
        "v": 1,
        "map_level": "interior",
        "node_type": "interior_entry",
        "node_id": "замок",
        "label": "замок",
        "area_label": "Таверна",
    }
    assert updated["movement_intent"]["target_node_type"] == "interior_entry"
    assert updated["movement_intent"]["target_node_id"] == "замок"
    assert updated["movement_intent"]["movement_mode"] == "normal"
    assert updated["movement_intent"]["movement_kind"] == "enter"
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
    assert updated["movement_intent"]["travel_activity"] == {
        "activity": "navigate",
        "assigned_actor_id": str(player_id),
        "source": "test",
    }
