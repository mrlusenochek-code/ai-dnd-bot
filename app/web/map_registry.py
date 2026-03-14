from __future__ import annotations

from typing import Any


STATIC_MAP_NODES: tuple[dict[str, Any], ...] = (
    {
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
    },
    {
        "node_id": "eastern_bank",
        "label": "Восточный берег",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Восточный берег",
        "aliases": (
            "восточный берег",
            "берег",
            "берег реки",
        ),
    },
    {
        "node_id": "forest_road",
        "label": "Лесная дорога",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Лесная дорога",
        "aliases": (
            "лесная дорога",
            "лесная тропа",
            "дорога в лес",
        ),
    },
    {
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
    },
    {
        "node_id": "watchtower",
        "label": "Сторожевая башня",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Восточный берег",
        "aliases": (
            "сторожевая башня",
            "башня",
            "смотровая башня",
        ),
    },
    {
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
    },
)


STATIC_MAP_LINKS: tuple[dict[str, str], ...] = (
    {
        "from_node_id": "start_trakt",
        "to_node_id": "eastern_bank",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "eastern_bank",
        "to_node_id": "start_trakt",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "start_trakt",
        "to_node_id": "forest_road",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "forest_road",
        "to_node_id": "start_trakt",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "start_trakt",
        "to_node_id": "fortress_gate",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "fortress_gate",
        "to_node_id": "start_trakt",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "eastern_bank",
        "to_node_id": "watchtower",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "watchtower",
        "to_node_id": "eastern_bank",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "forest_road",
        "to_node_id": "mine_entrance",
        "action_kind": "enter",
        "route_kind": "enter_location",
        "link_kind": "entrance",
    },
)


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower()


def get_static_map_nodes() -> list[dict[str, Any]]:
    return [dict(node) for node in STATIC_MAP_NODES]


def get_static_map_links() -> list[dict[str, str]]:
    return [dict(link) for link in STATIC_MAP_LINKS]


def get_static_node(node_id: str | None) -> dict[str, Any] | None:
    normalized_id = _normalized_text(node_id)
    if not normalized_id:
        return None
    for node in STATIC_MAP_NODES:
        if _normalized_text(node.get("node_id")) == normalized_id:
            return dict(node)
    return None


def resolve_static_map_node(query_text: str | None) -> dict[str, Any] | None:
    normalized_query = _normalized_text(query_text)
    if not normalized_query:
        return None
    for node in STATIC_MAP_NODES:
        values = [node.get("node_id"), node.get("label")]
        values.extend(node.get("aliases") or ())
        if any(_normalized_text(value) == normalized_query for value in values):
            return dict(node)
    for node in STATIC_MAP_NODES:
        values = [node.get("label")]
        values.extend(node.get("aliases") or ())
        if any(_normalized_text(value) in normalized_query for value in values if _normalized_text(value)):
            return dict(node)
    return None


def find_static_link(from_node_id: str | None, to_node_id: str | None, action_kind: str | None) -> dict[str, str] | None:
    normalized_from = _normalized_text(from_node_id)
    normalized_to = _normalized_text(to_node_id)
    normalized_action = _normalized_text(action_kind)
    if not normalized_from or not normalized_to or not normalized_action:
        return None
    for link in STATIC_MAP_LINKS:
        if (
            _normalized_text(link.get("from_node_id")) == normalized_from
            and _normalized_text(link.get("to_node_id")) == normalized_to
            and _normalized_text(link.get("action_kind")) == normalized_action
        ):
            return dict(link)
    return None
