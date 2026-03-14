import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Session
from app.web.map_registry import (
    STATIC_MAP_NODES,
    get_current_node_context_actions,
    get_obvious_linked_static_node_ids,
    get_static_navigation_options,
    get_static_node_detail,
    get_static_node,
    get_static_node_context,
    get_static_node_inspect_result,
    get_static_node_service_result,
    get_static_node_services,
)
from app.web.utils import as_int


DEFAULT_GROUP_ID = "main"
_MAP_KNOWLEDGE_KIND_ORDER = {"known": 1, "discovered": 2, "visited": 3}


def _ensure_settings(sess: Session) -> dict:
    if not sess.settings or not isinstance(sess.settings, dict):
        sess.settings = {}
    return sess.settings


def settings_get(sess: Session, key: str, default: Any) -> Any:
    st = _ensure_settings(sess)
    return st.get(key, default)


def settings_set(sess: Session, key: str, value: Any) -> None:
    st = _ensure_settings(sess)
    st[key] = value
    try:
        flag_modified(sess, "settings")
    except AttributeError:
        # Some tests use lightweight fake sessions without SQLAlchemy state.
        pass


def _get_ready_map(sess: Session) -> dict[str, bool]:
    return settings_get(sess, "ready", {}) or {}


def _set_ready(sess: Session, player_id: uuid.UUID, value: bool) -> None:
    m = dict(_get_ready_map(sess))
    m[str(player_id)] = bool(value)
    settings_set(sess, "ready", m)


def _get_init_map(sess: Session) -> dict[str, int]:
    raw = settings_get(sess, "initiative", {}) or {}
    out: dict[str, int] = {}
    for k, v in raw.items():
        out[str(k)] = as_int(v, 0)
    return out


def _set_init_value(sess: Session, player_id: uuid.UUID, value: int) -> None:
    m = dict(_get_init_map(sess))
    m[str(player_id)] = int(value)
    settings_set(sess, "initiative", m)


def _initiative_fixed(sess: Session) -> bool:
    return bool(settings_get(sess, "initiative_fixed", False))


def _get_initiative_order(sess: Session) -> list[uuid.UUID]:
    raw = settings_get(sess, "initiative_order", []) or []
    out: list[uuid.UUID] = []
    for x in raw:
        try:
            if isinstance(x, uuid.UUID):
                out.append(x)
            else:
                out.append(uuid.UUID(str(x)))
        except Exception:
            continue
    return out


def _set_initiative_order(sess: Session, order: list[uuid.UUID]) -> None:
    settings_set(sess, "initiative_order", [str(x) for x in order])


def _get_last_seen_map(sess: Session) -> dict[str, str]:
    raw = settings_get(sess, "last_seen", {}) or {}
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if k is None or v is None:
            continue
        out[str(k)] = str(v)
    return out


def _touch_last_seen(sess: Session, player_id: uuid.UUID) -> None:
    m = dict(_get_last_seen_map(sess))
    m[str(player_id)] = datetime.now(timezone.utc).isoformat()
    settings_set(sess, "last_seen", m)


def _default_map_position(zone_label: str = "стартовая локация") -> dict[str, Any]:
    label = str(zone_label or "").strip() or "стартовая локация"
    return {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": label[:80],
        "label": label[:80],
    }


def _default_map_level_for_node_type(node_type: str) -> str:
    normalized = str(node_type or "").strip().lower()
    if normalized == "landmark":
        return "landmark"
    if normalized in {"building", "interior_entry"}:
        return "interior"
    return "region"


def _normalize_map_position(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, str):
        return _default_map_position(raw)

    if not isinstance(raw, dict):
        return None

    map_level = str(raw.get("map_level") or "").strip().lower()
    node_type = str(raw.get("node_type") or "").strip().lower()
    node_id = str(raw.get("node_id") or "").strip()
    label = str(raw.get("label") or "").strip()
    area_label = str(raw.get("area_label") or "").strip()

    if not node_type:
        node_type = "zone"
    if node_type not in {"zone", "landmark", "building", "interior_entry"}:
        node_type = "zone"
    if not map_level:
        map_level = _default_map_level_for_node_type(node_type)
    if not node_id and label:
        node_id = label
    if not label and node_id:
        label = node_id

    if not node_id:
        return None

    normalized = {
        "v": 1,
        "map_level": map_level[:32],
        "node_type": node_type[:32],
        "node_id": node_id[:120],
        "label": label[:80] or node_id[:80],
    }
    if area_label:
        normalized["area_label"] = area_label[:80]
    return normalized


def _map_position_area_label(pos: Any, fallback: str = "стартовая локация") -> str:
    normalized = _normalize_map_position(pos)
    fallback_label = str(fallback or "").strip() or "стартовая локация"
    if not normalized:
        return fallback_label[:80]

    node_type = str(normalized.get("node_type") or "").strip().lower()
    if node_type == "zone":
        return _format_map_position_label(normalized)

    area_label = str(normalized.get("area_label") or "").strip()
    if area_label:
        return area_label[:80]

    return _format_map_position_label(normalized)


def _normalize_map_target_node(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, str):
        pos = _default_map_position(raw)
        return {**pos, "zone_label": pos["label"]}

    pos = _normalize_map_position(raw)
    if not pos:
        return None

    zone_label = ""
    area_label = ""
    if isinstance(raw, dict):
        zone_label = str(raw.get("zone_label") or "").strip()
        area_label = str(raw.get("area_label") or "").strip()
    if not zone_label:
        zone_label = str(pos.get("label") or pos.get("node_id") or "").strip()
    if not zone_label:
        return None

    target = {
        **pos,
        "zone_label": zone_label[:80],
    }
    if area_label:
        target["area_label"] = area_label[:80]
    return target


def _apply_map_position_transition(
    current_map_position: Any,
    target_node: Any,
    movement_reason: str | None = None,
) -> tuple[dict[str, Any] | None, str, bool, str | None]:
    current_pos = _normalize_map_position(current_map_position)
    current_zone = _map_position_area_label(current_pos)
    target = _normalize_map_target_node(target_node)
    if not target:
        return current_pos, current_zone, False, "invalid_target_node"

    target_node_type = str(target.get("node_type") or "zone").strip().lower()
    target_label = str(target.get("label") or target.get("node_id") or "").strip()
    current_area_label = _map_position_area_label(current_pos, fallback=current_zone)
    if target_node_type == "zone":
        next_area_label = target_label
    else:
        next_area_label = str(target.get("area_label") or "").strip() or current_area_label or target_label

    next_position = {
        "v": 1,
        "map_level": str(target.get("map_level") or "region"),
        "node_type": str(target.get("node_type") or "zone"),
        "node_id": str(target.get("node_id") or "")[:120],
        "label": str(target.get("label") or "")[:80],
        "area_label": next_area_label[:80] or target_label[:80] or current_zone,
    }
    next_zone = _map_position_area_label(next_position, fallback=current_zone)
    _ = movement_reason
    return next_position, next_zone[:80], True, None


def _format_map_position_label(pos: Any) -> str:
    normalized = _normalize_map_position(pos)
    if not normalized:
        return "стартовая локация"
    label = str(normalized.get("label") or "").strip()
    if label:
        return label[:80]
    node_id = str(normalized.get("node_id") or "").strip()
    return node_id[:80] or "стартовая локация"


def _format_map_position_prompt(pos: Any) -> str:
    normalized = _normalize_map_position(pos)
    if not normalized:
        return "стартовая локация"
    label = _format_map_position_label(normalized)
    map_level = str(normalized.get("map_level") or "").strip().lower()
    node_type = str(normalized.get("node_type") or "").strip().lower()
    node_id = str(normalized.get("node_id") or "").strip()
    extras: list[str] = []
    if map_level and map_level != "region":
        extras.append(f"level={map_level}")
    if node_type and node_type != "zone":
        extras.append(f"type={node_type}")
    if node_id and node_id != label:
        extras.append(f"node={node_id[:80]}")
    if not extras:
        return label
    return f"{label} [{', '.join(extras)}]"


def _get_map_positions(sess: Session) -> dict[str, dict[str, Any]]:
    groups = _get_group_states(sess)
    if groups:
        out: dict[str, dict[str, Any]] = {}
        for group in groups.values():
            pos = _normalize_map_position(group.get("current_map_position"))
            if not pos:
                continue
            for pid in group.get("player_ids", []):
                out[str(pid)] = dict(pos)
        if out:
            return out
    return _raw_player_map_positions(sess)


def _get_player_map_position(sess: Session, player_id: uuid.UUID | str) -> dict[str, Any] | None:
    group_id = _get_player_group_id(sess, player_id)
    if group_id:
        group = _get_group_states(sess).get(group_id)
        if group:
            pos = _normalize_map_position(group.get("current_map_position"))
            if pos:
                return pos

    positions = _raw_player_map_positions(sess)
    return positions.get(str(player_id))


def _get_player_position_context(sess: Session, player_id: uuid.UUID | str) -> dict[str, Any]:
    pid = str(player_id)
    group_id = _get_player_group_id(sess, pid)
    if group_id:
        group = _get_group_states(sess).get(group_id)
        if group:
            pos = _normalize_map_position(group.get("current_map_position"))
            if pos:
                return {
                    "group_id": group_id,
                    "zone_label": str(group.get("area_label") or _map_position_area_label(pos)),
                    "map_position": dict(pos),
                }

    pos = _get_player_map_position(sess, pid)
    if pos:
        return {
            "group_id": None,
            "zone_label": _map_position_area_label(pos),
            "map_position": dict(pos),
        }

    legacy_positions = _raw_pc_positions(sess)
    zone_label = "стартовая локация"
    raw_zone = legacy_positions.get(pid)
    zone_text = str(raw_zone or "").strip()
    if zone_text:
        zone_label = zone_text[:80]
    return {
        "group_id": None,
        "zone_label": zone_label,
        "map_position": None,
    }


def _get_player_position_label(sess: Session, player_id: uuid.UUID | str) -> str:
    return str(_get_player_position_context(sess, player_id).get("zone_label") or "стартовая локация")


def _map_position_identity(pos: Any) -> tuple[str, str, str] | None:
    normalized = _normalize_map_position(pos)
    if not normalized:
        return None
    map_level = str(normalized.get("map_level") or "").strip().lower()
    node_type = str(normalized.get("node_type") or "").strip().lower()
    node_id = str(normalized.get("node_id") or "").strip()
    if not map_level or not node_type or not node_id:
        return None
    return (map_level, node_type, node_id)


def _map_position_identity_equals(left: Any, right: Any) -> bool:
    left_identity = _map_position_identity(left)
    right_identity = _map_position_identity(right)
    return bool(left_identity and right_identity and left_identity == right_identity)


def _raw_player_map_positions(sess: Session) -> dict[str, dict[str, Any]]:
    raw = settings_get(sess, "map_positions", {}) or {}
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if k is None or v is None:
            continue
        pid = str(k).strip()
        pos = _normalize_map_position(v)
        if pid and pos:
            out[pid] = pos
    return out


def _raw_pc_positions(sess: Session) -> dict[str, str]:
    raw = settings_get(sess, "pc_positions", {}) or {}
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if k is None or v is None:
            continue
        pid = str(k).strip()
        zone = str(v).strip()
        if pid and zone:
            out[pid] = zone[:80]
    return out


def _normalize_group_status(raw: Any) -> str:
    status = str(raw or "idle").strip().lower()
    if status == "split-ready":
        return "idle"
    if status not in {"idle", "waiting", "camping", "moving_intent", "moving", "paused_travel"}:
        return "idle"
    return status


def _normalize_group_wait_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    reason = str(raw.get("reason") or "").strip()
    source = str(raw.get("source") or "manual").strip() or "manual"
    requested_by = str(raw.get("requested_by") or "").strip()
    started_at = str(raw.get("started_at") or "").strip()
    state: dict[str, Any] = {"source": source[:40]}
    if reason:
        state["reason"] = reason[:240]
    if requested_by:
        state["requested_by"] = requested_by[:80]
    if started_at:
        state["started_at"] = started_at[:80]
    return state


def _normalize_group_camp_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    reason = str(raw.get("reason") or "").strip()
    source = str(raw.get("source") or "manual").strip() or "manual"
    requested_by = str(raw.get("requested_by") or "").strip()
    started_at = str(raw.get("started_at") or "").strip()
    state: dict[str, Any] = {"source": source[:40]}
    if reason:
        state["reason"] = reason[:240]
    if requested_by:
        state["requested_by"] = requested_by[:80]
    if started_at:
        state["started_at"] = started_at[:80]
    return state


def _normalize_group_movement_mode(raw: Any) -> str:
    mode = str(raw or "normal").strip().lower()
    if mode not in {"normal", "cautious", "fast"}:
        return "normal"
    return mode


