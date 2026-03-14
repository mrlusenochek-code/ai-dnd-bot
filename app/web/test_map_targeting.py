from __future__ import annotations

from app.web.map_registry import (
    find_static_link,
    get_obvious_linked_static_node_ids,
    get_static_link_metadata,
    get_static_map_links,
    get_static_map_nodes,
    get_static_node_metadata,
    get_static_node,
    resolve_static_map_node,
)
from app.web.map_targeting import resolve_action_target_node, resolve_group_target_route, validate_group_target_transition


def test_static_map_registry_loads_known_nodes_and_links() -> None:
    nodes = get_static_map_nodes()
    links = get_static_map_links()

    node_ids = [node["node_id"] for node in nodes]

    assert len(nodes) >= 12
    assert len(node_ids) == len(set(node_ids))
    assert "craft_town" in node_ids
    assert "road_hamlet" in node_ids
    assert "chapel_village" in node_ids
    assert "forest_settlement" in node_ids
    assert "ruined_settlement" in node_ids
    assert "old_fortress_edge" in node_ids
    assert "marsh_edge" in node_ids
    assert "forgotten_shrine" in node_ids
    assert any(node["node_type"] == "zone" for node in nodes)
    assert any(node["node_type"] == "landmark" for node in nodes)
    assert any(node["node_type"] == "interior_entry" for node in nodes)
    assert get_static_node_metadata(get_static_node("craft_town")) == {
        "settlement_kind": "town",
        "environment_hint": "lakeshore",
        "safe_rest_hint": True,
    }
    assert get_static_node("start_trakt") == {
        "node_id": "start_trakt",
        "label": "Стартовый тракт",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Стартовый тракт",
        "zone_band": "safe",
        "settlement_kind": "roadside",
        "environment_hint": "roadland",
        "safe_rest_hint": True,
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
        "traversal_kind": "gate_approach",
        "risk_band": "low",
        "terrain_hint": "fortified",
        "travel_tags": ["fortified"],
    }
    assert find_static_link("craft_town", "fortress_gate", "move") == {
        "from_node_id": "craft_town",
        "to_node_id": "fortress_gate",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
        "traversal_kind": "gate_approach",
        "risk_band": "low",
        "terrain_hint": "fortified",
        "travel_tags": ["fortified"],
    }
    assert find_static_link("forest_settlement", "old_fortress_edge", "move") == {
        "from_node_id": "forest_settlement",
        "to_node_id": "old_fortress_edge",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "ruin_path",
        "traversal_kind": "ruin_path",
        "risk_band": "high",
        "terrain_hint": "ruins",
        "travel_tags": ["ruins", "elevated_watch"],
    }
    assert find_static_link("ruined_settlement", "mine_entrance", "enter") == {
        "from_node_id": "ruined_settlement",
        "to_node_id": "mine_entrance",
        "action_kind": "enter",
        "route_kind": "enter_location",
        "link_kind": "entrance",
        "traversal_kind": "entry",
        "risk_band": "high",
        "terrain_hint": "ruins",
        "travel_tags": ["transition", "interior_threshold"],
    }
    assert any(link["action_kind"] == "enter" for link in links)
    assert get_static_link_metadata(find_static_link("ruined_settlement", "mine_entrance", "enter")) == {
        "traversal_kind": "entry",
        "risk_band": "high",
        "terrain_hint": "ruins",
        "travel_tags": ["transition", "interior_threshold"],
    }
    assert get_obvious_linked_static_node_ids("start_trakt") == ["fortress_gate"]


