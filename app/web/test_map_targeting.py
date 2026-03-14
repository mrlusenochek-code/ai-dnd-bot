from __future__ import annotations

from app.web.map_registry import find_static_link, get_static_map_links, get_static_map_nodes, get_static_node, resolve_static_map_node
from app.web.map_targeting import resolve_action_target_node, resolve_group_target_route, validate_group_target_transition


def test_static_map_registry_loads_known_nodes_and_links() -> None:
    nodes = get_static_map_nodes()
    links = get_static_map_links()

    assert len(nodes) >= 5
    assert any(node["node_type"] == "zone" for node in nodes)
    assert any(node["node_type"] == "landmark" for node in nodes)
    assert any(node["node_type"] == "interior_entry" for node in nodes)
    assert get_static_node("start_trakt") == {
        "node_id": "start_trakt",
        "label": "Стартовый тракт",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Стартовый тракт",
        "aliases": (
            "стартовый тракт",
            "тракт",
            "дорога у лагеря",
            "лагерный тракт",
        ),
    }
    assert find_static_link("start_trakt", "fortress_gate", "move") == {
        "from_node_id": "start_trakt",
        "to_node_id": "fortress_gate",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    }
    assert any(link["action_kind"] == "enter" for link in links)


def test_resolve_static_map_node_supports_labels_and_aliases() -> None:
    assert resolve_static_map_node("ворота крепости") == {
        "node_id": "fortress_gate",
        "label": "Ворота крепости",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Стартовый тракт",
        "aliases": (
            "ворота крепости",
            "крепостные ворота",
            "ворота",
        ),
    }
    assert resolve_static_map_node("иду к шахте") == {
        "node_id": "mine_entrance",
        "label": "Шахтный вход",
        "node_type": "interior_entry",
        "map_level": "interior",
        "area_label": "Лесная дорога",
        "aliases": (
            "шахтный вход",
            "вход в шахту",
            "шахта",
            "шахте",
            "к шахте",
        ),
    }


def test_resolve_action_target_node_prefers_static_registry_for_move_text() -> None:
    target = resolve_action_target_node(
        action_text="иду к воротам крепости",
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        current_area_label="Стартовый тракт",
        action_kind="move",
        known_node_ids={"fortress_gate"},
        require_known_static=True,
    )

    assert target == {
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "fortress_gate",
        "label": "Ворота крепости",
        "zone_label": "Стартовый тракт",
        "area_label": "Стартовый тракт",
    }


def test_resolve_action_target_node_prefers_static_registry_for_enter_text() -> None:
    target = resolve_action_target_node(
        target_text="шахта",
        current_area_label="Лесная дорога",
        action_kind="enter",
        known_node_ids={"mine_entrance"},
        require_known_static=True,
    )

    assert target == {
        "map_level": "interior",
        "node_type": "interior_entry",
        "node_id": "mine_entrance",
        "label": "Шахтный вход",
        "zone_label": "Лесная дорога",
        "area_label": "Лесная дорога",
    }


def test_resolve_action_target_node_falls_back_to_heuristic_if_registry_has_no_match() -> None:
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


def test_resolve_action_target_node_blocks_unknown_static_target_in_strict_known_mode() -> None:
    target = resolve_action_target_node(
        action_text="иду к воротам крепости",
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        current_area_label="Стартовый тракт",
        action_kind="move",
        known_node_ids={"start_trakt"},
        require_known_static=True,
    )

    assert target is None


def test_validate_group_target_transition_allows_move_zone_and_landmark() -> None:
    assert validate_group_target_transition(
        action_kind="move",
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "eastern_bank",
            "label": "Восточный берег",
            "zone_label": "Восточный берег",
        },
    ) == (True, None)
    assert validate_group_target_transition(
        action_kind="move",
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "fortress_gate",
            "label": "Ворота крепости",
            "zone_label": "Стартовый тракт",
        },
    ) == (True, None)


def test_validate_group_target_transition_allows_enter_interior_entry() -> None:
    assert validate_group_target_transition(
        action_kind="enter",
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Лесная дорога",
        },
    ) == (True, None)


def test_validate_group_target_transition_rejects_enter_zone_with_clear_error() -> None:
    valid, error = validate_group_target_transition(
        action_kind="enter",
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
            "zone_label": "Стартовый тракт",
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
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "eastern_bank",
            "label": "Восточный берег",
            "zone_label": "Восточный берег",
            "area_label": "Восточный берег",
        },
        action_kind="move",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "zone_move"
    assert route["action_kind"] == "move"
    assert route["target_node_type"] == "zone"
    assert route["target_node_id"] == "eastern_bank"


def test_resolve_group_target_route_zone_to_landmark_move_valid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "fortress_gate",
            "label": "Ворота крепости",
            "zone_label": "Стартовый тракт",
            "area_label": "Стартовый тракт",
        },
        action_kind="move",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "landmark_move"
    assert route["target_node_type"] == "landmark"
    assert route["target_node_id"] == "fortress_gate"


def test_resolve_group_target_route_zone_to_interior_entry_enter_valid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Лесная дорога",
            "area_label": "Лесная дорога",
        },
        action_kind="enter",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "enter_location"
    assert route["action_kind"] == "enter"


def test_resolve_group_target_route_registry_missing_link_is_authoritative_error() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "watchtower",
            "label": "Сторожевая башня",
            "zone_label": "Восточный берег",
            "area_label": "Восточный берег",
        },
        action_kind="move",
    )

    assert route["allowed"] is False
    assert route["route_kind"] == "invalid"
    assert route["error"] == "Для известных узлов карты нет допустимого перехода по registry link."


def test_resolve_group_target_route_zone_to_interior_entry_move_invalid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Лесная дорога",
            "area_label": "Лесная дорога",
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
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "eastern_bank",
            "label": "Восточный берег",
            "zone_label": "Восточный берег",
            "area_label": "Восточный берег",
        },
        action_kind="enter",
    )

    assert route["allowed"] is False
    assert route["error"] == "Для `group enter` нужна interior/building цель, а не обычная zone."


def test_resolve_group_target_route_landmark_to_interior_entry_enter_falls_back_when_registry_data_missing() -> None:
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
    assert route["action_kind"] == "enter"


def test_resolve_group_target_route_falls_back_when_registry_data_is_missing() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "неизвестная поляна",
            "label": "неизвестная поляна",
        },
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "ворота",
            "label": "ворота",
            "zone_label": "неизвестная поляна",
            "area_label": "неизвестная поляна",
        },
        action_kind="move",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "landmark_move"
    assert route["target_node_id"] == "ворота"