def _normalize_group_travel_activity(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    activity = str(raw.get("activity") or raw.get("name") or "").strip().lower()
    if activity not in {"observe", "track", "forage", "navigate", "avoid_danger"}:
        return None
    assigned_actor_id = str(raw.get("assigned_actor_id") or raw.get("assigned_player_id") or "").strip()
    source = str(raw.get("source") or "manual").strip() or "manual"
    state: dict[str, Any] = {
        "activity": activity,
        "source": source[:40],
    }
    if assigned_actor_id:
        state["assigned_actor_id"] = assigned_actor_id[:80]
    return state


def _normalize_group_movement_intent(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    target_node = _normalize_map_target_node(raw.get("target_node") or raw.get("target"))
    target_label = str(raw.get("target_label") or "").strip()
    if not target_label and target_node:
        target_label = str(target_node.get("label") or target_node.get("node_id") or "").strip()
    if not target_label and isinstance(raw.get("target"), str):
        target_label = str(raw.get("target") or "").strip()
    movement_mode = _normalize_group_movement_mode(raw.get("movement_mode") or raw.get("mode"))
    movement_kind = str(raw.get("movement_kind") or raw.get("kind") or "move").strip().lower() or "move"
    source = str(raw.get("source") or "manual").strip() or "manual"
    active = bool(raw.get("active", True))
    travel_activity = _normalize_group_travel_activity(raw.get("travel_activity"))
    route_kind = str(raw.get("route_kind") or "").strip().lower()
    route_source = str(raw.get("route_source") or raw.get("source_kind") or "").strip().lower()
    traversal_kind = str(raw.get("traversal_kind") or "").strip().lower()
    risk_band = str(raw.get("risk_band") or "").strip().lower()
    terrain_hint = str(raw.get("terrain_hint") or "").strip().lower()
    action_kind = str(raw.get("action_kind") or "").strip().lower()
    allowed = bool(raw.get("allowed", True))
    travel_tags_raw = raw.get("travel_tags")
    travel_tags = [str(tag).strip().lower()[:40] for tag in travel_tags_raw if str(tag).strip()] if isinstance(travel_tags_raw, list) else []
    if not target_label and not target_node:
        return None
    state: dict[str, Any] = {
        "target_label": target_label[:80],
        "movement_mode": movement_mode[:40],
        "movement_kind": movement_kind[:40],
        "action_kind": (action_kind[:40] or movement_kind[:40] or "move"),
        "source": source[:40],
        "active": active,
        "allowed": allowed,
    }
    if route_kind:
        state["route_kind"] = route_kind[:40]
    if route_source:
        state["route_source"] = route_source[:40]
    if traversal_kind:
        state["traversal_kind"] = traversal_kind[:40]
    if risk_band:
        state["risk_band"] = risk_band[:40]
    if terrain_hint:
        state["terrain_hint"] = terrain_hint[:40]
    if travel_tags:
        state["travel_tags"] = travel_tags
    if target_node:
        state["target_node"] = target_node
        state["target_node_type"] = str(target_node.get("node_type") or "zone")[:32]
        state["target_node_id"] = str(target_node.get("node_id") or "")[:120]
    if travel_activity:
        state["travel_activity"] = travel_activity
    return state


def _normalize_group_route_summary(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    target_node = _normalize_map_target_node(raw.get("target_node") or raw.get("target"))
    next_map_position = _normalize_map_position(raw.get("next_map_position"))
    route_kind = str(raw.get("route_kind") or "").strip().lower()
    action_kind = str(raw.get("action_kind") or raw.get("movement_kind") or "").strip().lower() or "move"
    allowed = bool(raw.get("allowed", True))
    target_label = str(raw.get("target_label") or "").strip()
    target_node_type = str(raw.get("target_node_type") or "").strip().lower()
    target_node_id = str(raw.get("target_node_id") or "").strip()
    next_zone_label = str(raw.get("next_zone_label") or "").strip()
    error = str(raw.get("error") or "").strip()
    pause_hint = str(raw.get("pause_hint") or "").strip().lower()
    route_source = str(raw.get("source") or raw.get("route_source") or "").strip().lower()
    traversal_kind = str(raw.get("traversal_kind") or "").strip().lower()
    risk_band = str(raw.get("risk_band") or "").strip().lower()
    terrain_hint = str(raw.get("terrain_hint") or "").strip().lower()
    travel_tags_raw = raw.get("travel_tags")
    travel_tags = [str(tag).strip().lower()[:40] for tag in travel_tags_raw if str(tag).strip()] if isinstance(travel_tags_raw, list) else []
    if target_node:
        if not target_label:
            target_label = str(target_node.get("label") or target_node.get("node_id") or "").strip()
        if not target_node_type:
            target_node_type = str(target_node.get("node_type") or "").strip().lower()
        if not target_node_id:
            target_node_id = str(target_node.get("node_id") or "").strip()
    if not target_label and not target_node:
        return None
    summary: dict[str, Any] = {
        "allowed": allowed,
        "route_kind": route_kind[:40] or ("invalid" if not allowed else action_kind[:40]),
        "action_kind": action_kind[:40],
        "target_label": target_label[:80],
    }
    if target_node:
        summary["target_node"] = target_node
    if target_node_type:
        summary["target_node_type"] = target_node_type[:32]
    if target_node_id:
        summary["target_node_id"] = target_node_id[:120]
    if next_map_position:
        summary["next_map_position"] = next_map_position
    if next_zone_label:
        summary["next_zone_label"] = next_zone_label[:80]
    if route_source:
        summary["source"] = route_source[:40]
    if traversal_kind:
        summary["traversal_kind"] = traversal_kind[:40]
    if risk_band:
        summary["risk_band"] = risk_band[:40]
    if terrain_hint:
        summary["terrain_hint"] = terrain_hint[:40]
    if travel_tags:
        summary["travel_tags"] = travel_tags
    if error:
        summary["error"] = error[:240]
    if pause_hint:
        summary["pause_hint"] = pause_hint[:40]
    return summary


def _normalize_group_pause_reason(raw: Any) -> str | None:
    reason = str(raw or "").strip().lower()
    if reason not in {"manual", "point_of_interest_reached", "target_requires_enter", "route_blocked", "event_pending"}:
        return None
    return reason


def _normalize_group_pause_details(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    details: dict[str, Any] = {}
    for key, value in raw.items():
        normalized_key = str(key or "").strip()[:80]
        if not normalized_key:
            continue
        if isinstance(value, bool):
            details[normalized_key] = value
        elif isinstance(value, int):
            details[normalized_key] = value
        elif value is None:
            continue
        else:
            details[normalized_key] = str(value).strip()[:240]
    return details or None


def _normalize_group_travel_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    route_summary = _normalize_group_route_summary(raw.get("route_summary") or raw.get("route"))
    target_node = _normalize_map_target_node(raw.get("target_node") or ((route_summary or {}).get("target_node")))
    started_from = _normalize_map_position(raw.get("started_from"))
    movement_mode = _normalize_group_movement_mode(raw.get("movement_mode") or raw.get("mode"))
    travel_activity = _normalize_group_travel_activity(raw.get("travel_activity"))
    phase = str(raw.get("phase") or raw.get("status") or "in_transit").strip().lower() or "in_transit"
    progress_kind = str(raw.get("progress_kind") or "route").strip().lower() or "route"
    progress_step = max(0, as_int(raw.get("progress_step"), 0))
    active = bool(raw.get("active"))
    paused = bool(raw.get("paused"))
    pause_reason = _normalize_group_pause_reason(raw.get("pause_reason"))
    pause_details = _normalize_group_pause_details(raw.get("pause_details"))
    resume_allowed = bool(raw.get("resume_allowed", True))
    if not route_summary or not target_node or not started_from:
        return None
    state: dict[str, Any] = {
        "active": active,
        "phase": phase[:40],
        "route_summary": route_summary,
        "started_from": started_from,
        "target_node": target_node,
        "progress_kind": progress_kind[:40],
        "progress_step": progress_step,
        "movement_mode": movement_mode[:40],
        "paused": paused,
        "resume_allowed": resume_allowed,
    }
    if pause_reason:
        state["pause_reason"] = pause_reason
    if pause_details:
        state["pause_details"] = pause_details
    if travel_activity:
        state["travel_activity"] = travel_activity
    return state


def _normalize_group_travel_resolution(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    resolution_kind = str(raw.get("resolution_kind") or raw.get("kind") or "").strip().lower()
    if resolution_kind not in {"confirm_enter", "inspect_target", "bypass", "resolve_pause"}:
        return None
    pause_reason = _normalize_group_pause_reason(raw.get("pause_reason"))
    target_label = str(raw.get("target_label") or "").strip()
    source = str(raw.get("source") or "manual").strip() or "manual"
    details = _normalize_group_pause_details(raw.get("details") or raw.get("resolution_details"))
    summary: dict[str, Any] = {
        "resolution_kind": resolution_kind,
        "source": source[:40],
    }
    if pause_reason:
        summary["pause_reason"] = pause_reason
    if target_label:
        summary["target_label"] = target_label[:80]
    if details:
        summary["details"] = details
    return summary


def _normalize_group_travel_event(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    event_key = str(raw.get("event_key") or "").strip().lower()
    if event_key not in {"roadside_finding", "tracks_or_signs", "lost_traveler", "blocked_path", "ominous_quiet"}:
        return None
    event_id = str(raw.get("event_id") or "").strip()
    summary = str(raw.get("summary") or "").strip()
    route_snapshot = _normalize_group_route_summary(raw.get("route_snapshot") or raw.get("route"))
    if not event_id or not summary or not route_snapshot:
        return None
    resolution = str(raw.get("resolution") or "").strip().lower()
    if resolution not in {"", "resolve", "ignore"}:
        resolution = ""
    event: dict[str, Any] = {
        "event_id": event_id[:80],
        "event_key": event_key,
        "event_type": str(raw.get("event_type") or "roadside_hook")[:40] or "roadside_hook",
        "summary": summary[:400],
        "route_snapshot": route_snapshot,
        "source": str(raw.get("source") or "travel")[:40] or "travel",
        "active": bool(raw.get("active", True)),
        "resolved": bool(raw.get("resolved", False)),
    }
    if resolution:
        event["resolution"] = resolution
    return event


def _normalize_group_travel_event_outcome(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    outcome_id = str(raw.get("outcome_id") or "").strip()
    event_key = str(raw.get("event_key") or "").strip().lower()
    if event_key not in {"roadside_finding", "tracks_or_signs", "lost_traveler", "blocked_path", "ominous_quiet"}:
        return None
    event_type = str(raw.get("event_type") or "roadside_hook").strip() or "roadside_hook"
    outcome_type = str(raw.get("outcome_type") or "").strip().lower()
    if outcome_type not in {
        "finding_note",
        "route_hint",
        "guidance_note",
        "obstacle_cleared",
        "route_still_blocked",
        "warning_note",
        "ignored_event",
    }:
        return None
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or "").strip()
    if not outcome_id or not summary or not result_summary:
        return None
    source = str(raw.get("source") or "travel").strip() or "travel"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    applied_effects_raw = raw.get("applied_effects")
    applied_effects = (
        [str(item).strip()[:120] for item in applied_effects_raw if str(item or "").strip()]
        if isinstance(applied_effects_raw, list)
        else []
    )
    route_snapshot = _normalize_group_route_summary(raw.get("route_snapshot") or raw.get("route"))
    outcome: dict[str, Any] = {
        "outcome_id": outcome_id[:80],
        "event_key": event_key,
        "event_type": event_type[:40],
        "outcome_type": outcome_type[:40],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "applied_effects": applied_effects,
        "source": source[:40],
    }
    if resolved_at:
        outcome["resolved_at"] = resolved_at[:80]
    if route_snapshot:
        outcome["route_snapshot"] = route_snapshot
    return outcome


def _normalize_map_knowledge_kind(raw: Any) -> str:
    kind = str(raw or "known").strip().lower()
    if kind not in _MAP_KNOWLEDGE_KIND_ORDER:
        return "known"
    return kind


def _normalize_player_map_knowledge_record(node_id: str, raw: Any) -> dict[str, Any] | None:
    normalized_node_id = str(node_id or "").strip()
    if not normalized_node_id:
        return None
    if isinstance(raw, str):
        raw = {"knowledge_kind": raw}
    if not isinstance(raw, dict):
        return None
    knowledge_kind = _normalize_map_knowledge_kind(raw.get("knowledge_kind"))
    source = str(raw.get("source") or "manual").strip() or "manual"
    discovered_order = max(0, as_int(raw.get("discovered_order"), 0))
    discovered_at = str(raw.get("discovered_at") or "").strip()
    record: dict[str, Any] = {
        "node_id": normalized_node_id[:120],
        "knowledge_kind": knowledge_kind,
        "source": source[:40],
    }
    if discovered_order > 0:
        record["discovered_order"] = discovered_order
    if discovered_at:
        record["discovered_at"] = discovered_at[:80]
    return record


def _raw_player_map_knowledge(sess: Session) -> dict[str, dict[str, Any]]:
    raw = settings_get(sess, "player_map_knowledge", {}) or {}
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return out
    for player_id, records in raw.items():
        pid = str(player_id or "").strip()
        if not pid or not isinstance(records, dict):
            continue
        player_records: dict[str, Any] = {}
        for node_id, value in records.items():
            normalized = _normalize_player_map_knowledge_record(str(node_id), value)
            if normalized:
                player_records[normalized["node_id"]] = normalized
        if player_records:
            out[pid] = player_records
    return out


def _persist_player_map_knowledge(sess: Session, knowledge_map: dict[str, dict[str, Any]]) -> None:
    payload: dict[str, dict[str, Any]] = {}
    for player_id, records in knowledge_map.items():
        pid = str(player_id or "").strip()
        if not pid or not isinstance(records, dict):
            continue
        normalized_records: dict[str, Any] = {}
        for node_id, value in records.items():
            normalized = _normalize_player_map_knowledge_record(str(node_id), value)
            if normalized:
                normalized_records[normalized["node_id"]] = normalized
        if normalized_records:
            payload[pid] = normalized_records
    settings_set(sess, "player_map_knowledge", payload)


def _normalize_player_map_reveal_record(node_id: str, raw: Any) -> dict[str, Any] | None:
    normalized_node_id = str(node_id or "").strip()
    if not normalized_node_id:
        return None
    if isinstance(raw, str):
        raw = {"source": raw}
    if not isinstance(raw, dict):
        return None
    source = str(raw.get("source") or "manual").strip() or "manual"
    revealed_order = max(0, as_int(raw.get("revealed_order"), 0))
    revealed_at = str(raw.get("revealed_at") or "").strip()
    record: dict[str, Any] = {
        "node_id": normalized_node_id[:120],
        "source": source[:40],
    }
    if revealed_order > 0:
        record["revealed_order"] = revealed_order
    if revealed_at:
        record["revealed_at"] = revealed_at[:80]
    return record


def _raw_player_map_reveals(sess: Session) -> dict[str, dict[str, Any]]:
    raw = settings_get(sess, "player_map_reveals", {}) or {}
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return out
    for player_id, records in raw.items():
        pid = str(player_id or "").strip()
        if not pid or not isinstance(records, dict):
            continue
        player_records: dict[str, Any] = {}
        for node_id, value in records.items():
            normalized = _normalize_player_map_reveal_record(str(node_id), value)
            if normalized:
                player_records[normalized["node_id"]] = normalized
        if player_records:
            out[pid] = player_records
    return out


def _persist_player_map_reveals(sess: Session, reveal_map: dict[str, dict[str, Any]]) -> None:
    payload: dict[str, dict[str, Any]] = {}
    for player_id, records in reveal_map.items():
        pid = str(player_id or "").strip()
        if not pid or not isinstance(records, dict):
            continue
        normalized_records: dict[str, Any] = {}
        for node_id, value in records.items():
            normalized = _normalize_player_map_reveal_record(str(node_id), value)
            if normalized:
                normalized_records[normalized["node_id"]] = normalized
        if normalized_records:
            payload[pid] = normalized_records
    settings_set(sess, "player_map_reveals", payload)


def _default_known_static_node_ids_for_position(position: dict[str, Any] | None) -> list[str]:
    pos = _normalize_map_position(position)
    if not pos:
        return []
    known_node_ids: list[str] = []
    current_node_id = str(pos.get("node_id") or "").strip()
    current_static = get_static_node(current_node_id)
    if current_static:
        known_node_ids.append(str(current_static.get("node_id") or ""))
        current_area_label = str(current_static.get("area_label") or "").strip().lower()
        for node in STATIC_MAP_NODES:
            if (
                node.get("node_type") == "landmark"
                and str(node.get("area_label") or "").strip().lower() == current_area_label
            ):
                landmark_node_id = str(node.get("node_id") or "").strip()
                if landmark_node_id and landmark_node_id not in known_node_ids:
                    known_node_ids.append(landmark_node_id)
                    break
    return [node_id for node_id in known_node_ids if node_id]


def _default_revealed_static_node_ids_for_position(position: dict[str, Any] | None) -> list[str]:
    pos = _normalize_map_position(position)
    if not pos:
        return []
    current_node_id = str(pos.get("node_id") or "").strip()
    current_static = get_static_node(current_node_id)
    if not current_static:
        return []
    revealed_node_ids = [str(current_static.get("node_id") or "").strip()]
    for node_id in get_obvious_linked_static_node_ids(current_node_id, limit=1):
        if node_id and node_id not in revealed_node_ids:
            revealed_node_ids.append(node_id)
    return [node_id for node_id in revealed_node_ids if node_id]


def grant_player_map_knowledge(
    sess: Session,
    player_id: uuid.UUID | str,
    node_id: str,
    *,
    knowledge_kind: str = "known",
    source: str = "manual",
) -> dict[str, Any] | None:
    pid = str(player_id or "").strip()
    normalized_node_id = str(node_id or "").strip()
    if not pid or not normalized_node_id:
        return None
    normalized_kind = _normalize_map_knowledge_kind(knowledge_kind)
    knowledge_map = _raw_player_map_knowledge(sess)
    player_records = dict(knowledge_map.get(pid) or {})
    existing = _normalize_player_map_knowledge_record(normalized_node_id, player_records.get(normalized_node_id))
    next_order = max([as_int(record.get("discovered_order"), 0) for record in player_records.values()] or [0]) + 1
    if existing:
        existing_rank = _MAP_KNOWLEDGE_KIND_ORDER.get(existing["knowledge_kind"], 1)
        next_rank = _MAP_KNOWLEDGE_KIND_ORDER.get(normalized_kind, 1)
        if next_rank >= existing_rank:
            existing["knowledge_kind"] = normalized_kind
        existing["source"] = str(source or existing.get("source") or "manual")[:40] or "manual"
        if "discovered_order" not in existing:
            existing["discovered_order"] = next_order
        if "discovered_at" not in existing:
            existing["discovered_at"] = datetime.now(timezone.utc).isoformat()
        player_records[normalized_node_id] = existing
    else:
        player_records[normalized_node_id] = {
            "node_id": normalized_node_id[:120],
            "knowledge_kind": normalized_kind,
            "source": str(source or "manual")[:40] or "manual",
            "discovered_order": next_order,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
    knowledge_map[pid] = player_records
    _persist_player_map_knowledge(sess, knowledge_map)
    return dict(player_records[normalized_node_id])


def get_player_map_knowledge(sess: Session, player_id: uuid.UUID | str) -> dict[str, dict[str, Any]]:
    pid = str(player_id or "").strip()
    if not pid:
        return {}
    knowledge_map = _raw_player_map_knowledge(sess)
    player_records = dict(knowledge_map.get(pid) or {})
    if not player_records:
        current_position = _get_player_map_position(sess, pid)
        for node_id in _default_known_static_node_ids_for_position(current_position if isinstance(current_position, dict) else None):
            grant_player_map_knowledge(sess, pid, node_id, knowledge_kind="known", source="seed")
        knowledge_map = _raw_player_map_knowledge(sess)
        player_records = dict(knowledge_map.get(pid) or {})
    return {
        node_id: dict(record)
        for node_id, record in player_records.items()
        if _normalize_player_map_knowledge_record(node_id, record)
    }


def get_player_known_node_ids(sess: Session, player_id: uuid.UUID | str) -> list[str]:
    knowledge = get_player_map_knowledge(sess, player_id)
    return sorted(knowledge.keys())


def has_player_map_knowledge(
    sess: Session,
    player_id: uuid.UUID | str,
    node_id: str,
    *,
    minimum_kind: str = "known",
) -> bool:
    normalized_node_id = str(node_id or "").strip()
    if not normalized_node_id:
        return False
    knowledge = get_player_map_knowledge(sess, player_id)
    record = knowledge.get(normalized_node_id)
    if not record:
        return False
    current_rank = _MAP_KNOWLEDGE_KIND_ORDER.get(_normalize_map_knowledge_kind(record.get("knowledge_kind")), 0)
    required_rank = _MAP_KNOWLEDGE_KIND_ORDER.get(_normalize_map_knowledge_kind(minimum_kind), 0)
    return current_rank >= required_rank


def maybe_mark_player_node_visited(
    sess: Session,
    player_id: uuid.UUID | str,
    node_id: str,
    *,
    source: str = "travel",
) -> dict[str, Any] | None:
    return grant_player_map_knowledge(sess, player_id, node_id, knowledge_kind="visited", source=source)


def reveal_player_map_node(
    sess: Session,
    player_id: uuid.UUID | str,
    node_id: str,
    *,
    source: str = "manual",
) -> dict[str, Any] | None:
    pid = str(player_id or "").strip()
    normalized_node_id = str(node_id or "").strip()
    if not pid or not normalized_node_id:
        return None
    if get_static_node(normalized_node_id) is None:
        return None
    reveal_map = _raw_player_map_reveals(sess)
    player_records = dict(reveal_map.get(pid) or {})
    existing = _normalize_player_map_reveal_record(normalized_node_id, player_records.get(normalized_node_id))
    next_order = max([as_int(record.get("revealed_order"), 0) for record in player_records.values()] or [0]) + 1
    if existing:
        existing["source"] = str(source or existing.get("source") or "manual")[:40] or "manual"
        if "revealed_order" not in existing:
            existing["revealed_order"] = next_order
        if "revealed_at" not in existing:
            existing["revealed_at"] = datetime.now(timezone.utc).isoformat()
        player_records[normalized_node_id] = existing
    else:
        player_records[normalized_node_id] = {
            "node_id": normalized_node_id[:120],
            "source": str(source or "manual")[:40] or "manual",
            "revealed_order": next_order,
            "revealed_at": datetime.now(timezone.utc).isoformat(),
        }
    reveal_map[pid] = player_records
    _persist_player_map_reveals(sess, reveal_map)
    grant_player_map_knowledge(sess, pid, normalized_node_id, knowledge_kind="known", source=source)
    return dict(player_records[normalized_node_id])


def maybe_reveal_nearby_static_nodes(
    sess: Session,
    player_id: uuid.UUID | str,
    position: dict[str, Any] | None,
    *,
    source: str = "visibility",
) -> list[str]:
    revealed_node_ids: list[str] = []
    for node_id in _default_revealed_static_node_ids_for_position(position):
        if reveal_player_map_node(sess, player_id, node_id, source=source):
            revealed_node_ids.append(node_id)
    return revealed_node_ids


def get_player_revealed_node_ids(sess: Session, player_id: uuid.UUID | str) -> list[str]:
    pid = str(player_id or "").strip()
    if not pid:
        return []
    reveal_map = _raw_player_map_reveals(sess)
    player_records = dict(reveal_map.get(pid) or {})
    if not player_records:
        current_position = _get_player_map_position(sess, pid)
        maybe_reveal_nearby_static_nodes(sess, pid, current_position if isinstance(current_position, dict) else None, source="seed")
        reveal_map = _raw_player_map_reveals(sess)
        player_records = dict(reveal_map.get(pid) or {})
    return sorted(
        node_id
        for node_id, record in player_records.items()
        if _normalize_player_map_reveal_record(node_id, record)
    )


def is_player_node_revealed(sess: Session, player_id: uuid.UUID | str, node_id: str) -> bool:
    normalized_node_id = str(node_id or "").strip()
    if not normalized_node_id:
        return False
    return normalized_node_id in set(get_player_revealed_node_ids(sess, player_id))


def get_current_group_navigation_options(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> list[dict[str, Any]]:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return []
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return []
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    if not current_map_position:
        return []
    if not resolved_player_id:
        player_ids = group.get("player_ids") if isinstance(group.get("player_ids"), list) else []
        resolved_player_id = str(player_ids[0] or "").strip() if player_ids else ""
    return get_static_navigation_options(
        current_map_position=current_map_position,
        known_node_ids=get_player_known_node_ids(sess, resolved_player_id) if resolved_player_id else None,
        revealed_node_ids=get_player_revealed_node_ids(sess, resolved_player_id) if resolved_player_id else None,
    )


def get_group_navigation_option_by_target(
    sess: Session,
    *,
    target_node_id: str,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    normalized_target_node_id = str(target_node_id or "").strip()
    if not normalized_target_node_id:
        return None
    options = get_current_group_navigation_options(sess, player_id=player_id, group_id=group_id)
    for option in options:
        if str(option.get("target_node_id") or "").strip() == normalized_target_node_id:
            return dict(option)
    return None


def execute_group_navigation_option(
    sess: Session,
    *,
    target_node_id: str,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
    movement_mode: str | None = None,
    source: str = "manual",
) -> tuple[dict[str, Any] | None, str | None]:
    normalized_target_node_id = str(target_node_id or "").strip()
    if not normalized_target_node_id:
        return None, "Нужно указать target_node_id для navigation."
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None, "Группа игрока не найдена."
    option = get_group_navigation_option_by_target(
        sess,
        target_node_id=normalized_target_node_id,
        player_id=resolved_player_id or None,
        group_id=resolved_group_id,
    )
    if not option:
        static_target = get_static_node(normalized_target_node_id)
        if not static_target:
            return None, "Неизвестная navigation цель группы."
        if resolved_player_id and not has_player_map_knowledge(sess, resolved_player_id, normalized_target_node_id):
            return None, "Группа пока не знает эту точку карты."
        return None, "Эта navigation цель сейчас недоступна из текущей точки."

    group = _get_group_states(sess).get(resolved_group_id)
    current_map_position = _normalize_map_position((group or {}).get("current_map_position"))
    if not current_map_position:
        return None, "Не удалось определить текущую позицию группы."

    static_target = get_static_node(normalized_target_node_id)
    if not static_target:
        return None, "Неизвестная navigation цель группы."

    from app.web.map_targeting import resolve_group_target_route

    route_summary = resolve_group_target_route(
        current_map_position=current_map_position,
        target_node=static_target,
        action_kind=str(option.get("action_kind") or "move"),
    )
    if route_summary.get("allowed") is not True:
        return None, str(route_summary.get("error") or "Недопустимая navigation цель группы.")

    resolved_mode = str(movement_mode or get_group_movement_mode(sess, resolved_group_id) or "normal").strip().lower() or "normal"
    updated = start_group_travel(
        sess,
        resolved_group_id,
        route_summary,
        movement_mode=resolved_mode,
        source=source,
    )
    if not updated:
        return None, "Не удалось запустить navigation группы."
    updated = evaluate_group_travel_pause(sess, resolved_group_id) or updated
    return updated, None


def get_current_group_node_context(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return None
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    if not current_map_position:
        return None
    node_context = get_static_node_context(current_map_position=current_map_position)
    if not node_context:
        return None
    contextual_actions = get_current_node_context_actions(current_map_position=current_map_position)
    travel_state = _group_travel_state_summary(group)
    if isinstance(travel_state, dict) and travel_state.get("active") is True and travel_state.get("paused") is True:
        pause_reason = str(travel_state.get("pause_reason") or "").strip().lower()
        if pause_reason == "target_requires_enter" and not any(
            action.get("action_key") == "enter" for action in contextual_actions if isinstance(action, dict)
        ):
            contextual_actions.insert(0, {"action_key": "enter", "label": "Войти", "action_type": "action"})
        if pause_reason == "point_of_interest_reached" and not any(
            action.get("action_key") == "inspect" for action in contextual_actions if isinstance(action, dict)
        ):
            contextual_actions.insert(0, {"action_key": "inspect", "label": "Осмотреться", "action_type": "action"})
    return {
        "node_summary": node_context,
        "contextual_actions": contextual_actions,
        "available_services": get_current_group_node_services(sess, player_id=resolved_player_id or None, group_id=resolved_group_id),
        "service_actions": (
            [{"action_key": "use_service", "label": "Воспользоваться услугой", "action_type": "action"}]
            if get_current_group_node_services(sess, player_id=resolved_player_id or None, group_id=resolved_group_id)
            else []
        ),
    }


def _normalize_group_last_inspect_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    node_id = str(raw.get("node_id") or "").strip()
    label = str(raw.get("label") or node_id).strip()
    inspect_summary = str(raw.get("inspect_summary") or raw.get("short_description") or "").strip()
    if not node_id or not label or not inspect_summary:
        return None
    result: dict[str, Any] = {
        "node_id": node_id[:120],
        "label": label[:120],
        "node_type": str(raw.get("node_type") or "zone")[:40] or "zone",
        "inspect_summary": inspect_summary[:400],
        "short_description": str(raw.get("short_description") or inspect_summary)[:400] or inspect_summary[:400],
        "source": str(raw.get("source") or "inspect")[:40] or "inspect",
    }
    travel_note = str(raw.get("travel_note") or "").strip()
    if travel_note:
        result["travel_note"] = travel_note[:240]
    danger_note = str(raw.get("danger_note") or "").strip()
    if danger_note:
        result["danger_note"] = danger_note[:240]
    service_hints = raw.get("service_hints")
    if isinstance(service_hints, list):
        normalized_hints = [str(item).strip()[:120] for item in service_hints if str(item or "").strip()]
        if normalized_hints:
            result["service_hints"] = normalized_hints
    inspected_at = str(raw.get("inspected_at") or "").strip()
    if inspected_at:
        result["inspected_at"] = inspected_at
    return result


def _set_group_last_inspect_result(group: dict[str, Any], inspect_result: dict[str, Any] | None) -> dict[str, Any] | None:
    normalized = _normalize_group_last_inspect_result(inspect_result)
    if not normalized:
        group.pop("last_inspect_result", None)
        return None
    group["last_inspect_result"] = normalized
    return normalized


def _normalize_group_last_service_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    service_key = str(raw.get("service_key") or "").strip().lower()
    label = str(raw.get("label") or service_key).strip()
    result_summary = str(raw.get("result_summary") or raw.get("summary") or "").strip()
    node_id = str(raw.get("node_id") or "").strip()
    node_label = str(raw.get("node_label") or node_id).strip()
    if not service_key or not label or not result_summary or not node_id or not node_label:
        return None
    result: dict[str, Any] = {
        "service_key": service_key[:80],
        "label": label[:120],
        "service_type": str(raw.get("service_type") or "service")[:40] or "service",
        "summary": str(raw.get("summary") or result_summary)[:400] or result_summary[:400],
        "result_summary": result_summary[:400],
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "source": str(raw.get("source") or "service")[:40] or "service",
    }
    service_hints = raw.get("service_hints")
    if isinstance(service_hints, list):
        normalized_hints = [str(item).strip()[:120] for item in service_hints if str(item or "").strip()]
        if normalized_hints:
            result["service_hints"] = normalized_hints
    used_at = str(raw.get("used_at") or "").strip()
    if used_at:
        result["used_at"] = used_at
    return result


def _set_group_last_service_result(group: dict[str, Any], service_result: dict[str, Any] | None) -> dict[str, Any] | None:
    normalized = _normalize_group_last_service_result(service_result)
    if not normalized:
        group.pop("last_service_result", None)
        return None
    group["last_service_result"] = normalized
    return normalized


def get_current_group_node_detail(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return None
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    if not current_map_position:
        return None
    return get_static_node_detail(current_map_position=current_map_position)


def get_current_group_node_services(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> list[dict[str, Any]]:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return []
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return []
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    if not current_map_position:
        return []
    return get_static_node_services(current_map_position=current_map_position)


def get_current_group_last_inspect_result(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return None
    return _normalize_group_last_inspect_result(group.get("last_inspect_result"))


def get_current_group_last_service_result(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return None
    return _normalize_group_last_service_result(group.get("last_service_result"))


def inspect_current_group_node(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
    source: str = "manual",
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None
    groups = _get_group_states(sess)
    group = groups.get(resolved_group_id)
    if not isinstance(group, dict):
        return None
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    current_node_id = str((current_map_position or {}).get("node_id") or "").strip()
    inspect_result = get_static_node_inspect_result(current_map_position=current_map_position, source=source)
    if not current_map_position or not current_node_id or not inspect_result:
        return None
    _set_group_last_inspect_result(
        group,
        {
            **inspect_result,
            "inspected_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    if resolved_player_id:
        grant_player_map_knowledge(sess, resolved_player_id, current_node_id, knowledge_kind="discovered", source=source)
        reveal_player_map_node(sess, resolved_player_id, current_node_id, source=source)
        maybe_reveal_nearby_static_nodes(sess, resolved_player_id, current_map_position, source=source)
    return dict(group)


def execute_current_group_service(
    sess: Session,
    *,
    service_key: str,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
    source: str = "manual",
) -> tuple[dict[str, Any] | None, str | None]:
    normalized_service_key = str(service_key or "").strip().lower()
    if not normalized_service_key:
        return None, "Нужно указать service_key для услуги."
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None, "Группа игрока не найдена."
    available_services = get_current_group_node_services(sess, player_id=resolved_player_id or None, group_id=resolved_group_id)
    service = next(
        (
            dict(item)
            for item in available_services
            if isinstance(item, dict) and str(item.get("service_key") or "").strip().lower() == normalized_service_key
        ),
        None,
    )
    if not service:
        return None, "Эта услуга сейчас недоступна в текущем месте."
    groups = _get_group_states(sess)
    group = groups.get(resolved_group_id)
    if not isinstance(group, dict):
        return None, "Группа игрока не найдена."
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    service_result = get_static_node_service_result(
        service_key=normalized_service_key,
        current_map_position=current_map_position,
        source=source,
    )
    if not service_result:
        return None, "Не удалось подготовить результат услуги."
    _set_group_last_service_result(
        group,
        {
            **service_result,
            "used_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group), None


def build_group_travel_event_candidates(
    route_summary: dict[str, Any] | None,
    *,
    movement_mode: str | None = None,
    travel_activity: dict[str, Any] | None = None,
    source: str = "travel",
) -> list[dict[str, Any]]:
    route = _normalize_group_route_summary(route_summary)
    if not route or route.get("allowed") is not True:
        return []
    action_kind = str(route.get("action_kind") or "").strip().lower()
    if action_kind == "enter":
        return []
    resolved_mode = _normalize_group_movement_mode(movement_mode)
    resolved_activity = _normalize_group_travel_activity(travel_activity)
    activity_key = str((resolved_activity or {}).get("activity") or "").strip().lower()
    traversal_kind = str(route.get("traversal_kind") or "").strip().lower()
    risk_band = str(route.get("risk_band") or "").strip().lower()
    terrain_hint = str(route.get("terrain_hint") or "").strip().lower()
    travel_tags = {str(item or "").strip().lower() for item in (route.get("travel_tags") or []) if str(item or "").strip()}

    def _candidate(event_key: str, summary: str, *, event_type: str = "roadside_hook") -> dict[str, Any]:
        return {
            "event_key": event_key,
            "event_type": event_type,
            "summary": summary,
            "route_snapshot": route,
            "source": source,
            "active": True,
            "resolved": False,
        }

    candidates: list[dict[str, Any]] = []
    if traversal_kind == "marsh_path" or terrain_hint == "marsh" or "poor_visibility" in travel_tags:
        candidates.append(_candidate("blocked_path", "Путь впереди вязнет и требует осторожного решения перед продолжением."))
    if activity_key in {"track", "observe", "navigate"} or traversal_kind in {"trail", "wild", "ruin_path"}:
        candidates.append(_candidate("tracks_or_signs", "На пути заметны следы и знаки, которые могут подсказать, кто проходил здесь раньше."))
    if risk_band == "low" and traversal_kind in {"road", "gate_approach"}:
        candidates.append(_candidate("roadside_finding", "У дороги попалась мелкая находка или примета, которая делает путь чуть менее безликим."))
    if risk_band in {"low", "medium"} and traversal_kind in {"road", "trail", "gate_approach"}:
        candidates.append(_candidate("lost_traveler", "На дороге есть след недавнего путника или чужой короткий запрос о помощи."))
    if risk_band == "high" or terrain_hint in {"marsh", "ruins", "ruined_frontier"} or "ruins" in travel_tags:
        ominous_summary = "Окрестности подозрительно тихи и заставляют группу замедлиться."
        if resolved_mode == "fast":
            ominous_summary = "Быстрый ход по опасному пути делает тишину вокруг особенно тревожной."
        candidates.append(_candidate("ominous_quiet", ominous_summary))

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.get("event_key") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(_normalize_group_travel_event({**candidate, "event_id": f"candidate-{key}"}) or candidate)
    return deduped


def trigger_group_travel_event(
    sess: Session,
    group_id: str,
    *,
    event_key: str | None = None,
    event: dict[str, Any] | None = None,
    source: str = "travel",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    chosen_event = _normalize_group_travel_event(event)
    if not chosen_event:
        travel_state = _group_travel_state_summary(group)
        candidates = build_group_travel_event_candidates(
            (travel_state or {}).get("route_summary"),
            movement_mode=(travel_state or {}).get("movement_mode") or group.get("movement_mode"),
            travel_activity=(travel_state or {}).get("travel_activity") or group.get("travel_activity"),
            source=source,
        )
        normalized_event_key = str(event_key or "").strip().lower()
        if normalized_event_key:
            for candidate in candidates:
                if str(candidate.get("event_key") or "").strip().lower() == normalized_event_key:
                    chosen_event = _normalize_group_travel_event({**candidate, "event_id": uuid.uuid4().hex[:12], "source": source})
                    break
        elif candidates:
            chosen_event = _normalize_group_travel_event({**candidates[0], "event_id": uuid.uuid4().hex[:12], "source": source})
    if not chosen_event:
        return None
    group["travel_event"] = chosen_event
    if chosen_event.get("event_key") == "blocked_path":
        travel_state = _group_travel_state_summary(group)
        if travel_state and travel_state.get("active") is True and travel_state.get("paused") is not True:
            travel_state["paused"] = True
            travel_state["pause_reason"] = "route_blocked"
            travel_state["pause_details"] = {"event_id": chosen_event["event_id"], "event_key": "blocked_path"}
            travel_state["resume_allowed"] = False
            travel_state["phase"] = "paused"
            group["travel_state"] = travel_state
            group["status"] = "paused_travel"
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def get_current_group_travel_event(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return None
    return _normalize_group_travel_event(group.get("travel_event"))


def _set_group_last_travel_event_outcome(
    group: dict[str, Any],
    outcome: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized = _normalize_group_travel_event_outcome(outcome)
    if not normalized:
        group.pop("last_travel_event_outcome", None)
        return None
    group["last_travel_event_outcome"] = normalized
    return normalized


def build_group_travel_event_outcome(
    event: dict[str, Any] | None,
    *,
    resolution: str,
    source: str = "manual",
) -> dict[str, Any] | None:
    normalized_event = _normalize_group_travel_event(event)
    if not normalized_event:
        return None
    normalized_resolution = str(resolution or "").strip().lower()
    if normalized_resolution not in {"resolve", "ignore"}:
        return None
    event_key = str(normalized_event.get("event_key") or "").strip().lower()
    outcome_type = "ignored_event"
    result_summary = "Группа отмечает событие, но решает не задерживаться на нём."
    applied_effects: list[str] = ["event_closed"]
    if event_key == "roadside_finding":
        if normalized_resolution == "resolve":
            outcome_type = "finding_note"
            result_summary = "Группа отмечает дорожную примету и получает полезную заметку о ближайшем пути."
            applied_effects = ["event_closed", "travel_hint_recorded"]
        else:
            result_summary = "Группа оставляет находку у обочины без дальнейшего разбора."
    elif event_key == "tracks_or_signs":
        if normalized_resolution == "resolve":
            outcome_type = "route_hint"
            result_summary = "Следы и знаки подсказывают направление и делают ближайшую цель понятнее."
            applied_effects = ["event_closed", "knowledge_updated", "node_revealed"]
        else:
            result_summary = "Группа не тратит время на чтение следов и идёт дальше без новой подсказки."
    elif event_key == "lost_traveler":
        if normalized_resolution == "resolve":
            outcome_type = "guidance_note"
            result_summary = "Короткий разговор в пути даёт местную наводку и успокаивает дорогу."
            applied_effects = ["event_closed", "guidance_recorded", "knowledge_updated"]
        else:
            result_summary = "Группа не останавливается для разговора с путником."
    elif event_key == "blocked_path":
        if normalized_resolution == "resolve":
            outcome_type = "obstacle_cleared"
            result_summary = "Препятствие на пути разобрано достаточно, чтобы группа могла продолжить движение."
            applied_effects = ["event_closed", "travel_resumed"]
        else:
            outcome_type = "route_still_blocked"
            result_summary = "Группа отказывается разбирать преграду и снимает текущий переход."
            applied_effects = ["event_closed", "travel_interrupted"]
    elif event_key == "ominous_quiet":
        if normalized_resolution == "resolve":
            outcome_type = "warning_note"
            result_summary = "Подозрительная тишина фиксируется как предупреждение для дальнейшего пути."
            applied_effects = ["event_closed", "warning_recorded"]
        else:
            result_summary = "Группа предпочитает не задерживаться на тревожной тишине."
    return _normalize_group_travel_event_outcome(
        {
            "outcome_id": uuid.uuid4().hex[:12],
            "event_key": event_key,
            "event_type": normalized_event.get("event_type") or "roadside_hook",
            "outcome_type": outcome_type,
            "summary": str(normalized_event.get("summary") or ""),
            "result_summary": result_summary,
            "applied_effects": applied_effects,
            "route_snapshot": normalized_event.get("route_snapshot"),
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def apply_group_travel_event_outcome(
    sess: Session,
    group_id: str,
    outcome: dict[str, Any] | None,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "manual",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    normalized_outcome = _normalize_group_travel_event_outcome(outcome)
    if not group or not normalized_outcome:
        return None
    _set_group_last_travel_event_outcome(group, normalized_outcome)
    resolved_player_id = str(player_id or "").strip()
    route_snapshot = _normalize_group_route_summary(normalized_outcome.get("route_snapshot")) or {}
    target_node_id = str(route_snapshot.get("target_node_id") or "").strip()
    if resolved_player_id and target_node_id and get_static_node(target_node_id):
        outcome_type = str(normalized_outcome.get("outcome_type") or "").strip().lower()
        if outcome_type in {"route_hint", "guidance_note"}:
            grant_player_map_knowledge(sess, resolved_player_id, target_node_id, knowledge_kind="known", source=source)
        if outcome_type == "route_hint":
            reveal_player_map_node(sess, resolved_player_id, target_node_id, source=source)
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def get_current_group_last_travel_event_outcome(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return None
    return _normalize_group_travel_event_outcome(group.get("last_travel_event_outcome"))


def resolve_group_travel_event(
    sess: Session,
    group_id: str,
    *,
    resolution: str,
    player_id: uuid.UUID | str | None = None,
    source: str = "manual",
) -> tuple[dict[str, Any] | None, str | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None, "Группа не найдена."
    event = _group_travel_event_summary(group)
    if not event or event.get("active") is not True:
        return None, "У группы нет активного travel event."
    normalized_resolution = str(resolution or "").strip().lower()
    if normalized_resolution not in {"resolve", "ignore"}:
        return None, "Неизвестный способ завершения travel event."
    if normalized_resolution == "ignore" and str(event.get("event_key") or "") == "blocked_path":
        interrupted = interrupt_group_travel(sess, group_key)
        groups = _get_group_states(sess)
        group = groups.get(group_key)
        if not interrupted or not group:
            return None, "Не удалось проигнорировать blocked path."
        group["status"] = "idle"
    elif normalized_resolution == "resolve" and str(event.get("event_key") or "") == "blocked_path":
        travel_state = _group_travel_state_summary(group)
        if travel_state and travel_state.get("active") is True:
            travel_state["paused"] = False
            travel_state.pop("pause_reason", None)
            travel_state.pop("pause_details", None)
            travel_state["resume_allowed"] = True
            travel_state["phase"] = "in_transit"
            group["travel_state"] = travel_state
            group["status"] = "moving"
    outcome = build_group_travel_event_outcome(event, resolution=normalized_resolution, source=source)
    if not outcome:
        return None, "Не удалось подготовить outcome для travel event."
    resolved_event = dict(event)
    resolved_event["active"] = False
    resolved_event["resolved"] = True
    resolved_event["resolution"] = normalized_resolution
    resolved_event["source"] = str(source or event.get("source") or "travel")[:40] or "travel"
    group["travel_event"] = resolved_event
    _set_group_last_travel_event_outcome(group, outcome)
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    if player_id:
        updated = apply_group_travel_event_outcome(
            sess,
            group_key,
            outcome,
            player_id=player_id,
            source=source,
        )
        if updated:
            return updated, None
    return dict(group), None


def execute_current_group_context_action(
    sess: Session,
    *,
    action_key: str,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
    payload: dict[str, Any] | None = None,
    source: str = "manual",
) -> tuple[dict[str, Any] | None, str | None]:
    normalized_action_key = str(action_key or "").strip().lower()
    if not normalized_action_key:
        return None, "Нужно указать action_key для contextual action."
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None, "Группа игрока не найдена."
    context = get_current_group_node_context(sess, player_id=resolved_player_id or None, group_id=resolved_group_id)
    if not context:
        return None, "Не удалось определить current node context группы."
    payload = payload if isinstance(payload, dict) else {}
    available_action = next(
        (
            dict(item)
            for item in context.get("contextual_actions") or []
            if isinstance(item, dict) and str(item.get("action_key") or "").strip().lower() == normalized_action_key
        ),
        None,
    )
    if not available_action:
        return None, "Это contextual действие сейчас недоступно."
    if str(available_action.get("action_type") or "action").strip().lower() != "action":
        return None, "Это contextual действие доступно только как подсказка."

    if normalized_action_key == "navigate":
        return execute_group_navigation_option(
            sess,
            target_node_id=str(payload.get("target_node_id") or "").strip(),
            player_id=resolved_player_id or None,
            group_id=resolved_group_id,
            movement_mode=payload.get("movement_mode"),
            source=source,
        )

    if normalized_action_key == "wait":
        updated = set_group_wait(
            sess,
            resolved_group_id,
            reason=str(payload.get("reason") or "").strip() or None,
            source=source,
            requested_by=resolved_player_id or None,
        )
        return (updated, None) if updated else (None, "Не удалось перевести группу в ожидание.")

    if normalized_action_key == "camp":
        updated = set_group_camp(
            sess,
            resolved_group_id,
            reason=str(payload.get("reason") or "").strip() or None,
            source=source,
            requested_by=resolved_player_id or None,
        )
        return (updated, None) if updated else (None, "Не удалось перевести группу в лагерь.")

    if normalized_action_key == "enter":
        updated = confirm_group_enter(sess, resolved_group_id, player_id=resolved_player_id or None, source=source)
        if updated:
            return updated, None
        return None, "Для входа нужен активный paused travel с требованием enter."

    if normalized_action_key == "inspect":
        updated = inspect_group_travel_target(sess, resolved_group_id, player_id=resolved_player_id or None, source=source)
        if updated:
            return updated, None
        updated = inspect_current_group_node(
            sess,
            player_id=resolved_player_id or None,
            group_id=resolved_group_id,
            source=source,
        )
        if updated:
            return updated, None
        return None, "Не удалось осмотреть текущее место группы."

    return None, "Это contextual действие пока не поддерживается."


def create_group_wait_state(
    *,
    reason: str | None = None,
    source: str = "manual",
    requested_by: uuid.UUID | str | None = None,
    started_at: str | None = None,
) -> dict[str, Any]:
    return _normalize_group_wait_state(
        {
            "reason": reason,
            "source": source,
            "requested_by": requested_by,
            "started_at": started_at,
        }
    ) or {"source": "manual"}


def create_group_camp_state(
    *,
    reason: str | None = None,
    source: str = "manual",
    requested_by: uuid.UUID | str | None = None,
    started_at: str | None = None,
) -> dict[str, Any]:
    return _normalize_group_camp_state(
        {
            "reason": reason,
            "source": source,
            "requested_by": requested_by,
            "started_at": started_at,
        }
    ) or {"source": "manual"}


def create_group_movement_intent(
    *,
    target_node: dict[str, Any] | str | None = None,
    target_label: str | None = None,
    movement_mode: str | None = None,
    movement_kind: str | None = None,
    action_kind: str | None = None,
    route_kind: str | None = None,
    route_source: str | None = None,
    traversal_kind: str | None = None,
    risk_band: str | None = None,
    terrain_hint: str | None = None,
    travel_tags: list[str] | None = None,
    allowed: bool = True,
    travel_activity: dict[str, Any] | None = None,
    source: str = "manual",
    active: bool = True,
) -> dict[str, Any] | None:
    return _normalize_group_movement_intent(
        {
            "target_node": target_node,
            "target_label": target_label,
            "movement_mode": movement_mode,
            "movement_kind": movement_kind,
            "action_kind": action_kind,
            "route_kind": route_kind,
            "route_source": route_source,
            "traversal_kind": traversal_kind,
            "risk_band": risk_band,
            "terrain_hint": terrain_hint,
            "travel_tags": travel_tags,
            "allowed": allowed,
            "travel_activity": travel_activity,
            "source": source,
            "active": active,
        }
    )


def _resolve_group_status(
    raw_status: Any,
    *,
    wait_state: dict[str, Any] | None,
    camp_state: dict[str, Any] | None,
    movement_intent: dict[str, Any] | None,
    travel_state: dict[str, Any] | None,
) -> str:
    if travel_state and travel_state.get("active"):
        if travel_state.get("paused"):
            return "paused_travel"
        return "moving"
    if camp_state:
        return "camping"
    if wait_state:
        return "waiting"
    if movement_intent:
        return "moving_intent"
    return _normalize_group_status(raw_status)


def _clear_group_activity_state(group: dict[str, Any], *, status: str = "idle") -> dict[str, Any]:
    group.pop("wait_state", None)
    group.pop("camp_state", None)
    group.pop("movement_intent", None)
    group.pop("travel_state", None)
    group["status"] = _normalize_group_status(status)
    return group


def _set_group_last_travel_resolution(
    group: dict[str, Any],
    *,
    resolution_kind: str,
    pause_reason: str | None = None,
    target_label: str | None = None,
    source: str = "manual",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _normalize_group_travel_resolution(
        {
            "resolution_kind": resolution_kind,
            "pause_reason": pause_reason,
            "target_label": target_label,
            "source": source,
            "details": details,
        }
    )
    if normalized:
        group["last_travel_resolution"] = normalized
    return group


def _apply_group_activity_state(
    group: dict[str, Any],
    *,
    status: str,
    wait_state: dict[str, Any] | None = None,
    camp_state: dict[str, Any] | None = None,
    movement_intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _clear_group_activity_state(group)
    normalized_status = _normalize_group_status(status)
    if normalized_status == "waiting" and wait_state:
        group["wait_state"] = wait_state
    elif normalized_status == "camping" and camp_state:
        group["camp_state"] = camp_state
    elif normalized_status == "moving_intent" and movement_intent:
        group["movement_intent"] = movement_intent
    group["status"] = normalized_status
    return group


def _group_wait_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_wait_state(group.get("wait_state"))


def _group_camp_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_camp_state(group.get("camp_state"))


def _group_movement_mode(group: dict[str, Any]) -> str:
    return _normalize_group_movement_mode(group.get("movement_mode"))


def _group_travel_activity_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_travel_activity(group.get("travel_activity"))


def _group_movement_intent_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_movement_intent(group.get("movement_intent"))


def _group_travel_state_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_travel_state(group.get("travel_state"))


def _group_travel_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    travel_state = _group_travel_state_summary(group)
    if not travel_state:
        return None
    summary = {
        "active": bool(travel_state.get("active")),
        "phase": travel_state.get("phase"),
        "progress_kind": travel_state.get("progress_kind"),
        "progress_step": travel_state.get("progress_step"),
        "movement_mode": travel_state.get("movement_mode"),
        "paused": bool(travel_state.get("paused")),
        "resume_allowed": bool(travel_state.get("resume_allowed", True)),
        "route_summary": dict(travel_state.get("route_summary") or {}),
        "started_from": dict(travel_state.get("started_from") or {}),
        "target_node": dict(travel_state.get("target_node") or {}),
    }
    if travel_state.get("pause_reason"):
        summary["pause_reason"] = travel_state.get("pause_reason")
    if travel_state.get("pause_details"):
        summary["pause_details"] = dict(travel_state["pause_details"])
    if travel_state.get("travel_activity"):
        summary["travel_activity"] = dict(travel_state["travel_activity"])
    return summary


def _group_last_travel_resolution_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_travel_resolution(group.get("last_travel_resolution"))


def _group_last_inspect_result_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_last_inspect_result(group.get("last_inspect_result"))


def _group_last_service_result_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_last_service_result(group.get("last_service_result"))


def _group_travel_event_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_travel_event(group.get("travel_event"))


def _group_last_travel_event_outcome_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_travel_event_outcome(group.get("last_travel_event_outcome"))


def _travel_available_resolutions_for_reason(pause_reason: str | None) -> list[dict[str, str]]:
    reason = _normalize_group_pause_reason(pause_reason)
    if reason == "target_requires_enter":
        return [
            {"resolution": "confirm_enter", "label": "confirm_enter"},
            {"resolution": "resume", "label": "resume"},
            {"resolution": "interrupt", "label": "interrupt"},
        ]
    if reason == "point_of_interest_reached":
        return [
            {"resolution": "inspect_target", "label": "inspect_target"},
            {"resolution": "resume", "label": "resume"},
            {"resolution": "interrupt", "label": "interrupt"},
        ]
    if reason == "route_blocked":
        return [
            {"resolution": "bypass", "label": "bypass"},
            {"resolution": "interrupt", "label": "interrupt"},
        ]
    if reason == "event_pending":
        return [
            {"resolution": "resolve_pause", "label": "resolve_pause"},
            {"resolution": "resume", "label": "resume"},
            {"resolution": "interrupt", "label": "interrupt"},
        ]
    if reason == "manual":
        return [
            {"resolution": "resume", "label": "resume"},
            {"resolution": "interrupt", "label": "interrupt"},
        ]
    return []


def _group_available_resolutions_summary(group: dict[str, Any]) -> list[dict[str, str]] | None:
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True or travel_state.get("paused") is not True:
        return None
    available = _travel_available_resolutions_for_reason(travel_state.get("pause_reason"))
    return available or None


def _group_default_position(
    sess: Session,
    player_ids: list[str],
    fallback_position: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    pos = _normalize_map_position(fallback_position)
    if pos:
        return pos

    raw_positions = _raw_player_map_positions(sess)
    for pid in player_ids:
        existing = raw_positions.get(pid)
        if existing:
            return dict(existing)

    legacy_positions = _raw_pc_positions(sess)
    for pid in player_ids:
        zone = str(legacy_positions.get(pid) or "").strip()
        if zone:
            return _default_map_position(zone)

    return _default_map_position("стартовая локация")


def _normalize_group_state(
    sess: Session,
    group_id: str,
    raw: Any,
) -> dict[str, Any] | None:
    group_key = str(group_id or "").strip()[:80]
    if not group_key or not isinstance(raw, dict):
        return None

    raw_members = raw.get("player_ids")
    player_ids: list[str] = []
    if isinstance(raw_members, list):
        for item in raw_members:
            pid = str(item or "").strip()
            if pid and pid not in player_ids:
                player_ids.append(pid)
    if not player_ids:
        return None

    pos = _normalize_map_position(raw.get("current_map_position"))
    if not pos:
        pos = _group_default_position(sess, player_ids)
    area_label = str(raw.get("area_label") or "").strip() or _map_position_area_label(pos)
    wait_state = _normalize_group_wait_state(raw.get("wait_state"))
    camp_state = _normalize_group_camp_state(raw.get("camp_state"))
    movement_intent = _normalize_group_movement_intent(raw.get("movement_intent"))
    travel_state = _normalize_group_travel_state(raw.get("travel_state"))
    status = _resolve_group_status(
        raw.get("status"),
        wait_state=wait_state,
        camp_state=camp_state,
        movement_intent=movement_intent,
        travel_state=travel_state,
    )

    normalized = {
        "group_id": group_key,
        "player_ids": player_ids,
        "current_map_position": pos,
        "area_label": area_label[:80],
        "status": status,
        "movement_mode": _normalize_group_movement_mode(raw.get("movement_mode")),
    }
    travel_activity = _normalize_group_travel_activity(raw.get("travel_activity"))
    if travel_activity:
        normalized["travel_activity"] = travel_activity
    if wait_state:
        normalized["wait_state"] = wait_state
    if camp_state:
        normalized["camp_state"] = camp_state
    if movement_intent:
        normalized["movement_intent"] = movement_intent
    if travel_state:
        normalized["travel_state"] = travel_state
    last_resolution = _normalize_group_travel_resolution(raw.get("last_travel_resolution"))
    if last_resolution:
        normalized["last_travel_resolution"] = last_resolution
    last_inspect_result = _normalize_group_last_inspect_result(raw.get("last_inspect_result"))
    if last_inspect_result:
        normalized["last_inspect_result"] = last_inspect_result
    last_service_result = _normalize_group_last_service_result(raw.get("last_service_result"))
    if last_service_result:
        normalized["last_service_result"] = last_service_result
    travel_event = _normalize_group_travel_event(raw.get("travel_event"))
    if travel_event:
        normalized["travel_event"] = travel_event
    last_travel_event_outcome = _normalize_group_travel_event_outcome(raw.get("last_travel_event_outcome"))
    if last_travel_event_outcome:
        normalized["last_travel_event_outcome"] = last_travel_event_outcome
    return normalized


def _persist_group_states(sess: Session, groups: dict[str, dict[str, Any]]) -> None:
    payload: dict[str, dict[str, Any]] = {}
    for group_id, group in groups.items():
        normalized = _normalize_group_state(sess, group_id, group)
        if not normalized:
            continue
        payload[group_id] = normalized
    settings_set(sess, "groups", payload)


def _candidate_group_player_ids(sess: Session, player_ids: list[uuid.UUID | str] | None = None) -> list[str]:
    out: list[str] = []
    for item in player_ids or []:
        pid = str(item or "").strip()
        if pid and pid not in out:
            out.append(pid)

    for mapping in (_raw_player_map_positions(sess), _raw_pc_positions(sess)):
        for pid in mapping.keys():
            if pid not in out:
                out.append(pid)

    raw_groups = settings_get(sess, "groups", {}) or {}
    if isinstance(raw_groups, dict):
        for item in raw_groups.values():
            if not isinstance(item, dict):
                continue
            raw_members = item.get("player_ids")
            if not isinstance(raw_members, list):
                continue
            for member in raw_members:
                pid = str(member or "").strip()
                if pid and pid not in out:
                    out.append(pid)
    return out


def _sync_group_position_mirrors(sess: Session, group: dict[str, Any]) -> None:
    player_ids = [str(pid).strip() for pid in (group.get("player_ids") or []) if str(pid).strip()]
    if not player_ids:
        return

    pos = _normalize_map_position(group.get("current_map_position")) or _group_default_position(sess, player_ids)
    area_label = str(group.get("area_label") or "").strip() or _map_position_area_label(pos)

    map_positions = _raw_player_map_positions(sess)
    legacy_positions = _raw_pc_positions(sess)
    for pid in player_ids:
        map_positions[pid] = dict(pos)
        legacy_positions[pid] = area_label[:80]
    settings_set(sess, "map_positions", map_positions)
    settings_set(sess, "pc_positions", legacy_positions)


def _initialize_default_group(
    sess: Session,
    player_ids: list[uuid.UUID | str],
    default_position: dict[str, Any] | str | None = None,
    *,
    status: str = "idle",
) -> dict[str, dict[str, Any]]:
    normalized_player_ids: list[str] = []
    for item in player_ids:
        pid = str(item or "").strip()
        if pid and pid not in normalized_player_ids:
            normalized_player_ids.append(pid)

    if not normalized_player_ids:
        settings_set(sess, "groups", {})
        return {}

    pos = _group_default_position(sess, normalized_player_ids, default_position)
    group = {
        "group_id": DEFAULT_GROUP_ID,
        "player_ids": normalized_player_ids,
        "current_map_position": pos,
        "area_label": _map_position_area_label(pos),
        "status": _normalize_group_status(status),
        "movement_mode": "normal",
    }
    groups = {DEFAULT_GROUP_ID: group}
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return _get_group_states(sess)


def _get_group_states(
    sess: Session,
    player_ids: list[uuid.UUID | str] | None = None,
) -> dict[str, dict[str, Any]]:
    raw = settings_get(sess, "groups", {}) or {}
    groups: dict[str, dict[str, Any]] = {}
    assigned: set[str] = set()
    changed = not isinstance(raw, dict)

    if isinstance(raw, dict):
        for group_id, value in raw.items():
            normalized = _normalize_group_state(sess, str(group_id), value)
            if not normalized:
                changed = True
                continue
            deduped_members: list[str] = []
            for pid in normalized["player_ids"]:
                if pid in assigned:
                    changed = True
                    continue
                assigned.add(pid)
                deduped_members.append(pid)
            if not deduped_members:
                changed = True
                continue
            if deduped_members != normalized["player_ids"]:
                changed = True
            normalized["player_ids"] = deduped_members
            groups[normalized["group_id"]] = normalized

    candidate_player_ids = _candidate_group_player_ids(sess, player_ids)
    missing_player_ids = [pid for pid in candidate_player_ids if pid not in assigned]
    if not groups and candidate_player_ids:
        return _initialize_default_group(sess, candidate_player_ids)

    if missing_player_ids:
        main_group = groups.get(DEFAULT_GROUP_ID)
        if not main_group:
            pos = _group_default_position(sess, missing_player_ids)
            main_group = {
                "group_id": DEFAULT_GROUP_ID,
                "player_ids": [],
                "current_map_position": pos,
                "area_label": _map_position_area_label(pos),
                "status": "idle",
                "movement_mode": "normal",
            }
            groups[DEFAULT_GROUP_ID] = main_group
            changed = True
        for pid in missing_player_ids:
            if pid not in main_group["player_ids"]:
                main_group["player_ids"].append(pid)
                changed = True

    if changed:
        _persist_group_states(sess, groups)
        for group in groups.values():
            _sync_group_position_mirrors(sess, group)

    return groups


def _get_player_group_id(
    sess: Session,
    player_id: uuid.UUID | str,
    player_ids: list[uuid.UUID | str] | None = None,
) -> str | None:
    pid = str(player_id)
    for group_id, group in _get_group_states(sess, player_ids).items():
        if pid in group.get("player_ids", []):
            return group_id
    return None


def set_group_wait(
    sess: Session,
    group_id: str,
    *,
    reason: str | None = None,
    source: str = "manual",
    requested_by: uuid.UUID | str | None = None,
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    _apply_group_activity_state(
        group,
        status="waiting",
        wait_state=create_group_wait_state(reason=reason, source=source, requested_by=requested_by),
    )
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def set_group_camp(
    sess: Session,
    group_id: str,
    *,
    reason: str | None = None,
    source: str = "manual",
    requested_by: uuid.UUID | str | None = None,
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    _apply_group_activity_state(
        group,
        status="camping",
        camp_state=create_group_camp_state(reason=reason, source=source, requested_by=requested_by),
    )
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def get_group_movement_mode(sess: Session, group_id: str) -> str | None:
    group = _get_group_states(sess).get(str(group_id or "").strip())
    if not group:
        return None
    return _group_movement_mode(group)


def set_group_movement_mode(sess: Session, group_id: str, movement_mode: str) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    group["movement_mode"] = _normalize_group_movement_mode(movement_mode)
    current_intent = _group_movement_intent_summary(group)
    if current_intent:
        current_intent["movement_mode"] = group["movement_mode"]
        group["movement_intent"] = current_intent
    current_travel = _group_travel_state_summary(group)
    if current_travel:
        current_travel["movement_mode"] = group["movement_mode"]
        group["travel_state"] = current_travel
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def get_group_travel_activity(sess: Session, group_id: str) -> dict[str, Any] | None:
    group = _get_group_states(sess).get(str(group_id or "").strip())
    if not group:
        return None
    return _group_travel_activity_summary(group)


def set_group_travel_activity(
    sess: Session,
    group_id: str,
    *,
    activity: str,
    assigned_actor_id: uuid.UUID | str | None = None,
    source: str = "manual",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    normalized = _normalize_group_travel_activity(
        {
            "activity": activity,
            "assigned_actor_id": assigned_actor_id,
            "source": source,
        }
    )
    if not normalized:
        return None
    group["travel_activity"] = normalized
    current_intent = _group_movement_intent_summary(group)
    if current_intent:
        current_intent["travel_activity"] = normalized
        group["movement_intent"] = current_intent
    current_travel = _group_travel_state_summary(group)
    if current_travel:
        current_travel["travel_activity"] = normalized
        group["travel_state"] = current_travel
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def clear_group_travel_activity(sess: Session, group_id: str) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    group.pop("travel_activity", None)
    current_intent = _group_movement_intent_summary(group)
    if current_intent:
        current_intent.pop("travel_activity", None)
        group["movement_intent"] = current_intent
    current_travel = _group_travel_state_summary(group)
    if current_travel:
        current_travel.pop("travel_activity", None)
        group["travel_state"] = current_travel
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def set_group_movement_intent(
    sess: Session,
    group_id: str,
    *,
    target_node: dict[str, Any] | str,
    target_label: str | None = None,
    movement_mode: str | None = None,
    movement_kind: str = "move",
    source: str = "manual",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    resolved_mode = _normalize_group_movement_mode(movement_mode or group.get("movement_mode"))
    travel_activity = _group_travel_activity_summary(group)
    movement_intent = create_group_movement_intent(
        target_node=target_node,
        target_label=target_label,
        movement_mode=resolved_mode,
        movement_kind=movement_kind,
        travel_activity=travel_activity,
        source=source,
        active=True,
    )
    if not movement_intent:
        return None
    _apply_group_activity_state(
        group,
        status="moving_intent",
        movement_intent=movement_intent,
    )
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def clear_group_movement_intent(sess: Session, group_id: str) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    _clear_group_activity_state(group)
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def start_group_travel(
    sess: Session,
    group_id: str,
    route_summary: dict[str, Any] | None,
    *,
    movement_mode: str | None = None,
    source: str = "manual",
) -> dict[str, Any] | None:
    route = _normalize_group_route_summary(route_summary)
    if not route or route.get("allowed") is not True:
        return None
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    current_position = _normalize_map_position(group.get("current_map_position"))
    target_node = route.get("target_node")
    if not current_position or not isinstance(target_node, dict):
        return None
    resolved_mode = _normalize_group_movement_mode(movement_mode or group.get("movement_mode"))
    travel_activity = _group_travel_activity_summary(group)
    intent = create_group_movement_intent(
        target_node=target_node,
        target_label=str(route.get("target_label") or "") or None,
        movement_mode=resolved_mode,
        movement_kind=str(route.get("action_kind") or "move"),
        action_kind=str(route.get("action_kind") or "move"),
        route_kind=str(route.get("route_kind") or ""),
        route_source=str(route.get("source") or ""),
        traversal_kind=str(route.get("traversal_kind") or ""),
        risk_band=str(route.get("risk_band") or ""),
        terrain_hint=str(route.get("terrain_hint") or ""),
        travel_tags=list(route.get("travel_tags") or []),
        allowed=True,
        travel_activity=travel_activity,
        source=source,
        active=True,
    )
    travel_state = _normalize_group_travel_state(
        {
            "active": True,
            "phase": "in_transit",
            "route_summary": route,
            "started_from": current_position,
            "target_node": target_node,
            "progress_kind": "route",
            "progress_step": 0,
            "movement_mode": resolved_mode,
            "travel_activity": travel_activity,
        }
    )
    if not intent or not travel_state:
        return None
    _clear_group_activity_state(group, status="moving")
    group.pop("travel_event", None)
    group["movement_intent"] = intent
    group["travel_state"] = travel_state
    group["status"] = "moving"
    target_node_type = str((route.get("target_node") or {}).get("node_type") or "").strip().lower()
    pause_hint = str(route.get("pause_hint") or "").strip().lower()
    auto_pause_reason: str | None = None
    auto_pause_details: dict[str, Any] | None = None
    if target_node_type == "interior_entry":
        auto_pause_reason = "target_requires_enter"
        auto_pause_details = {"target_node_type": "interior_entry"}
    elif pause_hint == "inspection_required":
        auto_pause_reason = "point_of_interest_reached"
        auto_pause_details = {"pause_hint": pause_hint, "target_node_type": target_node_type or "unknown"}
    if auto_pause_reason:
        normalized_reason = _normalize_group_pause_reason(auto_pause_reason)
        if normalized_reason:
            group["travel_state"]["paused"] = True
            group["travel_state"]["pause_reason"] = normalized_reason
            if auto_pause_details:
                group["travel_state"]["pause_details"] = _normalize_group_pause_details(auto_pause_details) or auto_pause_details
            group["travel_state"]["resume_allowed"] = True
            group["travel_state"]["phase"] = "paused"
            group["status"] = "paused_travel"
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    if auto_pause_reason:
        return dict(_get_group_states(sess).get(group_key) or group)
    triggered = trigger_group_travel_event(sess, group_key, source=source)
    if triggered:
        return triggered
    return dict(group)


def pause_group_travel(
    sess: Session,
    group_id: str,
    *,
    reason: str,
    pause_details: dict[str, Any] | None = None,
    resume_allowed: bool = True,
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True:
        return None
    normalized_reason = _normalize_group_pause_reason(reason)
    if not normalized_reason:
        return None
    travel_state["paused"] = True
    travel_state["pause_reason"] = normalized_reason
    if pause_details:
        travel_state["pause_details"] = _normalize_group_pause_details(pause_details) or {}
    else:
        travel_state.pop("pause_details", None)
    travel_state["resume_allowed"] = bool(resume_allowed)
    travel_state["phase"] = "paused"
    group["travel_state"] = travel_state
    group["status"] = "paused_travel"
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def resume_group_travel(sess: Session, group_id: str) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True or travel_state.get("paused") is not True:
        return None
    if travel_state.get("resume_allowed") is not True:
        return None
    travel_state["paused"] = False
    travel_state.pop("pause_reason", None)
    travel_state.pop("pause_details", None)
    travel_state["resume_allowed"] = True
    travel_state["phase"] = "in_transit"
    group["travel_state"] = travel_state
    group["status"] = "moving"
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def confirm_group_enter(
    sess: Session,
    group_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "manual",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True or travel_state.get("paused") is not True:
        return None
    pause_reason = str(travel_state.get("pause_reason") or "").strip().lower()
    route_summary = _normalize_group_route_summary(travel_state.get("route_summary"))
    next_map_position = _normalize_map_position((route_summary or {}).get("next_map_position"))
    next_zone_label = str((route_summary or {}).get("next_zone_label") or "").strip()
    target_label = str((route_summary or {}).get("target_label") or "").strip()
    if pause_reason != "target_requires_enter" or not next_map_position or not next_zone_label:
        return None
    target_node_id = str((route_summary or {}).get("target_node_id") or next_map_position.get("node_id") or "").strip()
    group["current_map_position"] = next_map_position
    group["area_label"] = next_zone_label[:80]
    _set_group_last_travel_resolution(
        group,
        resolution_kind="confirm_enter",
        pause_reason=pause_reason,
        target_label=target_label or str(next_map_position.get("label") or ""),
        source=source,
        details={"confirmed": True},
    )
    _clear_group_activity_state(group, status="idle")
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    if player_id and target_node_id and get_static_node(target_node_id):
        maybe_mark_player_node_visited(sess, player_id, target_node_id, source=source)
        maybe_reveal_nearby_static_nodes(sess, player_id, next_map_position, source=source)
    return dict(group)


def inspect_group_travel_target(
    sess: Session,
    group_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "manual",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True or travel_state.get("paused") is not True:
        return None
    pause_reason = str(travel_state.get("pause_reason") or "").strip().lower()
    route_summary = _normalize_group_route_summary(travel_state.get("route_summary"))
    if pause_reason != "point_of_interest_reached" or not route_summary:
        return None
    target_label = str(route_summary.get("target_label") or "")
    target_node_id = str(route_summary.get("target_node_id") or "").strip()
    inspect_result = _normalize_group_last_inspect_result(
        {
            **(
                get_static_node_inspect_result(node_id=target_node_id, source=source)
                or {
                    "node_id": target_node_id or target_label or "unknown_target",
                    "label": target_label or target_node_id or "цель",
                    "node_type": str(route_summary.get("target_node_type") or "landmark"),
                    "inspect_summary": target_label or target_node_id or "Осмотр цели завершён.",
                    "short_description": target_label or target_node_id or "Осмотр цели завершён.",
                    "source": source,
                }
            ),
            "inspected_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _set_group_last_travel_resolution(
        group,
        resolution_kind="inspect_target",
        pause_reason=pause_reason,
        target_label=target_label,
        source=source,
        details={"inspected": True},
    )
    if inspect_result:
        group["last_inspect_result"] = inspect_result
    _clear_group_activity_state(group, status="idle")
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    if player_id and target_node_id and get_static_node(target_node_id):
        grant_player_map_knowledge(sess, player_id, target_node_id, knowledge_kind="discovered", source=source)
        reveal_player_map_node(sess, player_id, target_node_id, source=source)
    return dict(group)


def bypass_group_travel_pause(sess: Session, group_id: str, *, source: str = "manual") -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True or travel_state.get("paused") is not True:
        return None
    pause_reason = str(travel_state.get("pause_reason") or "").strip().lower()
    route_summary = _normalize_group_route_summary(travel_state.get("route_summary"))
    if pause_reason != "route_blocked" or not route_summary:
        return None
    target_label = str(route_summary.get("target_label") or "")
    _set_group_last_travel_resolution(
        group,
        resolution_kind="bypass",
        pause_reason=pause_reason,
        target_label=target_label,
        source=source,
        details={"bypassed": True},
    )
    _clear_group_activity_state(group, status="idle")
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def resolve_group_travel_pause(
    sess: Session,
    group_id: str,
    *,
    resolution_kind: str | None = None,
    source: str = "manual",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True or travel_state.get("paused") is not True:
        return None
    pause_reason = str(travel_state.get("pause_reason") or "").strip().lower()
    normalized_resolution = str(resolution_kind or "").strip().lower()
    if not normalized_resolution:
        if pause_reason == "target_requires_enter":
            normalized_resolution = "confirm_enter"
        elif pause_reason == "point_of_interest_reached":
            normalized_resolution = "inspect_target"
        elif pause_reason == "route_blocked":
            normalized_resolution = "bypass"
        elif pause_reason == "event_pending":
            normalized_resolution = "resolve_pause"
    if normalized_resolution == "confirm_enter":
        return confirm_group_enter(sess, group_id, source=source)
    if normalized_resolution == "inspect_target":
        return inspect_group_travel_target(sess, group_id, source=source)
    if normalized_resolution == "bypass":
        return bypass_group_travel_pause(sess, group_id, source=source)
    if normalized_resolution == "resolve_pause" and pause_reason == "event_pending":
        route_summary = _normalize_group_route_summary(travel_state.get("route_summary")) or {}
        target_label = str(route_summary.get("target_label") or "")
        _set_group_last_travel_resolution(
            group,
            resolution_kind="resolve_pause",
            pause_reason=pause_reason,
            target_label=target_label,
            source=source,
            details={"resolved": True},
        )
        group["travel_state"]["paused"] = False
        group["travel_state"].pop("pause_reason", None)
        group["travel_state"].pop("pause_details", None)
        group["travel_state"]["resume_allowed"] = True
        group["travel_state"]["phase"] = "in_transit"
        group["status"] = "moving"
        _persist_group_states(sess, groups)
        _sync_group_position_mirrors(sess, group)
        return dict(group)
    return None


def evaluate_group_travel_pause(
    sess: Session,
    group_id: str,
    *,
    pause_reason: str | None = None,
    pause_details: dict[str, Any] | None = None,
    resume_allowed: bool = True,
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True:
        return None
    if travel_state.get("paused") is True:
        return dict(group)

    normalized_reason = _normalize_group_pause_reason(pause_reason)
    normalized_details = _normalize_group_pause_details(pause_details)
    if not normalized_reason:
        route_summary = _normalize_group_route_summary(travel_state.get("route_summary")) or {}
        target_node = _normalize_map_target_node(travel_state.get("target_node")) or {}
        target_node_type = str(target_node.get("node_type") or route_summary.get("target_node_type") or "").strip().lower()
        pause_hint = str((normalized_details or {}).get("pause_hint") or route_summary.get("pause_hint") or "").strip().lower()
        if target_node_type == "interior_entry":
            normalized_reason = "target_requires_enter"
            normalized_details = normalized_details or {"target_node_type": "interior_entry"}
        elif str(route_summary.get("route_kind") or "").strip().lower() == "landmark_move" and pause_hint == "inspection_required":
            normalized_reason = "point_of_interest_reached"
            normalized_details = normalized_details or {"pause_hint": pause_hint}
    if not normalized_reason:
        return None
    return pause_group_travel(
        sess,
        group_id,
        reason=normalized_reason,
        pause_details=normalized_details,
        resume_allowed=resume_allowed,
    )


def advance_group_travel(
    sess: Session,
    group_id: str,
    *,
    progress_step_delta: int = 1,
    phase: str | None = None,
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True:
        return None
    if travel_state.get("paused") is True:
        return None
    travel_state["progress_step"] = max(0, as_int(travel_state.get("progress_step"), 0) + max(0, int(progress_step_delta)))
    if phase:
        travel_state["phase"] = str(phase).strip().lower()[:40] or travel_state["phase"]
    group["travel_state"] = travel_state
    group["status"] = "moving"
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def complete_group_travel(
    sess: Session,
    group_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "manual",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True:
        return None
    if travel_state.get("paused") is True:
        return None
    route_summary = _normalize_group_route_summary(travel_state.get("route_summary"))
    next_map_position = _normalize_map_position((route_summary or {}).get("next_map_position"))
    next_zone_label = str((route_summary or {}).get("next_zone_label") or "").strip()
    target_node_id = str((route_summary or {}).get("target_node_id") or (next_map_position or {}).get("node_id") or "").strip()
    if not next_map_position or not next_zone_label:
        return None
    group["current_map_position"] = next_map_position
    group["area_label"] = next_zone_label[:80]
    active_event = _group_travel_event_summary(group)
    if active_event and active_event.get("active") is True:
        group["travel_event"] = {
            **active_event,
            "active": False,
            "resolved": True,
            "resolution": "resolve",
            "source": str(source or active_event.get("source") or "travel")[:40] or "travel",
        }
    _clear_group_activity_state(group, status="idle")
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    if player_id and target_node_id and get_static_node(target_node_id):
        maybe_mark_player_node_visited(sess, player_id, target_node_id, source=source)
        maybe_reveal_nearby_static_nodes(sess, player_id, next_map_position, source=source)
    return dict(group)


def interrupt_group_travel(sess: Session, group_id: str) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    travel_state = _group_travel_state_summary(group)
    if not travel_state or travel_state.get("active") is not True:
        return None
    active_event = _group_travel_event_summary(group)
    if active_event and active_event.get("active") is True:
        group["travel_event"] = {
            **active_event,
            "active": False,
            "resolved": True,
            "resolution": "ignore",
            "source": str(active_event.get("source") or "travel")[:40] or "travel",
        }
    _clear_group_activity_state(group, status="idle")
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def apply_group_route(
    sess: Session,
    group_id: str,
    route_summary: dict[str, Any] | None,
    *,
    movement_mode: str | None = None,
    source: str = "manual",
) -> dict[str, Any] | None:
    if not isinstance(route_summary, dict):
        return None
    return start_group_travel(
        sess,
        group_id,
        route_summary,
        movement_mode=movement_mode,
        source=source,
    )


def apply_group_move_target(
    sess: Session,
    group_id: str,
    target_node: dict[str, Any] | str,
    *,
    target_label: str | None = None,
    movement_mode: str | None = None,
    movement_kind: str = "move",
    source: str = "manual",
) -> dict[str, Any] | None:
    target = _normalize_map_target_node(target_node)
    next_position, next_zone_label, ok, _error = _apply_map_position_transition(
        _get_group_states(sess).get(str(group_id or "").strip(), {}).get("current_map_position"),
        target,
        "group_move",
    )
    if not ok or not next_position:
        return None
    target_node_type = str((target or {}).get("node_type") or "").strip().lower()
    traversal_kind = "entry" if movement_kind == "enter" else ("approach" if target_node_type == "landmark" else "road")
    return apply_group_route(
        sess,
        group_id,
        {
            "allowed": True,
            "route_kind": "enter" if movement_kind == "enter" else "move",
            "action_kind": movement_kind,
            "source": "fallback",
            "traversal_kind": traversal_kind,
            "risk_band": "medium",
            "terrain_hint": "mixed",
            "travel_tags": [],
            "target_node": target,
            "target_label": target_label,
            "next_map_position": next_position,
            "next_zone_label": next_zone_label,
        },
        movement_mode=movement_mode,
        source=source,
    )


def maybe_apply_group_enter_target(
    sess: Session,
    group_id: str,
    target_node: dict[str, Any] | str,
    *,
    target_label: str | None = None,
    movement_mode: str | None = None,
    source: str = "manual",
) -> dict[str, Any] | None:
    target = _normalize_map_target_node(target_node)
    if not target:
        return None
    target_node_type = str(target.get("node_type") or "").strip().lower()
    if target_node_type not in {"landmark", "building", "interior_entry"}:
        return None
    return apply_group_move_target(
        sess,
        group_id,
        target,
        target_label=target_label,
        movement_mode=movement_mode,
        movement_kind="enter",
        source=source,
    )


def request_group_split(
    group_id: str,
    member_player_ids: list[uuid.UUID | str],
    *,
    new_group_id: str | None = None,
    source: str = "manual",
    requested_by: uuid.UUID | str | None = None,
) -> dict[str, Any] | None:
    group_key = str(group_id or "").strip()[:80]
    if not group_key:
        return None
    member_ids: list[str] = []
    for item in member_player_ids:
        pid = str(item or "").strip()
        if pid and pid not in member_ids:
            member_ids.append(pid)
    if not member_ids:
        return None
    new_key = str(new_group_id or "").strip()[:80]
    payload: dict[str, Any] = {
        "group_id": group_key,
        "member_player_ids": member_ids,
        "source": str(source or "manual").strip()[:40] or "manual",
    }
    if new_key:
        payload["new_group_id"] = new_key
    requested_by_value = str(requested_by or "").strip()
    if requested_by_value:
        payload["requested_by"] = requested_by_value[:80]
    return payload


def apply_group_split(sess: Session, request: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(request, dict):
        return None
    groups = _get_group_states(sess)
    source_key = str(request.get("group_id") or "").strip()
    source_group = groups.get(source_key)
    if not source_group:
        return None

    split_members: list[str] = []
    for item in request.get("member_player_ids") or []:
        pid = str(item or "").strip()
        if pid and pid in source_group["player_ids"] and pid not in split_members:
            split_members.append(pid)
    if not split_members or len(split_members) >= len(source_group["player_ids"]):
        return None

    new_key = str(request.get("new_group_id") or f"{source_group['group_id']}_split_{len(groups) + 1}").strip()[:80]
    if not new_key or new_key in groups:
        return None

    source_group["player_ids"] = [pid for pid in source_group["player_ids"] if pid not in split_members]
    _clear_group_activity_state(source_group)
    new_group = {
        "group_id": new_key,
        "player_ids": split_members,
        "current_map_position": dict(source_group["current_map_position"]),
        "area_label": str(source_group["area_label"]),
        "status": "idle",
    }
    groups[new_key] = new_group
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, source_group)
    _sync_group_position_mirrors(sess, new_group)
    return dict(new_group)


def request_group_merge(
    target_group_id: str,
    source_group_id: str,
    *,
    source: str = "manual",
    requested_by: uuid.UUID | str | None = None,
) -> dict[str, Any] | None:
    target_key = str(target_group_id or "").strip()[:80]
    source_key = str(source_group_id or "").strip()[:80]
    if not target_key or not source_key or target_key == source_key:
        return None
    payload: dict[str, Any] = {
        "target_group_id": target_key,
        "source_group_id": source_key,
        "source": str(source or "manual").strip()[:40] or "manual",
    }
    requested_by_value = str(requested_by or "").strip()
    if requested_by_value:
        payload["requested_by"] = requested_by_value[:80]
    return payload


def apply_group_merge(sess: Session, request: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(request, dict):
        return None
    groups = _get_group_states(sess)
    target_key = str(request.get("target_group_id") or "").strip()
    source_key = str(request.get("source_group_id") or "").strip()
    target_group = groups.get(target_key)
    source_group = groups.get(source_key)
    if not target_group or not source_group or target_key == source_key:
        return None

    target_pos = target_group.get("current_map_position")
    source_pos = source_group.get("current_map_position")
    if target_pos and source_pos and not _map_position_identity_equals(target_pos, source_pos):
        return None

    for pid in source_group.get("player_ids", []):
        if pid not in target_group["player_ids"]:
            target_group["player_ids"].append(pid)

    target_wait = _group_wait_summary(target_group)
    source_wait = _group_wait_summary(source_group)
    target_camp = _group_camp_summary(target_group)
    source_camp = _group_camp_summary(source_group)
    target_movement = _group_movement_intent_summary(target_group)
    source_movement = _group_movement_intent_summary(source_group)
    if target_camp or source_camp:
        _apply_group_activity_state(
            target_group,
            status="camping",
            camp_state=target_camp or source_camp,
        )
    elif target_wait or source_wait:
        _apply_group_activity_state(
            target_group,
            status="waiting",
            wait_state=target_wait or source_wait,
        )
    elif target_movement or source_movement:
        _apply_group_activity_state(
            target_group,
            status="moving_intent",
            movement_intent=target_movement or source_movement,
        )
    else:
        _clear_group_activity_state(target_group)

    groups.pop(source_key, None)
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, target_group)
    return dict(target_group)


def _set_group_map_position(
    sess: Session,
    group_id: str,
    position: dict[str, Any] | str,
    *,
    status: str | None = None,
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    pos = _normalize_map_position(position)
    if not group or not pos:
        return None
    group["current_map_position"] = pos
    group["area_label"] = _map_position_area_label(pos)
    if status is not None:
        group["status"] = _normalize_group_status(status)
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def _split_group(
    sess: Session,
    group_id: str,
    member_player_ids: list[uuid.UUID | str],
    *,
    new_group_id: str | None = None,
) -> dict[str, Any] | None:
    request = request_group_split(group_id, member_player_ids, new_group_id=new_group_id)
    return apply_group_split(sess, request)


def _merge_groups(
    sess: Session,
    target_group_id: str,
    source_group_id: str,
) -> dict[str, Any] | None:
    request = request_group_merge(target_group_id, source_group_id)
    return apply_group_merge(sess, request)


def _same_player_map_position(
    sess: Session,
    left_player_id: uuid.UUID | str,
    right_player_id: uuid.UUID | str,
) -> bool:
    left_group_id = _get_player_group_id(sess, left_player_id)
    right_group_id = _get_player_group_id(sess, right_player_id)
    if left_group_id and right_group_id and left_group_id == right_group_id:
        return True

    left_position = _get_player_map_position(sess, left_player_id)
    right_position = _get_player_map_position(sess, right_player_id)
    if left_position or right_position:
        return _map_position_identity_equals(left_position, right_position)

    left_zone = _get_player_position_label(sess, left_player_id).strip()
    right_zone = _get_player_position_label(sess, right_player_id).strip()
    return bool(left_zone and right_zone and left_zone == right_zone)


def _set_player_map_position(sess: Session, player_id: uuid.UUID, position: dict[str, Any] | str) -> None:
    pos = _normalize_map_position(position)
    if not pos:
        return
    pid = str(player_id)
    group_id = _get_player_group_id(sess, pid, [pid])
    if group_id:
        _set_group_map_position(sess, group_id, pos)
        return

    positions = dict(_raw_player_map_positions(sess))
    positions[pid] = pos
    settings_set(sess, "map_positions", positions)

    legacy = dict(_raw_pc_positions(sess))
    legacy[pid] = _map_position_area_label(pos)
    settings_set(sess, "pc_positions", legacy)


def _clear_player_map_position(sess: Session, player_id: uuid.UUID | str) -> None:
    pid = str(player_id)
    positions = dict(_raw_player_map_positions(sess))
    if pid in positions:
        positions.pop(pid, None)
    settings_set(sess, "map_positions", positions)

    legacy_positions = dict(_raw_pc_positions(sess))
    if pid in legacy_positions:
        legacy_positions.pop(pid, None)
    settings_set(sess, "pc_positions", legacy_positions)

    groups = _get_group_states(sess)
    changed = False
    for group_id, group in list(groups.items()):
        members = [member for member in group.get("player_ids", []) if member != pid]
        if len(members) == len(group.get("player_ids", [])):
            continue
        changed = True
        if not members:
            groups.pop(group_id, None)
            continue
        group["player_ids"] = members
        _sync_group_position_mirrors(sess, group)
    if changed:
        _persist_group_states(sess, groups)


def _initialize_map_positions(
    sess: Session,
    player_ids: list[uuid.UUID],
    default_position: dict[str, Any] | str,
) -> None:
    pos = _normalize_map_position(default_position) or _default_map_position("стартовая локация")
    map_positions: dict[str, dict[str, Any]] = {}
    legacy_positions: dict[str, str] = {}
    for pid in player_ids:
        pid_str = str(pid)
        map_positions[pid_str] = dict(pos)
        legacy_positions[pid_str] = _map_position_area_label(pos)
    settings_set(sess, "map_positions", map_positions)
    settings_set(sess, "pc_positions", legacy_positions)
    _initialize_default_group(sess, [str(pid) for pid in player_ids], pos)


def _get_pc_positions(sess: Session) -> dict[str, str]:
    groups = _get_group_states(sess)
    if groups:
        out: dict[str, str] = {}
        for group in groups.values():
            area_label = str(group.get("area_label") or "").strip()
            current_pos = group.get("current_map_position")
            zone = area_label or _map_position_area_label(current_pos)
            for pid in group.get("player_ids", []):
                out[str(pid)] = zone[:80]
        if out:
            return out

    # Prefer new structured positions if they already exist.
    map_positions = _raw_player_map_positions(sess)
    if map_positions:
        return {pid: _map_position_area_label(pos) for pid, pos in map_positions.items()}

    # Legacy fallback.
    return _raw_pc_positions(sess)


def _set_pc_zone(sess: Session, player_id: uuid.UUID, zone: str) -> None:
    z = str(zone or "").strip()
    if not z:
        return
    _set_player_map_position(sess, player_id, _default_map_position(z))


def _initialize_pc_positions(sess: Session, player_ids: list[uuid.UUID], default_zone: str) -> None:
    zone = str(default_zone or "").strip() or "стартовая локация"
    _initialize_map_positions(sess, player_ids, _default_map_position(zone))


def _get_phase(sess: Session) -> str:
    phase = str(settings_get(sess, "phase", "turns") or "turns").strip().lower()
    if phase not in {"lore_pending", "collecting_actions", "gm_pending", "turns"}:
        return "turns"
    return phase


def _set_phase(sess: Session, phase: str) -> None:
    settings_set(sess, "phase", str(phase).strip().lower())
