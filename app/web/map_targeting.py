from __future__ import annotations

from typing import Any, Optional

from app.web.session_state import _map_position_area_label, _normalize_map_target_node
from app.web.ws_gameplay import infer_zone_from_action


_LANDMARK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("ворот", "ворота"),
    ("подвал", "подвал"),
    ("фонтан", "фонтан"),
    ("башн", "башня"),
    ("двер", "дверь"),
)


def _extract_enter_target_label(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    lowered = raw.lower()
    prefixes = (
        "захожу в ",
        "вхожу в ",
        "войти в ",
        "иду в ",
        "enter ",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return raw[len(prefix):].strip()
    return raw


def resolve_action_target_node(
    *,
    action_text: str = "",
    target_text: str = "",
    current_map_position: dict[str, Any] | None = None,
    current_area_label: str = "стартовая локация",
    action_kind: str = "move",
    target_node: dict[str, Any] | str | None = None,
) -> dict[str, Any] | None:
    normalized_action_kind = str(action_kind or "move").strip().lower() or "move"
    current_area = str(current_area_label or "стартовая локация").strip() or "стартовая локация"

    if target_node is not None:
        return _normalize_map_target_node(target_node)

    text = str(target_text or action_text or "").strip()
    if not text:
        return None
    lowered = text.lower()

    if normalized_action_kind == "enter":
        target_label = _extract_enter_target_label(text) or text
        return {
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": target_label[:120],
            "label": target_label[:80],
            "zone_label": current_area[:80],
            "area_label": current_area[:80],
        }

    inferred_zone_label = infer_zone_from_action(text, current_area)
    current_parent_area = _map_position_area_label(current_map_position, fallback=current_area)
    for stem, label in _LANDMARK_PATTERNS:
        if stem in lowered:
            return {
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": label,
                "label": label,
                "zone_label": current_parent_area[:80],
                "area_label": current_parent_area[:80],
            }

    zone_label = str(inferred_zone_label or current_area).strip() or current_area
    return {
        "map_level": "region",
        "node_type": "zone",
        "node_id": zone_label[:120],
        "label": zone_label[:80],
        "zone_label": zone_label[:80],
        "area_label": zone_label[:80],
    }


def validate_group_target_transition(
    *,
    action_kind: str,
    target_node: dict[str, Any] | str | None,
) -> tuple[bool, Optional[str]]:
    target = _normalize_map_target_node(target_node)
    if not target:
        return False, "Не удалось определить цель перемещения."

    action = str(action_kind or "").strip().lower()
    node_type = str(target.get("node_type") or "zone").strip().lower()

    if action == "move":
        if node_type in {"zone", "landmark"}:
            return True, None
        return False, "Для `group move` допустимы только zone или landmark цели."

    if action == "enter":
        if node_type in {"interior_entry", "building"}:
            return True, None
        return False, "Для `group enter` нужна interior/building цель, а не обычная zone."

    return False, "Неизвестный тип перехода группы."
