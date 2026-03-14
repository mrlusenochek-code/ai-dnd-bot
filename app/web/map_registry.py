from __future__ import annotations

from typing import Any


STATIC_MAP_NODES: tuple[dict[str, Any], ...] = (
    {
        "node_id": "start_trakt",
        "label": "Стартовый тракт",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Стартовый тракт",
        "zone_band": "safe",
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
        "zone_band": "safe",
        "aliases": (
            "восточный берег",
            "берег",
            "берег реки",
        ),
    },
    {
        "node_id": "craft_town",
        "label": "Озёрный городок",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Озёрный городок",
        "zone_band": "safe",
        "aliases": (
            "озёрный городок",
            "ремесленный городок",
            "городок у озера",
            "городок",
        ),
    },
    {
        "node_id": "forest_road",
        "label": "Лесная дорога",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Лесная дорога",
        "zone_band": "border",
        "aliases": (
            "лесная дорога",
            "лесная тропа",
            "дорога в лес",
        ),
    },
    {
        "node_id": "road_hamlet",
        "label": "Дорожный хутор",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Дорожный хутор",
        "zone_band": "border",
        "aliases": (
            "дорожный хутор",
            "хутор у тракта",
            "хутор",
        ),
    },
    {
        "node_id": "chapel_village",
        "label": "Часовенное село",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Часовенное село",
        "zone_band": "border",
        "aliases": (
            "часовенное село",
            "часовня",
            "село у часовни",
        ),
    },
    {
        "node_id": "forest_settlement",
        "label": "Лесной посёлок",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Лесной посёлок",
        "zone_band": "border",
        "aliases": (
            "лесной посёлок",
            "посёлок в лесу",
            "лесное селение",
        ),
    },
    {
        "node_id": "ruined_settlement",
        "label": "Разрушенный посёлок",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Разрушенный посёлок",
        "zone_band": "danger",
        "aliases": (
            "разрушенный посёлок",
            "руины посёлка",
            "развалины",
        ),
    },
    {
        "node_id": "marsh_edge",
        "label": "Край болот",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Край болот",
        "zone_band": "danger",
        "aliases": (
            "край болот",
            "болотная кромка",
            "болота",
        ),
    },
    {
        "node_id": "fortress_gate",
        "label": "Ворота крепости",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Стартовый тракт",
        "zone_band": "safe",
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
        "zone_band": "border",
        "aliases": (
            "сторожевая башня",
            "башня",
            "смотровая башня",
        ),
    },
    {
        "node_id": "old_fortress_edge",
        "label": "Край старой крепости",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Лесной посёлок",
        "zone_band": "danger",
        "aliases": (
            "старая крепость",
            "край старой крепости",
            "старые руины крепости",
        ),
    },
    {
        "node_id": "forgotten_shrine",
        "label": "Забытое святилище",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Край болот",
        "zone_band": "danger",
        "aliases": (
            "забытое святилище",
            "святилище в болотах",
            "старое святилище",
        ),
    },
    {
        "node_id": "mine_entrance",
        "label": "Шахтный вход",
        "node_type": "interior_entry",
        "map_level": "interior",
        "area_label": "Разрушенный посёлок",
        "zone_band": "danger",
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
        "to_node_id": "craft_town",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "craft_town",
        "to_node_id": "start_trakt",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "craft_town",
        "to_node_id": "eastern_bank",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "shore_road",
    },
    {
        "from_node_id": "eastern_bank",
        "to_node_id": "craft_town",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "shore_road",
    },
    {
        "from_node_id": "craft_town",
        "to_node_id": "fortress_gate",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "fortress_gate",
        "to_node_id": "craft_town",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
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
        "to_node_id": "road_hamlet",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "road_hamlet",
        "to_node_id": "forest_road",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "road_hamlet",
        "to_node_id": "chapel_village",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "branch_road",
    },
    {
        "from_node_id": "chapel_village",
        "to_node_id": "road_hamlet",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "branch_road",
    },
    {
        "from_node_id": "eastern_bank",
        "to_node_id": "chapel_village",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "shore_track",
    },
    {
        "from_node_id": "chapel_village",
        "to_node_id": "eastern_bank",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "shore_track",
    },
    {
        "from_node_id": "forest_road",
        "to_node_id": "forest_settlement",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "forest_track",
    },
    {
        "from_node_id": "forest_settlement",
        "to_node_id": "forest_road",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "forest_track",
    },
    {
        "from_node_id": "forest_road",
        "to_node_id": "ruined_settlement",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "old_road",
    },
    {
        "from_node_id": "ruined_settlement",
        "to_node_id": "forest_road",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "old_road",
    },
    {
        "from_node_id": "forest_settlement",
        "to_node_id": "old_fortress_edge",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "ruin_path",
    },
    {
        "from_node_id": "old_fortress_edge",
        "to_node_id": "forest_settlement",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "ruined_settlement",
        "to_node_id": "marsh_edge",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "bog_track",
    },
    {
        "from_node_id": "marsh_edge",
        "to_node_id": "ruined_settlement",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "bog_track",
    },
    {
        "from_node_id": "marsh_edge",
        "to_node_id": "forgotten_shrine",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "forgotten_shrine",
        "to_node_id": "marsh_edge",
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
    {
        "from_node_id": "ruined_settlement",
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


def get_obvious_linked_static_node_ids(node_id: str | None, *, limit: int = 1) -> list[str]:
    normalized_id = _normalized_text(node_id)
    if not normalized_id or limit <= 0:
        return []

    def _link_priority(link: dict[str, str]) -> tuple[int, int, str]:
        target_node = get_static_node(link.get("to_node_id"))
        target_type = _normalized_text((target_node or {}).get("node_type"))
        type_priority = {
            "landmark": 0,
            "interior_entry": 1,
            "building": 1,
            "zone": 2,
        }.get(target_type, 3)
        action_priority = 0 if _normalized_text(link.get("action_kind")) == "move" else 1
        return (type_priority, action_priority, _normalized_text(link.get("to_node_id")))

    obvious_ids: list[str] = []
    candidate_links = sorted(
        [link for link in STATIC_MAP_LINKS if _normalized_text(link.get("from_node_id")) == normalized_id],
        key=_link_priority,
    )
    for link in candidate_links:
        target_node_id = str(link.get("to_node_id") or "").strip()
        if not target_node_id or target_node_id in obvious_ids:
            continue
        if get_static_node(target_node_id) is None:
            continue
        obvious_ids.append(target_node_id)
        if len(obvious_ids) >= limit:
            break
    return obvious_ids