def test_resolve_static_map_node_supports_labels_and_aliases() -> None:
    assert resolve_static_map_node("ворота крепости") == {
        "node_id": "fortress_gate",
        "label": "Ворота крепости",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Стартовый тракт",
        "zone_band": "safe",
        "poi_kind": "fortified",
        "environment_hint": "fortified",
        "safe_rest_hint": False,
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
        "area_label": "Разрушенный посёлок",
        "zone_band": "danger",
        "poi_kind": "mine",
        "environment_hint": "ruined_frontier",
        "safe_rest_hint": False,
        "aliases": (
            "шахтный вход",
            "вход в шахту",
            "шахта",
            "шахте",
            "к шахте",
        ),
    }
    assert resolve_static_map_node("ремесленный городок") == {
        "node_id": "craft_town",
        "label": "Озёрный городок",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Озёрный городок",
        "zone_band": "safe",
        "settlement_kind": "town",
        "environment_hint": "lakeshore",
        "safe_rest_hint": True,
        "aliases": (
            "озёрный городок",
            "ремесленный городок",
            "городок у озера",
            "городок",
        ),
    }
    assert resolve_static_map_node("старое святилище") == {
        "node_id": "forgotten_shrine",
        "label": "Забытое святилище",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Край болот",
        "zone_band": "danger",
        "poi_kind": "shrine",
        "environment_hint": "marsh",
        "safe_rest_hint": False,
        "aliases": (
            "забытое святилище",
            "святилище в болотах",
            "старое святилище",
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
        "zone_band": "safe",
        "poi_kind": "fortified",
        "environment_hint": "fortified",
        "safe_rest_hint": False,
    }


def test_resolve_action_target_node_prefers_static_registry_for_enter_text() -> None:
    target = resolve_action_target_node(
        target_text="шахта",
        current_area_label="Разрушенный посёлок",
        action_kind="enter",
        known_node_ids={"mine_entrance"},
        require_known_static=True,
    )

    assert target == {
        "map_level": "interior",
        "node_type": "interior_entry",
        "node_id": "mine_entrance",
        "label": "Шахтный вход",
        "zone_label": "Разрушенный посёлок",
        "area_label": "Разрушенный посёлок",
        "zone_band": "danger",
        "poi_kind": "mine",
        "environment_hint": "ruined_frontier",
        "safe_rest_hint": False,
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
    assert route["source"] == "registry"
    assert route["traversal_kind"] == "road"
    assert route["risk_band"] == "low"
    assert route["terrain_hint"] == "open"
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
    assert route["source"] == "registry"
    assert route["traversal_kind"] == "gate_approach"
    assert route["risk_band"] == "low"
    assert route["terrain_hint"] == "fortified"
    assert route["target_node_type"] == "landmark"
    assert route["target_node_id"] == "fortress_gate"


def test_resolve_group_target_route_zone_to_interior_entry_enter_valid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "ruined_settlement",
            "label": "Разрушенный посёлок",
        },
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Разрушенный посёлок",
            "area_label": "Разрушенный посёлок",
        },
        action_kind="enter",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "enter_location"
    assert route["action_kind"] == "enter"
    assert route["source"] == "registry"
    assert route["traversal_kind"] == "entry"
    assert route["risk_band"] == "high"
    assert route["terrain_hint"] == "ruins"


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
            "node_id": "ruined_settlement",
            "label": "Разрушенный посёлок",
        },
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Разрушенный посёлок",
            "area_label": "Разрушенный посёлок",
        },
        action_kind="move",
    )

    assert route["allowed"] is False
    assert route["route_kind"] == "invalid"
    assert route["error"] == "Для `group move` допустимы только zone или landmark цели."


def test_resolve_group_target_route_safe_and_danger_links_use_expanded_registry() -> None:
    safe_route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
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
    danger_route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "marsh_edge",
            "label": "Край болот",
        },
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "forgotten_shrine",
            "label": "Забытое святилище",
            "zone_label": "Край болот",
            "area_label": "Край болот",
        },
        action_kind="move",
    )

    assert safe_route["allowed"] is True
    assert safe_route["route_kind"] == "landmark_move"
    assert safe_route["traversal_kind"] == "gate_approach"
    assert danger_route["allowed"] is True
    assert danger_route["target_node_id"] == "forgotten_shrine"
    assert danger_route["risk_band"] == "high"
    assert danger_route["terrain_hint"] == "marsh"


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
    assert route["source"] == "fallback"
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
    assert route["source"] == "fallback"
    assert route["traversal_kind"] == "entry"


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
    assert route["source"] == "fallback"
    assert route["risk_band"] == "medium"
    assert route["terrain_hint"] == "mixed"
