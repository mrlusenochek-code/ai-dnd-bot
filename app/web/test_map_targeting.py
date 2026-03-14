from __future__ import annotations

from app.web.map_targeting import resolve_action_target_node, resolve_group_target_route, validate_group_target_transition


def test_resolve_action_target_node_returns_zone_target_for_move_text() -> None:
    target = resolve_action_target_node(
        action_text="выхожу на улицу",
        current_area_label="Старый подвал",
        action_kind="move",
    )

    assert target == {
        "map_level": "region",
        "node_type": "zone",
        "node_id": "улица у таверны",
        "label": "улица у таверны",
        "zone_label": "улица у таверны",
        "area_label": "улица у таверны",
    }


def test_resolve_action_target_node_returns_landmark_target_for_move_text() -> None:
    target = resolve_action_target_node(
        action_text="иду к воротам",
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "центр города",
            "label": "центр города",
        },
        current_area_label="центр города",
        action_kind="move",
    )

    assert target == {
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "ворота",
        "label": "ворота",
        "zone_label": "центр города",
        "area_label": "центр города",
    }


def test_resolve_action_target_node_returns_interior_entry_for_enter_text() -> None:
    target = resolve_action_target_node(
        target_text="замок",
        current_area_label="центр города",
        action_kind="enter",
    )

    assert target == {
        "map_level": "interior",
        "node_type": "interior_entry",
        "node_id": "замок",
        "label": "замок",
        "zone_label": "центр города",
        "area_label": "центр города",
    }


def test_validate_group_target_transition_allows_move_zone_and_landmark() -> None:
    assert validate_group_target_transition(
        action_kind="move",
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "улица у таверны",
            "label": "улица у таверны",
            "zone_label": "улица у таверны",
        },
    ) == (True, None)
    assert validate_group_target_transition(
        action_kind="move",
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "ворота",
            "label": "ворота",
            "zone_label": "центр города",
        },
    ) == (True, None)


def test_validate_group_target_transition_allows_enter_interior_entry() -> None:
    assert validate_group_target_transition(
        action_kind="enter",
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "замок",
            "label": "замок",
            "zone_label": "центр города",
        },
    ) == (True, None)


def test_validate_group_target_transition_rejects_enter_zone_with_clear_error() -> None:
    valid, error = validate_group_target_transition(
        action_kind="enter",
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "центр города",
            "label": "центр города",
            "zone_label": "центр города",
        },
    )

    assert valid is False
    assert error == "Для `group enter` нужна interior/building цель, а не обычная zone."


def test_resolve_group_target_route_zone_to_zone_move_valid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "таверна",
            "label": "таверна",
        },
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "улица у таверны",
            "label": "улица у таверны",
            "zone_label": "улица у таверны",
            "area_label": "улица у таверны",
        },
        action_kind="move",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "zone_move"
    assert route["action_kind"] == "move"
    assert route["target_node_type"] == "zone"
    assert route["target_node_id"] == "улица у таверны"


def test_resolve_group_target_route_zone_to_landmark_move_valid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "центр города",
            "label": "центр города",
        },
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "ворота",
            "label": "ворота",
            "zone_label": "центр города",
            "area_label": "центр города",
        },
        action_kind="move",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "landmark_move"
    assert route["target_node_type"] == "landmark"


def test_resolve_group_target_route_zone_to_interior_entry_enter_valid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "центр города",
            "label": "центр города",
        },
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "замок",
            "label": "замок",
            "zone_label": "центр города",
            "area_label": "центр города",
        },
        action_kind="enter",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "enter_location"
    assert route["action_kind"] == "enter"


def test_resolve_group_target_route_zone_to_interior_entry_move_invalid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "центр города",
            "label": "центр города",
        },
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "замок",
            "label": "замок",
            "zone_label": "центр города",
            "area_label": "центр города",
        },
        action_kind="move",
    )

    assert route["allowed"] is False
    assert route["route_kind"] == "invalid"
    assert route["error"] == "Для `group move` допустимы только zone или landmark цели."


def test_resolve_group_target_route_zone_enter_zone_invalid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "центр города",
            "label": "центр города",
        },
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "центр города",
            "label": "центр города",
            "zone_label": "центр города",
            "area_label": "центр города",
        },
        action_kind="enter",
    )

    assert route["allowed"] is False
    assert route["error"] == "Для `group enter` нужна interior/building цель, а не обычная zone."


def test_resolve_group_target_route_landmark_to_interior_entry_enter_valid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "ворота",
            "label": "ворота",
            "area_label": "центр города",
        },
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "замок",
            "label": "замок",
            "zone_label": "центр города",
            "area_label": "центр города",
        },
        action_kind="enter",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "enter_location"
