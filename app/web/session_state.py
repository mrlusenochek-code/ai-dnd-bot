import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Session
from app.web.map_registry import (
    STATIC_MAP_NODES,
    build_static_route_id,
    get_static_map_links,
    get_current_node_context_actions,
    get_obvious_linked_static_node_ids,
    get_static_node_context_action_effects,
    get_static_node_context_action_requirements,
    get_static_node_destination_events,
    get_static_node_entry_overlays,
    get_static_node_service_effects,
    get_static_node_service_requirements,
    get_static_node_state_overlays,
    get_static_node_scout_discoveries,
    get_static_node_region_gateways,
    get_static_navigation_options,
    get_static_node_detail,
    get_static_node,
    get_static_node_context,
    get_static_node_inspect_result,
    get_static_node_service_result,
    get_static_node_services,
    get_static_region_gateways,
    get_static_region_identity,
    get_static_region_onboarding,
    get_static_region_anchor_onboarding,
    resolve_static_map_node,
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


def _static_node_map_position(node: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(node, dict):
        return None
    node_id = str(node.get("node_id") or "").strip()
    label = str(node.get("label") or node_id).strip()
    if not node_id or not label:
        return None
    node_type = str(node.get("node_type") or "zone").strip().lower()
    if node_type not in {"zone", "landmark", "building", "interior_entry"}:
        node_type = "zone"
    map_level = str(node.get("map_level") or "").strip().lower() or _default_map_level_for_node_type(node_type)
    area_label = str(node.get("area_label") or "").strip()
    normalized = {
        "v": 1,
        "map_level": map_level[:32],
        "node_type": node_type[:32],
        "node_id": node_id[:120],
        "label": label[:80],
    }
    if area_label:
        normalized["area_label"] = area_label[:80]
    return normalized


def _static_zone_map_position_from_text(text: str | None) -> dict[str, Any] | None:
    node = resolve_static_map_node(text)
    node_type = str((node or {}).get("node_type") or "").strip().lower()
    if node_type != "zone":
        return None
    return _static_node_map_position(node)


def _default_map_position(zone_label: str = "стартовая локация") -> dict[str, Any]:
    label = str(zone_label or "").strip() or "стартовая локация"
    static_position = _static_zone_map_position_from_text(label)
    if static_position:
        return static_position
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
    raw_node_id = node_id

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

    is_label_based_zone = (
        node_type == "zone"
        and (
            not raw_node_id
            or (label and raw_node_id.strip().casefold() == label.strip().casefold())
        )
    )
    static_position = _static_zone_map_position_from_text(node_id) if is_label_based_zone else None
    if static_position:
        return static_position

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


def _normalize_group_last_camp_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type not in {"safe_rest", "uneasy_rest", "interrupted_rest", "roadside_pause", "sheltered_rest"}:
        return None
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or "").strip()
    node_id = str(raw.get("node_id") or "").strip()
    node_label = str(raw.get("node_label") or node_id).strip()
    rest_quality = str(raw.get("rest_quality") or "").strip().lower()
    if rest_quality not in {"restful", "sheltered", "uneasy", "interrupted", "brief"}:
        return None
    risk_band = str(raw.get("risk_band") or "").strip().lower()
    if risk_band not in {"low", "medium", "high"}:
        risk_band = "medium"
    source = str(raw.get("source") or "camp").strip() or "camp"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if not result_id or not summary or not result_summary or not node_id or not node_label:
        return None
    applied_effects_raw = raw.get("applied_effects")
    applied_effects = (
        [str(item).strip()[:120] for item in applied_effects_raw if str(item or "").strip()]
        if isinstance(applied_effects_raw, list)
        else []
    )
    result: dict[str, Any] = {
        "result_id": result_id[:80],
        "result_type": result_type[:40],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "rest_quality": rest_quality[:40],
        "risk_band": risk_band[:20],
        "source": source[:40],
        "applied_effects": applied_effects,
    }
    if resolved_at:
        result["resolved_at"] = resolved_at[:80]
    return result


def _normalize_group_last_scout_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type not in {"no_new_findings", "route_revealed", "landmark_revealed", "hidden_path_revealed", "local_clue_found"}:
        return None
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or "").strip()
    node_id = str(raw.get("node_id") or "").strip()
    node_label = str(raw.get("node_label") or node_id).strip()
    discovery_scope = str(raw.get("discovery_scope") or "").strip().lower()
    if discovery_scope not in {"none", "adjacent_route", "adjacent_landmark", "hidden_route", "local_area"}:
        discovery_scope = "none"
    source = str(raw.get("source") or "scout").strip() or "scout"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if not result_id or not summary or not result_summary or not node_id or not node_label:
        return None
    discovered_node_ids = [
        str(node_id_value).strip()[:120]
        for node_id_value in (raw.get("discovered_node_ids") or [])
        if str(node_id_value or "").strip()
    ] if isinstance(raw.get("discovered_node_ids"), list) else []
    discovered_route_ids = [
        str(route_id).strip()[:120]
        for route_id in (raw.get("discovered_route_ids") or [])
        if str(route_id or "").strip()
    ] if isinstance(raw.get("discovered_route_ids"), list) else []
    discovered_notes = [
        str(note).strip()[:240]
        for note in (raw.get("discovered_notes") or [])
        if str(note or "").strip()
    ] if isinstance(raw.get("discovered_notes"), list) else []
    result: dict[str, Any] = {
        "result_id": result_id[:80],
        "result_type": result_type[:40],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "discovery_scope": discovery_scope[:40],
        "discovered_node_ids": discovered_node_ids,
        "discovered_route_ids": discovered_route_ids,
        "discovered_notes": discovered_notes,
        "reveal_applied": bool(raw.get("reveal_applied")),
        "source": source[:40],
    }
    if resolved_at:
        result["resolved_at"] = resolved_at[:80]
    return result


def _normalize_group_last_context_action_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    action_id = str(raw.get("action_id") or "").strip().lower()
    action_label = str(raw.get("action_label") or action_id).strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type not in {"route_cleared", "route_still_blocked", "local_clue_found", "local_support_applied", "no_effect", "already_completed"}:
        return None
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or "").strip()
    node_id = str(raw.get("node_id") or "").strip()
    node_label = str(raw.get("node_label") or node_id).strip()
    source = str(raw.get("source") or "context_action").strip() or "context_action"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if not result_id or not action_id or not action_label or not summary or not result_summary or not node_id or not node_label:
        return None
    applied_effects = [
        str(item).strip()[:120]
        for item in (raw.get("applied_effects") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("applied_effects"), list) else []
    result: dict[str, Any] = {
        "result_id": result_id[:80],
        "action_id": action_id[:80],
        "action_label": action_label[:120],
        "result_type": result_type[:40],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "applied_effects": applied_effects,
        "source": source[:40],
    }
    if resolved_at:
        result["resolved_at"] = resolved_at[:80]
    return result


def _normalize_group_context_action_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    action_id = str(raw.get("action_id") or "").strip().lower()
    status = str(raw.get("status") or "").strip().lower()
    if status not in {"available", "completed", "resolved"}:
        return None
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type and result_type not in {"route_cleared", "route_still_blocked", "local_clue_found", "local_support_applied", "no_effect", "already_completed"}:
        return None
    summary = str(raw.get("summary") or "").strip()
    source = str(raw.get("source") or "context_action").strip() or "context_action"
    updated_at = str(raw.get("updated_at") or "").strip()
    if not action_id or not summary:
        return None
    state: dict[str, Any] = {
        "action_id": action_id[:80],
        "status": status[:40],
        "summary": summary[:240],
        "source": source[:40],
    }
    if result_type:
        state["result_type"] = result_type[:40]
    if updated_at:
        state["updated_at"] = updated_at[:80]
    return state


def _normalize_group_context_action_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for action_id, value in raw.items():
        candidate = value if isinstance(value, dict) else {"action_id": action_id, "status": value, "summary": str(value or action_id)}
        merged = {"action_id": action_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_context_action_state(merged)
        if state:
            normalized[state["action_id"]] = state
    return normalized


def _normalize_group_route_access_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    route_id = str(raw.get("route_id") or "").strip().lower()
    access_state = str(raw.get("access_state") or "").strip().lower()
    if access_state not in {"open", "blocked", "cleared"}:
        return None
    summary = str(raw.get("summary") or "").strip()
    source = str(raw.get("source") or "route_access").strip() or "route_access"
    updated_at = str(raw.get("updated_at") or "").strip()
    if not route_id or not summary:
        return None
    block_reason = str(raw.get("block_reason") or "").strip()
    is_traversable = access_state in {"open", "cleared"}
    state: dict[str, Any] = {
        "route_id": route_id[:160],
        "access_state": access_state[:40],
        "is_traversable": bool(raw.get("is_traversable", is_traversable)) if access_state == "blocked" else is_traversable,
        "summary": summary[:240],
        "source": source[:40],
    }
    state["is_traversable"] = access_state in {"open", "cleared"}
    if block_reason:
        state["block_reason"] = block_reason[:120]
    if updated_at:
        state["updated_at"] = updated_at[:80]
    return state


def _normalize_group_route_access_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for route_id, value in raw.items():
        candidate = value if isinstance(value, dict) else {"route_id": route_id, "access_state": value, "summary": str(value or route_id)}
        merged = {"route_id": route_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_route_access_state(merged)
        if state:
            normalized[state["route_id"]] = state
    return normalized


def _normalize_group_node_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    node_id = str(raw.get("node_id") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    source = str(raw.get("source") or "node_state").strip() or "node_state"
    updated_at = str(raw.get("updated_at") or "").strip()
    if not node_id or not summary:
        return None
    state_flags = [
        str(flag).strip().lower()[:80]
        for flag in (raw.get("state_flags") or [])
        if str(flag or "").strip()
    ] if isinstance(raw.get("state_flags"), list) else []
    deduped_flags: list[str] = []
    for flag in state_flags:
        if flag and flag not in deduped_flags:
            deduped_flags.append(flag)
    state: dict[str, Any] = {
        "node_id": node_id[:120],
        "state_flags": deduped_flags,
        "summary": summary[:240],
        "source": source[:40],
    }
    if updated_at:
        state["updated_at"] = updated_at[:80]
    return state


def _normalize_group_last_arrival_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type not in {"first_arrival", "return_arrival", "settlement_arrival", "landmark_arrival", "quiet_arrival"}:
        return None
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or "").strip()
    node_id = str(raw.get("node_id") or "").strip()
    node_label = str(raw.get("node_label") or node_id).strip()
    route_id = str(raw.get("route_id") or "").strip().lower()
    source = str(raw.get("source") or "arrival").strip() or "arrival"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    visit_count = max(0, as_int(raw.get("visit_count"), 0))
    if not result_id or not summary or not result_summary or not node_id or not node_label or visit_count <= 0:
        return None
    applied_effects = [
        str(item).strip()[:120]
        for item in (raw.get("applied_effects") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("applied_effects"), list) else []
    result: dict[str, Any] = {
        "result_id": result_id[:80],
        "result_type": result_type[:40],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "route_id": route_id[:160],
        "first_visit": bool(raw.get("first_visit")),
        "visit_count": visit_count,
        "source": source[:40],
        "applied_effects": applied_effects,
    }
    if resolved_at:
        result["resolved_at"] = resolved_at[:80]
    return result


def _normalize_group_node_visit_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    node_id = str(raw.get("node_id") or "").strip().lower()
    node_label = str(raw.get("node_label") or node_id).strip()
    visit_count = max(0, as_int(raw.get("visit_count"), 0))
    first_visited_at = str(raw.get("first_visited_at") or "").strip()
    last_visited_at = str(raw.get("last_visited_at") or "").strip()
    last_result_type = str(raw.get("last_result_type") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    if not node_id or not node_label or visit_count <= 0:
        return None
    state: dict[str, Any] = {
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "visit_count": visit_count,
        "last_result_type": last_result_type[:40],
        "summary": summary[:240],
    }
    if first_visited_at:
        state["first_visited_at"] = first_visited_at[:80]
    if last_visited_at:
        state["last_visited_at"] = last_visited_at[:80]
    return state


def _normalize_group_node_visit_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for node_id, value in raw.items():
        candidate = value if isinstance(value, dict) else {"node_id": node_id, "visit_count": 1, "summary": str(value or node_id)}
        merged = {"node_id": node_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_node_visit_state(merged)
        if state:
            normalized[state["node_id"]] = state
    return normalized


def _normalize_group_last_node_entry_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type not in {"first_entry", "return_entry", "settlement_welcome", "landmark_reached", "changed_place", "quiet_entry"}:
        return None
    title = str(raw.get("title") or "").strip()
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or summary).strip()
    node_id = str(raw.get("node_id") or "").strip().lower()
    node_label = str(raw.get("node_label") or node_id).strip()
    visit_count = max(0, as_int(raw.get("visit_count"), 0))
    source = str(raw.get("source") or "node_entry").strip() or "node_entry"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if not result_id or not title or not summary or not result_summary or not node_id or not node_label or visit_count <= 0:
        return None
    node_state_flags = [
        str(item).strip().lower()[:80]
        for item in (raw.get("node_state_flags") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("node_state_flags"), list) else []
    applied_effects = [
        str(item).strip()[:120]
        for item in (raw.get("applied_effects") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("applied_effects"), list) else []
    result: dict[str, Any] = {
        "result_id": result_id[:80],
        "result_type": result_type[:40],
        "title": title[:160],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "visit_count": visit_count,
        "first_visit": bool(raw.get("first_visit")),
        "node_state_flags": node_state_flags,
        "applied_effects": applied_effects,
        "source": source[:40],
    }
    if resolved_at:
        result["resolved_at"] = resolved_at[:80]
    return result


def _normalize_group_node_entry_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    node_id = str(raw.get("node_id") or "").strip().lower()
    node_label = str(raw.get("node_label") or node_id).strip()
    entry_count = max(0, as_int(raw.get("entry_count"), 0))
    last_entry_type = str(raw.get("last_entry_type") or "").strip().lower()
    if last_entry_type and last_entry_type not in {"first_entry", "return_entry", "settlement_welcome", "landmark_reached", "changed_place", "quiet_entry"}:
        return None
    summary = str(raw.get("summary") or "").strip()
    source = str(raw.get("source") or "node_entry").strip() or "node_entry"
    updated_at = str(raw.get("updated_at") or "").strip()
    if not node_id or not node_label or entry_count <= 0 or not summary:
        return None
    state: dict[str, Any] = {
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "entry_count": entry_count,
        "summary": summary[:240],
        "source": source[:40],
    }
    if last_entry_type:
        state["last_entry_type"] = last_entry_type[:40]
    if updated_at:
        state["updated_at"] = updated_at[:80]
    return state


def _normalize_group_node_entry_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for node_id, value in raw.items():
        candidate = value if isinstance(value, dict) else {"node_id": node_id, "entry_count": 1, "summary": str(value or node_id)}
        merged = {"node_id": node_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_node_entry_state(merged)
        if state:
            normalized[state["node_id"]] = state
    return normalized


def _normalize_group_last_destination_event_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    event_id = str(raw.get("event_id") or "").strip().lower()
    event_label = str(raw.get("event_label") or event_id).strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type not in {
        "local_notice",
        "first_discovery",
        "local_warning",
        "settlement_notice",
        "changed_place_notice",
        "no_event",
        "already_resolved",
    }:
        return None
    title = str(raw.get("title") or "").strip()
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or summary).strip()
    node_id = str(raw.get("node_id") or "").strip().lower()
    node_label = str(raw.get("node_label") or node_id).strip()
    visit_count = max(0, as_int(raw.get("visit_count"), 0))
    source = str(raw.get("source") or "destination_event").strip() or "destination_event"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if not result_id or not event_id or not event_label or not title or not summary or not result_summary or not node_id or not node_label or visit_count <= 0:
        return None
    applied_effects = [
        str(item).strip()[:120]
        for item in (raw.get("applied_effects") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("applied_effects"), list) else []
    result: dict[str, Any] = {
        "result_id": result_id[:80],
        "event_id": event_id[:120],
        "event_label": event_label[:160],
        "result_type": result_type[:40],
        "title": title[:160],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "visit_count": visit_count,
        "first_visit": bool(raw.get("first_visit")),
        "applied_effects": applied_effects,
        "source": source[:40],
    }
    if resolved_at:
        result["resolved_at"] = resolved_at[:80]
    return result


def _normalize_group_destination_event_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    event_id = str(raw.get("event_id") or "").strip().lower()
    node_id = str(raw.get("node_id") or "").strip().lower()
    status = str(raw.get("status") or "").strip().lower()
    if status not in {"completed", "resolved", "no_event"}:
        return None
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type and result_type not in {
        "local_notice",
        "first_discovery",
        "local_warning",
        "settlement_notice",
        "changed_place_notice",
        "no_event",
        "already_resolved",
    }:
        return None
    summary = str(raw.get("summary") or "").strip()
    source = str(raw.get("source") or "destination_event").strip() or "destination_event"
    updated_at = str(raw.get("updated_at") or "").strip()
    if not event_id or not node_id or not summary:
        return None
    state: dict[str, Any] = {
        "event_id": event_id[:120],
        "node_id": node_id[:120],
        "status": status[:40],
        "summary": summary[:240],
        "source": source[:40],
    }
    if result_type:
        state["result_type"] = result_type[:40]
    if updated_at:
        state["updated_at"] = updated_at[:80]
    return state


def _normalize_group_destination_event_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for node_id, value in raw.items():
        candidate = value if isinstance(value, dict) else {"node_id": node_id, "event_id": node_id, "status": "resolved", "summary": str(value or node_id)}
        merged = {"node_id": node_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_destination_event_state(merged)
        if state:
            normalized[state["node_id"]] = state
    return normalized


def _normalize_group_last_region_transition_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    gateway_id = str(raw.get("gateway_id") or "").strip().lower()
    gateway_label = str(raw.get("gateway_label") or gateway_id).strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or summary).strip()
    source_region_id = str(raw.get("source_region_id") or "").strip().lower()
    source_region_label = str(raw.get("source_region_label") or source_region_id).strip()
    source_node_id = str(raw.get("source_node_id") or "").strip().lower()
    target_region_id = str(raw.get("target_region_id") or "").strip().lower()
    target_region_label = str(raw.get("target_region_label") or target_region_id).strip()
    target_anchor_node_id = str(raw.get("target_anchor_node_id") or "").strip().lower()
    transition_status = str(raw.get("transition_status") or "").strip().lower()
    applied_effects = [
        str(item).strip()
        for item in (raw.get("applied_effects") or [])
        if str(item or "").strip()
    ]
    source = str(raw.get("source") or "region_transition").strip() or "region_transition"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if result_type not in {
        "region_transition_completed",
        "region_transition_blocked",
        "region_transition_locked",
        "region_transition_future_stub",
        "region_transition_unavailable",
        "region_transition_invalid",
    }:
        return None
    if transition_status not in {"completed", "blocked", "locked", "future_stub", "unavailable", "invalid"}:
        return None
    if not result_id or not gateway_id or not gateway_label or not summary or not result_summary or not source_region_id or not source_region_label or not source_node_id or not target_region_id or not target_region_label:
        return None
    result = {
        "result_id": result_id[:120],
        "gateway_id": gateway_id[:120],
        "gateway_label": gateway_label[:160],
        "result_type": result_type[:60],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "source_region_id": source_region_id[:120],
        "source_region_label": source_region_label[:160],
        "source_node_id": source_node_id[:120],
        "target_region_id": target_region_id[:120],
        "target_region_label": target_region_label[:160],
        "target_anchor_node_id": target_anchor_node_id[:120],
        "transition_status": transition_status[:40],
        "applied_effects": applied_effects,
        "source": source[:40],
    }
    if resolved_at:
        result["resolved_at"] = resolved_at[:80]
    return result


def _normalize_group_region_transition_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    last_gateway_id = str(raw.get("last_gateway_id") or "").strip().lower()
    last_result_type = str(raw.get("last_result_type") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    updated_at = str(raw.get("updated_at") or "").strip()
    if last_result_type not in {
        "region_transition_completed",
        "region_transition_blocked",
        "region_transition_locked",
        "region_transition_future_stub",
        "region_transition_unavailable",
        "region_transition_invalid",
    }:
        return None
    if not last_gateway_id or not summary:
        return None
    state = {
        "last_gateway_id": last_gateway_id[:120],
        "last_result_type": last_result_type[:60],
        "summary": summary[:240],
    }
    if updated_at:
        state["updated_at"] = updated_at[:80]
    return state


def _normalize_group_current_region_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    region_id = str(raw.get("region_id") or "").strip().lower()
    region_label = str(raw.get("region_label") or region_id).strip()
    current_node_id = str(raw.get("current_node_id") or "").strip().lower()
    entered_at = str(raw.get("entered_at") or "").strip()
    visit_count = max(0, as_int(raw.get("visit_count"), 0))
    source = str(raw.get("source") or "region_residency").strip() or "region_residency"
    if not region_id or not region_label or not current_node_id or visit_count <= 0:
        return None
    state: dict[str, Any] = {
        "region_id": region_id[:120],
        "region_label": region_label[:160],
        "current_node_id": current_node_id[:120],
        "visit_count": visit_count,
        "source": source[:40],
    }
    if entered_at:
        state["entered_at"] = entered_at[:80]
    return state


def _build_region_link_id(region_a_id: str, region_b_id: str) -> str:
    left = str(region_a_id or "").strip().lower()
    right = str(region_b_id or "").strip().lower()
    if not left or not right:
        return ""
    ordered = sorted([left, right])
    return f"region-link:{ordered[0]}::{ordered[1]}"


def _normalize_group_gateway_traversal_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    gateway_id = str(raw.get("gateway_id") or "").strip().lower()
    gateway_label = str(raw.get("gateway_label") or gateway_id).strip()
    source_region_id = str(raw.get("source_region_id") or "").strip().lower()
    source_region_label = str(raw.get("source_region_label") or source_region_id).strip()
    target_region_id = str(raw.get("target_region_id") or "").strip().lower()
    target_region_label = str(raw.get("target_region_label") or target_region_id).strip()
    traversal_count = max(0, as_int(raw.get("traversal_count"), 0))
    first_traversed_at = str(raw.get("first_traversed_at") or "").strip()
    last_traversed_at = str(raw.get("last_traversed_at") or "").strip()
    summary = str(raw.get("summary") or "").strip()
    if (
        not gateway_id
        or not gateway_label
        or not source_region_id
        or not source_region_label
        or not target_region_id
        or not target_region_label
        or traversal_count <= 0
        or not summary
    ):
        return None
    normalized: dict[str, Any] = {
        "gateway_id": gateway_id[:120],
        "gateway_label": gateway_label[:160],
        "source_region_id": source_region_id[:120],
        "source_region_label": source_region_label[:160],
        "target_region_id": target_region_id[:120],
        "target_region_label": target_region_label[:160],
        "traversal_count": traversal_count,
        "summary": summary[:240],
    }
    if first_traversed_at:
        normalized["first_traversed_at"] = first_traversed_at[:80]
    if last_traversed_at:
        normalized["last_traversed_at"] = last_traversed_at[:80]
    return normalized


def _normalize_group_gateway_traversal_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for gateway_id, value in raw.items():
        candidate = value if isinstance(value, dict) else {"gateway_id": gateway_id, "summary": str(value or gateway_id)}
        merged = {"gateway_id": gateway_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_gateway_traversal_state(merged)
        if state:
            normalized[state["gateway_id"]] = state
    return normalized


def _normalize_group_region_link_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    link_id = str(raw.get("link_id") or "").strip().lower()
    region_a_id = str(raw.get("region_a_id") or "").strip().lower()
    region_a_label = str(raw.get("region_a_label") or region_a_id).strip()
    region_b_id = str(raw.get("region_b_id") or "").strip().lower()
    region_b_label = str(raw.get("region_b_label") or region_b_id).strip()
    gateway_ids = [
        str(item).strip().lower()
        for item in (raw.get("gateway_ids") or [])
        if str(item or "").strip()
    ]
    traversal_count = max(0, as_int(raw.get("traversal_count"), 0))
    first_discovered_at = str(raw.get("first_discovered_at") or "").strip()
    last_traversed_at = str(raw.get("last_traversed_at") or "").strip()
    summary = str(raw.get("summary") or "").strip()
    expected_link_id = _build_region_link_id(region_a_id, region_b_id)
    if (
        not link_id
        or not region_a_id
        or not region_a_label
        or not region_b_id
        or not region_b_label
        or traversal_count <= 0
        or not summary
        or not expected_link_id
        or link_id != expected_link_id
    ):
        return None
    return {
        "link_id": link_id[:160],
        "region_a_id": region_a_id[:120],
        "region_a_label": region_a_label[:160],
        "region_b_id": region_b_id[:120],
        "region_b_label": region_b_label[:160],
        "gateway_ids": gateway_ids,
        "traversal_count": traversal_count,
        "first_discovered_at": first_discovered_at[:80],
        "last_traversed_at": last_traversed_at[:80],
        "summary": summary[:240],
    }


def _normalize_group_region_link_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for link_id, value in raw.items():
        candidate = value if isinstance(value, dict) else {"link_id": link_id, "summary": str(value or link_id)}
        merged = {"link_id": link_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_region_link_state(merged)
        if state:
            normalized[state["link_id"]] = state
    return normalized


def _normalize_group_last_region_link_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or summary).strip()
    gateway_id = str(raw.get("gateway_id") or "").strip().lower()
    gateway_label = str(raw.get("gateway_label") or gateway_id).strip()
    link_id = str(raw.get("link_id") or "").strip().lower()
    source_region_id = str(raw.get("source_region_id") or "").strip().lower()
    target_region_id = str(raw.get("target_region_id") or "").strip().lower()
    traversal_count = max(0, as_int(raw.get("traversal_count"), 0))
    source = str(raw.get("source") or "region_link_history").strip() or "region_link_history"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if result_type not in {
        "first_gateway_crossing",
        "repeated_gateway_crossing",
        "first_region_link_discovered",
        "known_region_link_traversed",
        "quiet_region_link_update",
    }:
        return None
    if (
        not result_id
        or not summary
        or not result_summary
        or not gateway_id
        or not gateway_label
        or not link_id
        or not source_region_id
        or not target_region_id
        or traversal_count <= 0
    ):
        return None
    normalized = {
        "result_id": result_id[:120],
        "result_type": result_type[:60],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "gateway_id": gateway_id[:120],
        "gateway_label": gateway_label[:160],
        "link_id": link_id[:160],
        "source_region_id": source_region_id[:120],
        "target_region_id": target_region_id[:120],
        "traversal_count": traversal_count,
        "source": source[:40],
    }
    if resolved_at:
        normalized["resolved_at"] = resolved_at[:80]
    return normalized


def _normalize_group_discovered_region(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    region_id = str(raw.get("region_id") or "").strip().lower()
    region_label = str(raw.get("region_label") or region_id).strip()
    visit_count = max(0, as_int(raw.get("visit_count"), 0))
    first_entered_at = str(raw.get("first_entered_at") or "").strip()
    last_entered_at = str(raw.get("last_entered_at") or "").strip()
    first_anchor_node_id = str(raw.get("first_anchor_node_id") or "").strip().lower()
    last_anchor_node_id = str(raw.get("last_anchor_node_id") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    if not region_id or not region_label or visit_count <= 0 or not summary:
        return None
    state: dict[str, Any] = {
        "region_id": region_id[:120],
        "region_label": region_label[:160],
        "visit_count": visit_count,
        "first_anchor_node_id": first_anchor_node_id[:120],
        "last_anchor_node_id": last_anchor_node_id[:120],
        "summary": summary[:240],
    }
    if first_entered_at:
        state["first_entered_at"] = first_entered_at[:80]
    if last_entered_at:
        state["last_entered_at"] = last_entered_at[:80]
    return state


def _normalize_group_discovered_region_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for region_id, value in raw.items():
        candidate = (
            value
            if isinstance(value, dict)
            else {
                "region_id": region_id,
                "region_label": str(value or region_id),
                "visit_count": 1,
                "summary": str(value or region_id),
            }
        )
        merged = {"region_id": region_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_discovered_region(merged)
        if state:
            normalized[state["region_id"]] = state
    return normalized


def _normalize_group_last_region_entry_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or summary).strip()
    region_id = str(raw.get("region_id") or "").strip().lower()
    region_label = str(raw.get("region_label") or region_id).strip()
    anchor_node_id = str(raw.get("anchor_node_id") or "").strip().lower()
    visit_count = max(0, as_int(raw.get("visit_count"), 0))
    first_region_visit = bool(raw.get("first_region_visit"))
    source = str(raw.get("source") or "region_residency").strip() or "region_residency"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if result_type not in {
        "first_region_entry",
        "return_region_entry",
        "current_region_confirmed",
        "region_transition_entry",
        "quiet_region_entry",
    }:
        return None
    if not result_id or not summary or not result_summary or not region_id or not region_label or not anchor_node_id or visit_count <= 0:
        return None
    result: dict[str, Any] = {
        "result_id": result_id[:120],
        "result_type": result_type[:60],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "region_id": region_id[:120],
        "region_label": region_label[:160],
        "anchor_node_id": anchor_node_id[:120],
        "first_region_visit": first_region_visit,
        "visit_count": visit_count,
        "source": source[:40],
    }
    if resolved_at:
        result["resolved_at"] = resolved_at[:80]
    return result


def _normalize_group_last_region_onboarding_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or summary).strip()
    region_id = str(raw.get("region_id") or "").strip().lower()
    region_label = str(raw.get("region_label") or region_id).strip()
    anchor_node_id = str(raw.get("anchor_node_id") or "").strip().lower()
    revealed_node_ids = [
        str(item).strip().lower()
        for item in (raw.get("revealed_node_ids") or [])
        if str(item or "").strip()
    ]
    revealed_route_ids = [
        str(item).strip().lower()
        for item in (raw.get("revealed_route_ids") or [])
        if str(item or "").strip()
    ]
    source = str(raw.get("source") or "region_onboarding").strip() or "region_onboarding"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if result_type not in {
        "first_region_onboarding",
        "repeat_region_onboarding",
        "anchor_reveal_applied",
        "quiet_region_onboarding",
        "region_onboarding_unavailable",
    }:
        return None
    if not result_id or not summary or not result_summary or not region_id or not region_label or not anchor_node_id:
        return None
    result: dict[str, Any] = {
        "result_id": result_id[:120],
        "result_type": result_type[:60],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "region_id": region_id[:120],
        "region_label": region_label[:160],
        "anchor_node_id": anchor_node_id[:120],
        "revealed_node_ids": revealed_node_ids,
        "revealed_route_ids": revealed_route_ids,
        "onboarding_applied": bool(raw.get("onboarding_applied")),
        "source": source[:40],
    }
    if resolved_at:
        result["resolved_at"] = resolved_at[:80]
    return result


def _normalize_group_region_onboarding_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    region_id = str(raw.get("region_id") or "").strip().lower()
    region_label = str(raw.get("region_label") or region_id).strip()
    status = str(raw.get("status") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    updated_at = str(raw.get("updated_at") or "").strip()
    revealed_node_ids = [
        str(item).strip().lower()
        for item in (raw.get("revealed_node_ids") or [])
        if str(item or "").strip()
    ]
    revealed_route_ids = [
        str(item).strip().lower()
        for item in (raw.get("revealed_route_ids") or [])
        if str(item or "").strip()
    ]
    if status not in {"applied", "repeat", "quiet", "unavailable"}:
        return None
    if not region_id or not region_label or not summary:
        return None
    state: dict[str, Any] = {
        "region_id": region_id[:120],
        "region_label": region_label[:160],
        "status": status[:40],
        "summary": summary[:240],
        "revealed_node_ids": revealed_node_ids,
        "revealed_route_ids": revealed_route_ids,
    }
    if updated_at:
        state["updated_at"] = updated_at[:80]
    return state


def _normalize_group_region_onboarding_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for region_id, value in raw.items():
        candidate = (
            value
            if isinstance(value, dict)
            else {"region_id": region_id, "region_label": str(value or region_id), "status": "quiet", "summary": str(value or region_id)}
        )
        merged = {"region_id": region_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_region_onboarding_state(merged)
        if state:
            normalized[state["region_id"]] = state
    return normalized


def _normalize_group_route_traversal_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    route_id = str(raw.get("route_id") or "").strip().lower()
    traversal_count = max(0, as_int(raw.get("traversal_count"), 0))
    first_traversed_at = str(raw.get("first_traversed_at") or "").strip()
    last_traversed_at = str(raw.get("last_traversed_at") or "").strip()
    summary = str(raw.get("summary") or "").strip()
    if not route_id or traversal_count <= 0:
        return None
    state: dict[str, Any] = {
        "route_id": route_id[:160],
        "traversal_count": traversal_count,
        "summary": summary[:240],
    }
    if first_traversed_at:
        state["first_traversed_at"] = first_traversed_at[:80]
    if last_traversed_at:
        state["last_traversed_at"] = last_traversed_at[:80]
    return state


def _normalize_group_route_traversal_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for route_id, value in raw.items():
        candidate = value if isinstance(value, dict) else {"route_id": route_id, "traversal_count": 1, "summary": str(value or route_id)}
        merged = {"route_id": route_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_route_traversal_state(merged)
        if state:
            normalized[state["route_id"]] = state
    return normalized


def _normalize_group_node_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for node_id, value in raw.items():
        candidate = value if isinstance(value, dict) else {"node_id": node_id, "state_flags": [value], "summary": str(value or node_id)}
        merged = {"node_id": node_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_node_state(merged)
        if state:
            normalized[state["node_id"]] = state
    return normalized


def _build_effective_node_state_notes(
    node_id: str,
    state_flags: list[str] | set[str] | None,
    *,
    note_kind: str,
) -> list[str]:
    notes: list[str] = []
    for overlay in get_static_node_state_overlays(node_id=node_id, state_flags=state_flags):
        note = str(overlay.get(note_kind) or "").strip()
        if note and note not in notes:
            notes.append(note)
    return notes


def get_group_node_state(
    sess: Session,
    group_id: str,
    node_id: str,
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    normalized_node_id = str(node_id or "").strip().lower()
    if not normalized_group_id or not normalized_node_id:
        return None
    group = _get_group_states(sess).get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    return _normalize_group_node_state((_normalize_group_node_state_map(group.get("node_states"))).get(normalized_node_id))


def record_group_node_visit(
    sess: Session,
    group_id: str,
    node_id: str,
    *,
    node_label: str,
    result_type: str,
    summary: str,
    visited_at: str | None = None,
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    normalized_node_id = str(node_id or "").strip().lower()
    normalized_node_label = str(node_label or node_id).strip()
    normalized_result_type = str(result_type or "").strip().lower()
    normalized_summary = str(summary or "").strip()
    if not normalized_group_id or not normalized_node_id or not normalized_node_label:
        return None
    groups = _get_group_states(sess)
    group = groups.get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    state_map = _normalize_group_node_visit_state_map(group.get("node_visit_states"))
    existing = state_map.get(normalized_node_id) or {}
    count = max(0, as_int(existing.get("visit_count"), 0)) + 1
    timestamp = str(visited_at or datetime.now(timezone.utc).isoformat()).strip()
    state = _normalize_group_node_visit_state(
        {
            "node_id": normalized_node_id,
            "node_label": normalized_node_label,
            "visit_count": count,
            "first_visited_at": str(existing.get("first_visited_at") or timestamp),
            "last_visited_at": timestamp,
            "last_result_type": normalized_result_type,
            "summary": normalized_summary or str(existing.get("summary") or ""),
        }
    )
    if not state:
        return None
    state_map[normalized_node_id] = state
    group["node_visit_states"] = state_map
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return state


def record_group_route_traversal(
    sess: Session,
    group_id: str,
    route_id: str,
    *,
    summary: str,
    traversed_at: str | None = None,
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    normalized_route_id = str(route_id or "").strip().lower()
    normalized_summary = str(summary or "").strip()
    if not normalized_group_id or not normalized_route_id:
        return None
    groups = _get_group_states(sess)
    group = groups.get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    state_map = _normalize_group_route_traversal_state_map(group.get("route_traversal_states"))
    existing = state_map.get(normalized_route_id) or {}
    count = max(0, as_int(existing.get("traversal_count"), 0)) + 1
    timestamp = str(traversed_at or datetime.now(timezone.utc).isoformat()).strip()
    state = _normalize_group_route_traversal_state(
        {
            "route_id": normalized_route_id,
            "traversal_count": count,
            "first_traversed_at": str(existing.get("first_traversed_at") or timestamp),
            "last_traversed_at": timestamp,
            "summary": normalized_summary or str(existing.get("summary") or ""),
        }
    )
    if not state:
        return None
    state_map[normalized_route_id] = state
    group["route_traversal_states"] = state_map
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return state


def build_group_arrival_result(
    *,
    node_visit_state: dict[str, Any] | None,
    route_traversal_state: dict[str, Any] | None = None,
    current_map_position: dict[str, Any] | None = None,
    route_summary: dict[str, Any] | None = None,
    source: str = "arrival",
) -> dict[str, Any] | None:
    visit = _normalize_group_node_visit_state(node_visit_state)
    position = _normalize_map_position(current_map_position)
    route = _normalize_group_route_summary(route_summary)
    if not visit or not position:
        return None
    node_id = str(visit.get("node_id") or position.get("node_id") or "").strip()
    node_label = str(visit.get("node_label") or position.get("label") or node_id).strip()
    visit_count = max(0, as_int(visit.get("visit_count"), 0))
    if not node_id or not node_label or visit_count <= 0:
        return None
    first_visit = visit_count == 1
    node_static = get_static_node(node_id)
    settlement_kind = str((node_static or {}).get("settlement_kind") or "").strip().lower()
    node_type = str((node_static or {}).get("node_type") or position.get("node_type") or "").strip().lower()
    route_id = str((route or {}).get("route_id") or (route_traversal_state or {}).get("route_id") or "").strip().lower()
    result_type = "first_arrival" if first_visit else "return_arrival"
    if settlement_kind in {"town", "village", "hamlet", "roadside"}:
        result_type = "settlement_arrival" if first_visit else "return_arrival"
    elif node_type in {"landmark", "interior_entry"}:
        result_type = "landmark_arrival" if first_visit else "return_arrival"
    elif not first_visit:
        result_type = "return_arrival"
    else:
        result_type = "quiet_arrival" if node_type == "zone" and not settlement_kind else result_type
    summary = f"Группа прибывает в {node_label}."
    result_summary = "Группа отмечает новое прибытие в этой точке пути."
    applied_effects = [f"visit_count:{visit_count}"]
    if route_id:
        applied_effects.append(f"route_traversed:{route_id}")
    if first_visit:
        result_summary = "Это первое фактическое прибытие группы в данную точку карты."
        applied_effects.append("visit:first_time")
    else:
        summary = f"Группа снова прибывает в {node_label}."
        result_summary = "Группа возвращается в уже посещённую точку и обновляет историю визитов."
        applied_effects.append("visit:return")
    if result_type == "settlement_arrival":
        result_summary = "Группа фактически достигает поселения и фиксирует его как посещённую точку маршрута."
    elif result_type == "landmark_arrival":
        result_summary = "Группа достигает заметного ориентира и фиксирует это прибытие в истории пути."
    elif result_type == "quiet_arrival":
        result_summary = "Группа спокойно достигает следующей точки пути без особого события, но с записью фактического визита."
    return _normalize_group_last_arrival_result(
        {
            "result_id": uuid.uuid4().hex[:12],
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "node_id": node_id,
            "node_label": node_label,
            "route_id": route_id,
            "first_visit": first_visit,
            "visit_count": visit_count,
            "source": source,
            "applied_effects": applied_effects,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def resolve_group_arrival(
    sess: Session,
    group_id: str,
    *,
    current_map_position: dict[str, Any] | None = None,
    route_summary: dict[str, Any] | None = None,
    source: str = "arrival",
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    if not normalized_group_id:
        return None
    group = _get_group_states(sess).get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    position = _normalize_map_position(current_map_position or group.get("current_map_position"))
    node_id = str((position or {}).get("node_id") or "").strip().lower()
    if not position or not node_id:
        return None
    visit_state = (_normalize_group_node_visit_state_map(group.get("node_visit_states"))).get(node_id)
    route_id = str((_normalize_group_route_summary(route_summary) or {}).get("route_id") or "").strip().lower()
    traversal_state = (_normalize_group_route_traversal_state_map(group.get("route_traversal_states"))).get(route_id) if route_id else None
    result = build_group_arrival_result(
        node_visit_state=visit_state,
        route_traversal_state=traversal_state,
        current_map_position=position,
        route_summary=route_summary,
        source=source,
    )
    if not result:
        return None
    groups = _get_group_states(sess)
    group = groups.get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    group["last_arrival_result"] = result
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return result


def _build_effective_node_entry_overlay(
    node_id: str,
    *,
    first_visit: bool,
    state_flags: list[str] | None = None,
) -> dict[str, Any]:
    overlays = get_static_node_entry_overlays(node_id=node_id, state_flags=state_flags or [])
    changed_overlay = next((item for item in overlays if str(item.get("entry_type") or "").strip().lower() == "changed_place"), None)
    if changed_overlay:
        return dict(changed_overlay)
    first_key = "first_" if first_visit else "return_"
    visit_overlay = next(
        (
            item for item in overlays
            if str(item.get(f"{first_key}entry_type") or "").strip()
            or str(item.get(f"{first_key}entry_title") or "").strip()
            or str(item.get(f"{first_key}entry_note") or "").strip()
        ),
        None,
    )
    return dict(visit_overlay or {})


def build_group_node_entry_result(
    *,
    current_map_position: dict[str, Any] | None,
    node_visit_state: dict[str, Any] | None,
    node_state: dict[str, Any] | None = None,
    source: str = "node_entry",
) -> dict[str, Any] | None:
    position = _normalize_map_position(current_map_position)
    visit = _normalize_group_node_visit_state(node_visit_state)
    current_node_state = _normalize_group_node_state(node_state)
    if not position or not visit:
        return None
    node_id = str(visit.get("node_id") or position.get("node_id") or "").strip().lower()
    node_label = str(visit.get("node_label") or position.get("label") or node_id).strip()
    visit_count = max(0, as_int(visit.get("visit_count"), 0))
    if not node_id or not node_label or visit_count <= 0:
        return None
    first_visit = visit_count == 1
    node_state_flags = list((current_node_state or {}).get("state_flags") or [])
    node_static = get_static_node(node_id) or {}
    node_type = str(position.get("node_type") or node_static.get("node_type") or "").strip().lower()
    settlement_kind = str(node_static.get("settlement_kind") or "").strip().lower()
    overlay = _build_effective_node_entry_overlay(node_id, first_visit=first_visit, state_flags=node_state_flags)
    overlay_result_type = str(
        overlay.get("entry_type")
        or overlay.get("first_entry_type" if first_visit else "return_entry_type")
        or ""
    ).strip().lower()
    overlay_title = str(
        overlay.get("entry_title")
        or overlay.get("first_entry_title" if first_visit else "return_entry_title")
        or ""
    ).strip()
    overlay_note = str(
        overlay.get("entry_note")
        or overlay.get("first_entry_note" if first_visit else "return_entry_note")
        or ""
    ).strip()

    result_type = "first_entry" if first_visit else "return_entry"
    title = overlay_title
    summary = overlay_note
    if overlay_result_type:
        result_type = overlay_result_type
    elif node_type in {"landmark", "interior_entry"}:
        result_type = "landmark_reached"
    elif settlement_kind in {"town", "village", "hamlet", "roadside"} and first_visit:
        result_type = "settlement_welcome"
    elif node_type == "zone" and not first_visit:
        result_type = "return_entry"
    elif node_type == "zone":
        result_type = "quiet_entry"

    if not title:
        if result_type == "settlement_welcome":
            title = f"{node_label} встречает группу"
        elif result_type == "landmark_reached":
            title = f"{node_label} достигнут(а)"
        elif result_type == "changed_place":
            title = f"{node_label} ощущается иначе"
        elif result_type == "return_entry":
            title = f"Возвращение в {node_label}"
        elif result_type == "first_entry":
            title = f"Первый вход в {node_label}"
        else:
            title = f"Прибытие в {node_label}"
    if not summary:
        if result_type == "settlement_welcome":
            summary = f"{node_label} принимает группу как новый спокойный узел маршрута."
        elif result_type == "landmark_reached":
            summary = f"{node_label} отмечает явную веху на пути группы."
        elif result_type == "changed_place":
            summary = f"{node_label} заметно изменился по сравнению с прежним визитом группы."
        elif result_type == "return_entry":
            summary = f"Группа возвращается в {node_label} и быстро считывает знакомую обстановку."
        elif result_type == "first_entry":
            summary = f"Группа впервые входит в {node_label}."
        else:
            summary = f"Группа спокойно входит в {node_label}."
    result_summary = summary
    applied_effects = [f"visit_count:{visit_count}", f"entry_type:{result_type}"]
    if first_visit:
        applied_effects.append("entry:first_visit")
    else:
        applied_effects.append("entry:return_visit")
    if node_state_flags:
        applied_effects.append(f"node_state_flags:{','.join(node_state_flags)}")
    return _normalize_group_last_node_entry_result(
        {
            "result_id": f"entry-{uuid.uuid4().hex[:12]}",
            "result_type": result_type,
            "title": title,
            "summary": summary,
            "result_summary": result_summary,
            "node_id": node_id,
            "node_label": node_label,
            "visit_count": visit_count,
            "first_visit": first_visit,
            "node_state_flags": node_state_flags,
            "applied_effects": applied_effects,
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def resolve_group_node_entry(
    sess: Session,
    group_id: str,
    *,
    current_map_position: dict[str, Any] | None = None,
    source: str = "node_entry",
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    if not normalized_group_id:
        return None
    groups = _get_group_states(sess)
    group = groups.get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    position = _normalize_map_position(current_map_position or group.get("current_map_position"))
    node_id = str((position or {}).get("node_id") or "").strip().lower()
    if not position or not node_id:
        return None
    visit_state = (_normalize_group_node_visit_state_map(group.get("node_visit_states"))).get(node_id)
    current_node_state = (_normalize_group_node_state_map(group.get("node_states"))).get(node_id)
    result = build_group_node_entry_result(
        current_map_position=position,
        node_visit_state=visit_state,
        node_state=current_node_state,
        source=source,
    )
    if not result:
        return None
    state_map = _normalize_group_node_entry_state_map(group.get("node_entry_states"))
    existing = state_map.get(node_id) or {}
    entry_count = max(0, as_int(existing.get("entry_count"), 0)) + 1
    state = _normalize_group_node_entry_state(
        {
            "node_id": node_id,
            "node_label": str(result.get("node_label") or node_id),
            "entry_count": entry_count,
            "last_entry_type": str(result.get("result_type") or ""),
            "summary": str(result.get("summary") or ""),
            "source": source,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if not state:
        return None
    group["last_node_entry_result"] = result
    state_map[node_id] = state
    group["node_entry_states"] = state_map
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return result


def get_current_group_last_node_entry_result(
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
    return _normalize_group_last_node_entry_result(group.get("last_node_entry_result"))


def get_current_group_current_node_entry_state(
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
    current_node_id = str((current_map_position or {}).get("node_id") or "").strip().lower()
    if not current_node_id:
        return None
    return (_normalize_group_node_entry_state_map(group.get("node_entry_states"))).get(current_node_id)


def get_current_group_node_entry_states(
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
    state_map = _normalize_group_node_entry_state_map(group.get("node_entry_states"))
    return [dict(state_map[key]) for key in sorted(state_map.keys())]


def build_group_destination_event_result(
    *,
    current_map_position: dict[str, Any] | None,
    node_visit_state: dict[str, Any] | None,
    node_state: dict[str, Any] | None = None,
    prior_destination_event_state: dict[str, Any] | None = None,
    source: str = "destination_event",
) -> dict[str, Any] | None:
    position = _normalize_map_position(current_map_position)
    visit = _normalize_group_node_visit_state(node_visit_state)
    current_node_state = _normalize_group_node_state(node_state)
    prior_state = _normalize_group_destination_event_state(prior_destination_event_state)
    if not position or not visit:
        return None
    node_id = str(visit.get("node_id") or position.get("node_id") or "").strip().lower()
    node_label = str(visit.get("node_label") or position.get("label") or node_id).strip()
    visit_count = max(0, as_int(visit.get("visit_count"), 0))
    if not node_id or not node_label or visit_count <= 0:
        return None
    first_visit = visit_count == 1
    node_state_flags = list((current_node_state or {}).get("state_flags") or [])
    node_static = get_static_node(node_id) or {}
    node_type = str(position.get("node_type") or node_static.get("node_type") or "").strip().lower()
    settlement_kind = str(node_static.get("settlement_kind") or "").strip().lower()
    authored_events = get_static_node_destination_events(
        current_map_position=position,
        state_flags=node_state_flags,
        visit_count=visit_count,
    )
    if not first_visit and prior_state and not authored_events:
        prior_event_id = str(prior_state.get("event_id") or "").strip().lower()
        historical_events = get_static_node_destination_events(
            current_map_position=position,
            state_flags=node_state_flags,
            visit_count=1,
        )
        authored_events = [
            dict(item)
            for item in historical_events
            if str(item.get("event_id") or "").strip().lower() == prior_event_id and bool(item.get("one_shot"))
        ]
    chosen_event: dict[str, Any] | None = None
    already_resolved_event: dict[str, Any] | None = None
    for event in authored_events:
        event_id = str(event.get("event_id") or "").strip().lower()
        if not event_id:
            continue
        if bool(event.get("one_shot")) and prior_state and str(prior_state.get("event_id") or "").strip().lower() == event_id:
            already_resolved_event = dict(event)
            continue
        chosen_event = dict(event)
        break

    if chosen_event:
        event_id = str(chosen_event.get("event_id") or f"{node_id}:event").strip().lower()
        event_label = str(chosen_event.get("label") or event_id).strip()
        result_type = str(chosen_event.get("result_type") or "").strip().lower() or "local_notice"
        title = str(chosen_event.get("title") or event_label or node_label).strip()
        summary = str(chosen_event.get("summary") or "").strip()
        result_summary = str(chosen_event.get("result_summary") or summary).strip() or summary
        applied_effects = [
            str(item).strip()
            for item in (chosen_event.get("applied_effects") or [])
            if str(item or "").strip()
        ]
    elif already_resolved_event:
        event_id = str(already_resolved_event.get("event_id") or f"{node_id}:event").strip().lower()
        event_label = str(already_resolved_event.get("label") or event_id).strip()
        title = str(already_resolved_event.get("title") or event_label or node_label).strip()
        result_type = "already_resolved"
        summary = f"Локальное событие {event_label} у {node_label} уже было отмечено для группы."
        result_summary = "Это authored событие прибытия уже было разыграно для текущей группы и повторно не даёт нового локального эффекта."
        applied_effects = ["destination_event:already_resolved"]
    else:
        event_id = f"{node_id}:no_event"
        if settlement_kind in {"town", "village", "hamlet", "roadside"}:
            title = f"{node_label} встречает без нового происшествия"
        elif node_type in {"landmark", "interior_entry"}:
            title = f"У {node_label} всё без новой перемены"
        else:
            title = f"На месте {node_label} тихо"
        event_label = node_label
        result_type = "no_event"
        summary = f"У прибытия в {node_label} сейчас нет отдельного локального authored события."
        result_summary = summary
        applied_effects = ["destination_event:none"]

    applied_effects = [*applied_effects, f"visit_count:{visit_count}", f"destination_event:{result_type}"]
    if first_visit:
        applied_effects.append("destination_event:first_visit")
    else:
        applied_effects.append("destination_event:return_visit")
    return _normalize_group_last_destination_event_result(
        {
            "result_id": f"dest-{uuid.uuid4().hex[:12]}",
            "event_id": event_id,
            "event_label": event_label,
            "result_type": result_type,
            "title": title,
            "summary": summary,
            "result_summary": result_summary,
            "node_id": node_id,
            "node_label": node_label,
            "visit_count": visit_count,
            "first_visit": first_visit,
            "applied_effects": applied_effects,
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def resolve_group_destination_event(
    sess: Session,
    group_id: str,
    *,
    current_map_position: dict[str, Any] | None = None,
    source: str = "destination_event",
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    if not normalized_group_id:
        return None
    groups = _get_group_states(sess)
    group = groups.get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    position = _normalize_map_position(current_map_position or group.get("current_map_position"))
    node_id = str((position or {}).get("node_id") or "").strip().lower()
    if not position or not node_id:
        return None
    visit_state = (_normalize_group_node_visit_state_map(group.get("node_visit_states"))).get(node_id)
    current_node_state = (_normalize_group_node_state_map(group.get("node_states"))).get(node_id)
    prior_event_state = (_normalize_group_destination_event_state_map(group.get("destination_event_states"))).get(node_id)
    result = build_group_destination_event_result(
        current_map_position=position,
        node_visit_state=visit_state,
        node_state=current_node_state,
        prior_destination_event_state=prior_event_state,
        source=source,
    )
    if not result:
        return None
    authored_events = get_static_node_destination_events(
        current_map_position=position,
        state_flags=list((current_node_state or {}).get("state_flags") or []),
        visit_count=max(0, as_int((visit_state or {}).get("visit_count"), 0)),
    )
    matched_event = next(
        (
            dict(item)
            for item in authored_events
            if str(item.get("event_id") or "").strip().lower() == str(result.get("event_id") or "").strip().lower()
        ),
        None,
    )
    group_player_ids = [str(pid).strip() for pid in (group.get("player_ids") or []) if str(pid).strip()]
    if matched_event and str(result.get("result_type") or "") not in {"already_resolved", "no_event"}:
        for revealed_node_id in matched_event.get("reveal_node_ids") or []:
            for pid in group_player_ids:
                reveal_player_map_node(sess, pid, str(revealed_node_id), source=source)
        for node_state_flag in matched_event.get("node_state_flags") or []:
            add_group_node_state_flag(
                sess,
                normalized_group_id,
                node_id,
                state_flag=str(node_state_flag),
                summary=str(matched_event.get("node_state_summary") or result.get("summary") or ""),
                source=source,
            )
        groups = _get_group_states(sess)
        group = groups.get(normalized_group_id)
        if not isinstance(group, dict):
            return None
        intel_entry = _build_map_intel_entry_from_destination_event_result(result, destination_event=matched_event)
        if intel_entry:
            _add_group_map_intel_entry_to_group(group, intel_entry)
    state_map = _normalize_group_destination_event_state_map(group.get("destination_event_states"))
    state = _normalize_group_destination_event_state(
        {
            "event_id": str(result.get("event_id") or f"{node_id}:no_event"),
            "node_id": node_id,
            "status": "no_event" if str(result.get("result_type") or "") == "no_event" else "completed",
            "result_type": str(result.get("result_type") or ""),
            "summary": str(result.get("summary") or ""),
            "source": source,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if not state:
        return None
    group["last_destination_event_result"] = result
    state_map[node_id] = state
    group["destination_event_states"] = state_map
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return result


def get_current_group_last_destination_event_result(
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
    return _normalize_group_last_destination_event_result(group.get("last_destination_event_result"))


def get_current_group_current_node_destination_event_state(
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
    current_node_id = str((current_map_position or {}).get("node_id") or "").strip().lower()
    if not current_node_id:
        return None
    return (_normalize_group_destination_event_state_map(group.get("destination_event_states"))).get(current_node_id)


def get_current_group_destination_event_states(
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
    state_map = _normalize_group_destination_event_state_map(group.get("destination_event_states"))
    return [dict(state_map[key]) for key in sorted(state_map.keys())]


def get_current_group_last_arrival_result(
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
    return _normalize_group_last_arrival_result(group.get("last_arrival_result"))


def get_current_group_current_node_visit_state(
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
    current_node_id = str((_normalize_map_position(group.get("current_map_position")) or {}).get("node_id") or "").strip().lower()
    if not current_node_id:
        return None
    return (_normalize_group_node_visit_state_map(group.get("node_visit_states"))).get(current_node_id)


def get_current_group_node_visit_states(
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
    state_map = _normalize_group_node_visit_state_map(group.get("node_visit_states"))
    return [dict(state_map[key]) for key in sorted(state_map.keys())]


def get_current_group_route_traversal_states(
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
    state_map = _normalize_group_route_traversal_state_map(group.get("route_traversal_states"))
    return [dict(state_map[key]) for key in sorted(state_map.keys())]


def _resolve_region_identity_for_position(current_map_position: dict[str, Any] | None) -> dict[str, Any] | None:
    position = _normalize_map_position(current_map_position)
    node_id = str((position or {}).get("node_id") or "").strip().lower()
    if not position or not node_id:
        return None
    region_identity = get_static_region_identity(node_id=node_id, current_map_position=position) or {}
    region_id = str(region_identity.get("region_id") or "").strip().lower()
    region_label = str(region_identity.get("region_label") or "").strip()
    if not region_id:
        map_level = str((position or {}).get("map_level") or "").strip().lower()
        if map_level == "region":
            region_id = "starter_frontier"
            region_label = region_label or "Стартовое пограничье"
    if not region_label:
        region_label = str((position or {}).get("area_label") or (position or {}).get("label") or "Текущий регион").strip()
    if not region_id or not region_label:
        return None
    return {
        "region_id": region_id[:120],
        "region_label": region_label[:160],
        "anchor_node_id": node_id[:120],
    }


def build_group_region_entry_result(
    *,
    result_type: str,
    summary: str,
    result_summary: str,
    region_id: str,
    region_label: str,
    anchor_node_id: str,
    first_region_visit: bool,
    visit_count: int,
    source: str = "region_residency",
) -> dict[str, Any] | None:
    return _normalize_group_last_region_entry_result(
        {
            "result_id": f"region-entry:{region_id}:{datetime.now(timezone.utc).isoformat()}",
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "region_id": region_id,
            "region_label": region_label,
            "anchor_node_id": anchor_node_id,
            "first_region_visit": first_region_visit,
            "visit_count": visit_count,
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def record_group_region_visit(
    sess: Session,
    group_id: str,
    region_id: str,
    *,
    region_label: str,
    anchor_node_id: str,
    source: str = "region_residency",
    entered_at: str | None = None,
    increment_visit: bool = True,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    normalized_group_id = str(group_id or "").strip()
    normalized_region_id = str(region_id or "").strip().lower()
    normalized_region_label = str(region_label or region_id).strip()
    normalized_anchor_node_id = str(anchor_node_id or "").strip().lower()
    if not normalized_group_id or not normalized_region_id or not normalized_region_label or not normalized_anchor_node_id:
        return None, None
    groups = _get_group_states(sess)
    group = groups.get(normalized_group_id)
    if not isinstance(group, dict):
        return None, None
    discovered_map = _normalize_group_discovered_region_map(group.get("discovered_regions"))
    existing_current_region = _normalize_group_current_region_state(group.get("current_region_state"))
    existing_region = discovered_map.get(normalized_region_id) or {}
    timestamp = str(entered_at or datetime.now(timezone.utc).isoformat()).strip()
    prior_visit_count = max(0, as_int(existing_region.get("visit_count"), 0))
    visit_count = prior_visit_count + 1 if increment_visit or prior_visit_count <= 0 else prior_visit_count
    summary = (
        f"Группа уже {visit_count}-й раз входит в регион {normalized_region_label}."
        if visit_count > 1
        else f"Группа впервые входит в регион {normalized_region_label}."
    )
    discovered_state = _normalize_group_discovered_region(
        {
            "region_id": normalized_region_id,
            "region_label": normalized_region_label,
            "visit_count": visit_count,
            "first_entered_at": str(existing_region.get("first_entered_at") or timestamp),
            "last_entered_at": timestamp,
            "first_anchor_node_id": str(existing_region.get("first_anchor_node_id") or normalized_anchor_node_id),
            "last_anchor_node_id": normalized_anchor_node_id,
            "summary": summary,
        }
    )
    current_region_state = _normalize_group_current_region_state(
        {
            "region_id": normalized_region_id,
            "region_label": normalized_region_label,
            "current_node_id": normalized_anchor_node_id,
            "entered_at": str((existing_current_region or {}).get("entered_at") or timestamp) if not increment_visit else timestamp,
            "visit_count": visit_count,
            "source": source,
        }
    )
    if not discovered_state or not current_region_state:
        return None, None
    discovered_map[normalized_region_id] = discovered_state
    group["discovered_regions"] = discovered_map
    group["current_region_state"] = current_region_state
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return current_region_state, discovered_state


def resolve_group_region_residency(
    sess: Session,
    group_id: str,
    *,
    current_map_position: dict[str, Any] | None = None,
    source: str = "region_residency",
    persist_result: bool = True,
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    if not normalized_group_id:
        return None
    groups = _get_group_states(sess)
    group = groups.get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    position = _normalize_map_position(current_map_position or group.get("current_map_position"))
    region_identity = _resolve_region_identity_for_position(position)
    if not position or not region_identity:
        return None
    current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    discovered_map = _normalize_group_discovered_region_map(group.get("discovered_regions"))
    region_id = str(region_identity.get("region_id") or "").strip().lower()
    region_label = str(region_identity.get("region_label") or region_id).strip()
    anchor_node_id = str(region_identity.get("anchor_node_id") or (position or {}).get("node_id") or "").strip().lower()
    if not region_id or not region_label or not anchor_node_id:
        return None
    previous_region_id = str((current_region_state or {}).get("region_id") or "").strip().lower()
    first_region_visit = region_id not in discovered_map
    increment_visit = first_region_visit or not previous_region_id or previous_region_id != region_id
    current_region_state, discovered_state = record_group_region_visit(
        sess,
        normalized_group_id,
        region_id,
        region_label=region_label,
        anchor_node_id=anchor_node_id,
        source=source,
        increment_visit=increment_visit,
    )
    if not current_region_state or not discovered_state:
        return None
    if not persist_result:
        return current_region_state
    visit_count = max(0, as_int(discovered_state.get("visit_count"), 0))
    if source == "region_transition" and previous_region_id and previous_region_id != region_id:
        result_type = "region_transition_entry"
        summary = f"Группа переходит в регион {region_label} через frontier gateway."
    elif first_region_visit:
        result_type = "first_region_entry"
        summary = f"Группа впервые закрепляется в регионе {region_label}."
    elif previous_region_id == region_id:
        result_type = "current_region_confirmed"
        summary = f"Группа подтверждает своё присутствие в регионе {region_label}."
    elif visit_count > 1:
        result_type = "return_region_entry"
        summary = f"Группа возвращается в уже известный регион {region_label}."
    else:
        result_type = "quiet_region_entry"
        summary = f"Группа отмечает присутствие в регионе {region_label}."
    result = build_group_region_entry_result(
        result_type=result_type,
        summary=summary,
        result_summary=summary,
        region_id=region_id,
        region_label=region_label,
        anchor_node_id=anchor_node_id,
        first_region_visit=first_region_visit,
        visit_count=visit_count,
        source=source,
    )
    groups = _get_group_states(sess)
    group = groups.get(normalized_group_id)
    if not result or not isinstance(group, dict):
        return current_region_state
    group["last_region_entry_result"] = result
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    resolve_group_region_onboarding(
        sess,
        normalized_group_id,
        current_region_state=current_region_state,
        source=source,
    )
    return current_region_state


def get_current_group_current_region_state(
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
    current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    region_identity = _resolve_region_identity_for_position(current_map_position)
    current_node_id = str((current_map_position or {}).get("node_id") or "").strip().lower()
    needs_refresh = bool(
        region_identity
        and (
            not current_region_state
            or str(current_region_state.get("region_id") or "").strip().lower() != str(region_identity.get("region_id") or "").strip().lower()
            or str(current_region_state.get("current_node_id") or "").strip().lower() != current_node_id
        )
    )
    if needs_refresh:
        resolve_group_region_residency(
            sess,
            resolved_group_id,
            current_map_position=current_map_position,
            source="region_residency",
            persist_result=not bool(current_region_state),
        )
        group = _get_group_states(sess).get(resolved_group_id)
        if not isinstance(group, dict):
            return None
        current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    return current_region_state


def get_current_group_discovered_regions(
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
    get_current_group_current_region_state(sess, player_id=resolved_player_id or None, group_id=resolved_group_id)
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return []
    region_map = _normalize_group_discovered_region_map(group.get("discovered_regions"))
    return sorted(
        (dict(item) for item in region_map.values()),
        key=lambda item: (
            str(item.get("first_entered_at") or ""),
            str(item.get("region_label") or ""),
            str(item.get("region_id") or ""),
        ),
    )


def get_current_group_last_region_entry_result(
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
    return _normalize_group_last_region_entry_result(group.get("last_region_entry_result"))


def build_group_region_onboarding_result(
    *,
    result_type: str,
    summary: str,
    result_summary: str,
    region_id: str,
    region_label: str,
    anchor_node_id: str,
    revealed_node_ids: list[str] | None = None,
    revealed_route_ids: list[str] | None = None,
    onboarding_applied: bool = False,
    source: str = "region_onboarding",
) -> dict[str, Any] | None:
    return _normalize_group_last_region_onboarding_result(
        {
            "result_id": f"region-onboarding:{region_id}:{datetime.now(timezone.utc).isoformat()}",
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "region_id": region_id,
            "region_label": region_label,
            "anchor_node_id": anchor_node_id,
            "revealed_node_ids": list(revealed_node_ids or []),
            "revealed_route_ids": list(revealed_route_ids or []),
            "onboarding_applied": onboarding_applied,
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def resolve_group_region_onboarding(
    sess: Session,
    group_id: str,
    *,
    current_region_state: dict[str, Any] | None = None,
    source: str = "region_onboarding",
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    if not normalized_group_id:
        return None
    groups = _get_group_states(sess)
    group = groups.get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    current_region = _normalize_group_current_region_state(current_region_state or group.get("current_region_state"))
    if not current_region:
        result = build_group_region_onboarding_result(
            result_type="region_onboarding_unavailable",
            summary="Не удалось определить текущий регион для onboarding.",
            result_summary="Для region onboarding нужен установленный current_region_state.",
            region_id="unknown_region",
            region_label="Неизвестный регион",
            anchor_node_id=str((_normalize_map_position(group.get("current_map_position")) or {}).get("node_id") or "unknown_anchor"),
            source=source,
        )
        if result:
            group["last_region_onboarding_result"] = result
            _persist_group_states(sess, groups)
            _sync_group_position_mirrors(sess, group)
        return result
    region_id = str(current_region.get("region_id") or "").strip().lower()
    region_label = str(current_region.get("region_label") or region_id).strip()
    anchor_node_id = str(current_region.get("current_node_id") or "").strip().lower()
    onboarding_definition = (
        get_static_region_onboarding(region_id)
        or get_static_region_anchor_onboarding(anchor_node_id)
        or {}
    )
    onboarding_state_map = _normalize_group_region_onboarding_state_map(group.get("region_onboarding_states"))
    existing_state = onboarding_state_map.get(region_id)
    group_player_ids = [str(pid).strip() for pid in (group.get("player_ids") or []) if str(pid).strip()]

    if existing_state:
        result = build_group_region_onboarding_result(
            result_type="repeat_region_onboarding",
            summary=f"Region onboarding для {region_label} уже был применён ранее.",
            result_summary="Повторный вход в уже onboarded регион не переоткрывает starter slice и остаётся идемпотентным.",
            region_id=region_id,
            region_label=region_label,
            anchor_node_id=anchor_node_id,
            revealed_node_ids=list(existing_state.get("revealed_node_ids") or []),
            revealed_route_ids=list(existing_state.get("revealed_route_ids") or []),
            onboarding_applied=False,
            source=source,
        )
        if result:
            group["last_region_onboarding_result"] = result
            _persist_group_states(sess, groups)
            _sync_group_position_mirrors(sess, group)
        return result

    starter_reveal_node_ids = [
        str(node_id).strip().lower()
        for node_id in (onboarding_definition.get("starter_reveal_node_ids") or [])
        if str(node_id or "").strip()
    ]
    starter_reveal_route_ids = [
        str(route_id).strip().lower()
        for route_id in (onboarding_definition.get("starter_reveal_route_ids") or [])
        if str(route_id or "").strip()
    ]
    newly_revealed_node_ids: list[str] = []
    for node_id in starter_reveal_node_ids:
        newly_revealed = False
        for pid in group_player_ids:
            if not is_player_node_revealed(sess, pid, node_id):
                reveal_player_map_node(sess, pid, node_id, source=source)
                newly_revealed = True
            else:
                reveal_player_map_node(sess, pid, node_id, source=source)
        if newly_revealed and node_id not in newly_revealed_node_ids:
            newly_revealed_node_ids.append(node_id)
    revealed_node_ids = list(starter_reveal_node_ids)
    revealed_route_ids = list(starter_reveal_route_ids)

    onboarding_applied = bool(newly_revealed_node_ids or revealed_route_ids)
    if onboarding_definition:
        result_type = "anchor_reveal_applied" if onboarding_applied else "first_region_onboarding"
        summary = str(onboarding_definition.get("onboarding_note") or "").strip() or f"Группа закрепляет стартовый срез региона {region_label}."
        result_summary = summary
    else:
        result_type = "quiet_region_onboarding"
        summary = f"Для региона {region_label} пока нет отдельного starter onboarding package."
        result_summary = summary
    result = build_group_region_onboarding_result(
        result_type=result_type,
        summary=summary,
        result_summary=result_summary,
        region_id=region_id,
        region_label=region_label,
        anchor_node_id=anchor_node_id,
        revealed_node_ids=revealed_node_ids,
        revealed_route_ids=revealed_route_ids,
        onboarding_applied=onboarding_applied,
        source=source,
    )
    if not result:
        return None
    state = _normalize_group_region_onboarding_state(
        {
            "region_id": region_id,
            "region_label": region_label,
            "status": "applied" if onboarding_definition else "quiet",
            "summary": summary,
            "revealed_node_ids": revealed_node_ids,
            "revealed_route_ids": revealed_route_ids,
            "updated_at": result.get("resolved_at"),
        }
    )
    if not state:
        return None
    if onboarding_definition:
        intel_title = str(onboarding_definition.get("intel_title") or "").strip()
        intel_summary = str(onboarding_definition.get("intel_summary") or summary).strip()
        if intel_title and intel_summary:
            intel_entry = build_group_map_intel_entry(
                entry_type="guidance",
                title=intel_title,
                summary=intel_summary,
                result_summary=intel_summary,
                source_kind="region_onboarding",
                source_id=region_id,
                node_id=anchor_node_id,
                node_label=str((get_static_node(anchor_node_id) or {}).get("label") or region_label),
                related_node_ids=revealed_node_ids,
                related_route_ids=revealed_route_ids,
                tags=["region", "onboarding", region_id],
                dedupe_key=f"region_onboarding:{region_id}",
            )
            if intel_entry:
                _add_group_map_intel_entry_to_group(group, intel_entry)
    onboarding_state_map[region_id] = state
    group["region_onboarding_states"] = onboarding_state_map
    group["last_region_onboarding_result"] = result
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return result


def get_current_group_last_region_onboarding_result(
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
    return _normalize_group_last_region_onboarding_result(group.get("last_region_onboarding_result"))


def get_current_group_region_onboarding_states(
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
    state_map = _normalize_group_region_onboarding_state_map(group.get("region_onboarding_states"))
    return [dict(state_map[key]) for key in sorted(state_map.keys())]


def set_group_node_state(
    sess: Session,
    group_id: str,
    node_id: str,
    *,
    state_flags: list[str] | None = None,
    summary: str,
    source: str = "node_state",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    normalized_node_id = str(node_id or "").strip().lower()
    group = groups.get(group_key)
    if not group or not normalized_node_id:
        return None
    node_state = _normalize_group_node_state(
        {
            "node_id": normalized_node_id,
            "state_flags": list(state_flags or []),
            "summary": summary,
            "source": source,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if not node_state:
        return None
    state_map = _normalize_group_node_state_map(group.get("node_states"))
    state_map[node_state["node_id"]] = node_state
    group["node_states"] = state_map
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return node_state


def add_group_node_state_flag(
    sess: Session,
    group_id: str,
    node_id: str,
    *,
    state_flag: str,
    summary: str,
    source: str = "node_state",
) -> dict[str, Any] | None:
    normalized_flag = str(state_flag or "").strip().lower()
    normalized_node_id = str(node_id or "").strip().lower()
    if not normalized_flag or not normalized_node_id:
        return None
    existing = get_group_node_state(sess, group_id, normalized_node_id) or {
        "node_id": normalized_node_id,
        "state_flags": [],
        "summary": summary,
    }
    next_flags = list(existing.get("state_flags") or [])
    if normalized_flag not in next_flags:
        next_flags.append(normalized_flag)
    return set_group_node_state(
        sess,
        group_id,
        normalized_node_id,
        state_flags=next_flags,
        summary=summary or str(existing.get("summary") or ""),
        source=source,
    )


def has_group_node_state_flag(
    sess: Session,
    group_id: str,
    node_id: str,
    state_flag: str,
) -> bool:
    normalized_flag = str(state_flag or "").strip().lower()
    state = get_group_node_state(sess, group_id, node_id)
    return bool(state and normalized_flag in set(state.get("state_flags") or []))


def get_current_group_node_states(
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
    state_map = _normalize_group_node_state_map(group.get("node_states"))
    return [dict(state_map[key]) for key in sorted(state_map.keys())]


def get_current_group_current_node_state(
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
    current_map_position = _normalize_map_position((group or {}).get("current_map_position"))
    current_node_id = str((current_map_position or {}).get("node_id") or "").strip().lower()
    if not current_node_id:
        return None
    return get_group_node_state(sess, resolved_group_id, current_node_id)


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
    route_id = str(raw.get("route_id") or "").strip().lower()
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
    if not route_id and target_node_id:
        route_id = build_static_route_id(
            (raw.get("from_node_id") or (raw.get("started_from") or {}).get("node_id") or (raw.get("current_map_position") or {}).get("node_id")),
            target_node_id,
            action_kind,
        )
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
    if route_id:
        summary["route_id"] = route_id[:160]
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


def get_group_route_access_state(
    sess: Session,
    group_id: str,
    route_id: str,
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    normalized_route_id = str(route_id or "").strip().lower()
    if not normalized_group_id or not normalized_route_id:
        return None
    group = _get_group_states(sess).get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    return _normalize_group_route_access_state((_normalize_group_route_access_state_map(group.get("route_access_states"))).get(normalized_route_id))


def set_group_route_access_state(
    sess: Session,
    group_id: str,
    route_id: str,
    *,
    access_state: str,
    summary: str,
    block_reason: str | None = None,
    source: str = "route_access",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    normalized_route_id = str(route_id or "").strip().lower()
    group = groups.get(group_key)
    if not group or not normalized_route_id:
        return None
    route_state = _normalize_group_route_access_state(
        {
            "route_id": normalized_route_id,
            "access_state": access_state,
            "summary": summary,
            "block_reason": block_reason,
            "source": source,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if not route_state:
        return None
    access_map = _normalize_group_route_access_state_map(group.get("route_access_states"))
    access_map[route_state["route_id"]] = route_state
    group["route_access_states"] = access_map
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return route_state


def get_effective_group_route_access_state(
    sess: Session,
    group_id: str,
    *,
    route_id: str | None = None,
    route_summary: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    route = _normalize_group_route_summary(route_summary) if isinstance(route_summary, dict) else None
    normalized_route_id = str(route_id or (route or {}).get("route_id") or "").strip().lower()
    if not normalized_group_id or not normalized_route_id:
        return None
    explicit = get_group_route_access_state(sess, normalized_group_id, normalized_route_id)
    if explicit:
        return explicit
    target_label = str((route or {}).get("target_label") or normalized_route_id).strip() or normalized_route_id
    return {
        "route_id": normalized_route_id,
        "access_state": "open",
        "is_traversable": True,
        "summary": f"Маршрут к {target_label} открыт для прохода.",
        "source": "registry",
    }


def get_current_group_route_access_states(
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
    access_map = _normalize_group_route_access_state_map(group.get("route_access_states"))
    return [dict(access_map[key]) for key in sorted(access_map.keys())]


def validate_group_route_accessibility(
    sess: Session,
    group_id: str,
    route_summary: dict[str, Any] | None,
) -> str | None:
    route = _normalize_group_route_summary(route_summary)
    group_key = str(group_id or "").strip()
    if not route or not group_key:
        return None
    effective = get_effective_group_route_access_state(sess, group_key, route_summary=route)
    if not effective or effective.get("is_traversable") is True:
        return None
    block_reason = str(effective.get("block_reason") or "").strip()
    target_label = str(route.get("target_label") or route.get("target_node_id") or "цель").strip()
    if block_reason:
        return f"Маршрут к {target_label} сейчас заблокирован: {block_reason}."
    return f"Маршрут к {target_label} сейчас заблокирован."


def _normalize_group_route_plan_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    target_node_id = str(raw.get("target_node_id") or "").strip()
    target_node_label = str(raw.get("target_node_label") or target_node_id).strip()
    plan_status = str(raw.get("plan_status") or "").strip().lower()
    if plan_status not in {"reachable", "blocked", "current_location", "unrevealed", "unknown"}:
        return None
    path_node_ids = [
        str(item).strip()[:120]
        for item in (raw.get("path_node_ids") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("path_node_ids"), list) else []
    path_route_ids = [
        str(item).strip().lower()[:160]
        for item in (raw.get("path_route_ids") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("path_route_ids"), list) else []
    step_count = max(0, as_int(raw.get("step_count"), 0))
    blocked_route_id = str(raw.get("blocked_route_id") or "").strip().lower()
    blocked_reason = str(raw.get("blocked_reason") or "").strip()
    first_unvisited = str(raw.get("first_unvisited") or "").strip()
    summary = str(raw.get("summary") or "").strip()
    if not target_node_id or not target_node_label or not summary:
        return None
    return {
        "target_node_id": target_node_id[:120],
        "target_node_label": target_node_label[:120],
        "plan_status": plan_status[:40],
        "path_node_ids": path_node_ids,
        "path_route_ids": path_route_ids,
        "step_count": step_count,
        "reachable": bool(raw.get("reachable")),
        "blocked_route_id": blocked_route_id[:160],
        "blocked_reason": blocked_reason[:120],
        "first_unvisited": first_unvisited[:120],
        "target_known": bool(raw.get("target_known")),
        "target_revealed": bool(raw.get("target_revealed")),
        "summary": summary[:400],
    }


def _normalize_group_route_frontier_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    from_node_id = str(raw.get("from_node_id") or "").strip()
    to_node_id = str(raw.get("to_node_id") or "").strip()
    route_id = str(raw.get("route_id") or "").strip().lower()
    frontier_type = str(raw.get("frontier_type") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    if frontier_type not in {"blocked_route", "unrevealed_branch", "accessible_branch"}:
        return None
    if not from_node_id or not to_node_id or not route_id or not summary:
        return None
    return {
        "from_node_id": from_node_id[:120],
        "to_node_id": to_node_id[:120],
        "route_id": route_id[:160],
        "frontier_type": frontier_type[:40],
        "summary": summary[:400],
    }


def _normalize_group_active_journey(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    journey_id = str(raw.get("journey_id") or "").strip()
    target_node_id = str(raw.get("target_node_id") or "").strip().lower()
    target_node_label = str(raw.get("target_node_label") or target_node_id).strip()
    journey_status = str(raw.get("journey_status") or "").strip().lower()
    if journey_status not in {"planned", "in_progress", "blocked", "arrived", "cleared"}:
        return None
    path_node_ids = [
        str(item).strip().lower()[:120]
        for item in (raw.get("path_node_ids") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("path_node_ids"), list) else []
    path_route_ids = [
        str(item).strip().lower()[:160]
        for item in (raw.get("path_route_ids") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("path_route_ids"), list) else []
    next_node_id = str(raw.get("next_node_id") or "").strip().lower()
    next_route_id = str(raw.get("next_route_id") or "").strip().lower()
    completed_step_count = max(0, as_int(raw.get("completed_step_count"), 0))
    total_step_count = max(0, as_int(raw.get("total_step_count"), 0))
    source = str(raw.get("source") or "journey").strip() or "journey"
    created_at = str(raw.get("created_at") or "").strip()
    updated_at = str(raw.get("updated_at") or "").strip()
    if not journey_id or not target_node_id or not target_node_label:
        return None
    normalized: dict[str, Any] = {
        "journey_id": journey_id[:80],
        "target_node_id": target_node_id[:120],
        "target_node_label": target_node_label[:120],
        "journey_status": journey_status[:40],
        "path_node_ids": path_node_ids,
        "path_route_ids": path_route_ids,
        "next_node_id": next_node_id[:120],
        "next_route_id": next_route_id[:160],
        "completed_step_count": completed_step_count,
        "total_step_count": total_step_count,
        "source": source[:40],
    }
    if created_at:
        normalized["created_at"] = created_at[:80]
    if updated_at:
        normalized["updated_at"] = updated_at[:80]
    return normalized


def _normalize_group_last_journey_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type not in {
        "journey_planned",
        "journey_advanced",
        "journey_arrived",
        "journey_blocked",
        "journey_cleared",
        "journey_unavailable",
    }:
        return None
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or summary).strip()
    journey_id = str(raw.get("journey_id") or "").strip()
    target_node_id = str(raw.get("target_node_id") or "").strip().lower()
    target_node_label = str(raw.get("target_node_label") or target_node_id).strip()
    next_node_id = str(raw.get("next_node_id") or "").strip().lower()
    next_route_id = str(raw.get("next_route_id") or "").strip().lower()
    completed_step_count = max(0, as_int(raw.get("completed_step_count"), 0))
    total_step_count = max(0, as_int(raw.get("total_step_count"), 0))
    source = str(raw.get("source") or "journey").strip() or "journey"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if not result_id or not summary or not result_summary or not journey_id or not target_node_id or not target_node_label:
        return None
    normalized: dict[str, Any] = {
        "result_id": result_id[:80],
        "result_type": result_type[:40],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "journey_id": journey_id[:80],
        "target_node_id": target_node_id[:120],
        "target_node_label": target_node_label[:120],
        "next_node_id": next_node_id[:120],
        "next_route_id": next_route_id[:160],
        "completed_step_count": completed_step_count,
        "total_step_count": total_step_count,
        "source": source[:40],
    }
    if resolved_at:
        normalized["resolved_at"] = resolved_at[:80]
    return normalized


def _get_group_player_ids(group: dict[str, Any] | None) -> list[str]:
    if not isinstance(group, dict):
        return []
    return [str(pid).strip() for pid in (group.get("player_ids") or []) if str(pid).strip()]


def _get_group_revealed_node_ids(sess: Session, group: dict[str, Any] | None) -> set[str]:
    player_ids = _get_group_player_ids(group)
    if not player_ids:
        return set()
    revealed_sets = [
        {
            str(node_id).strip().lower()
            for node_id in get_player_revealed_node_ids(sess, pid)
            if str(node_id or "").strip()
        }
        for pid in player_ids
    ]
    return set.intersection(*revealed_sets) if revealed_sets else set()


def _get_group_known_node_ids(sess: Session, group: dict[str, Any] | None) -> set[str]:
    player_ids = _get_group_player_ids(group)
    if not player_ids:
        return set()
    known_sets = [
        {
            str(node_id).strip().lower()
            for node_id in get_player_known_node_ids(sess, pid)
            if str(node_id or "").strip()
        }
        for pid in player_ids
    ]
    return set.intersection(*known_sets) if known_sets else set()


def _get_first_unvisited_node_for_path(sess: Session, group_id: str, path_node_ids: list[str]) -> str:
    visit_map = _normalize_group_node_visit_state_map((_get_group_states(sess).get(group_id) or {}).get("node_visit_states"))
    for node_id in path_node_ids:
        normalized_node_id = str(node_id).strip().lower()
        if normalized_node_id and not visit_map.get(normalized_node_id):
            return normalized_node_id
    return ""


def get_group_reachable_destinations(sess: Session, group_id: str) -> list[dict[str, Any]]:
    group_key = str(group_id or "").strip()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict):
        return []
    current_position = _normalize_map_position(group.get("current_map_position"))
    current_node_id = str((current_position or {}).get("node_id") or "").strip().lower()
    if not current_node_id:
        return []
    revealed_node_ids = _get_group_revealed_node_ids(sess, group)
    known_node_ids = _get_group_known_node_ids(sess, group)
    queue: list[tuple[str, list[str], list[str]]] = [(current_node_id, [current_node_id], [])]
    visited_nodes: set[str] = {current_node_id}
    plans: list[dict[str, Any]] = []
    for_index_links = get_static_map_links()
    while queue:
        node_id, path_nodes, path_routes = queue.pop(0)
        for link in for_index_links:
            from_node_id = str(link.get("from_node_id") or "").strip().lower()
            to_node_id = str(link.get("to_node_id") or "").strip().lower()
            route_id = str(link.get("route_id") or "").strip().lower()
            if from_node_id != node_id or not to_node_id or not route_id or to_node_id not in revealed_node_ids:
                continue
            effective = get_effective_group_route_access_state(sess, group_key, route_id=route_id)
            if not effective or effective.get("is_traversable") is not True:
                continue
            if to_node_id in visited_nodes:
                continue
            next_path_nodes = [*path_nodes, to_node_id]
            next_path_routes = [*path_routes, route_id]
            visited_nodes.add(to_node_id)
            queue.append((to_node_id, next_path_nodes, next_path_routes))
            if to_node_id == current_node_id:
                continue
            target_node = get_static_node(to_node_id) or {}
            plan = _normalize_group_route_plan_item(
                {
                    "target_node_id": to_node_id,
                    "target_node_label": str(target_node.get("label") or to_node_id),
                    "plan_status": "reachable",
                    "path_node_ids": next_path_nodes,
                    "path_route_ids": next_path_routes,
                    "step_count": len(next_path_routes),
                    "reachable": True,
                    "blocked_route_id": "",
                    "blocked_reason": "",
                    "first_unvisited": _get_first_unvisited_node_for_path(sess, group_key, next_path_nodes),
                    "target_known": to_node_id in known_node_ids,
                    "target_revealed": to_node_id in revealed_node_ids,
                    "summary": f"До {str(target_node.get('label') or to_node_id)} есть полностью открытый и проходимый путь.",
                }
            )
            if plan:
                plans.append(plan)
    plans.sort(key=lambda item: (item.get("step_count", 0), str(item.get("target_node_label") or "")))
    return plans


def get_group_route_frontiers(sess: Session, group_id: str) -> list[dict[str, Any]]:
    group_key = str(group_id or "").strip()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict):
        return []
    current_position = _normalize_map_position(group.get("current_map_position"))
    current_node_id = str((current_position or {}).get("node_id") or "").strip().lower()
    if not current_node_id:
        return []
    reachable_ids = {current_node_id}
    reachable_ids.update(str(item.get("target_node_id") or "").strip().lower() for item in get_group_reachable_destinations(sess, group_key))
    revealed_node_ids = _get_group_revealed_node_ids(sess, group)
    frontiers: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for link in get_static_map_links():
        from_node_id = str(link.get("from_node_id") or "").strip().lower()
        to_node_id = str(link.get("to_node_id") or "").strip().lower()
        route_id = str(link.get("route_id") or "").strip().lower()
        if from_node_id not in reachable_ids or not to_node_id or not route_id:
            continue
        frontier_type = ""
        summary = ""
        effective = get_effective_group_route_access_state(sess, group_key, route_id=route_id)
        if to_node_id not in revealed_node_ids:
            frontier_type = "unrevealed_branch"
            summary = f"От {from_node_id} уходит authored-ветка к ещё не раскрытой точке."
        elif effective and effective.get("is_traversable") is not True:
            frontier_type = "blocked_route"
            summary = f"Маршрут {route_id} видим, но сейчас заблокирован для группы."
        elif to_node_id not in reachable_ids:
            frontier_type = "accessible_branch"
            summary = f"От {from_node_id} есть доступная ветка к {to_node_id}."
        if not frontier_type:
            continue
        dedupe_key = f"{route_id}|{frontier_type}"
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        frontier = _normalize_group_route_frontier_item(
            {
                "from_node_id": from_node_id,
                "to_node_id": to_node_id,
                "route_id": route_id,
                "frontier_type": frontier_type,
                "summary": summary,
            }
        )
        if frontier:
            frontiers.append(frontier)
    frontiers.sort(key=lambda item: (str(item.get("frontier_type") or ""), str(item.get("route_id") or "")))
    return frontiers


def get_group_route_plan_to_node(sess: Session, group_id: str, target_node_id: str) -> dict[str, Any] | None:
    group_key = str(group_id or "").strip()
    normalized_target_node_id = str(target_node_id or "").strip().lower()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict) or not normalized_target_node_id:
        return None
    current_position = _normalize_map_position(group.get("current_map_position"))
    current_node_id = str((current_position or {}).get("node_id") or "").strip().lower()
    if not current_node_id:
        return None
    target_node = get_static_node(normalized_target_node_id)
    if current_node_id == normalized_target_node_id:
        return _normalize_group_route_plan_item(
            {
                "target_node_id": normalized_target_node_id,
                "target_node_label": str((target_node or {}).get("label") or normalized_target_node_id),
                "plan_status": "current_location",
                "path_node_ids": [normalized_target_node_id],
                "path_route_ids": [],
                "step_count": 0,
                "reachable": True,
                "blocked_route_id": "",
                "blocked_reason": "",
                "first_unvisited": "",
                "target_known": True,
                "target_revealed": True,
                "summary": "Группа уже находится в этой точке.",
            }
        )
    if not target_node:
        return _normalize_group_route_plan_item(
            {
                "target_node_id": normalized_target_node_id,
                "target_node_label": normalized_target_node_id,
                "plan_status": "unknown",
                "path_node_ids": [],
                "path_route_ids": [],
                "step_count": 0,
                "reachable": False,
                "blocked_route_id": "",
                "blocked_reason": "",
                "first_unvisited": "",
                "target_known": False,
                "target_revealed": False,
                "summary": "Для этой цели нет корректного authored route plan.",
            }
        )
    reachable = next((item for item in get_group_reachable_destinations(sess, group_key) if str(item.get("target_node_id") or "").strip().lower() == normalized_target_node_id), None)
    if reachable:
        return dict(reachable)
    revealed_node_ids = _get_group_revealed_node_ids(sess, group)
    known_node_ids = _get_group_known_node_ids(sess, group)
    if normalized_target_node_id not in revealed_node_ids:
        return _normalize_group_route_plan_item(
            {
                "target_node_id": normalized_target_node_id,
                "target_node_label": str(target_node.get("label") or normalized_target_node_id),
                "plan_status": "unrevealed",
                "path_node_ids": [],
                "path_route_ids": [],
                "step_count": 0,
                "reachable": False,
                "blocked_route_id": "",
                "blocked_reason": "",
                "first_unvisited": "",
                "target_known": normalized_target_node_id in known_node_ids,
                "target_revealed": False,
                "summary": "Цель существует в authored карте, но ещё не раскрыта для текущей группы.",
            }
        )
    queue: list[tuple[str, list[str], list[str]]] = [(current_node_id, [current_node_id], [])]
    visited_nodes: set[str] = {current_node_id}
    for link in get_static_map_links():
        pass
    while queue:
        node_id, path_nodes, path_routes = queue.pop(0)
        for link in get_static_map_links():
            from_node_id = str(link.get("from_node_id") or "").strip().lower()
            to_node_id = str(link.get("to_node_id") or "").strip().lower()
            route_id = str(link.get("route_id") or "").strip().lower()
            if from_node_id != node_id or not route_id or not to_node_id or to_node_id not in revealed_node_ids:
                continue
            effective = get_effective_group_route_access_state(sess, group_key, route_id=route_id)
            next_path_nodes = [*path_nodes, to_node_id]
            next_path_routes = [*path_routes, route_id]
            if effective and effective.get("is_traversable") is not True and to_node_id == normalized_target_node_id:
                return _normalize_group_route_plan_item(
                    {
                        "target_node_id": normalized_target_node_id,
                        "target_node_label": str(target_node.get("label") or normalized_target_node_id),
                        "plan_status": "blocked",
                        "path_node_ids": next_path_nodes,
                        "path_route_ids": next_path_routes,
                        "step_count": len(next_path_routes),
                        "reachable": False,
                        "blocked_route_id": route_id,
                        "blocked_reason": str(effective.get("block_reason") or ""),
                        "first_unvisited": _get_first_unvisited_node_for_path(sess, group_key, next_path_nodes),
                        "target_known": normalized_target_node_id in known_node_ids,
                        "target_revealed": True,
                        "summary": f"Путь к {str(target_node.get('label') or normalized_target_node_id)} упирается в заблокированный маршрут.",
                    }
                )
            if not effective or effective.get("is_traversable") is not True or to_node_id in visited_nodes:
                continue
            visited_nodes.add(to_node_id)
            queue.append((to_node_id, next_path_nodes, next_path_routes))
    return _normalize_group_route_plan_item(
        {
            "target_node_id": normalized_target_node_id,
            "target_node_label": str(target_node.get("label") or normalized_target_node_id),
            "plan_status": "unknown",
            "path_node_ids": [],
            "path_route_ids": [],
            "step_count": 0,
            "reachable": False,
            "blocked_route_id": "",
            "blocked_reason": "",
            "first_unvisited": "",
            "target_known": normalized_target_node_id in known_node_ids,
            "target_revealed": normalized_target_node_id in revealed_node_ids,
            "summary": "Для этой цели сейчас не удаётся собрать корректный план от текущей позиции группы.",
        }
    )


def build_group_route_plan(sess: Session, group_id: str) -> dict[str, Any]:
    return {
        "reachable_destinations": get_group_reachable_destinations(sess, group_id),
        "route_frontiers": get_group_route_frontiers(sess, group_id),
    }


def get_current_group_route_planning(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any]:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return {"reachable_destinations": [], "route_frontiers": []}
    return build_group_route_plan(sess, resolved_group_id)


def _build_group_journey_result(
    *,
    result_type: str,
    summary: str,
    result_summary: str,
    journey_state: dict[str, Any] | None,
    source: str = "journey",
) -> dict[str, Any] | None:
    journey = _normalize_group_active_journey(journey_state)
    if not journey:
        return None
    return _normalize_group_last_journey_result(
        {
            "result_id": f"journey-{uuid.uuid4().hex[:12]}",
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "journey_id": journey.get("journey_id"),
            "target_node_id": journey.get("target_node_id"),
            "target_node_label": journey.get("target_node_label"),
            "next_node_id": journey.get("next_node_id"),
            "next_route_id": journey.get("next_route_id"),
            "completed_step_count": journey.get("completed_step_count"),
            "total_step_count": journey.get("total_step_count"),
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def _normalize_group_exploration_lead(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    lead_id = str(raw.get("lead_id") or "").strip().lower()
    lead_type = str(raw.get("lead_type") or "").strip().lower()
    priority_band = str(raw.get("priority_band") or "").strip().lower()
    title = str(raw.get("title") or "").strip()
    summary = str(raw.get("summary") or "").strip()
    target_node_id = str(raw.get("target_node_id") or "").strip().lower()
    target_node_label = str(raw.get("target_node_label") or target_node_id).strip()
    route_id = str(raw.get("route_id") or "").strip().lower()
    source_kind = str(raw.get("source_kind") or "").strip().lower()
    source_ref = str(raw.get("source_ref") or "").strip().lower()
    blocked_reason = str(raw.get("blocked_reason") or "").strip()
    first_unvisited = str(raw.get("first_unvisited") or "").strip().lower()
    suggested_command = str(raw.get("suggested_command") or "").strip()
    tags = [
        str(item).strip().lower()[:40]
        for item in (raw.get("tags") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("tags"), list) else []
    if lead_type not in {"active_journey", "intel_target", "unvisited_reachable", "blocked_frontier", "local_opportunity"}:
        return None
    if priority_band not in {"high", "medium", "low"}:
        return None
    if not lead_id or not title or not summary:
        return None
    return {
        "lead_id": lead_id[:160],
        "lead_type": lead_type[:40],
        "priority_band": priority_band[:20],
        "title": title[:160],
        "summary": summary[:400],
        "target_node_id": target_node_id[:120],
        "target_node_label": target_node_label[:120],
        "route_id": route_id[:160],
        "source_kind": source_kind[:40],
        "source_ref": source_ref[:160],
        "reachable": bool(raw.get("reachable")),
        "blocked": bool(raw.get("blocked")),
        "blocked_reason": blocked_reason[:120],
        "first_unvisited": first_unvisited[:120],
        "has_active_journey": bool(raw.get("has_active_journey")),
        "suggested_command": suggested_command[:160],
        "tags": tags,
    }


def build_group_exploration_lead(
    *,
    lead_id: str,
    lead_type: str,
    priority_band: str,
    title: str,
    summary: str,
    target_node_id: str = "",
    target_node_label: str = "",
    route_id: str = "",
    source_kind: str,
    source_ref: str,
    reachable: bool = False,
    blocked: bool = False,
    blocked_reason: str = "",
    first_unvisited: str = "",
    has_active_journey: bool = False,
    suggested_command: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any] | None:
    return _normalize_group_exploration_lead(
        {
            "lead_id": lead_id,
            "lead_type": lead_type,
            "priority_band": priority_band,
            "title": title,
            "summary": summary,
            "target_node_id": target_node_id,
            "target_node_label": target_node_label,
            "route_id": route_id,
            "source_kind": source_kind,
            "source_ref": source_ref,
            "reachable": reachable,
            "blocked": blocked,
            "blocked_reason": blocked_reason,
            "first_unvisited": first_unvisited,
            "has_active_journey": has_active_journey,
            "suggested_command": suggested_command,
            "tags": list(tags or []),
        }
    )


def _normalize_group_node_progress_summary(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    node_id = str(raw.get("node_id") or "").strip().lower()
    node_label = str(raw.get("node_label") or node_id).strip()
    progression_status = str(raw.get("progression_status") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    source = str(raw.get("source") or "node_progression").strip().lower() or "node_progression"
    node_state_flags = [
        str(item).strip().lower()[:80]
        for item in (raw.get("node_state_flags") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("node_state_flags"), list) else []
    unresolved_local_opportunities = [
        str(item).strip()[:160]
        for item in (raw.get("unresolved_local_opportunities") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("unresolved_local_opportunities"), list) else []
    if progression_status not in {
        "newly_arrived",
        "locally_active",
        "partially_resolved",
        "locally_resolved",
        "revisit_changed",
        "quiet_location",
    }:
        return None
    if not node_id or not node_label or not summary:
        return None
    return {
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "progression_status": progression_status[:40],
        "summary": summary[:400],
        "visit_count": max(0, as_int(raw.get("visit_count"), 0)),
        "first_visit": bool(raw.get("first_visit")),
        "has_node_entry": bool(raw.get("has_node_entry")),
        "has_destination_event": bool(raw.get("has_destination_event")),
        "available_action_count": max(0, as_int(raw.get("available_action_count"), 0)),
        "locked_action_count": max(0, as_int(raw.get("locked_action_count"), 0)),
        "completed_action_count": max(0, as_int(raw.get("completed_action_count"), 0)),
        "available_service_count": max(0, as_int(raw.get("available_service_count"), 0)),
        "locked_service_count": max(0, as_int(raw.get("locked_service_count"), 0)),
        "completed_service_count": max(0, as_int(raw.get("completed_service_count"), 0)),
        "node_state_flags": node_state_flags,
        "unresolved_local_opportunities": unresolved_local_opportunities,
        "source": source[:40],
    }


def build_group_node_progress_summary(
    *,
    node_id: str,
    node_label: str,
    progression_status: str,
    summary: str,
    visit_count: int = 0,
    first_visit: bool = False,
    has_node_entry: bool = False,
    has_destination_event: bool = False,
    available_action_count: int = 0,
    locked_action_count: int = 0,
    completed_action_count: int = 0,
    available_service_count: int = 0,
    locked_service_count: int = 0,
    completed_service_count: int = 0,
    node_state_flags: list[str] | None = None,
    unresolved_local_opportunities: list[str] | None = None,
    source: str = "node_progression",
) -> dict[str, Any] | None:
    return _normalize_group_node_progress_summary(
        {
            "node_id": node_id,
            "node_label": node_label,
            "progression_status": progression_status,
            "summary": summary,
            "visit_count": visit_count,
            "first_visit": first_visit,
            "has_node_entry": has_node_entry,
            "has_destination_event": has_destination_event,
            "available_action_count": available_action_count,
            "locked_action_count": locked_action_count,
            "completed_action_count": completed_action_count,
            "available_service_count": available_service_count,
            "locked_service_count": locked_service_count,
            "completed_service_count": completed_service_count,
            "node_state_flags": list(node_state_flags or []),
            "unresolved_local_opportunities": list(unresolved_local_opportunities or []),
            "source": source,
        }
    )


def _build_group_node_progress_summary_for_node(
    sess: Session,
    group_id: str,
    node_id: str,
    *,
    current_map_position: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    group_key = str(group_id or "").strip()
    normalized_node_id = str(node_id or "").strip().lower()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict) or not normalized_node_id:
        return None
    position = _normalize_map_position(current_map_position)
    if not position:
        node_static = get_static_node(normalized_node_id) or {}
        if not node_static:
            return None
        position = {
            "map_level": "region",
            "node_type": str(node_static.get("node_type") or "zone"),
            "node_id": normalized_node_id,
            "label": str(node_static.get("label") or normalized_node_id),
        }
    node_summary = get_static_node(normalized_node_id) or {}
    node_label = str(node_summary.get("label") or position.get("label") or normalized_node_id).strip()
    visit_state = (_normalize_group_node_visit_state_map(group.get("node_visit_states"))).get(normalized_node_id)
    visit_count = max(0, as_int((visit_state or {}).get("visit_count"), 0))
    first_visit = visit_count <= 1 and bool(visit_state)
    node_entry_state = (_normalize_group_node_entry_state_map(group.get("node_entry_states"))).get(normalized_node_id)
    destination_event_state = (_normalize_group_destination_event_state_map(group.get("destination_event_states"))).get(normalized_node_id)
    node_state = (_normalize_group_node_state_map(group.get("node_states"))).get(normalized_node_id) or {}
    node_state_flags = list(node_state.get("state_flags") or [])
    action_states = _normalize_group_context_action_state_map(group.get("context_action_states"))
    service_states = _normalize_group_service_state_map(group.get("service_states"))
    requirement_map = {
        str(item.get("action_id") or "").strip().lower(): dict(item)
        for item in get_static_node_context_action_requirements(current_map_position=position)
        if isinstance(item, dict) and str(item.get("action_id") or "").strip()
    }
    effect_map = {
        str(item.get("action_id") or "").strip().lower(): dict(item)
        for item in get_static_node_context_action_effects(current_map_position=position)
        if isinstance(item, dict) and str(item.get("action_id") or "").strip()
    }
    service_requirement_map = {
        str(item.get("service_id") or item.get("service_key") or "").strip().lower(): dict(item)
        for item in get_static_node_service_requirements(current_map_position=position)
        if isinstance(item, dict) and str(item.get("service_id") or item.get("service_key") or "").strip()
    }
    available_actions: list[dict[str, Any]] = []
    locked_actions: list[dict[str, Any]] = []
    trivial_action_kinds = {"navigate", "inspect", "wait", "camp", "rest_hint", "enter"}
    for action in get_current_node_context_actions(current_map_position=position):
        if not isinstance(action, dict):
            continue
        action_id = str(action.get("action_id") or action.get("action_key") or "").strip().lower()
        action_state = action_states.get(action_id) or {}
        gate = build_group_interaction_gate_result(
            interaction_kind="context_action",
            interaction_id=action_id,
            label=str(action.get("label") or action_id),
            requirements=requirement_map.get(action_id),
            state_flags=node_state_flags,
            destination_event_state=destination_event_state,
            visit_count=visit_count,
            completed=str(action_state.get("status") or "").strip().lower() == "completed",
            interaction_type=str(action.get("action_type") or "action"),
            unlock_hint=str((requirement_map.get(action_id) or {}).get("unlock_hint") or ""),
        )
        if not gate:
            continue
        action_kind = str(action.get("action_kind") or action_id).strip().lower()
        if action_kind in trivial_action_kinds:
            continue
        annotated = {**action, **gate, "action_id": action_id}
        if str(gate.get("availability_status") or "") == "available":
            available_actions.append(annotated)
        else:
            locked_actions.append(annotated)
    available_services: list[dict[str, Any]] = []
    locked_services: list[dict[str, Any]] = []
    for service in get_static_node_services(current_map_position=position):
        if not isinstance(service, dict):
            continue
        service_id = str(service.get("service_id") or service.get("service_key") or "").strip().lower()
        service_state = service_states.get(service_id) or {}
        gate = build_group_interaction_gate_result(
            interaction_kind="service",
            interaction_id=service_id,
            label=str(service.get("label") or service_id),
            requirements=service_requirement_map.get(service_id) or service_requirement_map.get(str(service.get("service_key") or "").strip().lower()),
            state_flags=node_state_flags,
            destination_event_state=destination_event_state,
            visit_count=visit_count,
            completed=str(service_state.get("status") or "").strip().lower() == "completed",
            interaction_type="action",
            unlock_hint=str(((service_requirement_map.get(service_id) or {}).get("unlock_hint") or "")),
        )
        if not gate:
            continue
        annotated = {**service, **gate, "service_id": service_id}
        if str(gate.get("availability_status") or "") == "available":
            available_services.append(annotated)
        else:
            locked_services.append(annotated)
    current_action_ids = set(effect_map.keys()) | {
        str(item.get("action_id") or item.get("action_key") or "").strip().lower()
        for item in [*available_actions, *locked_actions]
        if str(item.get("action_id") or item.get("action_key") or "").strip()
    }
    current_service_ids = {
        str(item.get("service_id") or item.get("service_key") or "").strip().lower()
        for item in get_static_node_services(current_map_position=position)
        if isinstance(item, dict) and str(item.get("service_id") or item.get("service_key") or "").strip()
    } | {
        str(item.get("service_id") or item.get("service_key") or "").strip().lower()
        for item in [*available_services, *locked_services]
        if str(item.get("service_id") or item.get("service_key") or "").strip()
    }
    completed_action_count = sum(
        1
        for action_id, state in action_states.items()
        if action_id in current_action_ids and str(state.get("status") or "").strip().lower() in {"completed", "resolved"}
    )
    completed_service_count = sum(
        1
        for service_id, state in service_states.items()
        if service_id in current_service_ids and str(state.get("status") or "").strip().lower() in {"completed", "resolved"}
    )
    available_action_count = len(available_actions)
    locked_action_count = len(locked_actions)
    available_service_count = len(available_services)
    locked_service_count = len(locked_services)
    unresolved_local_opportunities = [
        str(item.get("label") or item.get("service_label") or item.get("action_id") or item.get("service_id") or "").strip()
        for item in [*available_actions, *available_services]
        if str(item.get("label") or item.get("service_label") or item.get("action_id") or item.get("service_id") or "").strip()
    ]
    has_node_entry = node_entry_state is not None
    destination_event_type = str((destination_event_state or {}).get("result_type") or "").strip().lower()
    has_destination_event = destination_event_type not in {"", "no_event"}
    changed_signal = bool(node_state_flags) or destination_event_type == "changed_place_notice"

    if visit_count <= 1 and (has_node_entry or has_destination_event) and (completed_action_count + completed_service_count) == 0:
        progression_status = "newly_arrived"
        summary = f"{node_label} только что отмечено для группы, местный прогресс ещё почти не тронут."
    elif visit_count > 1 and changed_signal:
        progression_status = "revisit_changed"
        summary = f"{node_label} изменилось с прошлого визита, здесь есть новые локальные последствия."
    elif (available_action_count + available_service_count) > 0 and (completed_action_count + completed_service_count) > 0:
        progression_status = "partially_resolved"
        summary = f"В {node_label} часть локальных возможностей уже закрыта, но остаётся активный местный контент."
    elif (available_action_count + available_service_count) > 0:
        progression_status = "locally_active"
        summary = f"В {node_label} ещё есть доступные локальные действия или услуги."
    elif (completed_action_count + completed_service_count) > 0 or has_destination_event or has_node_entry:
        progression_status = "locally_resolved"
        summary = f"Локальные возможности в {node_label} в основном уже выработаны."
    else:
        progression_status = "quiet_location"
        summary = f"{node_label} сейчас выглядит тихим местом без заметного локального прогресса."

    return build_group_node_progress_summary(
        node_id=normalized_node_id,
        node_label=node_label,
        progression_status=progression_status,
        summary=summary,
        visit_count=visit_count,
        first_visit=first_visit,
        has_node_entry=has_node_entry,
        has_destination_event=has_destination_event,
        available_action_count=available_action_count,
        locked_action_count=locked_action_count,
        completed_action_count=completed_action_count,
        available_service_count=available_service_count,
        locked_service_count=locked_service_count,
        completed_service_count=completed_service_count,
        node_state_flags=node_state_flags,
        unresolved_local_opportunities=unresolved_local_opportunities,
        source="node_progression",
    )


def build_group_journey_state(
    *,
    plan: dict[str, Any] | None,
    target_node_id: str,
    target_node_label: str,
    journey_status: str = "planned",
    journey_id: str | None = None,
    completed_step_count: int = 0,
    total_step_count: int | None = None,
    source: str = "journey",
    created_at: str | None = None,
) -> dict[str, Any] | None:
    normalized_plan = _normalize_group_route_plan_item(plan) if isinstance(plan, dict) else None
    normalized_target_node_id = str(target_node_id or "").strip().lower()
    normalized_target_node_label = str(target_node_label or normalized_target_node_id).strip()
    normalized_status = str(journey_status or "").strip().lower() or "planned"
    if normalized_status not in {"planned", "in_progress", "blocked", "arrived", "cleared"}:
        return None
    path_node_ids = list((normalized_plan or {}).get("path_node_ids") or [])
    path_route_ids = list((normalized_plan or {}).get("path_route_ids") or [])
    if not normalized_target_node_id or not normalized_target_node_label:
        return None
    next_node_id = path_node_ids[1] if len(path_node_ids) > 1 else ""
    next_route_id = path_route_ids[0] if path_route_ids else str((normalized_plan or {}).get("blocked_route_id") or "").strip().lower()
    computed_total_step_count = max(completed_step_count, completed_step_count + max(0, as_int((normalized_plan or {}).get("step_count"), 0)))
    if total_step_count is not None:
        computed_total_step_count = max(completed_step_count, int(total_step_count))
    return _normalize_group_active_journey(
        {
            "journey_id": str(journey_id or f"journey-{uuid.uuid4().hex[:12]}"),
            "target_node_id": normalized_target_node_id,
            "target_node_label": normalized_target_node_label,
            "journey_status": normalized_status,
            "path_node_ids": path_node_ids or [normalized_target_node_id],
            "path_route_ids": path_route_ids,
            "next_node_id": next_node_id,
            "next_route_id": next_route_id,
            "completed_step_count": max(0, int(completed_step_count)),
            "total_step_count": max(0, computed_total_step_count),
            "source": source,
            "created_at": str(created_at or datetime.now(timezone.utc).isoformat()),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def get_current_group_journey_state(
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
    return _normalize_group_active_journey(group.get("active_journey"))


def get_current_group_last_journey_result(
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
    return _normalize_group_last_journey_result(group.get("last_journey_result"))


def get_group_journey_remaining_plan(sess: Session, group_id: str) -> dict[str, Any] | None:
    journey = get_current_group_journey_state(sess, group_id=group_id)
    if not journey:
        return None
    return get_group_route_plan_to_node(sess, group_id, str(journey.get("target_node_id") or ""))


def set_group_journey_target(
    sess: Session,
    group_id: str,
    target_node_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "journey",
) -> tuple[dict[str, Any] | None, str | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    normalized_target_node_id = str(target_node_id or "").strip().lower()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None, "Группа не найдена."
    if not normalized_target_node_id:
        return None, "Нужно указать target_node_id для journey."
    plan = get_group_route_plan_to_node(sess, group_key, normalized_target_node_id)
    if not plan:
        return None, "Не удалось построить маршрут до этой точки."
    plan_status = str(plan.get("plan_status") or "").strip()
    target_node_label = str(plan.get("target_node_label") or normalized_target_node_id).strip()
    if plan_status != "reachable":
        group.pop("active_journey", None)
        unavailable_journey = build_group_journey_state(
            plan=plan,
            target_node_id=normalized_target_node_id,
            target_node_label=target_node_label,
            journey_status="cleared",
            source=source,
        )
        if unavailable_journey:
            group["last_journey_result"] = _build_group_journey_result(
                result_type="journey_unavailable",
                summary=f"Путь к {target_node_label} сейчас недоступен для планируемого путешествия.",
                result_summary=str(plan.get("summary") or f"Группа не может начать путь к {target_node_label}."),
                journey_state=unavailable_journey,
                source=source,
            )
        _persist_group_states(sess, groups)
        _sync_group_position_mirrors(sess, group)
        if plan_status == "current_location":
            return dict(group), f"Группа уже находится в точке {target_node_label}."
        if plan_status == "blocked":
            return dict(group), str(plan.get("summary") or f"Путь к {target_node_label} заблокирован.")
        if plan_status == "unrevealed":
            return dict(group), f"Точка {target_node_label} ещё не раскрыта для текущей группы."
        return dict(group), str(plan.get("summary") or f"Путь к {target_node_label} сейчас недоступен.")
    active_journey = build_group_journey_state(
        plan=plan,
        target_node_id=normalized_target_node_id,
        target_node_label=target_node_label,
        journey_status="planned",
        source=source,
    )
    if not active_journey:
        return None, "Не удалось создать состояние journey."
    group["active_journey"] = active_journey
    group["last_journey_result"] = _build_group_journey_result(
        result_type="journey_planned",
        summary=f"Группа намечает путь к {target_node_label}.",
        result_summary=f"Маршрут к {target_node_label} сохранён как активное путешествие.",
        journey_state=active_journey,
        source=source,
    )
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group), None


def clear_group_journey(
    sess: Session,
    group_id: str,
    *,
    source: str = "journey",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None
    journey = _normalize_group_active_journey(group.get("active_journey"))
    if not journey:
        return None
    cleared_journey = build_group_journey_state(
        plan={
            "target_node_id": journey.get("target_node_id"),
            "target_node_label": journey.get("target_node_label"),
            "plan_status": "current_location" if journey.get("journey_status") == "arrived" else "unknown",
            "path_node_ids": list(journey.get("path_node_ids") or []),
            "path_route_ids": list(journey.get("path_route_ids") or []),
            "step_count": max(0, as_int(journey.get("total_step_count"), 0) - as_int(journey.get("completed_step_count"), 0)),
            "reachable": False,
            "summary": f"Путешествие к {journey.get('target_node_label')} очищено.",
        },
        target_node_id=str(journey.get("target_node_id") or ""),
        target_node_label=str(journey.get("target_node_label") or ""),
        journey_status="cleared",
        journey_id=str(journey.get("journey_id") or ""),
        completed_step_count=max(0, as_int(journey.get("completed_step_count"), 0)),
        total_step_count=max(0, as_int(journey.get("total_step_count"), 0)),
        source=source,
        created_at=str(journey.get("created_at") or ""),
    )
    group.pop("active_journey", None)
    if cleared_journey:
        group["last_journey_result"] = _build_group_journey_result(
            result_type="journey_cleared",
            summary=f"Путешествие к {journey.get('target_node_label')} остановлено.",
            result_summary=f"Активный маршрут к {journey.get('target_node_label')} очищен.",
            journey_state=cleared_journey,
            source=source,
        )
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def advance_group_journey(
    sess: Session,
    group_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "journey",
) -> tuple[dict[str, Any] | None, str | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None, "Группа не найдена."
    journey = _normalize_group_active_journey(group.get("active_journey"))
    if not journey:
        return None, "У группы нет активного путешествия."
    current_plan = get_group_journey_remaining_plan(sess, group_key)
    target_node_label = str(journey.get("target_node_label") or journey.get("target_node_id") or "цель").strip()
    if not current_plan:
        return None, "Не удалось восстановить оставшийся план путешествия."
    plan_status = str(current_plan.get("plan_status") or "").strip()
    if plan_status == "current_location":
        arrived_journey = build_group_journey_state(
            plan=current_plan,
            target_node_id=str(journey.get("target_node_id") or ""),
            target_node_label=target_node_label,
            journey_status="arrived",
            journey_id=str(journey.get("journey_id") or ""),
            completed_step_count=max(as_int(journey.get("completed_step_count"), 0), as_int(journey.get("total_step_count"), 0)),
            total_step_count=max(as_int(journey.get("total_step_count"), 0), as_int(journey.get("completed_step_count"), 0)),
            source=source,
            created_at=str(journey.get("created_at") or ""),
        )
        if arrived_journey:
            group["active_journey"] = arrived_journey
            group["last_journey_result"] = _build_group_journey_result(
                result_type="journey_arrived",
                summary=f"Группа уже достигла {target_node_label}.",
                result_summary=f"Путешествие к {target_node_label} отмечено как завершённое.",
                journey_state=arrived_journey,
                source=source,
            )
            _persist_group_states(sess, groups)
            _sync_group_position_mirrors(sess, group)
        return dict(group), None
    if plan_status != "reachable":
        blocked_journey = build_group_journey_state(
            plan=current_plan,
            target_node_id=str(journey.get("target_node_id") or ""),
            target_node_label=target_node_label,
            journey_status="blocked",
            journey_id=str(journey.get("journey_id") or ""),
            completed_step_count=max(0, as_int(journey.get("completed_step_count"), 0)),
            total_step_count=max(as_int(journey.get("total_step_count"), 0), as_int(journey.get("completed_step_count"), 0)),
            source=source,
            created_at=str(journey.get("created_at") or ""),
        )
        if blocked_journey:
            group["active_journey"] = blocked_journey
            group["last_journey_result"] = _build_group_journey_result(
                result_type="journey_blocked",
                summary=f"Путь к {target_node_label} больше не проходим.",
                result_summary=str(current_plan.get("summary") or f"Оставшийся путь к {target_node_label} сейчас заблокирован."),
                journey_state=blocked_journey,
                source=source,
            )
            _persist_group_states(sess, groups)
            _sync_group_position_mirrors(sess, group)
        return dict(group), str(current_plan.get("summary") or f"Оставшийся путь к {target_node_label} сейчас недоступен.")
    next_node_id = str(current_plan.get("next_node_id") or "").strip().lower()
    if not next_node_id:
        path_node_ids = list(current_plan.get("path_node_ids") or [])
        next_node_id = str(path_node_ids[1] if len(path_node_ids) > 1 else "").strip().lower()
    if not next_node_id:
        return None, "Не удалось определить следующий шаг активного путешествия."
    updated, error = execute_group_navigation_option(
        sess,
        target_node_id=next_node_id,
        player_id=player_id,
        group_id=group_key,
        source=source,
    )
    if error:
        return None, error
    active_travel = evaluate_group_travel_pause(sess, group_key) or updated
    current_travel_state = _group_travel_state_summary((active_travel or {}))
    pause_reason = str((current_travel_state or {}).get("pause_reason") or "").strip().lower()
    if current_travel_state and current_travel_state.get("active") is True:
        if current_travel_state.get("paused") is True and pause_reason == "target_requires_enter":
            updated = confirm_group_enter(sess, group_key, player_id=player_id, source=source)
        elif current_travel_state.get("paused") is not True:
            updated = complete_group_travel(sess, group_key, player_id=player_id, source=source)
    if not isinstance(updated, dict):
        return None, "Не удалось завершить следующий шаг путешествия."
    refreshed_groups = _get_group_states(sess)
    refreshed_group = refreshed_groups.get(group_key)
    if not isinstance(refreshed_group, dict):
        return updated, None
    remaining_plan = get_group_route_plan_to_node(sess, group_key, str(journey.get("target_node_id") or ""))
    if remaining_plan and str(remaining_plan.get("plan_status") or "") == "current_location":
        arrived_journey = build_group_journey_state(
            plan=remaining_plan,
            target_node_id=str(journey.get("target_node_id") or ""),
            target_node_label=target_node_label,
            journey_status="arrived",
            journey_id=str(journey.get("journey_id") or ""),
            completed_step_count=max(0, as_int(journey.get("completed_step_count"), 0) + 1),
            total_step_count=max(as_int(journey.get("total_step_count"), 0), as_int(journey.get("completed_step_count"), 0) + 1),
            source=source,
            created_at=str(journey.get("created_at") or ""),
        )
        if arrived_journey:
            refreshed_group["active_journey"] = arrived_journey
            refreshed_group["last_journey_result"] = _build_group_journey_result(
                result_type="journey_arrived",
                summary=f"Группа достигает {target_node_label}.",
                result_summary=f"Путешествие к {target_node_label} завершено.",
                journey_state=arrived_journey,
                source=source,
            )
            _persist_group_states(sess, refreshed_groups)
            _sync_group_position_mirrors(sess, refreshed_group)
        return dict(refreshed_group), None
    if remaining_plan and str(remaining_plan.get("plan_status") or "") == "reachable":
        completed_step_count = max(0, as_int(journey.get("completed_step_count"), 0) + 1)
        in_progress_journey = build_group_journey_state(
            plan=remaining_plan,
            target_node_id=str(journey.get("target_node_id") or ""),
            target_node_label=target_node_label,
            journey_status="in_progress",
            journey_id=str(journey.get("journey_id") or ""),
            completed_step_count=completed_step_count,
            total_step_count=max(as_int(journey.get("total_step_count"), 0), completed_step_count + as_int(remaining_plan.get("step_count"), 0)),
            source=source,
            created_at=str(journey.get("created_at") or ""),
        )
        if in_progress_journey:
            refreshed_group["active_journey"] = in_progress_journey
            refreshed_group["last_journey_result"] = _build_group_journey_result(
                result_type="journey_advanced",
                summary=f"Группа продвигается к {target_node_label}.",
                result_summary=f"Путешествие к {target_node_label} продвинулось на один переход.",
                journey_state=in_progress_journey,
                source=source,
            )
            _persist_group_states(sess, refreshed_groups)
            _sync_group_position_mirrors(sess, refreshed_group)
        return dict(refreshed_group), None
    blocked_journey = build_group_journey_state(
        plan=remaining_plan or current_plan,
        target_node_id=str(journey.get("target_node_id") or ""),
        target_node_label=target_node_label,
        journey_status="blocked",
        journey_id=str(journey.get("journey_id") or ""),
        completed_step_count=max(0, as_int(journey.get("completed_step_count"), 0) + 1),
        total_step_count=max(as_int(journey.get("total_step_count"), 0), as_int(journey.get("completed_step_count"), 0) + 1),
        source=source,
        created_at=str(journey.get("created_at") or ""),
    )
    if blocked_journey:
        refreshed_group["active_journey"] = blocked_journey
        refreshed_group["last_journey_result"] = _build_group_journey_result(
            result_type="journey_blocked",
            summary=f"Путешествие к {target_node_label} упирается в новый блок.",
            result_summary=str((remaining_plan or current_plan).get("summary") or f"Оставшийся путь к {target_node_label} сейчас недоступен."),
            journey_state=blocked_journey,
            source=source,
        )
        _persist_group_states(sess, refreshed_groups)
        _sync_group_position_mirrors(sess, refreshed_group)
    return dict(refreshed_group), None


def get_group_exploration_leads(sess: Session, group_id: str) -> list[dict[str, Any]]:
    group_key = str(group_id or "").strip()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict):
        return []
    leads: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    journey = get_current_group_journey_state(sess, group_id=group_key)
    planning = build_group_route_plan(sess, group_key)
    reachable = list(planning.get("reachable_destinations") or [])
    frontiers = list(planning.get("route_frontiers") or [])
    map_intel = get_current_group_map_intel(sess, group_id=group_key)
    visit_map = _normalize_group_node_visit_state_map(group.get("node_visit_states"))
    current_position = _normalize_map_position(group.get("current_map_position"))
    current_node_id = str((current_position or {}).get("node_id") or "").strip().lower()
    current_context = get_current_group_node_context(sess, group_id=group_key) or {}
    current_services = get_current_group_node_services(sess, group_id=group_key)
    current_node_progress = get_current_group_current_node_progress(sess, group_id=group_key) or {}
    progression_status = str(current_node_progress.get("progression_status") or "").strip().lower()
    arrived_current_node_journey = bool(
        journey
        and str(journey.get("journey_status") or "").strip().lower() == "arrived"
        and current_node_id
        and str(journey.get("target_node_id") or "").strip().lower() == current_node_id
    )
    has_active_journey = journey is not None and not arrived_current_node_journey

    def _add(lead: dict[str, Any] | None) -> None:
        normalized = _normalize_group_exploration_lead(lead)
        if not normalized:
            return
        dedupe_key = f"{normalized['lead_type']}|{normalized['source_kind']}|{normalized['source_ref']}|{normalized['target_node_id']}|{normalized['route_id']}"
        if dedupe_key in seen_keys:
            return
        seen_keys.add(dedupe_key)
        leads.append(normalized)

    if journey and not arrived_current_node_journey:
        journey_status = str(journey.get("journey_status") or "").strip().lower()
        remaining_plan = get_group_journey_remaining_plan(sess, group_key) or {}
        blocked_reason = str((remaining_plan or {}).get("blocked_reason") or "").strip()
        suggested_command = "group continue"
        if journey_status == "blocked":
            suggested_command = f"group path {journey.get('target_node_id')}"
        elif journey_status == "arrived":
            suggested_command = "group stop"
        _add(
            build_group_exploration_lead(
                lead_id=f"active_journey:{journey.get('journey_id')}",
                lead_type="active_journey",
                priority_band="high",
                title=f"Активный путь: {journey.get('target_node_label')}",
                summary=(
                    f"У группы есть {journey_status} journey к {journey.get('target_node_label')} "
                    f"({journey.get('completed_step_count')}/{journey.get('total_step_count')} шагов)."
                ),
                target_node_id=str(journey.get("target_node_id") or ""),
                target_node_label=str(journey.get("target_node_label") or ""),
                route_id=str(journey.get("next_route_id") or ""),
                source_kind="journey",
                source_ref=str(journey.get("journey_id") or ""),
                reachable=journey_status in {"planned", "in_progress", "arrived"},
                blocked=journey_status == "blocked",
                blocked_reason=blocked_reason,
                first_unvisited=str((remaining_plan or {}).get("first_unvisited") or ""),
                has_active_journey=True,
                suggested_command=suggested_command,
                tags=["journey", journey_status],
            )
        )

    for entry in reversed(map_intel):
        target_node_ids = [str(item).strip().lower() for item in (entry.get("related_node_ids") or []) if str(item or "").strip()]
        route_ids = [str(item).strip().lower() for item in (entry.get("related_route_ids") or []) if str(item or "").strip()]
        target_node_id = target_node_ids[0] if target_node_ids else ""
        if not target_node_id:
            continue
        target_node = get_static_node(target_node_id) or {}
        target_node_label = str(target_node.get("label") or target_node_id).strip()
        plan = get_group_route_plan_to_node(sess, group_key, target_node_id) or {}
        plan_status = str(plan.get("plan_status") or "").strip().lower()
        if plan_status not in {"reachable", "blocked", "current_location"}:
            continue
        _add(
            build_group_exploration_lead(
                lead_id=f"intel:{entry.get('entry_id')}:{target_node_id}",
                lead_type="intel_target",
                priority_band="high" if plan_status == "reachable" else "medium",
                title=f"Зацепка: {target_node_label}",
                summary=str(entry.get("result_summary") or entry.get("summary") or f"Есть новая зацепка по точке {target_node_label}."),
                target_node_id=target_node_id,
                target_node_label=target_node_label,
                route_id=route_ids[0] if route_ids else str(plan.get("blocked_route_id") or ""),
                source_kind="map_intel",
                source_ref=str(entry.get("entry_id") or target_node_id),
                reachable=plan_status in {"reachable", "current_location"},
                blocked=plan_status == "blocked",
                blocked_reason=str(plan.get("blocked_reason") or ""),
                first_unvisited=str(plan.get("first_unvisited") or ""),
                has_active_journey=has_active_journey,
                suggested_command=f"group go {target_node_id}" if plan_status == "reachable" else f"group path {target_node_id}",
                tags=[str(entry.get("entry_type") or "intel"), "intel"],
            )
        )

    for item in reachable:
        target_node_id = str(item.get("target_node_id") or "").strip().lower()
        if not target_node_id or visit_map.get(target_node_id):
            continue
        target_node_label = str(item.get("target_node_label") or target_node_id).strip()
        _add(
            build_group_exploration_lead(
                lead_id=f"reachable:{target_node_id}",
                lead_type="unvisited_reachable",
                priority_band="medium" if int(item.get("step_count") or 0) <= 1 else "low",
                title=f"Непосещённая точка: {target_node_label}",
                summary=f"{target_node_label} уже достижима и группа там ещё не была.",
                target_node_id=target_node_id,
                target_node_label=target_node_label,
                route_id=str((item.get("path_route_ids") or [""])[0] or ""),
                source_kind="route_planning",
                source_ref=target_node_id,
                reachable=True,
                blocked=False,
                first_unvisited=str(item.get("first_unvisited") or target_node_id),
                has_active_journey=has_active_journey,
                suggested_command=f"group go {target_node_id}",
                tags=["reachable", "unvisited"],
            )
        )

    for item in frontiers:
        if str(item.get("frontier_type") or "") != "blocked_route":
            continue
        route_id = str(item.get("route_id") or "").strip().lower()
        target_node_id = str(item.get("to_node_id") or "").strip().lower()
        target_node = get_static_node(target_node_id) or {}
        access = get_group_route_access_state(sess, group_key, route_id) or {}
        _add(
            build_group_exploration_lead(
                lead_id=f"frontier:{route_id}",
                lead_type="blocked_frontier",
                priority_band="medium",
                title=f"Препятствие на пути: {str(target_node.get('label') or target_node_id)}",
                summary=str(item.get("summary") or f"На маршруте {route_id} есть известное препятствие."),
                target_node_id=target_node_id,
                target_node_label=str(target_node.get("label") or target_node_id).strip(),
                route_id=route_id,
                source_kind="route_frontier",
                source_ref=route_id,
                reachable=False,
                blocked=True,
                blocked_reason=str(access.get("block_reason") or ""),
                has_active_journey=has_active_journey,
                suggested_command=f"group path {target_node_id}" if target_node_id else "",
                tags=["blocked", "frontier"],
            )
        )

    if progression_status not in {"quiet_location", "locally_resolved"}:
        for service in current_services:
            if bool(service.get("available")) is not True:
                continue
            service_id = str(service.get("service_id") or "").strip().lower()
            service_label = str(service.get("label") or service_id).strip()
            _add(
                build_group_exploration_lead(
                    lead_id=f"service:{service_id}",
                    lead_type="local_opportunity",
                    priority_band="medium" if progression_status == "partially_resolved" else "low",
                    title=f"Локальная возможность: {service_label}",
                    summary=f"В текущей точке доступна полезная услуга: {service_label}.",
                    target_node_id=str(((current_context.get("node_summary") or {}).get("node_id") or "")).strip().lower(),
                    target_node_label=str(((current_context.get("node_summary") or {}).get("label") or "")).strip(),
                    source_kind="service",
                    source_ref=service_id,
                    reachable=True,
                    blocked=False,
                    has_active_journey=has_active_journey,
                    suggested_command=f"group service {service_id}",
                    tags=["local", "service", str(service.get("service_kind") or "service"), progression_status or "local"],
                )
            )
            break

        contextual_actions = list((current_context.get("contextual_actions") or [])) if isinstance(current_context, dict) else []
        for action in contextual_actions:
            if bool(action.get("available")) is not True or bool(action.get("exhausted")) is True:
                continue
            action_id = str(action.get("action_id") or action.get("action_key") or "").strip().lower()
            action_kind = str(action.get("action_kind") or action_id).strip().lower()
            if action_kind in {"navigate", "inspect", "wait", "camp", "rest_hint"}:
                continue
            action_label = str(action.get("label") or action_id).strip()
            _add(
                build_group_exploration_lead(
                    lead_id=f"action:{action_id}",
                    lead_type="local_opportunity",
                    priority_band="medium" if progression_status == "partially_resolved" else "low",
                    title=f"Локальная возможность: {action_label}",
                    summary=f"В текущей точке доступно контекстное действие: {action_label}.",
                    target_node_id=str(((current_context.get("node_summary") or {}).get("node_id") or "")).strip().lower(),
                    target_node_label=str(((current_context.get("node_summary") or {}).get("label") or "")).strip(),
                    source_kind="context_action",
                    source_ref=action_id,
                    reachable=True,
                    blocked=False,
                    has_active_journey=has_active_journey,
                    suggested_command=f"group action {action_id}",
                    tags=["local", "action", action_kind, progression_status or "local"],
                )
            )
            break

    priority_order = {"high": 0, "medium": 1, "low": 2}
    type_order = {
        "active_journey": 0,
        "intel_target": 1,
        "unvisited_reachable": 2,
        "blocked_frontier": 3,
        "local_opportunity": 4,
    }
    leads.sort(
        key=lambda item: (
            priority_order.get(str(item.get("priority_band") or ""), 99),
            type_order.get(str(item.get("lead_type") or ""), 99),
            str(item.get("title") or ""),
        )
    )
    return leads


def get_group_primary_exploration_lead(sess: Session, group_id: str) -> dict[str, Any] | None:
    leads = get_group_exploration_leads(sess, group_id)
    return dict(leads[0]) if leads else None


def get_current_group_exploration_leads(
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
    return get_group_exploration_leads(sess, resolved_group_id)


def get_current_group_primary_exploration_lead(
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
    return get_group_primary_exploration_lead(sess, resolved_group_id)


def build_group_interaction_gate_result(
    *,
    interaction_kind: str,
    interaction_id: str,
    label: str,
    requirements: dict[str, Any] | None = None,
    state_flags: list[str] | set[str] | None = None,
    group_state_flags: list[str] | set[str] | None = None,
    region_link_ids: list[str] | set[str] | None = None,
    destination_event_state: dict[str, Any] | None = None,
    visit_count: int = 0,
    completed: bool = False,
    interaction_type: str = "action",
    unlock_hint: str | None = None,
    source: str = "interaction_gating",
) -> dict[str, Any] | None:
    normalized_kind = str(interaction_kind or "").strip().lower()
    normalized_id = str(interaction_id or "").strip().lower()
    normalized_label = str(label or interaction_id).strip()
    normalized_type = str(interaction_type or "action").strip().lower() or "action"
    if normalized_kind not in {"context_action", "service"} or not normalized_id or not normalized_label:
        return None
    requirement_map = dict(requirements or {})
    destination_state = _normalize_group_destination_event_state(destination_event_state)
    available = True
    availability_status = "available"
    unavailable_reason = ""
    resolved_unlock_hint = str(unlock_hint or requirement_map.get("unlock_hint") or "").strip()
    requirement_eval = _evaluate_local_requirement_set(
        requirements=requirement_map,
        state_flags=state_flags,
        group_state_flags=group_state_flags,
        region_link_ids=region_link_ids,
        destination_event_state=destination_state,
        visit_count=visit_count,
    )
    missing_requirements = list(requirement_eval.get("missing_requirements") or [])
    satisfied_requirements = list(requirement_eval.get("satisfied_requirements") or [])

    if completed:
        availability_status = "completed"
        available = False
        unavailable_reason = "already_completed" if normalized_kind == "context_action" else "already_used"
    elif normalized_type != "action":
        availability_status = "unavailable"
        available = False
        unavailable_reason = "informational_only"
    elif bool(requirement_eval.get("locked")):
        availability_status = "locked"
        available = False
        unavailable_reason = str(requirement_eval.get("unavailable_reason") or "requirements_missing")

    result = {
        "interaction_kind": normalized_kind,
        "interaction_id": normalized_id,
        "label": normalized_label[:160],
        "availability_status": availability_status,
        "available": available,
        "unavailable_reason": unavailable_reason[:120],
        "unlock_hint": resolved_unlock_hint[:240],
        "satisfied_requirements": satisfied_requirements,
        "missing_requirements": missing_requirements,
        "source": str(source or "interaction_gating")[:40] or "interaction_gating",
    }
    return result


def _evaluate_local_requirement_set(
    *,
    requirements: dict[str, Any] | None = None,
    state_flags: list[str] | set[str] | None = None,
    group_state_flags: list[str] | set[str] | None = None,
    region_link_ids: list[str] | set[str] | None = None,
    destination_event_state: dict[str, Any] | None = None,
    visit_count: int = 0,
) -> dict[str, Any]:
    requirement_map = dict(requirements or {})
    destination_state = _normalize_group_destination_event_state(destination_event_state)
    available_state_flags = {
        str(flag or "").strip().lower()
        for flag in (state_flags or [])
        if str(flag or "").strip()
    }
    available_group_state_flags = {
        str(flag or "").strip().lower()
        for flag in (group_state_flags or [])
        if str(flag or "").strip()
    }
    available_region_link_ids = {
        str(link_id or "").strip().lower()
        for link_id in (region_link_ids or [])
        if str(link_id or "").strip()
    }
    resolved_visit_count = max(0, int(visit_count or 0))
    missing_requirements: list[str] = []
    satisfied_requirements: list[str] = []
    unavailable_reason = ""

    def _requirement_met(key: str, met: bool, *, missing_value: str = "", satisfied_value: str = "") -> None:
        nonlocal unavailable_reason
        if met:
            if satisfied_value:
                satisfied_requirements.append(satisfied_value)
            return
        if missing_value:
            missing_requirements.append(missing_value)
        if not unavailable_reason:
            unavailable_reason = key

    required_flag = str(requirement_map.get("requires_node_state_flag") or "").strip().lower()
    if required_flag:
        _requirement_met(
            "requires_node_state_flag",
            required_flag in available_state_flags,
            missing_value=f"node_state:{required_flag}",
            satisfied_value=f"node_state:{required_flag}",
        )
    required_event_id = str(requirement_map.get("requires_destination_event_id") or "").strip().lower()
    if required_event_id:
        actual_event_id = str((destination_state or {}).get("event_id") or "").strip().lower()
        _requirement_met(
            "requires_destination_event_id",
            actual_event_id == required_event_id,
            missing_value=f"destination_event:{required_event_id}",
            satisfied_value=f"destination_event:{required_event_id}",
        )
    required_event_type = str(requirement_map.get("requires_destination_event_result_type") or "").strip().lower()
    if required_event_type:
        actual_event_type = str((destination_state or {}).get("result_type") or "").strip().lower()
        _requirement_met(
            "requires_destination_event_result_type",
            actual_event_type == required_event_type,
            missing_value=f"destination_event_result:{required_event_type}",
            satisfied_value=f"destination_event_result:{required_event_type}",
        )
    required_any_group_flags = {
        str(flag or "").strip().lower()
        for flag in (requirement_map.get("requires_any_group_node_state_flags") or [])
        if str(flag or "").strip()
    }
    if required_any_group_flags:
        _requirement_met(
            "requires_any_group_node_state_flags",
            bool(required_any_group_flags & available_group_state_flags),
            missing_value=f"any_group_node_state:{','.join(sorted(required_any_group_flags))}",
            satisfied_value=f"any_group_node_state:{','.join(sorted(required_any_group_flags & available_group_state_flags))}",
        )
    required_all_group_flags = {
        str(flag or "").strip().lower()
        for flag in (requirement_map.get("requires_all_group_node_state_flags") or [])
        if str(flag or "").strip()
    }
    if required_all_group_flags:
        _requirement_met(
            "requires_all_group_node_state_flags",
            required_all_group_flags.issubset(available_group_state_flags),
            missing_value=f"all_group_node_state:{','.join(sorted(required_all_group_flags))}",
            satisfied_value=f"all_group_node_state:{','.join(sorted(required_all_group_flags))}",
        )
    required_min_group_flag_count = max(0, as_int(requirement_map.get("requires_min_group_node_state_flags"), 0))
    if required_min_group_flag_count > 0:
        group_flag_pool = {
            str(flag or "").strip().lower()
            for flag in (requirement_map.get("group_node_state_flag_pool") or [])
            if str(flag or "").strip()
        }
        _requirement_met(
            "requires_min_group_node_state_flags",
            len(group_flag_pool & available_group_state_flags) >= required_min_group_flag_count,
            missing_value=f"min_group_node_state_count:{required_min_group_flag_count}",
            satisfied_value=f"min_group_node_state_count:{required_min_group_flag_count}",
        )
    required_any_region_link_ids = {
        str(link_id or "").strip().lower()
        for link_id in (requirement_map.get("requires_any_region_link_ids") or [])
        if str(link_id or "").strip()
    }
    if required_any_region_link_ids:
        _requirement_met(
            "requires_any_region_link_ids",
            bool(required_any_region_link_ids & available_region_link_ids),
            missing_value=f"any_region_link:{','.join(sorted(required_any_region_link_ids))}",
            satisfied_value=f"any_region_link:{','.join(sorted(required_any_region_link_ids & available_region_link_ids))}",
        )
    required_all_region_link_ids = {
        str(link_id or "").strip().lower()
        for link_id in (requirement_map.get("requires_all_region_link_ids") or [])
        if str(link_id or "").strip()
    }
    if required_all_region_link_ids:
        _requirement_met(
            "requires_all_region_link_ids",
            required_all_region_link_ids.issubset(available_region_link_ids),
            missing_value=f"all_region_link:{','.join(sorted(required_all_region_link_ids))}",
            satisfied_value=f"all_region_link:{','.join(sorted(required_all_region_link_ids))}",
        )
    required_min_region_link_count = max(0, as_int(requirement_map.get("requires_min_region_link_count"), 0))
    if required_min_region_link_count > 0:
        region_link_id_pool = {
            str(link_id or "").strip().lower()
            for link_id in (requirement_map.get("region_link_id_pool") or [])
            if str(link_id or "").strip()
        }
        _requirement_met(
            "requires_min_region_link_count",
            len(region_link_id_pool & available_region_link_ids) >= required_min_region_link_count,
            missing_value=f"min_region_link_count:{required_min_region_link_count}",
            satisfied_value=f"min_region_link_count:{required_min_region_link_count}",
        )
    if bool(requirement_map.get("first_visit_only")):
        _requirement_met(
            "first_visit_only",
            resolved_visit_count == 1,
            missing_value="first_visit_only",
            satisfied_value="first_visit_only",
        )
    if bool(requirement_map.get("return_visit_only")):
        _requirement_met(
            "return_visit_only",
            resolved_visit_count >= 2,
            missing_value="return_visit_only",
            satisfied_value="return_visit_only",
        )
    min_visit_count = max(
        0,
        as_int(
            requirement_map.get("requires_min_visit_count")
            if requirement_map.get("requires_min_visit_count") is not None
            else requirement_map.get("min_visit_count"),
            0,
        ),
    )
    if min_visit_count > 0:
        _requirement_met(
            "min_visit_count",
            resolved_visit_count >= min_visit_count,
            missing_value=f"min_visit_count:{min_visit_count}",
            satisfied_value=f"min_visit_count:{min_visit_count}",
        )
    return {
        "locked": bool(missing_requirements),
        "unavailable_reason": unavailable_reason,
        "missing_requirements": missing_requirements,
        "satisfied_requirements": satisfied_requirements,
    }


def _collect_group_node_state_flags(group: dict[str, Any] | None) -> set[str]:
    if not isinstance(group, dict):
        return set()
    return {
        str(flag).strip().lower()
        for node_state in (_normalize_group_node_state_map(group.get("node_states"))).values()
        for flag in (dict(node_state).get("state_flags") or [])
        if str(flag or "").strip()
    }


def _collect_group_region_link_ids(group: dict[str, Any] | None) -> set[str]:
    if not isinstance(group, dict):
        return set()
    return {
        str(link_id).strip().lower()
        for link_id in _normalize_group_region_link_state_map(group.get("region_link_states")).keys()
        if str(link_id or "").strip()
    }


def _get_current_group_local_interaction_context(
    sess: Session,
    group_id: str,
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    if not resolved_group_id:
        return None
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return None
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    current_node_id = str((current_map_position or {}).get("node_id") or "").strip().lower()
    if not current_map_position or not current_node_id:
        return None
    current_node_state = (_normalize_group_node_state_map(group.get("node_states"))).get(current_node_id)
    current_visit_state = (_normalize_group_node_visit_state_map(group.get("node_visit_states"))).get(current_node_id)
    current_destination_event_state = (_normalize_group_destination_event_state_map(group.get("destination_event_states"))).get(current_node_id)
    group_state_flags = sorted(
        {
            str(flag).strip().lower()
            for node_state in (_normalize_group_node_state_map(group.get("node_states"))).values()
            for flag in (dict(node_state).get("state_flags") or [])
            if str(flag or "").strip()
        }
    )
    region_link_ids = sorted(_collect_group_region_link_ids(group))
    return {
        "group": group,
        "current_map_position": current_map_position,
        "current_node_id": current_node_id,
        "node_state_flags": list((current_node_state or {}).get("state_flags") or []),
        "group_state_flags": group_state_flags,
        "region_link_ids": region_link_ids,
        "visit_count": max(0, as_int((current_visit_state or {}).get("visit_count"), 0)),
        "destination_event_state": current_destination_event_state,
        "context_action_states": _normalize_group_context_action_state_map(group.get("context_action_states")),
        "service_states": _normalize_group_service_state_map(group.get("service_states")),
    }


def get_current_group_context_action_availability(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> list[dict[str, Any]]:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    context = _get_current_group_local_interaction_context(sess, resolved_group_id)
    if not context:
        return []
    current_map_position = dict(context.get("current_map_position") or {})
    action_states = dict(context.get("context_action_states") or {})
    requirement_map = {
        str(item.get("action_id") or "").strip().lower(): dict(item)
        for item in get_static_node_context_action_requirements(current_map_position=current_map_position)
        if isinstance(item, dict) and str(item.get("action_id") or "").strip()
    }
    effect_map = {
        str(item.get("action_id") or "").strip().lower(): dict(item)
        for item in get_static_node_context_action_effects(
            current_map_position=current_map_position,
            state_flags=context.get("node_state_flags"),
            group_state_flags=context.get("group_state_flags"),
            region_link_ids=context.get("region_link_ids"),
        )
        if isinstance(item, dict) and str(item.get("action_id") or "").strip()
    }
    availability: list[dict[str, Any]] = []
    for action in get_current_node_context_actions(current_map_position=current_map_position):
        if not isinstance(action, dict):
            continue
        annotated = dict(action)
        action_id = str(annotated.get("action_id") or annotated.get("action_key") or "").strip().lower()
        action_state = action_states.get(action_id) or {}
        completed = str(action_state.get("status") or "").strip().lower() == "completed"
        gate = build_group_interaction_gate_result(
            interaction_kind="context_action",
            interaction_id=action_id,
            label=str(annotated.get("label") or action_id),
            requirements=requirement_map.get(action_id),
            state_flags=context.get("node_state_flags"),
            group_state_flags=context.get("group_state_flags"),
            region_link_ids=context.get("region_link_ids"),
            destination_event_state=context.get("destination_event_state"),
            visit_count=int(context.get("visit_count") or 0),
            completed=completed,
            interaction_type=str(annotated.get("action_type") or "action"),
            unlock_hint=str((requirement_map.get(action_id) or {}).get("unlock_hint") or ""),
        )
        if not gate:
            continue
        availability_status = str(gate.get("availability_status") or "available").strip().lower()
        annotated.update(gate)
        if action_id:
            annotated["action_id"] = action_id
        effect = effect_map.get(action_id)
        if effect:
            annotated["source"] = str(effect.get("source") or annotated.get("source") or "registry")
            annotated["one_shot"] = bool(effect.get("one_shot"))
        annotated["status"] = availability_status
        annotated["available"] = bool(gate.get("available"))
        annotated["exhausted"] = availability_status == "completed"
        availability.append(annotated)
    return availability


def get_current_group_service_availability(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> list[dict[str, Any]]:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    context = _get_current_group_local_interaction_context(sess, resolved_group_id)
    if not context:
        return []
    current_map_position = dict(context.get("current_map_position") or {})
    service_states = dict(context.get("service_states") or {})
    requirement_map: dict[str, dict[str, Any]] = {}
    for item in get_static_node_service_requirements(current_map_position=current_map_position):
        if not isinstance(item, dict):
            continue
        service_id = str(item.get("service_id") or item.get("service_key") or "").strip().lower()
        if service_id:
            requirement_map[service_id] = dict(item)
    effect_map = {
        str(item.get("service_id") or item.get("service_key") or "").strip().lower(): dict(item)
        for item in get_static_node_service_effects(
            current_map_position=current_map_position,
            state_flags=context.get("node_state_flags"),
            group_state_flags=context.get("group_state_flags"),
        )
        if isinstance(item, dict) and str(item.get("service_id") or item.get("service_key") or "").strip()
    }
    availability: list[dict[str, Any]] = []
    for service in get_static_node_services(current_map_position=current_map_position):
        if not isinstance(service, dict):
            continue
        annotated = dict(service)
        service_id = str(annotated.get("service_id") or annotated.get("service_key") or "").strip().lower()
        service_state = service_states.get(service_id) or {}
        completed = str(service_state.get("status") or "").strip().lower() == "completed"
        requirements = requirement_map.get(service_id) or requirement_map.get(str(annotated.get("service_key") or "").strip().lower()) or {}
        gate = build_group_interaction_gate_result(
            interaction_kind="service",
            interaction_id=service_id,
            label=str(annotated.get("label") or service_id),
            requirements=requirements,
            state_flags=context.get("node_state_flags"),
            group_state_flags=context.get("group_state_flags"),
            region_link_ids=context.get("region_link_ids"),
            destination_event_state=context.get("destination_event_state"),
            visit_count=int(context.get("visit_count") or 0),
            completed=completed,
            interaction_type="action",
            unlock_hint=str(requirements.get("unlock_hint") or ""),
        )
        if not gate:
            continue
        availability_status = str(gate.get("availability_status") or "available").strip().lower()
        annotated.update(gate)
        annotated["service_id"] = service_id or annotated.get("service_id") or annotated.get("service_key")
        effect = effect_map.get(service_id) or effect_map.get(str(annotated.get("service_key") or "").strip().lower())
        if effect:
            effect_summary = str(effect.get("summary") or "").strip()
            if effect_summary:
                annotated["summary"] = effect_summary
            annotated["service_kind"] = str(effect.get("service_kind") or annotated.get("service_kind") or annotated.get("service_type") or "service")
            annotated["source"] = str(effect.get("source") or service.get("source") or annotated.get("source") or "registry")
            annotated["one_shot"] = bool(effect.get("one_shot"))
        else:
            annotated["source"] = str(service.get("source") or annotated.get("source") or "registry")
        annotated["status"] = availability_status
        annotated["available"] = bool(gate.get("available"))
        if availability_status == "completed" and not annotated.get("unavailable_reason"):
            annotated["unavailable_reason"] = "already_used"
        availability.append(annotated)
    return availability


def get_current_group_local_interaction_surface(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    context = _get_current_group_local_interaction_context(sess, resolved_group_id)
    if not context:
        return None
    current_map_position = dict(context.get("current_map_position") or {})
    node_id = str(current_map_position.get("node_id") or "").strip().lower()
    node_label = str(current_map_position.get("label") or node_id).strip()
    actions = get_current_group_context_action_availability(sess, group_id=resolved_group_id)
    services = get_current_group_service_availability(sess, group_id=resolved_group_id)
    available_actions = [dict(item) for item in actions if str(item.get("availability_status") or "") == "available"]
    locked_actions = [dict(item) for item in actions if str(item.get("availability_status") or "") != "available"]
    available_services = [dict(item) for item in services if str(item.get("availability_status") or "") == "available"]
    locked_services = [dict(item) for item in services if str(item.get("availability_status") or "") != "available"]
    summary = (
        f"У {node_label} доступно {len(available_actions)} действий и {len(available_services)} услуг; "
        f"ограничено {len(locked_actions)} действий и {len(locked_services)} услуг."
    )
    return {
        "node_id": node_id,
        "node_label": node_label,
        "available_actions": available_actions,
        "locked_actions": locked_actions,
        "available_services": available_services,
        "locked_services": locked_services,
        "summary": summary,
    }


def get_group_node_progress_summary(sess: Session, group_id: str, node_id: str) -> dict[str, Any] | None:
    group_key = str(group_id or "").strip()
    normalized_node_id = str(node_id or "").strip().lower()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict) or not normalized_node_id:
        return None
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    current_node_id = str((current_map_position or {}).get("node_id") or "").strip().lower()
    if normalized_node_id != current_node_id:
        return None
    return _build_group_node_progress_summary_for_node(
        sess,
        group_key,
        normalized_node_id,
        current_map_position=current_map_position,
    )


def get_current_group_node_progress_summary(
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
    current_node_id = str((current_map_position or {}).get("node_id") or "").strip().lower()
    if not current_node_id:
        return None
    return get_group_node_progress_summary(sess, resolved_group_id, current_node_id)


def get_current_group_current_node_progress(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    return get_current_group_node_progress_summary(sess, player_id=player_id, group_id=group_id)


def _normalize_group_region_exploration_summary(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    region_id = str(raw.get("region_id") or "").strip().lower()
    region_label = str(raw.get("region_label") or region_id).strip()
    progression_status = str(raw.get("progression_status") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    current_node_id = str(raw.get("current_node_id") or "").strip().lower()
    current_node_label = str(raw.get("current_node_label") or current_node_id).strip()
    if progression_status not in {
        "newly_opened_region",
        "active_frontier",
        "expanding_routes",
        "locally_saturated",
        "blocked_progress",
        "region_quiet",
    }:
        return None
    if not region_id or not region_label or not summary:
        return None
    return {
        "region_id": region_id[:120],
        "region_label": region_label[:160],
        "progression_status": progression_status[:40],
        "summary": summary[:400],
        "current_node_id": current_node_id[:120],
        "current_node_label": current_node_label[:160],
        "revealed_node_count": max(0, as_int(raw.get("revealed_node_count"), 0)),
        "visited_node_count": max(0, as_int(raw.get("visited_node_count"), 0)),
        "reachable_unvisited_count": max(0, as_int(raw.get("reachable_unvisited_count"), 0)),
        "blocked_frontier_count": max(0, as_int(raw.get("blocked_frontier_count"), 0)),
        "quiet_node_count": max(0, as_int(raw.get("quiet_node_count"), 0)),
        "active_local_node_count": max(0, as_int(raw.get("active_local_node_count"), 0)),
        "locally_resolved_node_count": max(0, as_int(raw.get("locally_resolved_node_count"), 0)),
        "current_primary_frontier": dict(raw.get("current_primary_frontier") or {}) if isinstance(raw.get("current_primary_frontier"), dict) else None,
        "current_primary_lead": dict(raw.get("current_primary_lead") or {}) if isinstance(raw.get("current_primary_lead"), dict) else None,
        "source": str(raw.get("source") or "region_exploration")[:40] or "region_exploration",
    }


def build_group_region_exploration_summary(
    *,
    region_id: str,
    region_label: str,
    progression_status: str,
    summary: str,
    current_node_id: str = "",
    current_node_label: str = "",
    revealed_node_count: int = 0,
    visited_node_count: int = 0,
    reachable_unvisited_count: int = 0,
    blocked_frontier_count: int = 0,
    quiet_node_count: int = 0,
    active_local_node_count: int = 0,
    locally_resolved_node_count: int = 0,
    current_primary_frontier: dict[str, Any] | None = None,
    current_primary_lead: dict[str, Any] | None = None,
    source: str = "region_exploration",
) -> dict[str, Any] | None:
    return _normalize_group_region_exploration_summary(
        {
            "region_id": region_id,
            "region_label": region_label,
            "progression_status": progression_status,
            "summary": summary,
            "current_node_id": current_node_id,
            "current_node_label": current_node_label,
            "revealed_node_count": revealed_node_count,
            "visited_node_count": visited_node_count,
            "reachable_unvisited_count": reachable_unvisited_count,
            "blocked_frontier_count": blocked_frontier_count,
            "quiet_node_count": quiet_node_count,
            "active_local_node_count": active_local_node_count,
            "locally_resolved_node_count": locally_resolved_node_count,
            "current_primary_frontier": current_primary_frontier,
            "current_primary_lead": current_primary_lead,
            "source": source,
        }
    )


def get_current_group_region_frontier_summary(
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
    planning = build_group_route_plan(sess, resolved_group_id)
    visit_map = _normalize_group_node_visit_state_map(group.get("node_visit_states"))
    reachable_unvisited_nodes = [
        dict(item)
        for item in (planning.get("reachable_destinations") or [])
        if str(item.get("target_node_id") or "").strip().lower()
        and str(item.get("target_node_id") or "").strip().lower() not in visit_map
    ]
    blocked_frontiers = [
        dict(item)
        for item in (planning.get("route_frontiers") or [])
        if str(item.get("frontier_type") or "").strip().lower() == "blocked_route"
    ]
    unresolved_local_nodes: list[dict[str, Any]] = []
    for node_id in sorted((_normalize_group_node_visit_state_map(group.get("node_visit_states"))).keys()):
        progress = _build_group_node_progress_summary_for_node(sess, resolved_group_id, node_id)
        if not progress:
            continue
        if str(progress.get("progression_status") or "").strip().lower() not in {
            "newly_arrived",
            "locally_active",
            "partially_resolved",
            "revisit_changed",
        }:
            continue
        unresolved_local_nodes.append(
            {
                "node_id": str(progress.get("node_id") or ""),
                "node_label": str(progress.get("node_label") or progress.get("node_id") or ""),
                "progression_status": str(progress.get("progression_status") or ""),
                "summary": str(progress.get("summary") or ""),
            }
        )
    summary = (
        f"У группы {len(reachable_unvisited_nodes)} достижимых непосещённых точек, "
        f"{len(blocked_frontiers)} заблокированных frontier-веток и "
        f"{len(unresolved_local_nodes)} локально незавершённых узлов."
    )
    return {
        "blocked_frontiers": blocked_frontiers,
        "reachable_unvisited_nodes": reachable_unvisited_nodes,
        "unresolved_local_nodes": unresolved_local_nodes,
        "summary": summary,
    }


def get_group_region_exploration_summary(sess: Session, group_id: str) -> dict[str, Any] | None:
    group_key = str(group_id or "").strip()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict):
        return None
    current_position = _normalize_map_position(group.get("current_map_position"))
    current_node_id = str((current_position or {}).get("node_id") or "").strip().lower()
    current_node_label = str((current_position or {}).get("label") or current_node_id).strip()
    revealed_node_ids = sorted(_get_group_revealed_node_ids(sess, group))
    visit_map = _normalize_group_node_visit_state_map(group.get("node_visit_states"))
    planning = build_group_route_plan(sess, group_key)
    frontier_summary = get_current_group_region_frontier_summary(sess, group_id=group_key) or {
        "blocked_frontiers": [],
        "reachable_unvisited_nodes": [],
        "unresolved_local_nodes": [],
        "summary": "",
    }
    current_primary_lead = get_group_primary_exploration_lead(sess, group_key)
    blocked_frontiers = list(frontier_summary.get("blocked_frontiers") or [])
    reachable_unvisited_nodes = list(frontier_summary.get("reachable_unvisited_nodes") or [])
    unresolved_local_nodes = list(frontier_summary.get("unresolved_local_nodes") or [])
    current_primary_frontier = dict(blocked_frontiers[0]) if blocked_frontiers else (dict(reachable_unvisited_nodes[0]) if reachable_unvisited_nodes else None)
    quiet_node_count = 0
    active_local_node_count = 0
    locally_resolved_node_count = 0
    for node_id in sorted(visit_map.keys()):
        progress = _build_group_node_progress_summary_for_node(sess, group_key, node_id)
        if not progress:
            continue
        status = str(progress.get("progression_status") or "").strip().lower()
        if status == "quiet_location":
            quiet_node_count += 1
        elif status == "locally_resolved":
            locally_resolved_node_count += 1
        elif status in {"newly_arrived", "locally_active", "partially_resolved", "revisit_changed"}:
            active_local_node_count += 1
    revealed_node_count = len(revealed_node_ids)
    visited_node_count = len(visit_map)
    reachable_unvisited_count = len(reachable_unvisited_nodes)
    blocked_frontier_count = len(blocked_frontiers)
    if visited_node_count > 0 and (locally_resolved_node_count + quiet_node_count) >= visited_node_count and active_local_node_count == 0 and reachable_unvisited_count == 0 and blocked_frontier_count == 0:
        progression_status = "locally_saturated"
        summary = "Текущая раскрытая часть региона в основном уже посещена и локально выработана."
    elif revealed_node_count <= 1 and reachable_unvisited_count == 0 and blocked_frontier_count == 0 and active_local_node_count == 0:
        progression_status = "region_quiet"
        summary = f"{current_node_label or 'Текущий регион'} пока выглядит тихим и почти не даёт новых направлений."
    elif revealed_node_count <= 2 and visited_node_count <= 1 and blocked_frontier_count == 0:
        progression_status = "newly_opened_region"
        summary = f"Группа только начинает раскрывать регион вокруг {current_node_label or 'текущей точки'}."
    elif blocked_frontier_count > 0 and reachable_unvisited_count == 0:
        progression_status = "blocked_progress"
        summary = "Следующее расширение региона сейчас в основном упирается в известные заблокированные frontier-ветки."
    elif reachable_unvisited_count >= 2:
        progression_status = "expanding_routes"
        summary = "Раскрытая сеть маршрутов ещё расширяется, и у группы уже есть несколько достижимых направлений вперёд."
    elif reachable_unvisited_count >= 1:
        progression_status = "active_frontier"
        summary = "У группы остаются достижимые непосещённые точки, так что frontier региона ещё активен."
    else:
        progression_status = "region_quiet"
        summary = "Текущая раскрытая часть региона пока даёт мало активных frontier-направлений."
    current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    region_identity = _resolve_region_identity_for_position(current_position) or {}
    region_id = str((current_region_state or {}).get("region_id") or region_identity.get("region_id") or (current_position or {}).get("map_level") or "region").strip().lower() or "region"
    region_label = str((current_region_state or {}).get("region_label") or region_identity.get("region_label") or (current_position or {}).get("area_label") or current_node_label or "Текущий регион").strip()
    return build_group_region_exploration_summary(
        region_id=region_id,
        region_label=region_label,
        progression_status=progression_status,
        summary=summary,
        current_node_id=current_node_id,
        current_node_label=current_node_label,
        revealed_node_count=revealed_node_count,
        visited_node_count=visited_node_count,
        reachable_unvisited_count=reachable_unvisited_count,
        blocked_frontier_count=blocked_frontier_count,
        quiet_node_count=quiet_node_count,
        active_local_node_count=active_local_node_count,
        locally_resolved_node_count=locally_resolved_node_count,
        current_primary_frontier=current_primary_frontier,
        current_primary_lead=current_primary_lead,
        source="region_exploration",
    )


def get_current_group_region_exploration_summary(
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
    return get_group_region_exploration_summary(sess, resolved_group_id)


def _normalize_group_discovered_region_summary(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    region_id = str(raw.get("region_id") or "").strip().lower()
    region_label = str(raw.get("region_label") or region_id).strip()
    region_status = str(raw.get("region_status") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    onboarding_status = str(raw.get("onboarding_status") or "").strip().lower()
    primary_frontier = dict(raw.get("primary_frontier") or {}) if isinstance(raw.get("primary_frontier"), dict) else None
    if region_status not in {
        "current_active_region",
        "current_blocked_region",
        "active_region",
        "blocked_region",
        "saturated_region",
        "quiet_region",
        "newly_onboarded_region",
    }:
        return None
    if not region_id or not region_label or not summary:
        return None
    return {
        "region_id": region_id[:120],
        "region_label": region_label[:160],
        "region_status": region_status[:40],
        "summary": summary[:400],
        "current_region": bool(raw.get("current_region")),
        "visit_count": max(0, as_int(raw.get("visit_count"), 0)),
        "first_entered_at": str(raw.get("first_entered_at") or "")[:80],
        "last_entered_at": str(raw.get("last_entered_at") or "")[:80],
        "revealed_node_count": max(0, as_int(raw.get("revealed_node_count"), 0)),
        "visited_node_count": max(0, as_int(raw.get("visited_node_count"), 0)),
        "unresolved_local_node_count": max(0, as_int(raw.get("unresolved_local_node_count"), 0)),
        "blocked_frontier_count": max(0, as_int(raw.get("blocked_frontier_count"), 0)),
        "reachable_unvisited_count": max(0, as_int(raw.get("reachable_unvisited_count"), 0)),
        "onboarding_status": onboarding_status[:40],
        "primary_frontier": primary_frontier,
        "source": str(raw.get("source") or "region_world_overview")[:40] or "region_world_overview",
    }


def build_group_discovered_region_summary(
    *,
    region_id: str,
    region_label: str,
    region_status: str,
    summary: str,
    current_region: bool = False,
    visit_count: int = 0,
    first_entered_at: str = "",
    last_entered_at: str = "",
    revealed_node_count: int = 0,
    visited_node_count: int = 0,
    unresolved_local_node_count: int = 0,
    blocked_frontier_count: int = 0,
    reachable_unvisited_count: int = 0,
    onboarding_status: str = "",
    primary_frontier: dict[str, Any] | None = None,
    source: str = "region_world_overview",
) -> dict[str, Any] | None:
    return _normalize_group_discovered_region_summary(
        {
            "region_id": region_id,
            "region_label": region_label,
            "region_status": region_status,
            "summary": summary,
            "current_region": current_region,
            "visit_count": visit_count,
            "first_entered_at": first_entered_at,
            "last_entered_at": last_entered_at,
            "revealed_node_count": revealed_node_count,
            "visited_node_count": visited_node_count,
            "unresolved_local_node_count": unresolved_local_node_count,
            "blocked_frontier_count": blocked_frontier_count,
            "reachable_unvisited_count": reachable_unvisited_count,
            "onboarding_status": onboarding_status,
            "primary_frontier": primary_frontier,
            "source": source,
        }
    )


def _normalize_group_region_world_overview(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    current_region_id = str(raw.get("current_region_id") or "").strip().lower()
    current_region_label = str(raw.get("current_region_label") or current_region_id).strip()
    region_summaries = [
        dict(item)
        for item in (raw.get("region_summaries") or [])
        if _normalize_group_discovered_region_summary(item)
    ] if isinstance(raw.get("region_summaries"), list) else []
    primary_region_focus = _normalize_group_discovered_region_summary(raw.get("primary_region_focus"))
    summary = str(raw.get("summary") or "").strip()
    if not current_region_id or not current_region_label or not summary:
        return None
    return {
        "current_region_id": current_region_id[:120],
        "current_region_label": current_region_label[:160],
        "discovered_region_count": max(0, as_int(raw.get("discovered_region_count"), 0)),
        "active_region_count": max(0, as_int(raw.get("active_region_count"), 0)),
        "blocked_region_count": max(0, as_int(raw.get("blocked_region_count"), 0)),
        "saturated_region_count": max(0, as_int(raw.get("saturated_region_count"), 0)),
        "quiet_region_count": max(0, as_int(raw.get("quiet_region_count"), 0)),
        "primary_region_focus": primary_region_focus,
        "region_summaries": region_summaries,
        "summary": summary[:400],
    }


def _resolve_region_identity_for_node_id(node_id: str | None) -> dict[str, Any] | None:
    resolved_node_id = str(node_id or "").strip().lower()
    if not resolved_node_id:
        return None
    identity = get_static_region_identity(node_id=resolved_node_id) or {}
    region_id = str(identity.get("region_id") or "").strip().lower()
    region_label = str(identity.get("region_label") or "").strip()
    if not region_id or not region_label:
        return None
    return {"region_id": region_id, "region_label": region_label}


def _build_region_gateway_snapshots_for_group(
    sess: Session,
    group_id: str,
) -> list[dict[str, Any]]:
    group_key = str(group_id or "").strip()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict):
        return []
    revealed_node_ids = _get_group_revealed_node_ids(sess, group)
    visit_map = _normalize_group_node_visit_state_map(group.get("node_visit_states"))
    discovered_map = _normalize_group_discovered_region_map(group.get("discovered_regions"))
    node_state_map = _normalize_group_node_state_map(group.get("node_states"))
    destination_event_map = _normalize_group_destination_event_state_map(group.get("destination_event_states"))
    known_anchor_node_ids = {
        str(node_id).strip().lower()
        for region in discovered_map.values()
        for node_id in (region.get("first_anchor_node_id"), region.get("last_anchor_node_id"))
        if str(node_id or "").strip()
    }
    current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    current_anchor_node_id = str((current_region_state or {}).get("current_node_id") or "").strip().lower()
    if current_anchor_node_id:
        known_anchor_node_ids.add(current_anchor_node_id)
    snapshots: list[dict[str, Any]] = []
    for definition in get_static_region_gateways(region_id="region"):
        if not isinstance(definition, dict):
            continue
        source_node_id = str(definition.get("source_node_id") or "").strip().lower()
        if not source_node_id:
            continue
        if source_node_id not in revealed_node_ids and source_node_id not in known_anchor_node_ids:
            continue
        if source_node_id not in visit_map and source_node_id not in known_anchor_node_ids:
            continue
        route_id = str(definition.get("route_id") or "").strip().lower()
        effective_route_access = get_effective_group_route_access_state(sess, group_key, route_id=route_id) if route_id else {}
        blocked = bool(route_id and str((effective_route_access or {}).get("access_state") or "").strip().lower() == "blocked")
        node_state_flags = list((node_state_map.get(source_node_id) or {}).get("state_flags") or [])
        destination_event_state = destination_event_map.get(source_node_id)
        visit_count = max(0, as_int((visit_map.get(source_node_id) or {}).get("visit_count"), 0))
        requirements = {
            key: definition.get(key)
            for key in (
                "requires_node_state_flag",
                "requires_destination_event_id",
                "requires_destination_event_result_type",
                "requires_min_visit_count",
            )
            if definition.get(key) not in {None, ""}
        }
        requirement_eval = _evaluate_local_requirement_set(
            requirements=requirements,
            state_flags=node_state_flags,
            destination_event_state=destination_event_state,
            visit_count=visit_count,
        )
        future_stub = bool(definition.get("future_stub"))
        locked = bool(requirement_eval.get("locked"))
        if future_stub:
            gateway_status = "future_stub"
        elif blocked:
            gateway_status = "blocked"
        elif locked:
            gateway_status = "locked"
        else:
            gateway_status = "open"
        snapshots.append(
            {
                "gateway_id": str(definition.get("gateway_id") or ""),
                "gateway_label": str(definition.get("label") or definition.get("gateway_id") or ""),
                "gateway_status": gateway_status,
                "source_node_id": source_node_id,
                "route_id": route_id,
                "target_region_id": str(definition.get("target_region_id") or "").strip().lower(),
                "target_region_label": str(definition.get("target_region_label") or definition.get("target_region_id") or ""),
                "blocked_reason": str((effective_route_access or {}).get("block_reason") or ""),
                "unlock_hint": str(definition.get("unlock_hint") or ""),
                "future_stub": future_stub,
            }
        )
    return snapshots


def _region_focus_sort_key(summary: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
    status = str(summary.get("region_status") or "").strip().lower()
    status_order = {
        "newly_onboarded_region": 0,
        "current_active_region": 1,
        "current_blocked_region": 2,
        "active_region": 3,
        "blocked_region": 4,
        "saturated_region": 5,
        "quiet_region": 6,
    }
    return (
        status_order.get(status, 99),
        0 if bool(summary.get("current_region")) else 1,
        -max(0, as_int(summary.get("reachable_unvisited_count"), 0)),
        -max(0, as_int(summary.get("unresolved_local_node_count"), 0)),
        -max(0, as_int(summary.get("visit_count"), 0)),
        str(summary.get("region_label") or ""),
    )


def get_group_discovered_region_summaries(sess: Session, group_id: str) -> list[dict[str, Any]]:
    group_key = str(group_id or "").strip()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict):
        return []
    current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    discovered_map = _normalize_group_discovered_region_map(group.get("discovered_regions"))
    if not discovered_map:
        return []
    current_region_summary = get_group_region_exploration_summary(sess, group_key) or {}
    onboarding_map = _normalize_group_region_onboarding_state_map(group.get("region_onboarding_states"))
    revealed_node_ids = sorted(_get_group_revealed_node_ids(sess, group))
    visit_map = _normalize_group_node_visit_state_map(group.get("node_visit_states"))
    gateway_snapshots = _build_region_gateway_snapshots_for_group(sess, group_key)
    region_summaries: list[dict[str, Any]] = []
    for region_id, discovered_state in discovered_map.items():
        region_label = str(discovered_state.get("region_label") or region_id).strip()
        is_current_region = str((current_region_state or {}).get("region_id") or "").strip().lower() == region_id
        revealed_nodes_in_region = [
            node_id
            for node_id in revealed_node_ids
            if str(((_resolve_region_identity_for_node_id(node_id) or {}).get("region_id")) or "") == region_id
        ]
        visited_nodes_in_region = [
            node_id
            for node_id in visit_map.keys()
            if str(((_resolve_region_identity_for_node_id(node_id) or {}).get("region_id")) or "") == region_id
        ]
        for anchor_key in ("first_anchor_node_id", "last_anchor_node_id"):
            anchor_node_id = str(discovered_state.get(anchor_key) or "").strip().lower()
            if not anchor_node_id:
                continue
            anchor_identity = _resolve_region_identity_for_node_id(anchor_node_id) or {}
            if str(anchor_identity.get("region_id") or "") != region_id:
                continue
            if anchor_node_id not in revealed_nodes_in_region:
                revealed_nodes_in_region.append(anchor_node_id)
            if anchor_node_id not in visited_nodes_in_region:
                visited_nodes_in_region.append(anchor_node_id)
        unresolved_local_nodes = []
        for node_id in sorted(visited_nodes_in_region):
            progress = _build_group_node_progress_summary_for_node(sess, group_key, node_id)
            if not progress:
                continue
            if str(progress.get("progression_status") or "").strip().lower() not in {
                "newly_arrived",
                "locally_active",
                "partially_resolved",
                "revisit_changed",
            }:
                continue
            unresolved_local_nodes.append(progress)
        region_gateway_snapshots = [
            dict(item)
            for item in gateway_snapshots
            if str(((_resolve_region_identity_for_node_id(item.get("source_node_id")) or {}).get("region_id")) or "") == region_id
        ]
        blocked_frontier_count = sum(1 for item in region_gateway_snapshots if str(item.get("gateway_status") or "") == "blocked")
        primary_frontier: dict[str, Any] | None = None
        reachable_unvisited_count = max(0, len(revealed_nodes_in_region) - len(visited_nodes_in_region))
        summary_text = ""
        onboarding_status = str((onboarding_map.get(region_id) or {}).get("status") or "").strip().lower()
        if is_current_region and current_region_summary:
            blocked_frontier_count = max(blocked_frontier_count, as_int(current_region_summary.get("blocked_frontier_count"), 0))
            reachable_unvisited_count = max(reachable_unvisited_count, as_int(current_region_summary.get("reachable_unvisited_count"), 0))
            primary_frontier = dict(current_region_summary.get("current_primary_frontier") or {}) if isinstance(current_region_summary.get("current_primary_frontier"), dict) else None
            current_progression_status = str(current_region_summary.get("progression_status") or "").strip().lower()
            if onboarding_status == "applied" and as_int(discovered_state.get("visit_count"), 0) <= 1 and as_int(current_region_summary.get("visited_node_count"), 0) <= 1:
                region_status = "newly_onboarded_region"
                summary_text = f"{region_label} только что onboarded и пока раскрывает стартовый срез вокруг якоря входа."
            elif current_progression_status == "blocked_progress":
                region_status = "current_blocked_region"
                summary_text = str(current_region_summary.get("summary") or "")
            elif current_progression_status in {"active_frontier", "expanding_routes", "newly_opened_region"} or unresolved_local_nodes:
                region_status = "current_active_region"
                summary_text = str(current_region_summary.get("summary") or "")
            elif current_progression_status == "locally_saturated":
                region_status = "saturated_region"
                summary_text = str(current_region_summary.get("summary") or "")
            else:
                region_status = "quiet_region"
                summary_text = str(current_region_summary.get("summary") or "")
        else:
            blocked_gateway = next((item for item in region_gateway_snapshots if str(item.get("gateway_status") or "") == "blocked"), None)
            if blocked_gateway:
                primary_frontier = {
                    "gateway_id": str(blocked_gateway.get("gateway_id") or ""),
                    "gateway_label": str(blocked_gateway.get("gateway_label") or ""),
                    "gateway_status": "blocked",
                }
            elif reachable_unvisited_count > 0:
                first_unvisited = next((node_id for node_id in revealed_nodes_in_region if node_id not in visit_map), "")
                if first_unvisited:
                    primary_frontier = {
                        "target_node_id": first_unvisited,
                        "target_node_label": str((get_static_node(first_unvisited) or {}).get("label") or first_unvisited),
                        "plan_status": "reachable",
                    }
            if blocked_frontier_count > 0:
                region_status = "blocked_region"
                summary_text = f"В {region_label} дальнейший прогресс сейчас в основном упирается в известные заблокированные выходы."
            elif onboarding_status == "applied" and as_int(discovered_state.get("visit_count"), 0) <= 1 and len(visited_nodes_in_region) <= 1:
                region_status = "newly_onboarded_region"
                summary_text = f"{region_label} только что закреплён как новый регион и пока остаётся свежим стартовым плацдармом."
            elif unresolved_local_nodes or reachable_unvisited_count > 0:
                region_status = "active_region"
                summary_text = f"{region_label} остаётся значимым направлением: там ещё есть незавершённые локальные точки или видимые непосещённые узлы."
            elif len(visited_nodes_in_region) > 0 and len(revealed_nodes_in_region) <= len(visited_nodes_in_region):
                region_status = "saturated_region"
                summary_text = f"{region_label} в основном уже посещён и локально выработан."
            else:
                region_status = "quiet_region"
                summary_text = f"{region_label} пока выглядит тихим известным регионом без сильного текущего давления на прогресс."
        summary = build_group_discovered_region_summary(
            region_id=region_id,
            region_label=region_label,
            region_status=region_status,
            summary=summary_text,
            current_region=is_current_region,
            visit_count=as_int(discovered_state.get("visit_count"), 0),
            first_entered_at=str(discovered_state.get("first_entered_at") or ""),
            last_entered_at=str(discovered_state.get("last_entered_at") or ""),
            revealed_node_count=len(revealed_nodes_in_region),
            visited_node_count=len(visited_nodes_in_region),
            unresolved_local_node_count=len(unresolved_local_nodes),
            blocked_frontier_count=blocked_frontier_count,
            reachable_unvisited_count=reachable_unvisited_count,
            onboarding_status=onboarding_status,
            primary_frontier=primary_frontier,
            source="region_world_overview",
        )
        if summary:
            region_summaries.append(summary)
    region_summaries.sort(key=_region_focus_sort_key)
    return region_summaries


def get_current_group_discovered_region_summaries(
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
    return get_group_discovered_region_summaries(sess, resolved_group_id)


def get_current_group_primary_region_focus(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    summaries = get_current_group_discovered_region_summaries(sess, player_id=player_id, group_id=group_id)
    return dict(summaries[0]) if summaries else None


def get_current_group_region_world_overview(
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
    summaries = get_group_discovered_region_summaries(sess, resolved_group_id)
    current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    if not summaries or not current_region_state:
        return None
    active_region_count = sum(1 for item in summaries if str(item.get("region_status") or "") in {"current_active_region", "active_region", "newly_onboarded_region"})
    blocked_region_count = sum(1 for item in summaries if str(item.get("region_status") or "") in {"current_blocked_region", "blocked_region"})
    saturated_region_count = sum(1 for item in summaries if str(item.get("region_status") or "") == "saturated_region")
    quiet_region_count = sum(1 for item in summaries if str(item.get("region_status") or "") == "quiet_region")
    primary_region_focus = dict(summaries[0])
    summary = (
        f"Группа видит {len(summaries)} открытых регионов: "
        f"{active_region_count} активных, {blocked_region_count} упёршихся в блоки, "
        f"{saturated_region_count} в основном выработанных и {quiet_region_count} тихих."
    )
    return _normalize_group_region_world_overview(
        {
            "current_region_id": str(current_region_state.get("region_id") or ""),
            "current_region_label": str(current_region_state.get("region_label") or ""),
            "discovered_region_count": len(summaries),
            "active_region_count": active_region_count,
            "blocked_region_count": blocked_region_count,
            "saturated_region_count": saturated_region_count,
            "quiet_region_count": quiet_region_count,
            "primary_region_focus": primary_region_focus,
            "region_summaries": summaries,
            "summary": summary,
        }
    )


def _normalize_group_region_gateway(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    gateway_id = str(raw.get("gateway_id") or "").strip().lower()
    gateway_label = str(raw.get("gateway_label") or raw.get("label") or gateway_id).strip()
    gateway_status = str(raw.get("gateway_status") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    source_node_id = str(raw.get("source_node_id") or "").strip().lower()
    source_node_label = str(raw.get("source_node_label") or source_node_id).strip()
    route_id = str(raw.get("route_id") or "").strip().lower()
    target_region_id = str(raw.get("target_region_id") or "").strip().lower()
    target_region_label = str(raw.get("target_region_label") or target_region_id).strip()
    if gateway_status not in {"open", "blocked", "locked", "future_stub", "unavailable"}:
        return None
    if not gateway_id or not gateway_label or not summary or not source_node_id or not target_region_id or not target_region_label:
        return None
    return {
        "gateway_id": gateway_id[:120],
        "gateway_label": gateway_label[:160],
        "gateway_status": gateway_status[:40],
        "summary": summary[:400],
        "source_node_id": source_node_id[:120],
        "source_node_label": source_node_label[:160],
        "route_id": route_id[:160],
        "target_region_id": target_region_id[:120],
        "target_region_label": target_region_label[:160],
        "reachable": bool(raw.get("reachable")),
        "blocked": bool(raw.get("blocked")),
        "locked": bool(raw.get("locked")),
        "blocked_reason": str(raw.get("blocked_reason") or "")[:160],
        "unlock_hint": str(raw.get("unlock_hint") or "")[:240],
        "future_stub": bool(raw.get("future_stub")),
        "source": str(raw.get("source") or "region_gateway")[:40] or "region_gateway",
    }


def _normalize_group_region_target_plan(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    target_region_id = str(raw.get("target_region_id") or "").strip().lower()
    target_region_label = str(raw.get("target_region_label") or target_region_id).strip()
    plan_status = str(raw.get("plan_status") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    current_region_id = str(raw.get("current_region_id") or "").strip().lower()
    current_region_label = str(raw.get("current_region_label") or current_region_id).strip()
    gateway_id = str(raw.get("gateway_id") or "").strip().lower()
    gateway_label = str(raw.get("gateway_label") or gateway_id).strip()
    gateway_status = str(raw.get("gateway_status") or "").strip().lower()
    gateway_source_node_id = str(raw.get("gateway_source_node_id") or "").strip().lower()
    gateway_source_node_label = str(raw.get("gateway_source_node_label") or gateway_source_node_id).strip()
    blocked_reason = str(raw.get("blocked_reason") or "").strip()
    suggested_command = str(raw.get("suggested_command") or "").strip()
    source = str(raw.get("source") or "region_target_guidance").strip() or "region_target_guidance"
    path_node_ids = [
        str(item).strip().lower()
        for item in (raw.get("path_node_ids") or [])
        if str(item or "").strip()
    ]
    path_route_ids = [
        str(item).strip().lower()
        for item in (raw.get("path_route_ids") or [])
        if str(item or "").strip()
    ]
    if plan_status not in {
        "current_region",
        "approach_gateway",
        "gateway_ready",
        "gateway_blocked",
        "gateway_locked",
        "gateway_future_stub",
        "target_region_undiscovered",
        "target_region_unavailable",
    }:
        return None
    if not target_region_id or not target_region_label or not summary or not current_region_id or not current_region_label:
        return None
    return {
        "target_region_id": target_region_id[:120],
        "target_region_label": target_region_label[:160],
        "plan_status": plan_status[:60],
        "summary": summary[:400],
        "current_region_id": current_region_id[:120],
        "current_region_label": current_region_label[:160],
        "gateway_id": gateway_id[:120],
        "gateway_label": gateway_label[:160],
        "gateway_status": gateway_status[:40],
        "gateway_source_node_id": gateway_source_node_id[:120],
        "gateway_source_node_label": gateway_source_node_label[:160],
        "path_node_ids": path_node_ids,
        "path_route_ids": path_route_ids,
        "path_step_count": max(0, as_int(raw.get("path_step_count"), len(path_route_ids))),
        "reachable": bool(raw.get("reachable")),
        "blocked_reason": blocked_reason[:240],
        "suggested_command": suggested_command[:160],
        "source": source[:40],
    }


def _normalize_group_region_target_options(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    current_region_id = str(raw.get("current_region_id") or "").strip().lower()
    current_region_label = str(raw.get("current_region_label") or current_region_id).strip()
    summary = str(raw.get("summary") or "").strip()
    primary_region_focus_plan = _normalize_group_region_target_plan(raw.get("primary_region_focus_plan"))
    target_region_plans = [
        plan
        for item in (raw.get("target_region_plans") or [])
        if (plan := _normalize_group_region_target_plan(item))
    ]
    if not current_region_id or not current_region_label or not summary:
        return None
    return {
        "current_region_id": current_region_id[:120],
        "current_region_label": current_region_label[:160],
        "primary_region_focus_plan": primary_region_focus_plan,
        "target_region_plans": target_region_plans,
        "summary": summary[:400],
    }


def _normalize_group_known_region_route(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    target_region_id = str(raw.get("target_region_id") or "").strip().lower()
    target_region_label = str(raw.get("target_region_label") or target_region_id).strip()
    route_status = str(raw.get("route_status") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    current_region_id = str(raw.get("current_region_id") or "").strip().lower()
    current_region_label = str(raw.get("current_region_label") or current_region_id).strip()
    region_path_ids = [str(item).strip().lower() for item in (raw.get("region_path_ids") or []) if str(item or "").strip()]
    region_path_labels = [str(item).strip() for item in (raw.get("region_path_labels") or []) if str(item or "").strip()]
    link_ids = [str(item).strip().lower() for item in (raw.get("link_ids") or []) if str(item or "").strip()]
    next_gateway_id = str(raw.get("next_gateway_id") or "").strip().lower()
    next_gateway_label = str(raw.get("next_gateway_label") or next_gateway_id).strip()
    next_gateway_status = str(raw.get("next_gateway_status") or "").strip().lower()
    next_gateway_source_node_id = str(raw.get("next_gateway_source_node_id") or "").strip().lower()
    next_gateway_source_node_label = str(raw.get("next_gateway_source_node_label") or next_gateway_source_node_id).strip()
    suggested_command = str(raw.get("suggested_command") or "").strip()
    source = str(raw.get("source") or "known_region_route").strip() or "known_region_route"
    if route_status not in {
        "current_region",
        "direct_route",
        "multi_region_route",
        "blocked_next_gateway",
        "locked_next_gateway",
        "future_stub_next_gateway",
        "target_region_undiscovered",
        "no_known_route",
    }:
        return None
    if not target_region_id or not target_region_label or not summary or not current_region_id or not current_region_label:
        return None
    return {
        "target_region_id": target_region_id[:120],
        "target_region_label": target_region_label[:160],
        "route_status": route_status[:60],
        "summary": summary[:400],
        "current_region_id": current_region_id[:120],
        "current_region_label": current_region_label[:160],
        "region_path_ids": region_path_ids,
        "region_path_labels": region_path_labels[:16] if len(region_path_labels) > 16 else region_path_labels,
        "link_ids": link_ids,
        "hop_count": max(0, as_int(raw.get("hop_count"), len(link_ids))),
        "next_gateway_id": next_gateway_id[:120],
        "next_gateway_label": next_gateway_label[:160],
        "next_gateway_status": next_gateway_status[:40],
        "next_gateway_source_node_id": next_gateway_source_node_id[:120],
        "next_gateway_source_node_label": next_gateway_source_node_label[:160],
        "suggested_command": suggested_command[:160],
        "source": source[:40],
    }


def _normalize_group_known_region_route_options(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    current_region_id = str(raw.get("current_region_id") or "").strip().lower()
    current_region_label = str(raw.get("current_region_label") or current_region_id).strip()
    primary_region_route = _normalize_group_known_region_route(raw.get("primary_region_route"))
    target_region_routes = [
        route
        for item in (raw.get("target_region_routes") or [])
        if (route := _normalize_group_known_region_route(item))
    ]
    summary = str(raw.get("summary") or "").strip()
    if not current_region_id or not current_region_label or not summary:
        return None
    return {
        "current_region_id": current_region_id[:120],
        "current_region_label": current_region_label[:160],
        "primary_region_route": primary_region_route,
        "target_region_routes": target_region_routes,
        "summary": summary[:400],
    }


def _normalize_group_active_region_pursuit(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    pursuit_id = str(raw.get("pursuit_id") or "").strip()
    target_region_id = str(raw.get("target_region_id") or "").strip().lower()
    target_region_label = str(raw.get("target_region_label") or target_region_id).strip()
    pursuit_status = str(raw.get("pursuit_status") or "").strip().lower()
    guidance_status = str(raw.get("guidance_status") or "").strip().lower()
    gateway_id = str(raw.get("gateway_id") or "").strip().lower()
    gateway_label = str(raw.get("gateway_label") or gateway_id).strip()
    gateway_source_node_id = str(raw.get("gateway_source_node_id") or "").strip().lower()
    gateway_source_node_label = str(raw.get("gateway_source_node_label") or gateway_source_node_id).strip()
    linked_journey_id = str(raw.get("linked_journey_id") or "").strip()
    suggested_next_command = str(raw.get("suggested_next_command") or "").strip()
    pursuit_scope = str(raw.get("pursuit_scope") or "").strip().lower()
    current_hop_region_id = str(raw.get("current_hop_region_id") or "").strip().lower()
    next_hop_region_id = str(raw.get("next_hop_region_id") or "").strip().lower()
    known_route_status = str(raw.get("known_route_status") or "").strip().lower()
    target_region_path_ids = [str(item).strip().lower() for item in (raw.get("target_region_path_ids") or []) if str(item or "").strip()]
    target_region_path_labels = [str(item).strip() for item in (raw.get("target_region_path_labels") or []) if str(item or "").strip()]
    source = str(raw.get("source") or "region_pursuit").strip() or "region_pursuit"
    created_at = str(raw.get("created_at") or "").strip()
    updated_at = str(raw.get("updated_at") or "").strip()
    if pursuit_status not in {
        "pursuing_gateway",
        "gateway_ready",
        "blocked",
        "locked",
        "future_stub",
        "unavailable",
        "cleared",
    }:
        return None
    if guidance_status not in {
        "current_region",
        "approach_gateway",
        "gateway_ready",
        "gateway_blocked",
        "gateway_locked",
        "gateway_future_stub",
        "target_region_undiscovered",
        "target_region_unavailable",
    }:
        return None
    if not pursuit_id or not target_region_id or not target_region_label:
        return None
    normalized = {
        "pursuit_id": pursuit_id[:80],
        "target_region_id": target_region_id[:120],
        "target_region_label": target_region_label[:160],
        "pursuit_status": pursuit_status[:40],
        "guidance_status": guidance_status[:60],
        "gateway_id": gateway_id[:120],
        "gateway_label": gateway_label[:160],
        "gateway_source_node_id": gateway_source_node_id[:120],
        "gateway_source_node_label": gateway_source_node_label[:160],
        "linked_journey_id": linked_journey_id[:80],
        "suggested_next_command": suggested_next_command[:160],
        "source": source[:40],
    }
    if pursuit_scope:
        if pursuit_scope not in {"direct_region", "known_multi_region"}:
            return None
        normalized["pursuit_scope"] = pursuit_scope[:40]
    if current_hop_region_id:
        normalized["current_hop_region_id"] = current_hop_region_id[:120]
    if next_hop_region_id:
        normalized["next_hop_region_id"] = next_hop_region_id[:120]
    if known_route_status:
        if known_route_status not in {
            "current_region",
            "direct_route",
            "multi_region_route",
            "blocked_next_gateway",
            "locked_next_gateway",
            "future_stub_next_gateway",
            "target_region_undiscovered",
            "no_known_route",
        }:
            return None
        normalized["known_route_status"] = known_route_status[:60]
    if target_region_path_ids:
        normalized["target_region_path_ids"] = target_region_path_ids
    if target_region_path_labels:
        normalized["target_region_path_labels"] = target_region_path_labels[:16] if len(target_region_path_labels) > 16 else target_region_path_labels
    if created_at:
        normalized["created_at"] = created_at[:80]
    if updated_at:
        normalized["updated_at"] = updated_at[:80]
    return normalized


def _normalize_group_last_region_pursuit_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or summary).strip()
    target_region_id = str(raw.get("target_region_id") or "").strip().lower()
    target_region_label = str(raw.get("target_region_label") or target_region_id).strip()
    guidance_status = str(raw.get("guidance_status") or "").strip().lower()
    gateway_id = str(raw.get("gateway_id") or "").strip().lower()
    gateway_label = str(raw.get("gateway_label") or gateway_id).strip()
    linked_journey_id = str(raw.get("linked_journey_id") or "").strip()
    pursuit_scope = str(raw.get("pursuit_scope") or "").strip().lower()
    current_hop_region_id = str(raw.get("current_hop_region_id") or "").strip().lower()
    next_hop_region_id = str(raw.get("next_hop_region_id") or "").strip().lower()
    known_route_status = str(raw.get("known_route_status") or "").strip().lower()
    target_region_path_ids = [str(item).strip().lower() for item in (raw.get("target_region_path_ids") or []) if str(item or "").strip()]
    target_region_path_labels = [str(item).strip() for item in (raw.get("target_region_path_labels") or []) if str(item or "").strip()]
    source = str(raw.get("source") or "region_pursuit").strip() or "region_pursuit"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if result_type not in {
        "region_pursuit_set",
        "region_pursuit_updated",
        "region_pursuit_gateway_ready",
        "region_pursuit_blocked",
        "region_pursuit_locked",
        "region_pursuit_future_stub",
        "region_pursuit_unavailable",
        "region_pursuit_cleared",
        "region_pursuit_multihop_set",
        "region_pursuit_multihop_updated",
        "region_pursuit_multihop_blocked",
        "region_pursuit_multihop_unavailable",
    }:
        return None
    if guidance_status and guidance_status not in {
        "current_region",
        "approach_gateway",
        "gateway_ready",
        "gateway_blocked",
        "gateway_locked",
        "gateway_future_stub",
        "target_region_undiscovered",
        "target_region_unavailable",
    }:
        return None
    if not result_id or not summary or not result_summary or not target_region_id or not target_region_label:
        return None
    normalized = {
        "result_id": result_id[:80],
        "result_type": result_type[:60],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "target_region_id": target_region_id[:120],
        "target_region_label": target_region_label[:160],
        "guidance_status": guidance_status[:60],
        "gateway_id": gateway_id[:120],
        "gateway_label": gateway_label[:160],
        "linked_journey_id": linked_journey_id[:80],
        "source": source[:40],
    }
    if pursuit_scope:
        if pursuit_scope not in {"direct_region", "known_multi_region"}:
            return None
        normalized["pursuit_scope"] = pursuit_scope[:40]
    if current_hop_region_id:
        normalized["current_hop_region_id"] = current_hop_region_id[:120]
    if next_hop_region_id:
        normalized["next_hop_region_id"] = next_hop_region_id[:120]
    if known_route_status:
        if known_route_status not in {
            "current_region",
            "direct_route",
            "multi_region_route",
            "blocked_next_gateway",
            "locked_next_gateway",
            "future_stub_next_gateway",
            "target_region_undiscovered",
            "no_known_route",
        }:
            return None
        normalized["known_route_status"] = known_route_status[:60]
    if target_region_path_ids:
        normalized["target_region_path_ids"] = target_region_path_ids
    if target_region_path_labels:
        normalized["target_region_path_labels"] = target_region_path_labels[:16] if len(target_region_path_labels) > 16 else target_region_path_labels
    if resolved_at:
        normalized["resolved_at"] = resolved_at[:80]
    return normalized


def _normalize_group_last_region_pursuit_step_result(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result_id = str(raw.get("result_id") or "").strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or summary).strip()
    target_region_id = str(raw.get("target_region_id") or "").strip().lower()
    target_region_label = str(raw.get("target_region_label") or target_region_id).strip()
    pursuit_id = str(raw.get("pursuit_id") or "").strip()
    pursuit_status = str(raw.get("pursuit_status") or "").strip().lower()
    step_kind = str(raw.get("step_kind") or "").strip().lower()
    linked_journey_id = str(raw.get("linked_journey_id") or "").strip()
    gateway_id = str(raw.get("gateway_id") or "").strip().lower()
    gateway_label = str(raw.get("gateway_label") or gateway_id).strip()
    source = str(raw.get("source") or "region_pursuit_step").strip() or "region_pursuit_step"
    resolved_at = str(raw.get("resolved_at") or "").strip()
    if result_type not in {
        "region_pursuit_step_advanced",
        "region_pursuit_step_gateway_ready",
        "region_pursuit_step_transitioned",
        "region_pursuit_step_blocked",
        "region_pursuit_step_locked",
        "region_pursuit_step_future_stub",
        "region_pursuit_step_unavailable",
        "region_pursuit_step_invalid",
    }:
        return None
    if pursuit_status and pursuit_status not in {
        "pursuing_gateway",
        "gateway_ready",
        "blocked",
        "locked",
        "future_stub",
        "unavailable",
        "cleared",
    }:
        return None
    if step_kind not in {"journey_leg", "gateway_cross", "no_step"}:
        return None
    if not result_id or not summary or not result_summary or not target_region_id or not target_region_label:
        return None
    normalized = {
        "result_id": result_id[:80],
        "result_type": result_type[:80],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "target_region_id": target_region_id[:120],
        "target_region_label": target_region_label[:160],
        "pursuit_id": pursuit_id[:80],
        "pursuit_status": pursuit_status[:40],
        "step_kind": step_kind[:40],
        "linked_journey_id": linked_journey_id[:80],
        "gateway_id": gateway_id[:120],
        "gateway_label": gateway_label[:160],
        "source": source[:40],
    }
    if resolved_at:
        normalized["resolved_at"] = resolved_at[:80]
    return normalized


def build_group_region_gateway(
    *,
    gateway_id: str,
    gateway_label: str,
    gateway_status: str,
    summary: str,
    source_node_id: str,
    source_node_label: str,
    route_id: str = "",
    target_region_id: str,
    target_region_label: str,
    reachable: bool = False,
    blocked: bool = False,
    locked: bool = False,
    blocked_reason: str = "",
    unlock_hint: str = "",
    future_stub: bool = False,
    source: str = "region_gateway",
) -> dict[str, Any] | None:
    return _normalize_group_region_gateway(
        {
            "gateway_id": gateway_id,
            "gateway_label": gateway_label,
            "gateway_status": gateway_status,
            "summary": summary,
            "source_node_id": source_node_id,
            "source_node_label": source_node_label,
            "route_id": route_id,
            "target_region_id": target_region_id,
            "target_region_label": target_region_label,
            "reachable": reachable,
            "blocked": blocked,
            "locked": locked,
            "blocked_reason": blocked_reason,
            "unlock_hint": unlock_hint,
            "future_stub": future_stub,
            "source": source,
        }
    )


def get_group_region_gateways(sess: Session, group_id: str) -> list[dict[str, Any]]:
    group_key = str(group_id or "").strip()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict):
        return []
    current_position = _normalize_map_position(group.get("current_map_position"))
    current_node_id = str((current_position or {}).get("node_id") or "").strip().lower()
    region_id = str((current_position or {}).get("map_level") or "region").strip().lower() or "region"
    revealed_node_ids = _get_group_revealed_node_ids(sess, group)
    node_state_map = _normalize_group_node_state_map(group.get("node_states"))
    visit_map = _normalize_group_node_visit_state_map(group.get("node_visit_states"))
    destination_event_map = _normalize_group_destination_event_state_map(group.get("destination_event_states"))
    group_state_flags = _collect_group_node_state_flags(group)
    gateways: list[dict[str, Any]] = []
    for definition in get_static_region_gateways(region_id=region_id, current_map_position=current_position):
        if not isinstance(definition, dict):
            continue
        source_node_id = str(definition.get("source_node_id") or "").strip().lower()
        if not source_node_id or source_node_id not in revealed_node_ids:
            continue
        if source_node_id != current_node_id and source_node_id not in visit_map:
            continue
        source_node = get_static_node(source_node_id) or {}
        source_node_label = str(source_node.get("label") or definition.get("source_node_label") or source_node_id).strip()
        route_id = str(definition.get("route_id") or "").strip().lower()
        route_plan = get_group_route_plan_to_node(sess, group_key, source_node_id) or {}
        plan_status = str(route_plan.get("plan_status") or "").strip().lower()
        effective_route_access = get_effective_group_route_access_state(sess, group_key, route_id=route_id) if route_id else {}
        blocked_reason = str((effective_route_access or {}).get("block_reason") or route_plan.get("blocked_reason") or "").strip()
        node_state_flags = list((node_state_map.get(source_node_id) or {}).get("state_flags") or [])
        destination_event_state = destination_event_map.get(source_node_id)
        visit_count = max(0, as_int((visit_map.get(source_node_id) or {}).get("visit_count"), 0))
        requirements: dict[str, Any] = {}
        for key in (
            "requires_node_state_flag",
            "requires_destination_event_id",
            "requires_destination_event_result_type",
            "requires_any_group_node_state_flags",
            "requires_all_group_node_state_flags",
            "requires_any_region_link_ids",
            "requires_all_region_link_ids",
            "requires_min_visit_count",
        ):
            value = definition.get(key)
            if value is None or value == "":
                continue
            requirements[key] = value
        for key in ("requires_min_region_link_count", "region_link_id_pool"):
            value = definition.get(key)
            if value is None or value == "" or value == []:
                continue
            requirements[key] = value
        requirement_eval = _evaluate_local_requirement_set(
            requirements=requirements,
            state_flags=node_state_flags,
            group_state_flags=group_state_flags,
            region_link_ids=sorted(_collect_group_region_link_ids(group)),
            destination_event_state=destination_event_state,
            visit_count=visit_count,
        )
        future_stub = bool(definition.get("future_stub"))
        reachable = plan_status in {"current_location", "reachable"}
        blocked = bool(
            route_id
            and str((effective_route_access or {}).get("access_state") or "").strip().lower() == "blocked"
        ) or plan_status == "blocked"
        locked = bool(requirement_eval.get("locked"))
        gateway_status = "open"
        if future_stub:
            gateway_status = "future_stub"
        elif blocked:
            gateway_status = "blocked"
        elif locked:
            gateway_status = "locked"
        elif not reachable:
            gateway_status = "unavailable"
        summary = (
            f"{source_node_label} выводит к региону {str(definition.get('target_region_label') or definition.get('target_region_id') or '').strip()}."
        )
        if gateway_status == "blocked":
            summary = (
                f"Выход через {source_node_label} известен, но сейчас упирается в блок на маршруте."
            )
        elif gateway_status == "locked":
            summary = (
                f"Выход через {source_node_label} уже известен, но ещё требует локальной подготовки."
            )
        elif gateway_status == "future_stub":
            summary = (
                f"У {source_node_label} отмечен будущий выход в соседний регион, но он пока остаётся только заготовкой."
            )
        elif gateway_status == "unavailable":
            continue
        gateway = build_group_region_gateway(
            gateway_id=str(definition.get("gateway_id") or ""),
            gateway_label=str(definition.get("label") or definition.get("gateway_id") or ""),
            gateway_status=gateway_status,
            summary=summary,
            source_node_id=source_node_id,
            source_node_label=source_node_label,
            route_id=route_id,
            target_region_id=str(definition.get("target_region_id") or ""),
            target_region_label=str(definition.get("target_region_label") or definition.get("target_region_id") or ""),
            reachable=reachable,
            blocked=blocked,
            locked=locked,
            blocked_reason=blocked_reason,
            unlock_hint=str(definition.get("unlock_hint") or ""),
            future_stub=future_stub,
            source="region_gateway",
        )
        if gateway:
            gateways.append(gateway)
    status_order = {"open": 0, "blocked": 1, "locked": 2, "future_stub": 3, "unavailable": 4}
    gateways.sort(
        key=lambda item: (
            status_order.get(str(item.get("gateway_status") or ""), 99),
            str(item.get("source_node_label") or ""),
            str(item.get("gateway_label") or ""),
        )
    )
    return gateways


def get_group_primary_region_gateway(sess: Session, group_id: str) -> dict[str, Any] | None:
    gateways = get_group_region_gateways(sess, group_id)
    return dict(gateways[0]) if gateways else None


def get_current_group_region_gateways(
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
    return get_group_region_gateways(sess, resolved_group_id)


def get_current_group_primary_region_gateway(
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
    return get_group_primary_region_gateway(sess, resolved_group_id)


def _build_group_region_target_gateway_candidate(
    sess: Session,
    *,
    group_key: str,
    group: dict[str, Any],
    definition: dict[str, Any],
    current_position: dict[str, Any] | None,
) -> dict[str, Any] | None:
    source_node_id = str(definition.get("source_node_id") or "").strip().lower()
    if not source_node_id:
        return None
    source_node = get_static_node(source_node_id) or {}
    source_node_label = str(source_node.get("label") or definition.get("source_node_label") or source_node_id).strip()
    route_id = str(definition.get("route_id") or "").strip().lower()
    route_plan = get_group_route_plan_to_node(sess, group_key, source_node_id) or {}
    plan_status = str(route_plan.get("plan_status") or "").strip().lower()
    effective_route_access = get_effective_group_route_access_state(sess, group_key, route_id=route_id) if route_id else {}
    blocked_reason = str((effective_route_access or {}).get("block_reason") or route_plan.get("blocked_reason") or "").strip()
    node_state_map = _normalize_group_node_state_map(group.get("node_states"))
    visit_map = _normalize_group_node_visit_state_map(group.get("node_visit_states"))
    destination_event_map = _normalize_group_destination_event_state_map(group.get("destination_event_states"))
    group_state_flags = _collect_group_node_state_flags(group)
    node_state_flags = list((node_state_map.get(source_node_id) or {}).get("state_flags") or [])
    destination_event_state = destination_event_map.get(source_node_id)
    visit_count = max(0, as_int((visit_map.get(source_node_id) or {}).get("visit_count"), 0))
    requirements: dict[str, Any] = {}
    for key in (
        "requires_node_state_flag",
        "requires_destination_event_id",
        "requires_destination_event_result_type",
        "requires_any_group_node_state_flags",
        "requires_all_group_node_state_flags",
        "requires_any_region_link_ids",
        "requires_all_region_link_ids",
        "requires_min_visit_count",
    ):
        value = definition.get(key)
        if value is None or value == "":
            continue
        requirements[key] = value
    for key in ("requires_min_region_link_count", "region_link_id_pool"):
        value = definition.get(key)
        if value is None or value == "" or value == []:
            continue
        requirements[key] = value
    requirement_eval = _evaluate_local_requirement_set(
        requirements=requirements,
        state_flags=node_state_flags,
        group_state_flags=group_state_flags,
        region_link_ids=sorted(_collect_group_region_link_ids(group)),
        destination_event_state=destination_event_state,
        visit_count=visit_count,
    )
    future_stub = bool(definition.get("future_stub"))
    reachable = plan_status in {"current_location", "reachable"}
    blocked = bool(
        route_id
        and str((effective_route_access or {}).get("access_state") or "").strip().lower() == "blocked"
    ) or plan_status == "blocked"
    locked = bool(requirement_eval.get("locked"))
    gateway_status = "open"
    if future_stub:
        gateway_status = "future_stub"
    elif blocked:
        gateway_status = "blocked"
    elif locked:
        gateway_status = "locked"
    elif not reachable:
        gateway_status = "unavailable"
    summary = f"{source_node_label} выводит к региону {str(definition.get('target_region_label') or definition.get('target_region_id') or '').strip()}."
    if gateway_status == "blocked":
        summary = f"Выход через {source_node_label} известен, но сейчас упирается в блок на маршруте."
    elif gateway_status == "locked":
        summary = f"Выход через {source_node_label} уже известен, но ещё требует локальной подготовки."
    elif gateway_status == "future_stub":
        summary = f"У {source_node_label} отмечен будущий выход в соседний регион, но он пока остаётся только заготовкой."
    return build_group_region_gateway(
        gateway_id=str(definition.get("gateway_id") or ""),
        gateway_label=str(definition.get("label") or definition.get("gateway_id") or ""),
        gateway_status=gateway_status,
        summary=summary,
        source_node_id=source_node_id,
        source_node_label=source_node_label,
        route_id=route_id,
        target_region_id=str(definition.get("target_region_id") or ""),
        target_region_label=str(definition.get("target_region_label") or definition.get("target_region_id") or ""),
        reachable=reachable,
        blocked=blocked,
        locked=locked,
        blocked_reason=blocked_reason,
        unlock_hint=str(definition.get("unlock_hint") or ""),
        future_stub=future_stub,
        source="region_target_guidance",
    )


def build_group_region_target_plan(
    sess: Session,
    group_id: str,
    target_region_id: str,
) -> dict[str, Any] | None:
    group_key = str(group_id or "").strip()
    normalized_target_region_id = str(target_region_id or "").strip().lower()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict) or not normalized_target_region_id:
        return None
    current_position = _normalize_map_position(group.get("current_map_position"))
    current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    if not current_region_state and current_position:
        region_identity = get_static_region_identity(current_map_position=current_position)
        if region_identity:
            current_region_state = _normalize_group_current_region_state(
                {
                    "region_id": str(region_identity.get("region_id") or ""),
                    "region_label": str(region_identity.get("region_label") or ""),
                    "current_node_id": str(current_position.get("node_id") or ""),
                    "visit_count": max(
                        1,
                        as_int(
                            (_normalize_group_discovered_region_map(group.get("discovered_regions")).get(
                                str(region_identity.get("region_id") or "").strip().lower()
                            ) or {}).get("visit_count"),
                            0,
                        ),
                    ),
                    "source": "region_target_guidance",
                }
            )
    if not current_region_state:
        return None
    current_region_id = str(current_region_state.get("region_id") or "").strip().lower()
    current_region_label = str(current_region_state.get("region_label") or current_region_id).strip()
    discovered_map = _normalize_group_discovered_region_map(group.get("discovered_regions"))
    discovered_target = discovered_map.get(normalized_target_region_id)
    target_label = str(
        (discovered_target or {}).get("region_label")
        or normalized_target_region_id
    ).strip()
    authored_gateway_definitions = [
        item
        for item in get_static_region_gateways(current_map_position=current_position)
        if str(item.get("target_region_id") or "").strip().lower() == normalized_target_region_id
    ]
    gateways = [
        item
        for item in get_group_region_gateways(sess, group_key)
        if str(item.get("target_region_id") or "").strip().lower() == normalized_target_region_id
    ]
    synthesized_gateways: list[dict[str, Any]] = []
    if authored_gateway_definitions:
        synthesized_gateways = [
            candidate
            for definition in authored_gateway_definitions
            if (candidate := _build_group_region_target_gateway_candidate(
                sess,
                group_key=group_key,
                group=group,
                definition=definition,
                current_position=current_position,
            ))
        ]
    status_order = {"open": 0, "blocked": 1, "locked": 2, "future_stub": 3, "unavailable": 4}
    gateways.sort(
        key=lambda item: (
            status_order.get(str(item.get("gateway_status") or ""), 99),
            str(item.get("gateway_label") or ""),
        )
    )
    synthesized_gateways.sort(
        key=lambda item: (
            status_order.get(str(item.get("gateway_status") or ""), 99),
            str(item.get("gateway_label") or ""),
        )
    )
    preferred_exported_gateway = gateways[0] if gateways else None
    preferred_synthesized_gateway = synthesized_gateways[0] if synthesized_gateways else None
    gateway = preferred_exported_gateway
    if preferred_synthesized_gateway and (
        not preferred_exported_gateway
        or status_order.get(str(preferred_synthesized_gateway.get("gateway_status") or ""), 99)
        < status_order.get(str(preferred_exported_gateway.get("gateway_status") or ""), 99)
    ):
        gateway = preferred_synthesized_gateway
    if preferred_synthesized_gateway and str(preferred_synthesized_gateway.get("gateway_status") or "").strip().lower() == "open":
        gateway = preferred_synthesized_gateway
    if not target_label and authored_gateway_definitions:
        target_label = str(
            authored_gateway_definitions[0].get("target_region_label")
            or normalized_target_region_id
        ).strip()
    target_label = target_label or normalized_target_region_id
    current_node_id = str((current_position or {}).get("node_id") or "").strip().lower()
    if normalized_target_region_id == current_region_id:
        return _normalize_group_region_target_plan(
            {
                "target_region_id": normalized_target_region_id,
                "target_region_label": target_label or current_region_label,
                "plan_status": "current_region",
                "summary": f"Группа уже находится в регионе {current_region_label}.",
                "current_region_id": current_region_id,
                "current_region_label": current_region_label,
                "path_node_ids": [current_node_id] if current_node_id else [],
                "path_route_ids": [],
                "path_step_count": 0,
                "reachable": True,
                "blocked_reason": "",
                "suggested_command": "",
                "source": "region_target_guidance",
            }
        )
    if not gateway:
        if not authored_gateway_definitions and not discovered_target:
            return _normalize_group_region_target_plan(
                {
                    "target_region_id": normalized_target_region_id,
                    "target_region_label": target_label,
                    "plan_status": "target_region_undiscovered",
                    "summary": f"Регион {target_label} ещё не открыт, и для него пока нет известного выхода из текущего региона.",
                    "current_region_id": current_region_id,
                    "current_region_label": current_region_label,
                    "path_node_ids": [],
                    "path_route_ids": [],
                    "path_step_count": 0,
                    "reachable": False,
                    "blocked_reason": "",
                    "suggested_command": "",
                    "source": "region_target_guidance",
                }
            )
        return _normalize_group_region_target_plan(
            {
                "target_region_id": normalized_target_region_id,
                "target_region_label": target_label,
                "plan_status": "target_region_unavailable",
                "summary": f"Сейчас нельзя собрать внятный gateway-план до региона {target_label} из {current_region_label}.",
                "current_region_id": current_region_id,
                "current_region_label": current_region_label,
                "path_node_ids": [],
                "path_route_ids": [],
                "path_step_count": 0,
                "reachable": False,
                "blocked_reason": "",
                "suggested_command": "",
                "source": "region_target_guidance",
            }
        )
    gateway_status = str(gateway.get("gateway_status") or "").strip().lower()
    gateway_source_node_id = str(gateway.get("source_node_id") or "").strip().lower()
    gateway_source_node_label = str(gateway.get("source_node_label") or gateway_source_node_id).strip()
    base_plan: dict[str, Any] = {
        "target_region_id": normalized_target_region_id,
        "target_region_label": str(gateway.get("target_region_label") or target_label).strip() or target_label,
        "current_region_id": current_region_id,
        "current_region_label": current_region_label,
        "gateway_id": str(gateway.get("gateway_id") or ""),
        "gateway_label": str(gateway.get("gateway_label") or ""),
        "gateway_status": gateway_status,
        "gateway_source_node_id": gateway_source_node_id,
        "gateway_source_node_label": gateway_source_node_label,
        "path_node_ids": [],
        "path_route_ids": [],
        "path_step_count": 0,
        "reachable": False,
        "blocked_reason": str(gateway.get("blocked_reason") or ""),
        "suggested_command": "",
        "source": "region_target_guidance",
    }
    if gateway_status == "blocked":
        base_plan.update(
            {
                "plan_status": "gateway_blocked",
                "summary": f"Выход {base_plan['gateway_label']} к региону {base_plan['target_region_label']} известен, но сейчас заблокирован.",
                "suggested_command": f"group path {gateway_source_node_id}" if gateway_source_node_id else "",
            }
        )
        return _normalize_group_region_target_plan(base_plan)
    if gateway_status == "locked":
        base_plan.update(
            {
                "plan_status": "gateway_locked",
                "summary": f"Выход {base_plan['gateway_label']} к региону {base_plan['target_region_label']} уже найден, но ещё закрыт локальными требованиями.",
                "blocked_reason": str(gateway.get("unlock_hint") or gateway.get("blocked_reason") or ""),
                "suggested_command": f"group path {gateway_source_node_id}" if gateway_source_node_id else "",
            }
        )
        return _normalize_group_region_target_plan(base_plan)
    if gateway_status == "future_stub":
        base_plan.update(
            {
                "plan_status": "gateway_future_stub",
                "summary": f"Выход {base_plan['gateway_label']} к региону {base_plan['target_region_label']} отмечен как будущая заготовка.",
                "suggested_command": "",
            }
        )
        return _normalize_group_region_target_plan(base_plan)
    if gateway_status != "open":
        base_plan.update(
            {
                "plan_status": "target_region_unavailable",
                "summary": f"Сейчас нет пригодного gateway-подхода к региону {base_plan['target_region_label']}.",
            }
        )
        return _normalize_group_region_target_plan(base_plan)
    if gateway_source_node_id and gateway_source_node_id == current_node_id:
        base_plan.update(
            {
                "plan_status": "gateway_ready",
                "summary": f"Группа уже стоит у выхода {base_plan['gateway_label']} и может перейти в регион {base_plan['target_region_label']}.",
                "path_node_ids": [current_node_id],
                "reachable": True,
                "suggested_command": f"group exit {base_plan['gateway_id']}" if base_plan["gateway_id"] else "",
            }
        )
        return _normalize_group_region_target_plan(base_plan)
    route_plan = get_group_route_plan_to_node(sess, group_key, gateway_source_node_id) or {}
    if bool(route_plan.get("reachable")):
        base_plan.update(
            {
                "plan_status": "approach_gateway",
                "summary": f"Чтобы выйти в регион {base_plan['target_region_label']}, группе нужно сначала дойти до {gateway_source_node_label}.",
                "path_node_ids": list(route_plan.get("path_node_ids") or []),
                "path_route_ids": list(route_plan.get("path_route_ids") or []),
                "path_step_count": max(0, as_int(route_plan.get("step_count"), 0)),
                "reachable": True,
                "blocked_reason": str(route_plan.get("blocked_reason") or ""),
                "suggested_command": f"group go {gateway_source_node_id}",
            }
        )
        return _normalize_group_region_target_plan(base_plan)
    base_plan.update(
        {
            "plan_status": "target_region_unavailable",
            "summary": f"Выход {base_plan['gateway_label']} известен, но сейчас не удаётся построить подход к {gateway_source_node_label}.",
            "path_node_ids": list(route_plan.get("path_node_ids") or []),
            "path_route_ids": list(route_plan.get("path_route_ids") or []),
            "path_step_count": max(0, as_int(route_plan.get("step_count"), 0)),
            "blocked_reason": str(route_plan.get("blocked_reason") or ""),
            "suggested_command": f"group path {gateway_source_node_id}" if gateway_source_node_id else "",
        }
    )
    return _normalize_group_region_target_plan(base_plan)


def get_group_region_target_plan(
    sess: Session,
    group_id: str,
    target_region_id: str,
) -> dict[str, Any] | None:
    return build_group_region_target_plan(sess, group_id, target_region_id)


def get_current_group_region_target_plan(
    sess: Session,
    *,
    target_region_id: str,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None
    return get_group_region_target_plan(sess, resolved_group_id, target_region_id)


def get_current_group_primary_region_focus_plan(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    focus = get_current_group_primary_region_focus(sess, player_id=player_id, group_id=group_id)
    if not focus:
        return None
    return get_current_group_region_target_plan(
        sess,
        target_region_id=str(focus.get("region_id") or ""),
        player_id=player_id,
        group_id=group_id,
    )


def get_current_group_region_target_options(
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
    current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    if not current_region_state:
        return None
    discovered_regions = get_current_group_discovered_regions(
        sess,
        player_id=resolved_player_id or None,
        group_id=resolved_group_id,
    )
    target_region_plans = [
        plan
        for item in discovered_regions
        if (plan := get_group_region_target_plan(sess, resolved_group_id, str(item.get("region_id") or "")))
    ]
    focus_plan = get_current_group_primary_region_focus_plan(
        sess,
        player_id=resolved_player_id or None,
        group_id=resolved_group_id,
    )
    focus_region_id = str((focus_plan or {}).get("target_region_id") or "").strip().lower()
    if focus_region_id:
        target_region_plans.sort(
            key=lambda item: (
                0 if str(item.get("target_region_id") or "").strip().lower() == focus_region_id else 1,
                str(item.get("target_region_label") or ""),
            )
        )
    current_region_label = str(current_region_state.get("region_label") or "")
    return _normalize_group_region_target_options(
        {
            "current_region_id": str(current_region_state.get("region_id") or ""),
            "current_region_label": current_region_label,
            "primary_region_focus_plan": focus_plan,
            "target_region_plans": target_region_plans,
            "summary": (
                f"Из региона {current_region_label} собрано {len(target_region_plans)} canonical target-region plan(s)."
            ),
        }
    )


def _build_group_known_region_path_from_links(
    *,
    current_region_id: str,
    target_region_id: str,
    discovered_region_ids: set[str],
    region_links: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    start = str(current_region_id or "").strip().lower()
    target = str(target_region_id or "").strip().lower()
    if not start or not target or start == target:
        return ([start] if start else []), []
    adjacency: dict[str, list[tuple[str, str]]] = {}
    for link in region_links:
        region_a_id = str(link.get("region_a_id") or "").strip().lower()
        region_b_id = str(link.get("region_b_id") or "").strip().lower()
        link_id = str(link.get("link_id") or "").strip().lower()
        if not region_a_id or not region_b_id or not link_id:
            continue
        if region_a_id not in discovered_region_ids or region_b_id not in discovered_region_ids:
            continue
        adjacency.setdefault(region_a_id, []).append((region_b_id, link_id))
        adjacency.setdefault(region_b_id, []).append((region_a_id, link_id))
    if start not in adjacency:
        return [], []
    queue: deque[tuple[str, list[str], list[str]]] = deque([(start, [start], [])])
    visited = {start}
    while queue:
        node_id, region_path, link_path = queue.popleft()
        if node_id == target:
            return region_path, link_path
        neighbors = sorted(adjacency.get(node_id, []), key=lambda item: (item[0], item[1]))
        for next_region_id, link_id in neighbors:
            if next_region_id in visited:
                continue
            visited.add(next_region_id)
            queue.append((next_region_id, [*region_path, next_region_id], [*link_path, link_id]))
    return [], []


def build_group_known_region_route(
    sess: Session,
    group_id: str,
    target_region_id: str,
) -> dict[str, Any] | None:
    group_key = str(group_id or "").strip()
    normalized_target_region_id = str(target_region_id or "").strip().lower()
    group = _get_group_states(sess).get(group_key)
    if not isinstance(group, dict) or not normalized_target_region_id:
        return None
    current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    if not current_region_state:
        return None
    current_region_id = str(current_region_state.get("region_id") or "").strip().lower()
    current_region_label = str(current_region_state.get("region_label") or current_region_id).strip()
    discovered_regions = get_current_group_discovered_regions(sess, group_id=group_key)
    discovered_map = {str(item.get("region_id") or "").strip().lower(): item for item in discovered_regions}
    target_region = discovered_map.get(normalized_target_region_id)
    target_region_label = str((target_region or {}).get("region_label") or normalized_target_region_id).strip()
    if normalized_target_region_id == current_region_id:
        return _normalize_group_known_region_route(
            {
                "target_region_id": normalized_target_region_id,
                "target_region_label": target_region_label or current_region_label,
                "route_status": "current_region",
                "summary": f"Группа уже находится в регионе {current_region_label}.",
                "current_region_id": current_region_id,
                "current_region_label": current_region_label,
                "region_path_ids": [current_region_id],
                "region_path_labels": [current_region_label],
                "link_ids": [],
                "hop_count": 0,
                "next_gateway_id": "",
                "next_gateway_label": "",
                "next_gateway_status": "",
                "next_gateway_source_node_id": "",
                "next_gateway_source_node_label": "",
                "suggested_command": "",
                "source": "known_region_route",
            }
        )
    if not target_region:
        return _normalize_group_known_region_route(
            {
                "target_region_id": normalized_target_region_id,
                "target_region_label": target_region_label,
                "route_status": "target_region_undiscovered",
                "summary": f"Регион {target_region_label} ещё не входит в discovered regions группы, поэтому known-region path недоступен.",
                "current_region_id": current_region_id,
                "current_region_label": current_region_label,
                "region_path_ids": [],
                "region_path_labels": [],
                "link_ids": [],
                "hop_count": 0,
                "next_gateway_id": "",
                "next_gateway_label": "",
                "next_gateway_status": "",
                "next_gateway_source_node_id": "",
                "next_gateway_source_node_label": "",
                "suggested_command": "",
                "source": "known_region_route",
            }
        )
    region_links = get_current_group_region_link_states(sess, group_id=group_key)
    region_path_ids, link_ids = _build_group_known_region_path_from_links(
        current_region_id=current_region_id,
        target_region_id=normalized_target_region_id,
        discovered_region_ids=set(discovered_map.keys()),
        region_links=region_links,
    )
    if not region_path_ids or region_path_ids[-1] != normalized_target_region_id:
        return _normalize_group_known_region_route(
            {
                "target_region_id": normalized_target_region_id,
                "target_region_label": target_region_label,
                "route_status": "no_known_route",
                "summary": f"Регион {target_region_label} открыт, но пока не связан с {current_region_label} известной traversed region-link цепочкой.",
                "current_region_id": current_region_id,
                "current_region_label": current_region_label,
                "region_path_ids": [],
                "region_path_labels": [],
                "link_ids": [],
                "hop_count": 0,
                "next_gateway_id": "",
                "next_gateway_label": "",
                "next_gateway_status": "",
                "next_gateway_source_node_id": "",
                "next_gateway_source_node_label": "",
                "suggested_command": "",
                "source": "known_region_route",
            }
        )
    next_region_id = str(region_path_ids[1] if len(region_path_ids) > 1 else "").strip().lower()
    next_region_label = str((discovered_map.get(next_region_id) or {}).get("region_label") or next_region_id).strip()
    next_hop_plan = get_group_region_target_plan(sess, group_key, next_region_id) if next_region_id else None
    next_hop_status = str((next_hop_plan or {}).get("plan_status") or "").strip().lower()
    route_status = "multi_region_route" if len(region_path_ids) > 2 else "direct_route"
    summary = (
        f"Из {current_region_label} к региону {target_region_label} известен маршрут через {max(1, len(region_path_ids) - 1)} region hop(s)."
    )
    if next_hop_status == "gateway_blocked":
        route_status = "blocked_next_gateway"
        summary = f"Известный путь к {target_region_label} найден, но следующий gateway к региону {next_region_label} сейчас заблокирован."
    elif next_hop_status == "gateway_locked":
        route_status = "locked_next_gateway"
        summary = f"Известный путь к {target_region_label} найден, но следующий gateway к региону {next_region_label} ещё закрыт условиями."
    elif next_hop_status == "gateway_future_stub":
        route_status = "future_stub_next_gateway"
        summary = f"Известный путь к {target_region_label} найден, но следующий gateway к региону {next_region_label} пока остаётся future stub."
    region_path_labels = [
        str((discovered_map.get(region_id) or {}).get("region_label") or region_id).strip()
        for region_id in region_path_ids
    ]
    return _normalize_group_known_region_route(
        {
            "target_region_id": normalized_target_region_id,
            "target_region_label": target_region_label,
            "route_status": route_status,
            "summary": summary,
            "current_region_id": current_region_id,
            "current_region_label": current_region_label,
            "region_path_ids": region_path_ids,
            "region_path_labels": region_path_labels,
            "link_ids": link_ids,
            "hop_count": max(0, len(region_path_ids) - 1),
            "next_gateway_id": str((next_hop_plan or {}).get("gateway_id") or ""),
            "next_gateway_label": str((next_hop_plan or {}).get("gateway_label") or ""),
            "next_gateway_status": str((next_hop_plan or {}).get("gateway_status") or ""),
            "next_gateway_source_node_id": str((next_hop_plan or {}).get("gateway_source_node_id") or ""),
            "next_gateway_source_node_label": str((next_hop_plan or {}).get("gateway_source_node_label") or ""),
            "suggested_command": str((next_hop_plan or {}).get("suggested_command") or ""),
            "source": "known_region_route",
        }
    )


def get_group_known_region_route(
    sess: Session,
    group_id: str,
    target_region_id: str,
) -> dict[str, Any] | None:
    return build_group_known_region_route(sess, group_id, target_region_id)


def get_current_group_known_region_route(
    sess: Session,
    *,
    target_region_id: str,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None
    return get_group_known_region_route(sess, resolved_group_id, target_region_id)


def get_current_group_primary_region_route(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    focus = get_current_group_primary_region_focus(sess, player_id=player_id, group_id=group_id)
    if not focus:
        return None
    return get_current_group_known_region_route(
        sess,
        target_region_id=str(focus.get("region_id") or ""),
        player_id=player_id,
        group_id=group_id,
    )


def get_current_group_known_region_route_options(
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
    current_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    if not current_region_state:
        return None
    discovered_regions = get_current_group_discovered_regions(
        sess,
        player_id=resolved_player_id or None,
        group_id=resolved_group_id,
    )
    target_region_routes = [
        route
        for item in discovered_regions
        if (route := get_group_known_region_route(sess, resolved_group_id, str(item.get("region_id") or "")))
    ]
    primary_region_route = get_current_group_primary_region_route(
        sess,
        player_id=resolved_player_id or None,
        group_id=resolved_group_id,
    )
    focus_region_id = str((primary_region_route or {}).get("target_region_id") or "").strip().lower()
    if focus_region_id:
        target_region_routes.sort(
            key=lambda item: (
                0 if str(item.get("target_region_id") or "").strip().lower() == focus_region_id else 1,
                str(item.get("target_region_label") or ""),
            )
        )
    current_region_label = str(current_region_state.get("region_label") or "")
    return _normalize_group_known_region_route_options(
        {
            "current_region_id": str(current_region_state.get("region_id") or ""),
            "current_region_label": current_region_label,
            "primary_region_route": primary_region_route,
            "target_region_routes": target_region_routes,
            "summary": f"Из региона {current_region_label} собрано {len(target_region_routes)} known-region route(s).",
        }
    )


def build_group_multi_region_pursuit_result(
    *,
    result_type: str,
    summary: str,
    result_summary: str,
    target_region_id: str,
    target_region_label: str,
    guidance_status: str,
    gateway_id: str = "",
    gateway_label: str = "",
    linked_journey_id: str = "",
    pursuit_scope: str = "known_multi_region",
    target_region_path_ids: list[str] | None = None,
    target_region_path_labels: list[str] | None = None,
    current_hop_region_id: str = "",
    next_hop_region_id: str = "",
    known_route_status: str = "",
    source: str = "region_pursuit",
) -> dict[str, Any] | None:
    return build_group_region_pursuit_result(
        result_type=result_type,
        summary=summary,
        result_summary=result_summary,
        target_region_id=target_region_id,
        target_region_label=target_region_label,
        guidance_status=guidance_status,
        gateway_id=gateway_id,
        gateway_label=gateway_label,
        linked_journey_id=linked_journey_id,
        pursuit_scope=pursuit_scope,
        target_region_path_ids=target_region_path_ids,
        target_region_path_labels=target_region_path_labels,
        current_hop_region_id=current_hop_region_id,
        next_hop_region_id=next_hop_region_id,
        known_route_status=known_route_status,
        source=source,
    )


def _build_group_pursuit_from_known_route(
    sess: Session,
    *,
    group_key: str,
    route: dict[str, Any],
    player_id: uuid.UUID | str | None = None,
    source: str = "region_pursuit",
    existing_pursuit: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    normalized_route = _normalize_group_known_region_route(route)
    if not normalized_route:
        return None, None, "Не удалось нормализовать known-region route."
    route_status = str(normalized_route.get("route_status") or "").strip().lower()
    target_region_id = str(normalized_route.get("target_region_id") or "")
    target_region_label = str(normalized_route.get("target_region_label") or target_region_id)
    region_path_ids = list(normalized_route.get("region_path_ids") or [])
    region_path_labels = list(normalized_route.get("region_path_labels") or [])
    current_hop_region_id = str(region_path_ids[0] if region_path_ids else normalized_route.get("current_region_id") or "").strip().lower()
    next_hop_region_id = str(region_path_ids[1] if len(region_path_ids) > 1 else "").strip().lower()
    next_hop_label = str(region_path_labels[1] if len(region_path_labels) > 1 else next_hop_region_id).strip()
    next_hop_plan = get_group_region_target_plan(sess, group_key, next_hop_region_id) if next_hop_region_id else None
    if route_status in {
        "direct_route",
        "multi_region_route",
        "blocked_next_gateway",
        "locked_next_gateway",
        "future_stub_next_gateway",
    } and next_hop_region_id and not next_hop_plan:
        return None, None, "Не удалось собрать direct target-region guidance для следующего region hop."
    existing_scope = str((existing_pursuit or {}).get("pursuit_scope") or "").strip().lower()
    if existing_scope == "known_multi_region":
        pursuit_scope = "known_multi_region"
    else:
        pursuit_scope = "known_multi_region" if route_status == "multi_region_route" else "direct_region"
    linked_journey_id = ""
    result_type = "region_pursuit_multihop_updated" if existing_pursuit else "region_pursuit_multihop_set"
    pursuit_status = "unavailable"
    summary = str(normalized_route.get("summary") or "").strip() or f"Region pursuit к {target_region_label} обновлён."
    result_summary = summary
    gateway_id = str((next_hop_plan or {}).get("gateway_id") or "")
    gateway_label = str((next_hop_plan or {}).get("gateway_label") or "")
    guidance_status = str((next_hop_plan or {}).get("plan_status") or "")
    group = _get_group_states(sess).get(group_key) or {}
    active_journey = _normalize_group_active_journey((group or {}).get("active_journey"))

    if route_status in {
        "direct_route",
        "multi_region_route",
        "blocked_next_gateway",
        "locked_next_gateway",
        "future_stub_next_gateway",
    }:
        if guidance_status == "approach_gateway":
            gateway_source_node_id = str((next_hop_plan or {}).get("gateway_source_node_id") or "").strip().lower()
            if (
                active_journey
                and gateway_source_node_id
                and str(active_journey.get("target_node_id") or "").strip().lower() == gateway_source_node_id
            ):
                linked_journey_id = str(active_journey.get("journey_id") or "")
            else:
                updated_group, error = set_group_journey_target(
                    sess,
                    group_key,
                    str((next_hop_plan or {}).get("gateway_source_node_id") or ""),
                    player_id=player_id,
                    source=source,
                )
                if error:
                    return updated_group, None, error
                groups = _get_group_states(sess)
                group = groups.get(group_key) or updated_group or {}
                active_journey = _normalize_group_active_journey((group or {}).get("active_journey"))
                linked_journey_id = str((active_journey or {}).get("journey_id") or "")
            pursuit_status = "pursuing_gateway"
            result_type = "region_pursuit_multihop_updated" if pursuit_scope == "known_multi_region" and existing_pursuit else (
                "region_pursuit_multihop_set" if pursuit_scope == "known_multi_region" else ("region_pursuit_updated" if existing_pursuit else "region_pursuit_set")
            )
            summary = (
                f"Группа начинает long-range pursuit региона {target_region_label} через следующий hop к региону {next_hop_label}."
                if pursuit_scope == "known_multi_region"
                else f"Группа начинает pursuit региона {target_region_label} через подход к {str((next_hop_plan or {}).get('gateway_source_node_label') or 'gateway source')}."
            )
            result_summary = str(normalized_route.get("summary") or (next_hop_plan or {}).get("summary") or summary)
        elif guidance_status == "gateway_ready":
            active_group = (_get_group_states(sess).get(group_key) or {})
            active_journey = _normalize_group_active_journey(active_group.get("active_journey"))
            if active_journey and str(active_journey.get("target_node_id") or "").strip().lower() == str((next_hop_plan or {}).get("gateway_source_node_id") or "").strip().lower():
                clear_group_journey(sess, group_key, source=source)
            pursuit_status = "gateway_ready"
            result_type = "region_pursuit_gateway_ready" if pursuit_scope == "direct_region" else "region_pursuit_multihop_updated"
            summary = (
                f"Группа уже готова пройти следующий gateway к региону {next_hop_label} на пути к {target_region_label}."
                if pursuit_scope == "known_multi_region"
                else f"Группа уже готова пересечь {gateway_label or 'gateway'} и войти в регион {target_region_label}."
            )
            result_summary = summary
        elif guidance_status == "gateway_blocked":
            pursuit_status = "blocked"
            result_type = "region_pursuit_multihop_blocked" if pursuit_scope == "known_multi_region" else "region_pursuit_blocked"
        elif guidance_status == "gateway_locked":
            pursuit_status = "locked"
            result_type = "region_pursuit_multihop_blocked" if pursuit_scope == "known_multi_region" else "region_pursuit_locked"
        elif guidance_status == "gateway_future_stub":
            pursuit_status = "future_stub"
            result_type = "region_pursuit_multihop_blocked" if pursuit_scope == "known_multi_region" else "region_pursuit_future_stub"
        else:
            pursuit_status = "unavailable"
            result_type = "region_pursuit_multihop_unavailable" if pursuit_scope == "known_multi_region" else "region_pursuit_unavailable"
    else:
        pursuit_status = "unavailable"
        result_type = "region_pursuit_multihop_unavailable" if pursuit_scope == "known_multi_region" else "region_pursuit_unavailable"

    pursuit = _build_group_active_region_pursuit(
        target_region_plan=next_hop_plan or {
            "target_region_id": next_hop_region_id or target_region_id,
            "target_region_label": next_hop_label or target_region_label,
            "plan_status": guidance_status or "target_region_unavailable",
            "summary": summary,
            "current_region_id": str(normalized_route.get("current_region_id") or ""),
            "current_region_label": str(normalized_route.get("current_region_label") or ""),
        },
        pursuit_status=pursuit_status,
        linked_journey_id=linked_journey_id,
        pursuit_scope=pursuit_scope,
        target_region_id=target_region_id,
        target_region_label=target_region_label,
        target_region_path_ids=region_path_ids,
        target_region_path_labels=region_path_labels,
        current_hop_region_id=current_hop_region_id,
        next_hop_region_id=next_hop_region_id,
        known_route_status=route_status,
        source=source,
        pursuit_id=str((existing_pursuit or {}).get("pursuit_id") or ""),
        created_at=str((existing_pursuit or {}).get("created_at") or ""),
    )
    if not pursuit:
        return None, None, "Не удалось создать canonical multi-region pursuit."
    result = build_group_multi_region_pursuit_result(
        result_type=result_type,
        summary=summary,
        result_summary=result_summary,
        target_region_id=target_region_id,
        target_region_label=target_region_label,
        guidance_status=guidance_status or route_status,
        gateway_id=gateway_id,
        gateway_label=gateway_label,
        linked_journey_id=linked_journey_id,
        pursuit_scope=pursuit_scope,
        target_region_path_ids=region_path_ids,
        target_region_path_labels=region_path_labels,
        current_hop_region_id=current_hop_region_id,
        next_hop_region_id=next_hop_region_id,
        known_route_status=route_status,
        source=source,
    )
    return pursuit, result, None


def set_group_multi_region_pursuit(
    sess: Session,
    group_id: str,
    target_region_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "region_pursuit",
) -> tuple[dict[str, Any] | None, str | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    normalized_target_region_id = str(target_region_id or "").strip().lower()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None, "Группа не найдена."
    if not normalized_target_region_id:
        return None, "Нужно указать target_region_id для multi-region pursuit."
    route = get_group_known_region_route(sess, group_key, normalized_target_region_id)
    if not route:
        return None, "Не удалось собрать canonical known-region route для multi-region pursuit."
    existing_pursuit = _normalize_group_active_region_pursuit(group.get("active_region_pursuit"))
    pursuit, result, error = _build_group_pursuit_from_known_route(
        sess,
        group_key=group_key,
        route=route,
        player_id=player_id,
        source=source,
        existing_pursuit=existing_pursuit,
    )
    if error:
        return None, error
    groups = _get_group_states(sess)
    group = groups.get(group_key) or group
    if not isinstance(group, dict) or not pursuit:
        return None, "Не удалось сохранить multi-region pursuit."
    group["active_region_pursuit"] = pursuit
    if result:
        group["last_region_pursuit_result"] = result
    groups[group_key] = group
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group), None


def sync_group_multi_region_pursuit(
    sess: Session,
    group_id: str,
    *,
    source: str = "region_pursuit",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None
    pursuit = _normalize_group_active_region_pursuit(group.get("active_region_pursuit"))
    if not pursuit or str(pursuit.get("pursuit_scope") or "").strip().lower() != "known_multi_region":
        return pursuit
    route = get_group_known_region_route(sess, group_key, str(pursuit.get("target_region_id") or ""))
    if not route:
        return pursuit
    route_status = str(route.get("route_status") or "").strip().lower()
    if route_status == "current_region":
        group.pop("active_region_pursuit", None)
        result = build_group_multi_region_pursuit_result(
            result_type="region_pursuit_cleared",
            summary=f"Группа достигла целевого региона {str(pursuit.get('target_region_label') or 'региона')}.",
            result_summary=f"Long-range pursuit к {str(pursuit.get('target_region_label') or 'региону')} завершён.",
            target_region_id=str(pursuit.get("target_region_id") or ""),
            target_region_label=str(pursuit.get("target_region_label") or ""),
            guidance_status="current_region",
            gateway_id=str(pursuit.get("gateway_id") or ""),
            gateway_label=str(pursuit.get("gateway_label") or ""),
            linked_journey_id=str(pursuit.get("linked_journey_id") or ""),
            pursuit_scope="known_multi_region",
            target_region_path_ids=list(route.get("region_path_ids") or []),
            target_region_path_labels=list(route.get("region_path_labels") or []),
            current_hop_region_id=str(route.get("current_region_id") or ""),
            next_hop_region_id="",
            known_route_status=route_status,
            source=source,
        )
        if result:
            group["last_region_pursuit_result"] = result
        groups[group_key] = group
        _persist_group_states(sess, groups)
        _sync_group_position_mirrors(sess, group)
        return None
    refreshed_pursuit, refreshed_result, error = _build_group_pursuit_from_known_route(
        sess,
        group_key=group_key,
        route=route,
        player_id=None,
        source=source,
        existing_pursuit=pursuit,
    )
    if error or not refreshed_pursuit:
        return pursuit
    group["active_region_pursuit"] = refreshed_pursuit
    if refreshed_result:
        group["last_region_pursuit_result"] = refreshed_result
    groups[group_key] = group
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return refreshed_pursuit


def get_current_group_multi_region_pursuit(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    pursuit = get_current_group_region_pursuit(sess, player_id=player_id, group_id=group_id)
    if pursuit and str(pursuit.get("pursuit_scope") or "").strip().lower() == "known_multi_region":
        return pursuit
    return None


def get_current_group_last_multi_region_pursuit_result(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
) -> dict[str, Any] | None:
    result = get_current_group_last_region_pursuit_result(sess, player_id=player_id, group_id=group_id)
    if result and str(result.get("pursuit_scope") or "").strip().lower() == "known_multi_region":
        return result
    return None


def build_group_region_pursuit_result(
    *,
    result_type: str,
    summary: str,
    result_summary: str,
    target_region_id: str,
    target_region_label: str,
    guidance_status: str,
    gateway_id: str = "",
    gateway_label: str = "",
    linked_journey_id: str = "",
    pursuit_scope: str = "",
    target_region_path_ids: list[str] | None = None,
    target_region_path_labels: list[str] | None = None,
    current_hop_region_id: str = "",
    next_hop_region_id: str = "",
    known_route_status: str = "",
    source: str = "region_pursuit",
) -> dict[str, Any] | None:
    return _normalize_group_last_region_pursuit_result(
        {
            "result_id": f"region-pursuit-{uuid.uuid4().hex[:12]}",
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "target_region_id": target_region_id,
            "target_region_label": target_region_label,
            "guidance_status": guidance_status,
            "gateway_id": gateway_id,
            "gateway_label": gateway_label,
            "linked_journey_id": linked_journey_id,
            "pursuit_scope": pursuit_scope,
            "target_region_path_ids": list(target_region_path_ids or []),
            "target_region_path_labels": list(target_region_path_labels or []),
            "current_hop_region_id": current_hop_region_id,
            "next_hop_region_id": next_hop_region_id,
            "known_route_status": known_route_status,
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def _build_group_active_region_pursuit(
    *,
    target_region_plan: dict[str, Any],
    pursuit_status: str,
    linked_journey_id: str = "",
    pursuit_scope: str = "",
    target_region_id: str | None = None,
    target_region_label: str | None = None,
    target_region_path_ids: list[str] | None = None,
    target_region_path_labels: list[str] | None = None,
    current_hop_region_id: str = "",
    next_hop_region_id: str = "",
    known_route_status: str = "",
    source: str = "region_pursuit",
    pursuit_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any] | None:
    plan = _normalize_group_region_target_plan(target_region_plan)
    if not plan:
        return None
    return _normalize_group_active_region_pursuit(
        {
            "pursuit_id": str(pursuit_id or f"region-pursuit-{uuid.uuid4().hex[:12]}"),
            "target_region_id": str(target_region_id or plan.get("target_region_id") or ""),
            "target_region_label": str(target_region_label or plan.get("target_region_label") or ""),
            "pursuit_status": pursuit_status,
            "guidance_status": str(plan.get("plan_status") or ""),
            "gateway_id": str(plan.get("gateway_id") or ""),
            "gateway_label": str(plan.get("gateway_label") or ""),
            "gateway_source_node_id": str(plan.get("gateway_source_node_id") or ""),
            "gateway_source_node_label": str(plan.get("gateway_source_node_label") or ""),
            "linked_journey_id": linked_journey_id,
            "suggested_next_command": str(plan.get("suggested_command") or ""),
            "pursuit_scope": pursuit_scope,
            "target_region_path_ids": list(target_region_path_ids or []),
            "target_region_path_labels": list(target_region_path_labels or []),
            "current_hop_region_id": current_hop_region_id,
            "next_hop_region_id": next_hop_region_id,
            "known_route_status": known_route_status,
            "source": source,
            "created_at": str(created_at or datetime.now(timezone.utc).isoformat()),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def sync_group_region_pursuit_with_guidance(
    sess: Session,
    group_id: str,
    *,
    source: str = "region_pursuit",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None
    pursuit = _normalize_group_active_region_pursuit(group.get("active_region_pursuit"))
    if not pursuit:
        return None
    if str(pursuit.get("pursuit_scope") or "").strip().lower() == "known_multi_region":
        return sync_group_multi_region_pursuit(sess, group_key, source=source)
    plan = get_group_region_target_plan(sess, group_key, str(pursuit.get("target_region_id") or ""))
    if not plan:
        return pursuit
    plan_status = str(plan.get("plan_status") or "").strip().lower()
    linked_journey_id = ""
    active_journey = _normalize_group_active_journey(group.get("active_journey"))
    if (
        plan_status == "approach_gateway"
        and active_journey
        and str(active_journey.get("target_node_id") or "").strip().lower()
        == str(plan.get("gateway_source_node_id") or "").strip().lower()
    ):
        linked_journey_id = str(active_journey.get("journey_id") or "")
        pursuit_status = "pursuing_gateway"
    elif plan_status == "gateway_ready":
        pursuit_status = "gateway_ready"
    elif plan_status == "gateway_blocked":
        pursuit_status = "blocked"
    elif plan_status == "gateway_locked":
        pursuit_status = "locked"
    elif plan_status == "gateway_future_stub":
        pursuit_status = "future_stub"
    else:
        pursuit_status = "unavailable"
    updated = _build_group_active_region_pursuit(
        target_region_plan=plan,
        pursuit_status=pursuit_status,
        linked_journey_id=linked_journey_id,
        source=source,
        pursuit_id=str(pursuit.get("pursuit_id") or ""),
        created_at=str(pursuit.get("created_at") or ""),
        pursuit_scope=str(pursuit.get("pursuit_scope") or "direct_region"),
        target_region_path_ids=list(pursuit.get("target_region_path_ids") or []),
        target_region_path_labels=list(pursuit.get("target_region_path_labels") or []),
        current_hop_region_id=str(pursuit.get("current_hop_region_id") or ""),
        next_hop_region_id=str(pursuit.get("next_hop_region_id") or ""),
        known_route_status=str(pursuit.get("known_route_status") or ""),
    )
    if not updated:
        return pursuit
    group["active_region_pursuit"] = updated
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return updated


def set_group_region_pursuit(
    sess: Session,
    group_id: str,
    target_region_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "region_pursuit",
) -> tuple[dict[str, Any] | None, str | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    normalized_target_region_id = str(target_region_id or "").strip().lower()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None, "Группа не найдена."
    if not normalized_target_region_id:
        return None, "Нужно указать target_region_id для region pursuit."
    existing_pursuit = _normalize_group_active_region_pursuit(group.get("active_region_pursuit"))
    plan = get_group_region_target_plan(sess, group_key, normalized_target_region_id)
    if not plan:
        return None, "Не удалось собрать canonical target-region guidance для region pursuit."
    plan_status = str(plan.get("plan_status") or "").strip().lower()
    target_region_label = str(plan.get("target_region_label") or normalized_target_region_id).strip()
    gateway_id = str(plan.get("gateway_id") or "")
    gateway_label = str(plan.get("gateway_label") or "")
    linked_journey_id = ""
    result_type = "region_pursuit_updated" if existing_pursuit else "region_pursuit_set"
    summary = str(plan.get("summary") or "").strip() or f"Region pursuit для {target_region_label} обновлён."
    result_summary = summary
    pursuit_status = "unavailable"

    if plan_status == "approach_gateway":
        updated_group, error = set_group_journey_target(
            sess,
            group_key,
            str(plan.get("gateway_source_node_id") or ""),
            player_id=player_id,
            source=source,
        )
        if error:
            return updated_group, error
        groups = _get_group_states(sess)
        group = (groups.get(group_key) or group)
        active_journey = _normalize_group_active_journey(group.get("active_journey"))
        linked_journey_id = str((active_journey or {}).get("journey_id") or "")
        pursuit_status = "pursuing_gateway"
        summary = f"Группа начинает pursuit региона {target_region_label} через подход к {str(plan.get('gateway_source_node_label') or 'gateway source')}."
        result_summary = str(plan.get("summary") or summary)
    elif plan_status == "gateway_ready":
        active_journey = _normalize_group_active_journey(group.get("active_journey"))
        if active_journey and str(active_journey.get("target_node_id") or "").strip().lower() == str(plan.get("gateway_source_node_id") or "").strip().lower():
            cleared = clear_group_journey(sess, group_key, source=source)
            groups = _get_group_states(sess)
            group = (groups.get(group_key) or cleared or group)
        pursuit_status = "gateway_ready"
        result_type = "region_pursuit_gateway_ready"
        summary = f"Группа уже готова пересечь {gateway_label or 'gateway'} и войти в регион {target_region_label}."
        result_summary = summary
    elif plan_status == "gateway_blocked":
        pursuit_status = "blocked"
        result_type = "region_pursuit_blocked"
    elif plan_status == "gateway_locked":
        pursuit_status = "locked"
        result_type = "region_pursuit_locked"
    elif plan_status == "gateway_future_stub":
        pursuit_status = "future_stub"
        result_type = "region_pursuit_future_stub"
    else:
        pursuit_status = "unavailable"
        result_type = "region_pursuit_unavailable"

    pursuit = _build_group_active_region_pursuit(
        target_region_plan=plan,
        pursuit_status=pursuit_status,
        linked_journey_id=linked_journey_id,
        source=source,
        pursuit_id=str((existing_pursuit or {}).get("pursuit_id") or ""),
        created_at=str((existing_pursuit or {}).get("created_at") or ""),
    )
    if not pursuit:
        return None, "Не удалось создать canonical region pursuit."
    groups = _get_group_states(sess)
    group = groups.get(group_key) or group
    group["active_region_pursuit"] = pursuit
    result = build_group_region_pursuit_result(
        result_type=result_type,
        summary=summary,
        result_summary=result_summary,
        target_region_id=normalized_target_region_id,
        target_region_label=target_region_label,
        guidance_status=plan_status,
        gateway_id=gateway_id,
        gateway_label=gateway_label,
        linked_journey_id=linked_journey_id,
        source=source,
    )
    if result:
        group["last_region_pursuit_result"] = result
    groups[group_key] = group
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group), None


def clear_group_region_pursuit(
    sess: Session,
    group_id: str,
    *,
    source: str = "region_pursuit",
) -> dict[str, Any] | None:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None
    pursuit = _normalize_group_active_region_pursuit(group.get("active_region_pursuit"))
    if not pursuit:
        return None
    active_journey = _normalize_group_active_journey(group.get("active_journey"))
    if active_journey and str(active_journey.get("journey_id") or "") == str(pursuit.get("linked_journey_id") or ""):
        clear_group_journey(sess, group_key, source=source)
        groups = _get_group_states(sess)
        group = groups.get(group_key) or group
    group.pop("active_region_pursuit", None)
    result = build_group_region_pursuit_result(
        result_type="region_pursuit_cleared",
        summary=f"Region pursuit к {str(pursuit.get('target_region_label') or 'региону')} очищен.",
        result_summary=f"Активный region pursuit к {str(pursuit.get('target_region_label') or 'региону')} остановлен.",
        target_region_id=str(pursuit.get("target_region_id") or ""),
        target_region_label=str(pursuit.get("target_region_label") or ""),
        guidance_status=str(pursuit.get("guidance_status") or ""),
        gateway_id=str(pursuit.get("gateway_id") or ""),
        gateway_label=str(pursuit.get("gateway_label") or ""),
        linked_journey_id=str(pursuit.get("linked_journey_id") or ""),
        source=source,
    )
    if result:
        group["last_region_pursuit_result"] = result
    groups[group_key] = group
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group)


def get_current_group_region_pursuit(
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
    synced = sync_group_region_pursuit_with_guidance(sess, resolved_group_id)
    if synced:
        return synced
    group = _get_group_states(sess).get(resolved_group_id)
    if not isinstance(group, dict):
        return None
    return _normalize_group_active_region_pursuit(group.get("active_region_pursuit"))


def get_current_group_last_region_pursuit_result(
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
    return _normalize_group_last_region_pursuit_result(group.get("last_region_pursuit_result"))


def build_group_region_pursuit_step_result(
    *,
    result_type: str,
    summary: str,
    result_summary: str,
    target_region_id: str,
    target_region_label: str,
    pursuit_id: str = "",
    pursuit_status: str = "",
    step_kind: str = "no_step",
    linked_journey_id: str = "",
    gateway_id: str = "",
    gateway_label: str = "",
    source: str = "region_pursuit_step",
) -> dict[str, Any] | None:
    return _normalize_group_last_region_pursuit_step_result(
        {
            "result_id": f"region-pursuit-step-{uuid.uuid4().hex[:12]}",
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "target_region_id": target_region_id,
            "target_region_label": target_region_label,
            "pursuit_id": pursuit_id,
            "pursuit_status": pursuit_status,
            "step_kind": step_kind,
            "linked_journey_id": linked_journey_id,
            "gateway_id": gateway_id,
            "gateway_label": gateway_label,
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def advance_group_region_pursuit(
    sess: Session,
    group_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "region_pursuit_step",
) -> tuple[dict[str, Any] | None, str | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None, "Группа не найдена."
    pursuit = sync_group_region_pursuit_with_guidance(sess, group_key, source=source)
    groups = _get_group_states(sess)
    group = groups.get(group_key) or group
    if not isinstance(group, dict):
        return None, "Группа не найдена."
    pursuit = pursuit or _normalize_group_active_region_pursuit(group.get("active_region_pursuit"))
    if not pursuit:
        result = build_group_region_pursuit_step_result(
            result_type="region_pursuit_step_invalid",
            summary="У группы нет активного region pursuit.",
            result_summary="Сначала задайте region pursuit, чтобы продолжить движение к целевому региону.",
            target_region_id="unknown_region",
            target_region_label="Неизвестный регион",
            source=source,
        )
        if result:
            group["last_region_pursuit_step_result"] = result
            groups[group_key] = group
            _persist_group_states(sess, groups)
            _sync_group_position_mirrors(sess, group)
        return dict(group), "У группы нет активного region pursuit."

    target_region_id = str(pursuit.get("target_region_id") or "")
    target_region_label = str(pursuit.get("target_region_label") or target_region_id)
    pursuit_id = str(pursuit.get("pursuit_id") or "")
    pursuit_status = str(pursuit.get("pursuit_status") or "").strip().lower()
    linked_journey_id = str(pursuit.get("linked_journey_id") or "")
    gateway_id = str(pursuit.get("gateway_id") or "")
    gateway_label = str(pursuit.get("gateway_label") or gateway_id)

    def _store_step(
        *,
        result_type: str,
        summary: str,
        result_summary: str,
        step_kind: str,
        error: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        latest_groups = _get_group_states(sess)
        latest_group = latest_groups.get(group_key) or group
        if not isinstance(latest_group, dict):
            return None, error
        latest_pursuit = _normalize_group_active_region_pursuit(latest_group.get("active_region_pursuit")) or pursuit
        result = build_group_region_pursuit_step_result(
            result_type=result_type,
            summary=summary,
            result_summary=result_summary,
            target_region_id=str((latest_pursuit or {}).get("target_region_id") or target_region_id),
            target_region_label=str((latest_pursuit or {}).get("target_region_label") or target_region_label),
            pursuit_id=str((latest_pursuit or {}).get("pursuit_id") or pursuit_id),
            pursuit_status=str((latest_pursuit or {}).get("pursuit_status") or pursuit_status),
            step_kind=step_kind,
            linked_journey_id=str((latest_pursuit or {}).get("linked_journey_id") or linked_journey_id),
            gateway_id=str((latest_pursuit or {}).get("gateway_id") or gateway_id),
            gateway_label=str((latest_pursuit or {}).get("gateway_label") or gateway_label),
            source=source,
        )
        if result:
            latest_group["last_region_pursuit_step_result"] = result
            latest_groups[group_key] = latest_group
            _persist_group_states(sess, latest_groups)
            _sync_group_position_mirrors(sess, latest_group)
        return dict(latest_group), error

    if pursuit_status == "pursuing_gateway":
        updated, error = advance_group_journey(
            sess,
            group_key,
            player_id=player_id,
            source=source,
        )
        if error:
            return _store_step(
                result_type="region_pursuit_step_unavailable",
                summary=f"Не удалось продвинуть region pursuit к {target_region_label}.",
                result_summary=error,
                step_kind="journey_leg",
                error=error,
            )
        synced = sync_group_region_pursuit_with_guidance(sess, group_key, source=source)
        synced_status = str((synced or {}).get("pursuit_status") or pursuit_status).strip().lower()
        if synced_status == "gateway_ready":
            return _store_step(
                result_type="region_pursuit_step_gateway_ready",
                summary=f"Группа дошла до выхода {gateway_label or 'gateway'} и готова перейти в регион {target_region_label}.",
                result_summary=f"Подход к gateway завершён. Следующий шаг: {str((synced or {}).get('suggested_next_command') or f'group exit {gateway_id}').strip()}",
                step_kind="journey_leg",
            )
        return _store_step(
            result_type="region_pursuit_step_advanced",
            summary=f"Группа делает один переход по пути к региону {target_region_label}.",
            result_summary=f"Region pursuit к {target_region_label} продвинулся на один journey leg.",
            step_kind="journey_leg",
        )

    if pursuit_status == "gateway_ready":
        updated, error = resolve_group_region_transition(
            sess,
            group_key,
            gateway_id,
            player_id=player_id,
            source=source,
        )
        transition_result = get_current_group_last_region_transition_result(sess, group_id=group_key) or {}
        transition_summary = str(transition_result.get("result_summary") or error or "").strip()
        transition_type = str(transition_result.get("result_type") or "").strip().lower()
        transition_status = str(transition_result.get("transition_status") or "").strip().lower()
        if error or transition_status != "completed":
            step_type = "region_pursuit_step_unavailable"
            if transition_type == "region_transition_blocked":
                step_type = "region_pursuit_step_blocked"
            elif transition_type == "region_transition_locked":
                step_type = "region_pursuit_step_locked"
            elif transition_type == "region_transition_future_stub":
                step_type = "region_pursuit_step_future_stub"
            elif transition_type == "region_transition_invalid":
                step_type = "region_pursuit_step_invalid"
            return _store_step(
                result_type=step_type,
                summary=f"Переход к региону {target_region_label} через {gateway_label or 'gateway'} не выполнен.",
                result_summary=transition_summary or error or f"Переход через {gateway_label or 'gateway'} сейчас недоступен.",
                step_kind="gateway_cross",
                error=error,
            )
        latest_groups = _get_group_states(sess)
        latest_group = latest_groups.get(group_key) or updated or group
        if not isinstance(latest_group, dict):
            return None, "Не удалось обновить группу после регионального перехода."
        transition_result = _normalize_group_last_region_transition_result(latest_group.get("last_region_transition_result")) or transition_result
        if str(transition_result.get("transition_status") or "").strip().lower() == "completed":
            if str(pursuit.get("pursuit_scope") or "").strip().lower() == "known_multi_region":
                synced = sync_group_multi_region_pursuit(sess, group_key, source=source)
                latest_groups = _get_group_states(sess)
                latest_group = latest_groups.get(group_key) or latest_group
            else:
                latest_group.pop("active_region_pursuit", None)
                latest_groups[group_key] = latest_group
                _persist_group_states(sess, latest_groups)
                _sync_group_position_mirrors(sess, latest_group)
        return _store_step(
            result_type="region_pursuit_step_transitioned",
            summary=f"Группа выполняет переход через {gateway_label or 'gateway'} в регион {target_region_label}.",
            result_summary=str(transition_result.get("result_summary") or f"Переход в регион {target_region_label} выполнен.").strip(),
            step_kind="gateway_cross",
        )

    if pursuit_status == "blocked":
        return _store_step(
            result_type="region_pursuit_step_blocked",
            summary=f"Region pursuit к {target_region_label} сейчас упирается в блокировку.",
            result_summary=f"Выход {gateway_label or 'gateway'} сейчас заблокирован.",
            step_kind="no_step",
        )
    if pursuit_status == "locked":
        return _store_step(
            result_type="region_pursuit_step_locked",
            summary=f"Region pursuit к {target_region_label} пока закрыт локальными условиями.",
            result_summary=f"Выход {gateway_label or 'gateway'} ещё не разблокирован.",
            step_kind="no_step",
        )
    if pursuit_status == "future_stub":
        return _store_step(
            result_type="region_pursuit_step_future_stub",
            summary=f"Region pursuit к {target_region_label} упирается в будущий gateway stub.",
            result_summary=f"Выход {gateway_label or 'gateway'} ещё не реализован как активный переход.",
            step_kind="no_step",
        )
    return _store_step(
        result_type="region_pursuit_step_unavailable",
        summary=f"Region pursuit к {target_region_label} сейчас не может сделать следующий шаг.",
        result_summary="Сейчас нет canonical следующего execution step для этого region pursuit.",
        step_kind="no_step",
    )


def get_current_group_last_region_pursuit_step_result(
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
    return _normalize_group_last_region_pursuit_step_result(group.get("last_region_pursuit_step_result"))


def build_group_region_link_result(
    *,
    result_type: str,
    summary: str,
    result_summary: str,
    gateway_id: str,
    gateway_label: str,
    link_id: str,
    source_region_id: str,
    target_region_id: str,
    traversal_count: int,
    source: str = "region_link_history",
) -> dict[str, Any] | None:
    return _normalize_group_last_region_link_result(
        {
            "result_id": f"region-link:{gateway_id}:{datetime.now(timezone.utc).isoformat()}",
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "gateway_id": gateway_id,
            "gateway_label": gateway_label,
            "link_id": link_id,
            "source_region_id": source_region_id,
            "target_region_id": target_region_id,
            "traversal_count": max(1, traversal_count),
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def record_group_gateway_traversal(
    sess: Session,
    group_id: str,
    *,
    gateway_id: str,
    gateway_label: str,
    source_region_id: str,
    source_region_label: str,
    target_region_id: str,
    target_region_label: str,
    traversed_at: str | None = None,
    source: str = "region_link_history",
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None, None
    normalized_gateway_id = str(gateway_id or "").strip().lower()
    normalized_source_region_id = str(source_region_id or "").strip().lower()
    normalized_target_region_id = str(target_region_id or "").strip().lower()
    if not normalized_gateway_id or not normalized_source_region_id or not normalized_target_region_id:
        return None, None
    resolved_at = str(traversed_at or datetime.now(timezone.utc).isoformat()).strip() or datetime.now(timezone.utc).isoformat()
    gateway_states = _normalize_group_gateway_traversal_state_map(group.get("gateway_traversal_states"))
    region_link_states = _normalize_group_region_link_state_map(group.get("region_link_states"))
    existing_gateway = gateway_states.get(normalized_gateway_id)
    link_region_pairs = sorted(
        [
            (normalized_source_region_id, str(source_region_label or normalized_source_region_id).strip()),
            (normalized_target_region_id, str(target_region_label or normalized_target_region_id).strip()),
        ],
        key=lambda item: item[0],
    )
    link_id = _build_region_link_id(link_region_pairs[0][0], link_region_pairs[1][0])
    if not link_id:
        return None, None
    existing_link = region_link_states.get(link_id)
    gateway_traversal_count = max(0, as_int((existing_gateway or {}).get("traversal_count"), 0)) + 1
    link_traversal_count = max(0, as_int((existing_link or {}).get("traversal_count"), 0)) + 1
    gateway_summary = (
        f"Выход {str(gateway_label or normalized_gateway_id).strip()} был пройден {gateway_traversal_count} раз "
        f"между регионами {str(source_region_label or normalized_source_region_id).strip()} и {str(target_region_label or normalized_target_region_id).strip()}."
    )
    gateway_states[normalized_gateway_id] = _normalize_group_gateway_traversal_state(
        {
            "gateway_id": normalized_gateway_id,
            "gateway_label": gateway_label,
            "source_region_id": normalized_source_region_id,
            "source_region_label": source_region_label,
            "target_region_id": normalized_target_region_id,
            "target_region_label": target_region_label,
            "traversal_count": gateway_traversal_count,
            "first_traversed_at": str((existing_gateway or {}).get("first_traversed_at") or resolved_at),
            "last_traversed_at": resolved_at,
            "summary": gateway_summary,
        }
    ) or {}
    region_link_summary = (
        f"Связь между регионами {link_region_pairs[0][1]} и {link_region_pairs[1][1]} подтверждена "
        f"{link_traversal_count} traversal(s) через {len(set([*list((existing_link or {}).get('gateway_ids') or []), normalized_gateway_id]))} gateway(s)."
    )
    region_link_states[link_id] = _normalize_group_region_link_state(
        {
            "link_id": link_id,
            "region_a_id": link_region_pairs[0][0],
            "region_a_label": link_region_pairs[0][1],
            "region_b_id": link_region_pairs[1][0],
            "region_b_label": link_region_pairs[1][1],
            "gateway_ids": sorted(set([*list((existing_link or {}).get("gateway_ids") or []), normalized_gateway_id])),
            "traversal_count": link_traversal_count,
            "first_discovered_at": str((existing_link or {}).get("first_discovered_at") or resolved_at),
            "last_traversed_at": resolved_at,
            "summary": region_link_summary,
        }
    ) or {}
    if not gateway_states[normalized_gateway_id] or not region_link_states[link_id]:
        return None, None
    if not existing_link:
        result_type = "first_region_link_discovered"
        result_summary = (
            f"Группа впервые подтверждает связку регионов {link_region_pairs[0][1]} и {link_region_pairs[1][1]} "
            f"через {str(gateway_label or normalized_gateway_id).strip()}."
        )
    elif not existing_gateway:
        result_type = "first_gateway_crossing"
        result_summary = f"Группа впервые проходит через {str(gateway_label or normalized_gateway_id).strip()}."
    elif normalized_gateway_id in list((existing_link or {}).get("gateway_ids") or []):
        result_type = "repeated_gateway_crossing"
        result_summary = f"Группа снова проходит через {str(gateway_label or normalized_gateway_id).strip()}."
    elif link_traversal_count > 1:
        result_type = "known_region_link_traversed"
        result_summary = (
            f"Группа использует уже известную связь между {link_region_pairs[0][1]} и {link_region_pairs[1][1]} "
            f"через новый gateway {str(gateway_label or normalized_gateway_id).strip()}."
        )
    else:
        result_type = "quiet_region_link_update"
        result_summary = region_link_summary
    result = build_group_region_link_result(
        result_type=result_type,
        summary=result_summary,
        result_summary=result_summary,
        gateway_id=normalized_gateway_id,
        gateway_label=str(gateway_label or normalized_gateway_id).strip(),
        link_id=link_id,
        source_region_id=normalized_source_region_id,
        target_region_id=normalized_target_region_id,
        traversal_count=link_traversal_count,
        source=source,
    )
    group["gateway_traversal_states"] = gateway_states
    group["region_link_states"] = region_link_states
    if result:
        group["last_region_link_result"] = result
    groups[group_key] = group
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(gateway_states[normalized_gateway_id]), result


def get_current_group_gateway_traversal_states(
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
    states = _normalize_group_gateway_traversal_state_map(group.get("gateway_traversal_states"))
    return sorted(
        [dict(item) for item in states.values()],
        key=lambda item: (str(item.get("last_traversed_at") or ""), str(item.get("gateway_id") or "")),
        reverse=True,
    )


def get_current_group_region_link_states(
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
    states = _normalize_group_region_link_state_map(group.get("region_link_states"))
    return sorted(
        [dict(item) for item in states.values()],
        key=lambda item: (str(item.get("last_traversed_at") or ""), str(item.get("link_id") or "")),
        reverse=True,
    )


def get_current_group_last_region_link_result(
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
    return _normalize_group_last_region_link_result(group.get("last_region_link_result"))


def build_group_region_transition_result(
    *,
    gateway_id: str,
    gateway_label: str,
    result_type: str,
    summary: str,
    result_summary: str,
    source_region_id: str,
    source_region_label: str,
    source_node_id: str,
    target_region_id: str,
    target_region_label: str,
    target_anchor_node_id: str = "",
    transition_status: str,
    applied_effects: list[str] | None = None,
    source: str = "region_transition",
) -> dict[str, Any] | None:
    return _normalize_group_last_region_transition_result(
        {
            "result_id": f"region_transition:{gateway_id}:{datetime.now(timezone.utc).isoformat()}",
            "gateway_id": gateway_id,
            "gateway_label": gateway_label,
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "source_region_id": source_region_id,
            "source_region_label": source_region_label,
            "source_node_id": source_node_id,
            "target_region_id": target_region_id,
            "target_region_label": target_region_label,
            "target_anchor_node_id": target_anchor_node_id,
            "transition_status": transition_status,
            "applied_effects": list(applied_effects or []),
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def get_current_group_last_region_transition_result(
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
    return _normalize_group_last_region_transition_result(group.get("last_region_transition_result"))


def get_current_group_region_transition_state(
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
    return _normalize_group_region_transition_state(group.get("region_transition_state"))


def _build_static_map_position_from_node(node_id: str) -> dict[str, Any] | None:
    node = get_static_node(node_id) or {}
    if not node:
        return None
    return _normalize_map_position(
        {
            "map_level": str(node.get("map_level") or "region"),
            "node_type": str(node.get("node_type") or "zone"),
            "node_id": str(node.get("node_id") or node_id),
            "label": str(node.get("label") or node_id),
            "area_label": str(node.get("area_label") or node.get("label") or node_id),
        }
    )


def _apply_group_arrival_pipeline(
    sess: Session,
    group_id: str,
    *,
    next_map_position: dict[str, Any],
    route_summary: dict[str, Any] | None = None,
    route_id: str = "",
    player_ids: list[str] | None = None,
    source: str = "manual",
) -> None:
    group_key = str(group_id or "").strip()
    target_position = _normalize_map_position(next_map_position)
    target_node_id = str((target_position or {}).get("node_id") or "").strip().lower()
    effective_route_summary = _normalize_group_route_summary(route_summary) or None
    resolved_route_id = str(route_id or (effective_route_summary or {}).get("route_id") or "").strip().lower()
    if resolved_route_id:
        record_group_route_traversal(
            sess,
            group_key,
            resolved_route_id,
            summary=f"Группа проходит маршрутом к {str((target_position or {}).get('label') or target_node_id or 'цели')}.",
            traversed_at=datetime.now(timezone.utc).isoformat(),
        )
    if target_position and target_node_id:
        record_group_node_visit(
            sess,
            group_key,
            target_node_id,
            node_label=str(target_position.get("label") or target_node_id),
            result_type="landmark_arrival" if str(target_position.get("node_type") or "").strip().lower() in {"landmark", "interior_entry"} else "first_arrival",
            summary=f"Группа достигает {str(target_position.get('label') or target_node_id)}.",
            visited_at=datetime.now(timezone.utc).isoformat(),
        )
        resolve_group_arrival(
            sess,
            group_key,
            current_map_position=target_position,
            route_summary=effective_route_summary or {"route_id": resolved_route_id},
            source=source,
        )
        resolve_group_node_entry(
            sess,
            group_key,
            current_map_position=target_position,
            source=source,
        )
        resolve_group_destination_event(
            sess,
            group_key,
            current_map_position=target_position,
            source=source,
        )
    if target_position and target_node_id and get_static_node(target_node_id):
        for pid in [str(item).strip() for item in (player_ids or []) if str(item).strip()]:
            maybe_mark_player_node_visited(sess, pid, target_node_id, source=source)
            maybe_reveal_nearby_static_nodes(sess, pid, target_position, source=source)


def resolve_group_region_transition(
    sess: Session,
    group_id: str,
    gateway_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "region_transition",
) -> tuple[dict[str, Any] | None, str | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    normalized_gateway_id = str(gateway_id or "").strip().lower()
    group = groups.get(group_key)
    if not isinstance(group, dict):
        return None, "Группа не найдена."
    if not normalized_gateway_id:
        return None, "Нужно указать gateway_id для перехода."
    current_position = _normalize_map_position(group.get("current_map_position"))
    current_node_id = str((current_position or {}).get("node_id") or "").strip().lower()
    source_region_identity = _resolve_region_identity_for_position(current_position) or {}
    source_region_state = _normalize_group_current_region_state(group.get("current_region_state"))
    source_region_id = str((source_region_state or {}).get("region_id") or source_region_identity.get("region_id") or (current_position or {}).get("map_level") or "region").strip().lower() or "region"
    source_region_label = str((source_region_state or {}).get("region_label") or source_region_identity.get("region_label") or (current_position or {}).get("area_label") or (current_position or {}).get("label") or "Текущий регион").strip()
    gateway_lookup_region_id = str((current_position or {}).get("map_level") or "region").strip().lower() or "region"
    definition = next(
        (
            dict(item)
            for item in get_static_region_gateways(region_id=gateway_lookup_region_id, current_map_position=current_position)
            if str(item.get("gateway_id") or "").strip().lower() == normalized_gateway_id
        ),
        None,
    )
    if not definition:
        result = build_group_region_transition_result(
            gateway_id=normalized_gateway_id,
            gateway_label=normalized_gateway_id,
            result_type="region_transition_invalid",
            summary="Неизвестный региональный выход.",
            result_summary="Группа пытается пройти через неизвестный gateway_id, но такого выхода нет в authored frontier map.",
            source_region_id=source_region_id,
            source_region_label=source_region_label,
            source_node_id=current_node_id or "unknown_source",
            target_region_id="unknown_region",
            target_region_label="Неизвестный регион",
            transition_status="invalid",
            applied_effects=["region_transition:invalid"],
            source=source,
        )
        if result:
            group["last_region_transition_result"] = result
            group["region_transition_state"] = _normalize_group_region_transition_state(
                {
                    "last_gateway_id": normalized_gateway_id,
                    "last_result_type": result.get("result_type"),
                    "summary": result.get("summary"),
                    "updated_at": result.get("resolved_at"),
                }
            )
            _persist_group_states(sess, groups)
            _sync_group_position_mirrors(sess, group)
        return dict(group), "Неизвестный gateway_id."
    source_node_id = str(definition.get("source_node_id") or "").strip().lower()
    if current_node_id != source_node_id:
        result = build_group_region_transition_result(
            gateway_id=normalized_gateway_id,
            gateway_label=str(definition.get("label") or normalized_gateway_id),
            result_type="region_transition_invalid",
            summary="Группа находится не у этого выхода.",
            result_summary=f"Для перехода через {str(definition.get('label') or normalized_gateway_id)} нужно сначала оказаться в точке {source_node_id}.",
            source_region_id=source_region_id,
            source_region_label=source_region_label,
            source_node_id=current_node_id or "unknown_source",
            target_region_id=str(definition.get("target_region_id") or "unknown_region"),
            target_region_label=str(definition.get("target_region_label") or "Неизвестный регион"),
            target_anchor_node_id=str(definition.get("target_anchor_node_id") or ""),
            transition_status="invalid",
            applied_effects=["region_transition:invalid", f"wrong_source:{source_node_id}"],
            source=source,
        )
        if result:
            group["last_region_transition_result"] = result
            group["region_transition_state"] = _normalize_group_region_transition_state(
                {
                    "last_gateway_id": normalized_gateway_id,
                    "last_result_type": result.get("result_type"),
                    "summary": result.get("summary"),
                    "updated_at": result.get("resolved_at"),
                }
            )
            _persist_group_states(sess, groups)
            _sync_group_position_mirrors(sess, group)
        return dict(group), "Переход нельзя выполнить из текущего узла."
    gateway = next(
        (item for item in get_group_region_gateways(sess, group_key) if str(item.get("gateway_id") or "").strip().lower() == normalized_gateway_id),
        None,
    )
    gateway_status = str((gateway or {}).get("gateway_status") or "unavailable").strip().lower()
    gateway_label = str((gateway or {}).get("gateway_label") or definition.get("label") or normalized_gateway_id).strip()
    target_region_id = str(definition.get("target_region_id") or "unknown_region")
    target_region_label = str(definition.get("target_region_label") or target_region_id or "Неизвестный регион").strip()
    target_anchor_node_id = str(definition.get("target_anchor_node_id") or "").strip().lower()
    result_type = "region_transition_unavailable"
    transition_status = "unavailable"
    summary = f"Выход {gateway_label} сейчас недоступен."
    result_summary = summary
    applied_effects = ["region_transition:unavailable"]
    if gateway_status == "blocked":
        result_type = "region_transition_blocked"
        transition_status = "blocked"
        summary = f"Выход {gateway_label} сейчас заблокирован."
        result_summary = str((gateway or {}).get("summary") or summary)
        applied_effects = ["region_transition:blocked"]
    elif gateway_status == "locked":
        result_type = "region_transition_locked"
        transition_status = "locked"
        summary = f"Выход {gateway_label} пока закрыт локальными условиями."
        result_summary = str((gateway or {}).get("summary") or summary)
        applied_effects = ["region_transition:locked"]
    elif gateway_status == "future_stub":
        result_type = "region_transition_future_stub"
        transition_status = "future_stub"
        summary = f"Выход {gateway_label} отмечен как будущий переход."
        result_summary = str((gateway or {}).get("summary") or summary)
        applied_effects = ["region_transition:future_stub"]
    elif gateway_status == "open":
        target_anchor_position = _build_static_map_position_from_node(target_anchor_node_id)
        if not target_anchor_node_id or not target_anchor_position:
            result_type = "region_transition_unavailable"
            transition_status = "unavailable"
            summary = f"У выхода {gateway_label} пока нет готовой точки перехода."
            result_summary = "Gateway найден, но у него ещё нет authored target anchor для фактического перемещения группы."
            applied_effects = ["region_transition:unavailable", "missing_target_anchor"]
        else:
            group["current_map_position"] = target_anchor_position
            group["area_label"] = str(target_anchor_position.get("area_label") or target_anchor_position.get("label") or target_region_label)[:80]
            _clear_group_activity_state(group, status="idle")
            _persist_group_states(sess, groups)
            _sync_group_position_mirrors(sess, group)
            _apply_group_arrival_pipeline(
                sess,
                group_key,
                next_map_position=target_anchor_position,
                route_summary={
                    "route_id": str((gateway or {}).get("route_id") or definition.get("route_id") or ""),
                    "target_node_id": target_anchor_node_id,
                    "target_label": str(target_anchor_position.get("label") or target_anchor_node_id),
                    "target_node": target_anchor_position,
                },
                route_id=str((gateway or {}).get("route_id") or definition.get("route_id") or ""),
                player_ids=[str(pid).strip() for pid in (group.get("player_ids") or []) if str(pid).strip()],
                source=source,
            )
            resolve_group_region_residency(
                sess,
                group_key,
                current_map_position=target_anchor_position,
                source=source,
                persist_result=True,
            )
            groups = _get_group_states(sess)
            group = groups.get(group_key)
            if not isinstance(group, dict):
                return None, "Не удалось завершить переход между регионами."
            result_type = "region_transition_completed"
            transition_status = "completed"
            summary = f"Группа проходит через {gateway_label} и выходит в регион {target_region_label}."
            result_summary = summary
            applied_effects = [
                "region_transition:completed",
                f"target_region:{target_region_id}",
                f"target_anchor:{target_anchor_node_id}",
            ]
    result = build_group_region_transition_result(
        gateway_id=normalized_gateway_id,
        gateway_label=gateway_label,
        result_type=result_type,
        summary=summary,
        result_summary=result_summary,
        source_region_id=source_region_id,
        source_region_label=source_region_label,
        source_node_id=source_node_id or current_node_id or "unknown_source",
        target_region_id=target_region_id,
        target_region_label=target_region_label,
        target_anchor_node_id=target_anchor_node_id,
        transition_status=transition_status,
        applied_effects=applied_effects,
        source=source,
    )
    if result and isinstance(group, dict):
        group["last_region_transition_result"] = result
        group["region_transition_state"] = _normalize_group_region_transition_state(
            {
                "last_gateway_id": normalized_gateway_id,
                "last_result_type": result.get("result_type"),
                "summary": result.get("summary"),
                "updated_at": result.get("resolved_at"),
            }
        )
        groups[group_key] = group
        _persist_group_states(sess, groups)
        _sync_group_position_mirrors(sess, group)
        if str(result.get("transition_status") or "").strip().lower() == "completed":
            record_group_gateway_traversal(
                sess,
                group_key,
                gateway_id=normalized_gateway_id,
                gateway_label=gateway_label,
                source_region_id=source_region_id,
                source_region_label=source_region_label,
                target_region_id=target_region_id,
                target_region_label=target_region_label,
                traversed_at=str(result.get("resolved_at") or ""),
                source=source,
            )
            groups = _get_group_states(sess)
            group = groups.get(group_key) or group
            groups[group_key] = group
            _persist_group_states(sess, groups)
            _sync_group_position_mirrors(sess, group)
    error_message = None
    if transition_status == "blocked":
        error_message = "Выход сейчас заблокирован."
    elif transition_status == "locked":
        error_message = "Выход пока закрыт условиями этого узла."
    elif transition_status == "future_stub":
        error_message = "Этот выход пока существует только как future stub."
    elif transition_status == "unavailable":
        error_message = "Этот выход сейчас недоступен."
    elif transition_status == "invalid":
        error_message = "Переход через этот выход недействителен."
    return (dict(group) if isinstance(group, dict) else None), error_message


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
    options = get_static_navigation_options(
        current_map_position=current_map_position,
        known_node_ids=get_player_known_node_ids(sess, resolved_player_id) if resolved_player_id else None,
        revealed_node_ids=get_player_revealed_node_ids(sess, resolved_player_id) if resolved_player_id else None,
    )
    annotated: list[dict[str, Any]] = []
    for option in options:
        annotated_option = dict(option)
        effective = get_effective_group_route_access_state(sess, resolved_group_id, route_id=annotated_option.get("route_id"))
        if effective:
            annotated_option["access_state"] = effective.get("access_state")
            annotated_option["is_traversable"] = bool(effective.get("is_traversable"))
            annotated_option["blocked"] = annotated_option["is_traversable"] is not True
            if effective.get("block_reason"):
                annotated_option["block_reason"] = effective.get("block_reason")
        else:
            annotated_option["access_state"] = "open"
            annotated_option["is_traversable"] = True
            annotated_option["blocked"] = False
        annotated.append(annotated_option)
    return annotated


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
    blocked_error = validate_group_route_accessibility(sess, resolved_group_id, route_summary)
    if blocked_error:
        return None, blocked_error

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
    current_node_id = str(current_map_position.get("node_id") or "").strip().lower()
    node_context = get_static_node_context(current_map_position=current_map_position)
    if not node_context:
        return None
    current_node_state = get_group_node_state(sess, resolved_group_id, current_node_id) if current_node_id else None
    node_state_flags = list((current_node_state or {}).get("state_flags") or [])
    state_notes = _build_effective_node_state_notes(current_node_id, node_state_flags, note_kind="context_note") if current_node_id else []
    current_visit_state = get_current_group_current_node_visit_state(sess, group_id=resolved_group_id) if current_node_id else None
    annotated_actions = get_current_group_context_action_availability(
        sess,
        player_id=resolved_player_id or None,
        group_id=resolved_group_id,
    )
    travel_state = _group_travel_state_summary(group)
    if isinstance(travel_state, dict) and travel_state.get("active") is True and travel_state.get("paused") is True:
        pause_reason = str(travel_state.get("pause_reason") or "").strip().lower()
        if pause_reason == "target_requires_enter" and not any(
            action.get("action_key") == "enter" for action in annotated_actions if isinstance(action, dict)
        ):
            annotated_actions.insert(
                0,
                {
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
                },
            )
        if pause_reason == "point_of_interest_reached" and not any(
            action.get("action_key") == "inspect" for action in annotated_actions if isinstance(action, dict)
        ):
            annotated_actions.insert(
                0,
                {
                    "action_id": "inspect",
                    "action_key": "inspect",
                    "label": "Осмотреться",
                    "action_type": "action",
                    "action_kind": "inspect",
                    "interaction_kind": "context_action",
                    "interaction_id": "inspect",
                    "availability_status": "available",
                    "status": "available",
                    "available": True,
                    "unavailable_reason": "",
                    "unlock_hint": "",
                    "satisfied_requirements": [],
                    "missing_requirements": [],
                    "source": "interaction_gating",
                    "exhausted": False,
                },
            )
    payload = {
        "node_summary": node_context,
        "contextual_actions": annotated_actions,
        "available_services": get_current_group_service_availability(sess, player_id=resolved_player_id or None, group_id=resolved_group_id),
        "service_actions": (
            [{"action_key": "use_service", "label": "Воспользоваться услугой", "action_type": "action"}]
            if get_current_group_service_availability(sess, player_id=resolved_player_id or None, group_id=resolved_group_id)
            else []
        ),
    }
    if node_state_flags:
        payload["node_state_flags"] = node_state_flags
    if state_notes:
        payload["state_notes"] = state_notes
    if current_visit_state:
        payload["visit_count"] = int(current_visit_state.get("visit_count") or 0)
        payload["current_node_visit_state"] = dict(current_visit_state)
    current_entry_result = get_current_group_last_node_entry_result(sess, group_id=resolved_group_id) if current_node_id else None
    if current_entry_result and str(current_entry_result.get("node_id") or "").strip().lower() == current_node_id:
        payload["current_entry_type"] = str(current_entry_result.get("result_type") or "")
        payload["current_entry_note"] = str(current_entry_result.get("summary") or "")
    current_destination_event = get_current_group_last_destination_event_result(sess, group_id=resolved_group_id) if current_node_id else None
    if current_destination_event and str(current_destination_event.get("node_id") or "").strip().lower() == current_node_id:
        payload["current_destination_event_type"] = str(current_destination_event.get("result_type") or "")
        payload["current_destination_event_note"] = str(current_destination_event.get("summary") or "")
    current_node_progress = get_current_group_current_node_progress(sess, group_id=resolved_group_id) if current_node_id else None
    if current_node_progress:
        payload["current_node_progression_status"] = str(current_node_progress.get("progression_status") or "")
        payload["current_node_progression_summary"] = str(current_node_progress.get("summary") or "")
    return payload


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
    state_notes = raw.get("state_notes")
    if isinstance(state_notes, list):
        normalized_state_notes = [str(item).strip()[:240] for item in state_notes if str(item or "").strip()]
        if normalized_state_notes:
            result["state_notes"] = normalized_state_notes
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
    result_id = str(raw.get("result_id") or "").strip()
    service_id = str(raw.get("service_id") or raw.get("service_key") or "").strip().lower()
    service_key = str(raw.get("service_key") or service_id).strip().lower()
    label = str(raw.get("service_label") or raw.get("label") or service_id).strip()
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type not in {"lodging_received", "guidance_received", "supplies_secured", "service_unavailable", "already_used", "no_effect"}:
        return None
    result_summary = str(raw.get("result_summary") or raw.get("summary") or "").strip()
    node_id = str(raw.get("node_id") or "").strip()
    node_label = str(raw.get("node_label") or node_id).strip()
    if not result_id or not service_id or not label or not result_summary or not node_id or not node_label:
        return None
    result: dict[str, Any] = {
        "result_id": result_id[:80],
        "service_id": service_id[:120],
        "service_key": service_key[:80],
        "service_label": label[:120],
        "label": label[:120],
        "result_type": result_type[:40],
        "service_type": str(raw.get("service_type") or "service")[:40] or "service",
        "service_kind": str(raw.get("service_kind") or raw.get("service_type") or "service")[:40] or "service",
        "summary": str(raw.get("summary") or result_summary)[:400] or result_summary[:400],
        "result_summary": result_summary[:400],
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "source": str(raw.get("source") or "service")[:40] or "service",
    }
    applied_effects = raw.get("applied_effects")
    if isinstance(applied_effects, list):
        normalized_effects = [str(item).strip()[:120] for item in applied_effects if str(item or "").strip()]
        if normalized_effects:
            result["applied_effects"] = normalized_effects
    discovered_notes = raw.get("discovered_notes")
    if isinstance(discovered_notes, list):
        normalized_notes = [str(item).strip()[:240] for item in discovered_notes if str(item or "").strip()]
        if normalized_notes:
            result["discovered_notes"] = normalized_notes
    result["reveal_applied"] = bool(raw.get("reveal_applied"))
    service_hints = raw.get("service_hints")
    if isinstance(service_hints, list):
        normalized_hints = [str(item).strip()[:120] for item in service_hints if str(item or "").strip()]
        if normalized_hints:
            result["service_hints"] = normalized_hints
    resolved_at = str(raw.get("resolved_at") or raw.get("used_at") or "").strip()
    if resolved_at:
        result["resolved_at"] = resolved_at[:80]
    return result


def _normalize_group_service_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    service_id = str(raw.get("service_id") or "").strip().lower()
    status = str(raw.get("status") or "").strip().lower()
    if status not in {"available", "completed", "resolved"}:
        return None
    result_type = str(raw.get("result_type") or "").strip().lower()
    if result_type and result_type not in {"lodging_received", "guidance_received", "supplies_secured", "service_unavailable", "already_used", "no_effect"}:
        return None
    summary = str(raw.get("summary") or "").strip()
    source = str(raw.get("source") or "service").strip() or "service"
    updated_at = str(raw.get("updated_at") or "").strip()
    if not service_id or not summary:
        return None
    state: dict[str, Any] = {
        "service_id": service_id[:120],
        "status": status[:40],
        "summary": summary[:240],
        "source": source[:40],
    }
    if result_type:
        state["result_type"] = result_type[:40]
    if updated_at:
        state["updated_at"] = updated_at[:80]
    return state


def _normalize_group_service_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for service_id, value in raw.items():
        candidate = value if isinstance(value, dict) else {"service_id": service_id, "status": value, "summary": str(value or service_id)}
        merged = {"service_id": service_id, **candidate} if isinstance(candidate, dict) else candidate
        state = _normalize_group_service_state(merged)
        if state:
            normalized[state["service_id"]] = state
    return normalized


def _normalize_group_map_intel_entry(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    entry_id = str(raw.get("entry_id") or "").strip()
    entry_type = str(raw.get("entry_type") or "").strip().lower()
    if entry_type not in {"clue", "guidance", "route_hint", "warning", "landmark_note", "travel_note"}:
        return None
    title = str(raw.get("title") or "").strip()
    summary = str(raw.get("summary") or "").strip()
    result_summary = str(raw.get("result_summary") or "").strip()
    source_kind = str(raw.get("source_kind") or "").strip().lower()
    if source_kind not in {"scout", "service", "context_action", "travel_event", "destination_event", "region_onboarding"}:
        return None
    source_id = str(raw.get("source_id") or "").strip()
    node_id = str(raw.get("node_id") or "").strip()
    node_label = str(raw.get("node_label") or node_id).strip()
    dedupe_key = str(raw.get("dedupe_key") or "").strip().lower()
    discovered_at = str(raw.get("discovered_at") or "").strip()
    if not entry_id or not title or not summary or not result_summary or not source_id or not node_id or not node_label or not dedupe_key:
        return None
    related_node_ids = [
        str(item).strip()[:120]
        for item in (raw.get("related_node_ids") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("related_node_ids"), list) else []
    related_route_ids = [
        str(item).strip()[:120]
        for item in (raw.get("related_route_ids") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("related_route_ids"), list) else []
    tags = [
        str(item).strip().lower()[:40]
        for item in (raw.get("tags") or [])
        if str(item or "").strip()
    ] if isinstance(raw.get("tags"), list) else []
    entry: dict[str, Any] = {
        "entry_id": entry_id[:80],
        "entry_type": entry_type[:40],
        "title": title[:160],
        "summary": summary[:400],
        "result_summary": result_summary[:400],
        "source_kind": source_kind[:40],
        "source_id": source_id[:120],
        "node_id": node_id[:120],
        "node_label": node_label[:120],
        "related_node_ids": related_node_ids,
        "related_route_ids": related_route_ids,
        "tags": tags,
        "dedupe_key": dedupe_key[:240],
    }
    if discovered_at:
        entry["discovered_at"] = discovered_at[:80]
    return entry


def _normalize_group_map_intel_entries(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in raw:
        entry = _normalize_group_map_intel_entry(item)
        if not entry:
            continue
        entry_id = str(entry.get("entry_id") or "").strip().lower()
        if entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        entries.append(entry)
    return entries


def build_group_map_intel_entry(
    *,
    entry_type: str,
    title: str,
    summary: str,
    result_summary: str,
    source_kind: str,
    source_id: str,
    node_id: str,
    node_label: str,
    related_node_ids: list[str] | set[str] | None = None,
    related_route_ids: list[str] | set[str] | None = None,
    tags: list[str] | set[str] | None = None,
    dedupe_key: str,
    discovered_at: str | None = None,
) -> dict[str, Any] | None:
    return _normalize_group_map_intel_entry(
        {
            "entry_id": uuid.uuid4().hex[:12],
            "entry_type": entry_type,
            "title": title,
            "summary": summary,
            "result_summary": result_summary,
            "source_kind": source_kind,
            "source_id": source_id,
            "node_id": node_id,
            "node_label": node_label,
            "related_node_ids": list(related_node_ids or []),
            "related_route_ids": list(related_route_ids or []),
            "tags": list(tags or []),
            "dedupe_key": dedupe_key,
            "discovered_at": discovered_at or datetime.now(timezone.utc).isoformat(),
        }
    )


def _add_group_map_intel_entry_to_group(
    group: dict[str, Any],
    entry: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized_entry = _normalize_group_map_intel_entry(entry)
    if not normalized_entry:
        return None
    entries = _normalize_group_map_intel_entries(group.get("map_intel_entries"))
    dedupe_key = str(normalized_entry.get("dedupe_key") or "").strip().lower()
    existing = next(
        (
            dict(item)
            for item in entries
            if str(item.get("dedupe_key") or "").strip().lower() == dedupe_key
        ),
        None,
    )
    if existing:
        group["map_intel_entries"] = entries
        return existing
    entries.append(normalized_entry)
    group["map_intel_entries"] = entries
    return dict(normalized_entry)


def add_group_map_intel_entry(
    sess: Session,
    group_id: str,
    entry: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized_group_id = str(group_id or "").strip()
    if not normalized_group_id:
        return None
    groups = _get_group_states(sess)
    group = groups.get(normalized_group_id)
    if not isinstance(group, dict):
        return None
    stored = _add_group_map_intel_entry_to_group(group, entry)
    if not stored:
        return None
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return stored


def get_current_group_map_intel(
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
    return [dict(item) for item in _normalize_group_map_intel_entries(group.get("map_intel_entries"))]


def get_current_group_recent_map_intel(
    sess: Session,
    *,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    entries = get_current_group_map_intel(sess, player_id=player_id, group_id=group_id)
    resolved_limit = max(0, int(limit or 0))
    if resolved_limit <= 0:
        return []
    return entries[-resolved_limit:]


def _build_map_intel_tags(
    *,
    entry_type: str,
    node_id: str,
    related_node_ids: list[str] | set[str] | None = None,
) -> list[str]:
    tags: list[str] = []
    for candidate in [entry_type, node_id, *(related_node_ids or [])]:
        tag = str(candidate or "").strip().lower()
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:8]


def _build_map_intel_entry_from_scout_result(result: dict[str, Any] | None) -> dict[str, Any] | None:
    normalized = _normalize_group_last_scout_result(result)
    if not normalized:
        return None
    result_type = str(normalized.get("result_type") or "").strip().lower()
    if result_type == "no_new_findings":
        return None
    node_id = str(normalized.get("node_id") or "").strip()
    node_label = str(normalized.get("node_label") or node_id).strip()
    related_node_ids = list(normalized.get("discovered_node_ids") or [])
    related_route_ids = list(normalized.get("discovered_route_ids") or [])
    discovered_notes = [str(note).strip() for note in (normalized.get("discovered_notes") or []) if str(note or "").strip()]
    entry_type = "route_hint"
    title = f"Разведка у {node_label}"
    if result_type == "landmark_revealed":
        entry_type = "landmark_note"
        title = f"Ориентир у {node_label}"
    elif result_type == "hidden_path_revealed":
        entry_type = "route_hint"
        title = f"Скрытый проход у {node_label}"
    elif result_type == "local_clue_found":
        entry_type = "clue"
        title = f"Локальная зацепка у {node_label}"
    primary_note = discovered_notes[0] if discovered_notes else str(normalized.get("result_summary") or normalized.get("summary") or "").strip()
    dedupe_parts = [
        "scout",
        node_id,
        result_type,
        ",".join(sorted(str(item).strip().lower() for item in related_node_ids if str(item).strip())),
        ",".join(sorted(str(item).strip().lower() for item in related_route_ids if str(item).strip())),
        primary_note.lower(),
    ]
    return build_group_map_intel_entry(
        entry_type=entry_type,
        title=title,
        summary=str(normalized.get("summary") or ""),
        result_summary=primary_note or str(normalized.get("result_summary") or ""),
        source_kind="scout",
        source_id=str(normalized.get("result_id") or ""),
        node_id=node_id,
        node_label=node_label,
        related_node_ids=related_node_ids,
        related_route_ids=related_route_ids,
        tags=_build_map_intel_tags(entry_type=entry_type, node_id=node_id, related_node_ids=related_node_ids),
        dedupe_key="|".join(part for part in dedupe_parts if part),
        discovered_at=str(normalized.get("resolved_at") or ""),
    )


def _build_map_intel_entry_from_service_result(
    result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized = _normalize_group_last_service_result(result)
    if not normalized:
        return None
    result_type = str(normalized.get("result_type") or "").strip().lower()
    discovered_notes = [str(note).strip() for note in (normalized.get("discovered_notes") or []) if str(note or "").strip()]
    if result_type == "guidance_received":
        entry_type = "guidance"
    elif result_type in {"supplies_secured", "lodging_received"} and discovered_notes:
        entry_type = "travel_note"
    else:
        return None
    node_id = str(normalized.get("node_id") or "").strip()
    node_label = str(normalized.get("node_label") or node_id).strip()
    primary_note = discovered_notes[0] if discovered_notes else str(normalized.get("result_summary") or normalized.get("summary") or "").strip()
    related_node_ids = [
        effect.split(":", 1)[1]
        for effect in (normalized.get("applied_effects") or [])
        if isinstance(effect, str) and effect.startswith("node_revealed:")
    ]
    dedupe_parts = [
        "service",
        str(normalized.get("service_id") or ""),
        result_type,
        primary_note.lower(),
    ]
    return build_group_map_intel_entry(
        entry_type=entry_type,
        title=f"Услуга у {node_label}",
        summary=str(normalized.get("summary") or ""),
        result_summary=primary_note or str(normalized.get("result_summary") or ""),
        source_kind="service",
        source_id=str(normalized.get("service_id") or normalized.get("result_id") or ""),
        node_id=node_id,
        node_label=node_label,
        related_node_ids=related_node_ids,
        related_route_ids=[],
        tags=_build_map_intel_tags(entry_type=entry_type, node_id=node_id, related_node_ids=related_node_ids),
        dedupe_key="|".join(part for part in dedupe_parts if part),
        discovered_at=str(normalized.get("resolved_at") or ""),
    )


def _build_map_intel_entry_from_context_action_result(
    result: dict[str, Any] | None,
    *,
    action_effect: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    normalized = _normalize_group_last_context_action_result(result)
    if not normalized:
        return None
    result_type = str(normalized.get("result_type") or "").strip().lower()
    effect = dict(action_effect or {})
    discovered_notes = [
        str(note).strip()
        for note in (effect.get("discovered_notes") or [])
        if str(note or "").strip()
    ]
    if result_type == "local_clue_found":
        entry_type = "clue"
        title = f"Локальная находка у {normalized.get('node_label')}"
        result_summary = discovered_notes[0] if discovered_notes else str(normalized.get("result_summary") or normalized.get("summary") or "").strip()
    elif result_type == "route_cleared" and discovered_notes:
        entry_type = "route_hint"
        title = f"Проход открыт у {normalized.get('node_label')}"
        result_summary = discovered_notes[0]
    elif result_type == "route_still_blocked" and discovered_notes:
        entry_type = "warning"
        title = f"Предупреждение у {normalized.get('node_label')}"
        result_summary = discovered_notes[0]
    elif result_type == "local_support_applied" and discovered_notes:
        entry_type = "guidance"
        title = f"Поддержка закреплена у {normalized.get('node_label')}"
        result_summary = discovered_notes[0]
    else:
        return None
    route_id = str(effect.get("route_id") or "").strip().lower()
    dedupe_parts = [
        "context_action",
        str(normalized.get("action_id") or ""),
        result_type,
        route_id,
        result_summary.lower(),
    ]
    return build_group_map_intel_entry(
        entry_type=entry_type,
        title=title,
        summary=str(normalized.get("summary") or ""),
        result_summary=result_summary,
        source_kind="context_action",
        source_id=str(normalized.get("action_id") or normalized.get("result_id") or ""),
        node_id=str(normalized.get("node_id") or ""),
        node_label=str(normalized.get("node_label") or normalized.get("node_id") or ""),
        related_node_ids=[],
        related_route_ids=[route_id] if route_id else [],
        tags=_build_map_intel_tags(entry_type=entry_type, node_id=str(normalized.get("node_id") or "")),
        dedupe_key="|".join(part for part in dedupe_parts if part),
        discovered_at=str(normalized.get("resolved_at") or ""),
    )


def _build_map_intel_entry_from_travel_event_outcome(
    outcome: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized = _normalize_group_travel_event_outcome(outcome)
    if not normalized:
        return None
    outcome_type = str(normalized.get("outcome_type") or "").strip().lower()
    entry_type_by_outcome = {
        "finding_note": "travel_note",
        "route_hint": "route_hint",
        "guidance_note": "guidance",
        "warning_note": "warning",
    }
    entry_type = entry_type_by_outcome.get(outcome_type)
    if not entry_type:
        return None
    route_snapshot = _normalize_group_route_summary(normalized.get("route_snapshot")) or {}
    related_node_ids = [str(route_snapshot.get("target_node_id") or "").strip()] if str(route_snapshot.get("target_node_id") or "").strip() else []
    related_route_ids = [str(route_snapshot.get("route_id") or "").strip().lower()] if str(route_snapshot.get("route_id") or "").strip() else []
    node_label = str(route_snapshot.get("target_label") or normalized.get("event_key") or "путь").strip()
    dedupe_parts = [
        "travel_event",
        str(normalized.get("event_key") or ""),
        outcome_type,
        ",".join(related_node_ids),
        ",".join(related_route_ids),
        str(normalized.get("result_summary") or "").strip().lower(),
    ]
    return build_group_map_intel_entry(
        entry_type=entry_type,
        title=f"Дорожная заметка: {node_label}",
        summary=str(normalized.get("summary") or ""),
        result_summary=str(normalized.get("result_summary") or normalized.get("summary") or ""),
        source_kind="travel_event",
        source_id=str(normalized.get("outcome_id") or normalized.get("event_key") or ""),
        node_id=str(route_snapshot.get("target_node_id") or normalized.get("event_key") or "travel_event"),
        node_label=node_label,
        related_node_ids=related_node_ids,
        related_route_ids=related_route_ids,
        tags=_build_map_intel_tags(entry_type=entry_type, node_id=str(route_snapshot.get("target_node_id") or normalized.get("event_key") or "")),
        dedupe_key="|".join(part for part in dedupe_parts if part),
        discovered_at=str(normalized.get("resolved_at") or ""),
    )


def _build_map_intel_entry_from_destination_event_result(
    result: dict[str, Any] | None,
    *,
    destination_event: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    normalized = _normalize_group_last_destination_event_result(result)
    if not normalized:
        return None
    result_type = str(normalized.get("result_type") or "").strip().lower()
    if result_type in {"no_event", "already_resolved"}:
        return None
    event = dict(destination_event or {})
    entry_type = str(event.get("intel_entry_type") or "").strip().lower()
    if not entry_type:
        entry_type = {
            "first_discovery": "landmark_note",
            "settlement_notice": "guidance",
            "local_warning": "warning",
            "changed_place_notice": "warning",
            "local_notice": "travel_note",
        }.get(result_type, "travel_note")
    node_id = str(normalized.get("node_id") or "").strip()
    node_label = str(normalized.get("node_label") or node_id).strip()
    event_id = str(normalized.get("event_id") or "").strip().lower()
    related_node_ids = [
        str(item).strip().lower()
        for item in (event.get("reveal_node_ids") or [])
        if str(item or "").strip()
    ]
    title = str(event.get("intel_title") or normalized.get("title") or normalized.get("event_label") or "Локальная заметка").strip()
    dedupe_parts = [
        "destination_event",
        event_id,
        result_type,
        ",".join(sorted(related_node_ids)),
        str(normalized.get("result_summary") or "").strip().lower(),
    ]
    return build_group_map_intel_entry(
        entry_type=entry_type,
        title=title,
        summary=str(normalized.get("summary") or ""),
        result_summary=str(normalized.get("result_summary") or normalized.get("summary") or ""),
        source_kind="destination_event",
        source_id=event_id,
        node_id=node_id,
        node_label=node_label,
        related_node_ids=related_node_ids,
        related_route_ids=[],
        tags=[
            str(item).strip().lower()
            for item in (event.get("tags") or _build_map_intel_tags(entry_type=entry_type, node_id=node_id, related_node_ids=related_node_ids))
            if str(item or "").strip()
        ],
        dedupe_key="|".join(part for part in dedupe_parts if part),
        discovered_at=str(normalized.get("resolved_at") or ""),
    )


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
    detail = dict(get_static_node_detail(current_map_position=current_map_position) or {})
    current_node_id = str(current_map_position.get("node_id") or "").strip().lower()
    current_node_state = get_group_node_state(sess, resolved_group_id, current_node_id) if current_node_id else None
    node_state_flags = list((current_node_state or {}).get("state_flags") or [])
    state_notes = _build_effective_node_state_notes(current_node_id, node_state_flags, note_kind="detail_note") if current_node_id else []
    if node_state_flags:
        detail["node_state_flags"] = node_state_flags
    if state_notes:
        detail["state_notes"] = state_notes
    return detail or None


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
    return get_current_group_service_availability(
        sess,
        player_id=resolved_player_id or None,
        group_id=resolved_group_id,
    )


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


def get_current_group_service_states(
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
    service_states = _normalize_group_service_state_map(group.get("service_states"))
    return [dict(service_states[key]) for key in sorted(service_states.keys())]


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
    current_node_state = get_group_node_state(sess, resolved_group_id, current_node_id)
    state_notes = _build_effective_node_state_notes(current_node_id, (current_node_state or {}).get("state_flags"), note_kind="detail_note")
    _set_group_last_inspect_result(
        group,
        {
            **inspect_result,
            "state_notes": state_notes,
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


def build_group_service_result(
    *,
    service: dict[str, Any] | None,
    service_effect: dict[str, Any] | None = None,
    prior_service_state: dict[str, Any] | None = None,
    fully_revealed_node_ids: list[str] | set[str] | None = None,
    source: str = "service",
) -> dict[str, Any] | None:
    resolved_service = dict(service or {})
    if not resolved_service:
        return None
    service_id = str(resolved_service.get("service_id") or resolved_service.get("service_key") or "").strip().lower()
    service_key = str(resolved_service.get("service_key") or service_id).strip().lower()
    service_label = str(resolved_service.get("label") or resolved_service.get("service_label") or service_id).strip()
    node_id = str(resolved_service.get("node_id") or "").strip()
    node_label = str(resolved_service.get("node_label") or node_id).strip()
    if not service_id or not service_label or not node_id or not node_label:
        return None
    prior_state = _normalize_group_service_state(prior_service_state)
    effect = dict(service_effect or {})
    one_shot = bool(effect.get("one_shot") or resolved_service.get("one_shot"))
    if one_shot and prior_state and str(prior_state.get("status") or "").strip().lower() == "completed":
        return _normalize_group_last_service_result(
            {
                "result_id": uuid.uuid4().hex[:12],
                "service_id": service_id,
                "service_key": service_key,
                "service_label": service_label,
                "service_type": resolved_service.get("service_type"),
                "service_kind": resolved_service.get("service_kind"),
                "result_type": "already_used",
                "summary": f"Услуга {service_label} у {node_label} уже использована.",
                "result_summary": "Эта одноразовая услуга уже была использована текущей группой и больше не даёт нового эффекта.",
                "node_id": node_id,
                "node_label": node_label,
                "applied_effects": ["service:already_used"],
                "discovered_notes": [],
                "reveal_applied": False,
                "source": source,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    revealed_set = {
        str(node_ref).strip().lower()
        for node_ref in (fully_revealed_node_ids or [])
        if str(node_ref or "").strip()
    }
    reveal_node_ids = [
        str(node_ref).strip()
        for node_ref in (effect.get("reveal_node_ids") or [])
        if str(node_ref or "").strip()
    ]
    undiscovered_reveal_node_ids = [node_ref for node_ref in reveal_node_ids if node_ref.lower() not in revealed_set]
    discovered_notes = [
        str(note).strip()
        for note in (effect.get("discovered_notes") or [])
        if str(note or "").strip()
    ]
    applied_effects = [
        str(item).strip()
        for item in (effect.get("applied_effects") or [])
        if str(item or "").strip()
    ]
    service_kind = str(effect.get("service_kind") or resolved_service.get("service_kind") or resolved_service.get("service_type") or "service").strip().lower()
    result_type = str(effect.get("result_type") or "").strip().lower()
    if not result_type:
        if service_kind in {"rest", "lodging", "shrine"} or service_key in {"safe_rest", "shrine_aid"}:
            result_type = "lodging_received"
        elif service_kind in {"guidance"} or service_key == "local_guidance":
            result_type = "guidance_received"
        elif service_kind in {"supplies"} or service_key == "resupply":
            result_type = "supplies_secured"
        else:
            result_type = "no_effect"
    summary = str(effect.get("summary") or resolved_service.get("summary") or f"Группа использует услугу {service_label}.").strip()
    result_summary = str(effect.get("result_summary") or resolved_service.get("result_summary") or resolved_service.get("summary") or "").strip()
    reveal_applied = bool(undiscovered_reveal_node_ids)
    has_node_state = any(str(flag or "").strip() for flag in (effect.get("node_state_flags") or []))
    if not result_summary:
        result_summary = summary
    return _normalize_group_last_service_result(
        {
            "result_id": uuid.uuid4().hex[:12],
            "service_id": service_id,
            "service_key": service_key,
            "service_label": service_label,
            "service_type": resolved_service.get("service_type"),
            "service_kind": service_kind,
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "node_id": node_id,
            "node_label": node_label,
            "applied_effects": applied_effects,
            "discovered_notes": discovered_notes,
            "reveal_applied": reveal_applied,
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "service_hints": resolved_service.get("service_hints"),
        }
    )


def _set_group_service_state(
    group: dict[str, Any],
    service_id: str,
    state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized_service_id = str(service_id or "").strip().lower()
    if not normalized_service_id:
        return None
    service_states = _normalize_group_service_state_map(group.get("service_states"))
    normalized_state = _normalize_group_service_state(state)
    if not normalized_state:
        service_states.pop(normalized_service_id, None)
    else:
        service_states[normalized_service_id] = normalized_state
    if service_states:
        group["service_states"] = service_states
    else:
        group.pop("service_states", None)
    return normalized_state


def resolve_group_service(
    sess: Session,
    group_id: str,
    *,
    service_id: str,
    player_id: uuid.UUID | str | None = None,
    source: str = "service",
) -> tuple[dict[str, Any] | None, str | None]:
    normalized_service_id = str(service_id or "").strip().lower()
    if not normalized_service_id:
        return None, "Нужно указать service_id для услуги."
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    groups = _get_group_states(sess)
    group = groups.get(resolved_group_id)
    if not isinstance(group, dict):
        return None, "Группа игрока не найдена."
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    if not current_map_position:
        return None, "Не удалось определить текущую позицию группы."
    interaction_context = _get_current_group_local_interaction_context(sess, resolved_group_id) or {}
    available_services = get_current_group_node_services(sess, player_id=resolved_player_id or None, group_id=resolved_group_id)
    service = next(
        (
            dict(item)
            for item in available_services
            if isinstance(item, dict)
            and (
                str(item.get("service_id") or item.get("service_key") or "").strip().lower() == normalized_service_id
                or str(item.get("service_key") or "").strip().lower() == normalized_service_id
            )
        ),
        None,
    )
    if not service:
        return None, "Эта услуга сейчас недоступна в текущем месте."
    availability_status = str(service.get("availability_status") or service.get("status") or "").strip().lower()
    unavailable_reason = str(service.get("unavailable_reason") or "").strip()
    unlock_hint = str(service.get("unlock_hint") or "").strip()
    if availability_status == "locked":
        return None, unlock_hint or unavailable_reason or "Эта услуга пока заблокирована в текущем месте."
    if availability_status == "unavailable" and str(unavailable_reason).strip().lower() != "already_used":
        return None, unlock_hint or unavailable_reason or "Эта услуга сейчас недоступна в текущем месте."
    if service.get("available") is False and str(service.get("unavailable_reason") or "").strip().lower() == "already_used":
        service_state = (_normalize_group_service_state_map(group.get("service_states"))).get(normalized_service_id)
        result = build_group_service_result(
            service={
                **(get_static_node_service_result(
                    service_id=normalized_service_id,
                    current_map_position=current_map_position,
                    source=source,
                ) or {}),
                **service,
                "node_id": str(current_map_position.get("node_id") or ""),
                "node_label": str(current_map_position.get("label") or current_map_position.get("node_id") or ""),
            },
            service_effect=next(
                (
                    effect
                    for effect in get_static_node_service_effects(
                        current_map_position=current_map_position,
                        state_flags=interaction_context.get("node_state_flags"),
                        group_state_flags=interaction_context.get("group_state_flags"),
                    )
                    if (
                        str(effect.get("service_id") or "").strip().lower() == normalized_service_id
                        or str(effect.get("service_key") or "").strip().lower() == normalized_service_id
                    )
                ),
                None,
            ),
            prior_service_state=service_state,
            source=source,
        )
        if result:
            _set_group_last_service_result(group, result)
            intel_entry = _build_map_intel_entry_from_service_result(result)
            if intel_entry:
                _add_group_map_intel_entry_to_group(group, intel_entry)
            _persist_group_states(sess, groups)
            _sync_group_position_mirrors(sess, group)
            return dict(group), None
        return None, "Эта услуга уже использована текущей группой."
    service_effect = next(
        (
            effect
            for effect in get_static_node_service_effects(
                current_map_position=current_map_position,
                state_flags=interaction_context.get("node_state_flags"),
                group_state_flags=interaction_context.get("group_state_flags"),
            )
            if (
                str(effect.get("service_id") or "").strip().lower() == normalized_service_id
                or str(effect.get("service_key") or "").strip().lower() == normalized_service_id
            )
        ),
        None,
    )
    service_state = (_normalize_group_service_state_map(group.get("service_states"))).get(normalized_service_id)
    group_player_ids = [str(pid).strip() for pid in (group.get("player_ids") or []) if str(pid).strip()]
    fully_revealed_node_ids = [
        node_id
        for node_id in {
            str(node_ref).strip()
            for pid in group_player_ids
            for node_ref in get_player_revealed_node_ids(sess, pid)
            if str(node_ref or "").strip()
        }
        if all(is_player_node_revealed(sess, pid, node_id) for pid in group_player_ids)
    ]
    service_result = build_group_service_result(
        service={
            **(get_static_node_service_result(
                service_id=normalized_service_id,
                current_map_position=current_map_position,
                source=source,
            ) or {}),
            **service,
            "node_id": str(current_map_position.get("node_id") or ""),
            "node_label": str(current_map_position.get("label") or current_map_position.get("node_id") or ""),
        },
        service_effect=service_effect,
        prior_service_state=service_state,
        fully_revealed_node_ids=fully_revealed_node_ids,
        source=source,
    )
    if not service_result:
        return None, "Не удалось подготовить результат услуги."
    if service_result.get("reveal_applied") is True and service_effect:
        for pid in group_player_ids:
            for revealed_node_id in service_effect.get("reveal_node_ids") or []:
                reveal_player_map_node(sess, pid, str(revealed_node_id), source=source)
    if service_effect and service_effect.get("node_state_flags"):
        current_node_id = str(current_map_position.get("node_id") or "").strip().lower()
        node_state_summary = str(service_effect.get("node_state_summary") or service_result.get("result_summary") or "").strip()
        for flag in service_effect.get("node_state_flags") or []:
            add_group_node_state_flag(
                sess,
                resolved_group_id,
                current_node_id,
                state_flag=str(flag),
                summary=node_state_summary,
                source=source,
            )
        groups = _get_group_states(sess)
        group = groups.get(resolved_group_id)
        if not isinstance(group, dict):
            return None, "Группа игрока не найдена."
    _set_group_last_service_result(group, service_result)
    intel_entry = _build_map_intel_entry_from_service_result(service_result)
    if intel_entry:
        _add_group_map_intel_entry_to_group(group, intel_entry)
    _set_group_service_state(
        group,
        normalized_service_id,
        {
            "service_id": normalized_service_id,
            "status": "completed" if bool((service_effect or {}).get("one_shot") or service.get("one_shot")) else "resolved",
            "result_type": service_result.get("result_type"),
            "summary": str(service_result.get("result_summary") or service_result.get("summary") or ""),
            "source": source,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group), None


def execute_current_group_service(
    sess: Session,
    *,
    service_key: str | None = None,
    service_id: str | None = None,
    player_id: uuid.UUID | str | None = None,
    group_id: str | None = None,
    source: str = "manual",
) -> tuple[dict[str, Any] | None, str | None]:
    normalized_service_id = str(service_id or service_key or "").strip().lower()
    if not normalized_service_id:
        return None, "Нужно указать service_id для услуги."
    resolved_group_id = str(group_id or "").strip()
    resolved_player_id = str(player_id or "").strip()
    if not resolved_group_id and resolved_player_id:
        resolved_group_id = str(_get_player_group_id(sess, resolved_player_id) or "").strip()
    if not resolved_group_id:
        return None, "Группа игрока не найдена."
    return resolve_group_service(
        sess,
        resolved_group_id,
        service_id=normalized_service_id,
        player_id=resolved_player_id or None,
        source=source,
    )


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


def _set_group_last_camp_result(
    group: dict[str, Any],
    result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized = _normalize_group_last_camp_result(result)
    if not normalized:
        group.pop("last_camp_result", None)
        return None
    group["last_camp_result"] = normalized
    return normalized


def _set_group_last_scout_result(
    group: dict[str, Any],
    result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized = _normalize_group_last_scout_result(result)
    if not normalized:
        group.pop("last_scout_result", None)
        return None
    group["last_scout_result"] = normalized
    return normalized


def _set_group_last_context_action_result(
    group: dict[str, Any],
    result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized = _normalize_group_last_context_action_result(result)
    if not normalized:
        group.pop("last_context_action_result", None)
        return None
    group["last_context_action_result"] = normalized
    return normalized


def _set_group_context_action_state(
    group: dict[str, Any],
    action_id: str,
    state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized_action_id = str(action_id or "").strip().lower()
    if not normalized_action_id:
        return None
    action_states = _normalize_group_context_action_state_map(group.get("context_action_states"))
    normalized_state = _normalize_group_context_action_state(state)
    if not normalized_state:
        action_states.pop(normalized_action_id, None)
    else:
        action_states[normalized_action_id] = normalized_state
    if action_states:
        group["context_action_states"] = action_states
    else:
        group.pop("context_action_states", None)
    return normalized_state


def build_group_context_action_result(
    *,
    action_effect: dict[str, Any] | None,
    node_context: dict[str, Any] | None = None,
    prior_action_state: dict[str, Any] | None = None,
    route_access_state: dict[str, Any] | None = None,
    source: str = "context_action",
) -> dict[str, Any] | None:
    effect = dict(action_effect or {})
    action_id = str(effect.get("action_id") or "").strip().lower()
    action_label = str(effect.get("label") or action_id).strip()
    if not action_id or not action_label:
        return None
    node_summary = dict((node_context or {}).get("node_summary") or {})
    node_id = str(node_summary.get("node_id") or effect.get("node_id") or "").strip()
    node_label = str(node_summary.get("label") or node_id).strip()
    if not node_id or not node_label:
        return None
    previous = _normalize_group_context_action_state(prior_action_state)
    one_shot = bool(effect.get("one_shot"))
    if one_shot and previous and str(previous.get("status") or "").strip().lower() == "completed":
        return _normalize_group_last_context_action_result(
            {
                "result_id": uuid.uuid4().hex[:12],
                "action_id": action_id,
                "action_label": action_label,
                "result_type": "already_completed",
                "summary": f"Действие {action_label} у {node_label} уже завершено.",
                "result_summary": "Это одноразовое действие уже было выполнено для текущей группы и больше не меняет ситуацию.",
                "node_id": node_id,
                "node_label": node_label,
                "applied_effects": ["context_action:already_completed"],
                "source": source,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    effect_type = str(effect.get("effect_type") or "").strip().lower()
    route_state = _normalize_group_route_access_state(route_access_state)
    applied_effects = [
        str(item).strip()
        for item in (effect.get("applied_effects") or [])
        if str(item or "").strip()
    ]
    discovered_notes = [
        str(note).strip()
        for note in (effect.get("discovered_notes") or [])
        if str(note or "").strip()
    ]
    result_type = str(effect.get("result_type") or "no_effect").strip().lower() or "no_effect"
    summary = str(effect.get("summary") or f"Группа выполняет действие {action_label}.").strip()
    result_summary = str(effect.get("result_summary") or "Действие не даёт заметного изменения.").strip()

    if effect_type == "clear_route":
        if route_state and str(route_state.get("access_state") or "").strip().lower() in {"open", "cleared"}:
            result_type = "no_effect"
            summary = f"Маршрут после действия {action_label} у {node_label} уже остаётся проходимым."
            result_summary = "Проход уже открыт для этой группы, поэтому повторная расчистка не меняет локальное состояние."
            applied_effects = ["route_access:unchanged"]
        else:
            result_type = "route_cleared"
    elif effect_type == "keep_route_blocked":
        result_type = "route_still_blocked"
    elif effect_type == "clue":
        result_type = "local_clue_found"
    elif effect_type == "support":
        result_type = str(effect.get("result_type") or "local_support_applied").strip().lower() or "local_support_applied"
    else:
        result_type = "no_effect"

    if result_type == "local_clue_found" and not discovered_notes:
        detail_hint = str(node_summary.get("detail_summary") or "").strip()
        if detail_hint:
            discovered_notes = [detail_hint]

    return _normalize_group_last_context_action_result(
        {
            "result_id": uuid.uuid4().hex[:12],
            "action_id": action_id,
            "action_label": action_label,
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "node_id": node_id,
            "node_label": node_label,
            "applied_effects": applied_effects + [f"discovered_note:{note[:40]}" for note in discovered_notes],
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def get_current_group_last_context_action_result(
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
    return _normalize_group_last_context_action_result(group.get("last_context_action_result"))


def get_current_group_context_action_states(
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
    action_states = _normalize_group_context_action_state_map(group.get("context_action_states"))
    return [dict(action_states[key]) for key in sorted(action_states.keys())]


def resolve_group_context_action(
    sess: Session,
    group_id: str,
    *,
    action_id: str,
    player_id: uuid.UUID | str | None = None,
    source: str = "context_action",
) -> tuple[dict[str, Any] | None, str | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    normalized_action_id = str(action_id or "").strip().lower()
    group = groups.get(group_key)
    if not group:
        return None, "Группа не найдена."
    if not normalized_action_id:
        return None, "Нужно указать action_id для contextual action."
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    if not current_map_position:
        return None, "Не удалось определить текущую позицию группы."
    context = _get_current_group_local_interaction_context(sess, group_key) or {}
    available_effects = {
        str(effect.get("action_id") or "").strip().lower(): effect
        for effect in get_static_node_context_action_effects(
            current_map_position=current_map_position,
            state_flags=context.get("node_state_flags"),
            group_state_flags=context.get("group_state_flags"),
            region_link_ids=context.get("region_link_ids"),
        )
        if isinstance(effect, dict) and str(effect.get("action_id") or "").strip()
    }
    action_effect = available_effects.get(normalized_action_id)
    if not action_effect:
        return None, "Это contextual действие недоступно в текущем узле."
    available_actions = get_current_group_context_action_availability(
        sess,
        player_id=player_id,
        group_id=group_key,
    )
    action_surface = next(
        (
            dict(item)
            for item in available_actions
            if str(item.get("action_id") or item.get("action_key") or "").strip().lower() == normalized_action_id
        ),
        None,
    )
    if action_surface:
        availability_status = str(action_surface.get("availability_status") or action_surface.get("status") or "").strip().lower()
        unavailable_reason = str(action_surface.get("unavailable_reason") or "").strip()
        unlock_hint = str(action_surface.get("unlock_hint") or "").strip()
        if availability_status == "locked":
            return None, unlock_hint or unavailable_reason or "Это contextual действие пока заблокировано."
        if availability_status == "unavailable":
            return None, unlock_hint or unavailable_reason or "Это contextual действие сейчас недоступно."
    prior_action_state = (_normalize_group_context_action_state_map(group.get("context_action_states"))).get(normalized_action_id)
    route_id = str(action_effect.get("route_id") or "").strip().lower()
    route_access_state = get_effective_group_route_access_state(sess, group_key, route_id=route_id) if route_id else None
    node_context = get_current_group_node_context(sess, player_id=player_id, group_id=group_key)
    result = build_group_context_action_result(
        action_effect=action_effect,
        node_context=node_context,
        prior_action_state=prior_action_state,
        route_access_state=route_access_state,
        source=source,
    )
    if not result:
        return None, "Не удалось подготовить результат contextual действия."
    result_type = str(result.get("result_type") or "").strip().lower()
    if route_id and result_type == "route_cleared":
        set_group_route_access_state(
            sess,
            group_key,
            route_id,
            access_state="cleared",
            summary="Маршрут открыт локальным действием группы.",
            source=source,
        )
        groups = _get_group_states(sess)
        group = groups.get(group_key)
    elif route_id and result_type == "route_still_blocked":
        set_group_route_access_state(
            sess,
            group_key,
            route_id,
            access_state="blocked",
            summary="Локальное действие подтверждает, что маршрут всё ещё заблокирован.",
            block_reason=str(action_effect.get("block_reason") or "context_action_blocked").strip() or "context_action_blocked",
            source=source,
        )
        groups = _get_group_states(sess)
        group = groups.get(group_key)
    node_state_flags = [
        str(flag).strip().lower()
        for flag in (action_effect.get("node_state_flags") or [])
        if str(flag or "").strip()
    ]
    if group and node_state_flags:
        node_state_summary = str(action_effect.get("node_state_summary") or result.get("result_summary") or result.get("summary") or "").strip()
        current_node_id = str((_normalize_map_position(group.get("current_map_position")) or {}).get("node_id") or "").strip().lower()
        for node_state_flag in node_state_flags:
            add_group_node_state_flag(
                sess,
                group_key,
                current_node_id,
                state_flag=node_state_flag,
                summary=node_state_summary,
                source=source,
            )
        groups = _get_group_states(sess)
        group = groups.get(group_key)
    reveal_node_ids = [
        str(node_ref).strip()
        for node_ref in (action_effect.get("reveal_node_ids") or [])
        if str(node_ref or "").strip()
    ]
    if group and reveal_node_ids:
        group_player_ids = [
            str(pid).strip()
            for pid in (group.get("player_ids") or [])
            if str(pid or "").strip()
        ]
        for pid in group_player_ids:
            for revealed_node_id in reveal_node_ids:
                reveal_player_map_node(sess, pid, revealed_node_id, source=source)
        groups = _get_group_states(sess)
        group = groups.get(group_key)
    for route_update in (action_effect.get("route_access_updates") or []):
        if not isinstance(route_update, dict):
            continue
        route_id = str(route_update.get("route_id") or "").strip().lower()
        access_state = str(route_update.get("access_state") or "").strip().lower()
        if not route_id or access_state not in {"open", "cleared", "blocked"}:
            continue
        set_group_route_access_state(
            sess,
            group_key,
            route_id,
            access_state=access_state,
            summary=str(route_update.get("summary") or result.get("result_summary") or result.get("summary") or "").strip(),
            block_reason=str(route_update.get("block_reason") or "").strip() or None,
            source=source,
        )
        groups = _get_group_states(sess)
        group = groups.get(group_key)
    if not group:
        return None, "Группа не найдена."
    _set_group_last_context_action_result(group, result)
    intel_entry = _build_map_intel_entry_from_context_action_result(result, action_effect=action_effect)
    if intel_entry:
        _add_group_map_intel_entry_to_group(group, intel_entry)
    _set_group_context_action_state(
        group,
        normalized_action_id,
        {
            "action_id": normalized_action_id,
            "status": "completed" if bool(action_effect.get("one_shot")) else "resolved",
            "result_type": result_type,
            "summary": str(result.get("result_summary") or result.get("summary") or ""),
            "source": source,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group), None


def build_group_scout_result(
    *,
    node_context: dict[str, Any] | None = None,
    node_detail: dict[str, Any] | None = None,
    scout_discoveries: list[dict[str, Any]] | None = None,
    fully_revealed_node_ids: list[str] | set[str] | None = None,
    source: str = "scout",
) -> dict[str, Any] | None:
    node_summary = dict((node_context or {}).get("node_summary") or {})
    node_id = str(node_summary.get("node_id") or "").strip()
    node_label = str(node_summary.get("label") or node_id).strip()
    if not node_id or not node_label:
        return None
    revealed_set = {
        str(node_ref).strip().lower()
        for node_ref in (fully_revealed_node_ids or [])
        if str(node_ref or "").strip()
    }
    discoveries = [dict(item) for item in (scout_discoveries or []) if isinstance(item, dict)]
    next_discovery = next(
        (
            item
            for item in discoveries
            if any(str(node_ref).strip().lower() not in revealed_set for node_ref in (item.get("discovered_node_ids") or []))
        ),
        None,
    )
    if next_discovery:
        discovered_node_ids = [
            str(node_ref).strip()
            for node_ref in (next_discovery.get("discovered_node_ids") or [])
            if str(node_ref or "").strip()
        ]
        discovered_route_ids = [
            str(route_id).strip()
            for route_id in (next_discovery.get("discovered_route_ids") or [])
            if str(route_id or "").strip()
        ]
        discovered_notes = [
            str(note).strip()
            for note in (next_discovery.get("discovered_notes") or [])
            if str(note or "").strip()
        ]
        result_type = str(next_discovery.get("result_type") or "route_revealed").strip().lower()
        result_summary = "Разведка открывает новый ориентир на текущем участке пути."
        if result_type == "hidden_path_revealed":
            result_summary = "Разведка выводит группу на скрытый проход, который раньше не читался с дороги."
        elif result_type == "landmark_revealed":
            result_summary = "Разведка замечает новый ориентир рядом с текущим узлом и делает подход к нему видимым."
        elif result_type == "route_revealed":
            result_summary = "Разведка проясняет соседний маршрут и добавляет новый понятный выход из текущей точки."
        return _normalize_group_last_scout_result(
            {
                "result_id": uuid.uuid4().hex[:12],
                "result_type": result_type,
                "summary": f"Разведка у {node_label} приносит новый маршрутный результат.",
                "result_summary": result_summary,
                "node_id": node_id,
                "node_label": node_label,
                "discovery_scope": str(next_discovery.get("discovery_scope") or "local_area"),
                "discovered_node_ids": discovered_node_ids,
                "discovered_route_ids": discovered_route_ids,
                "discovered_notes": discovered_notes,
                "reveal_applied": True,
                "source": source,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    if discoveries:
        return _normalize_group_last_scout_result(
            {
                "result_id": uuid.uuid4().hex[:12],
                "result_type": "no_new_findings",
                "summary": f"Разведка у {node_label} не приносит новых открытий.",
                "result_summary": "Ближайшие авторские ориентиры уже раскрыты для этой группы, и новых находок сейчас нет.",
                "node_id": node_id,
                "node_label": node_label,
                "discovery_scope": "none",
                "discovered_node_ids": [],
                "discovered_route_ids": [],
                "discovered_notes": [],
                "reveal_applied": False,
                "source": source,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    detail = dict(node_detail or {})
    clue_note = str(detail.get("travel_note") or detail.get("inspect_summary") or detail.get("danger_note") or "").strip()
    if clue_note:
        return _normalize_group_last_scout_result(
            {
                "result_id": uuid.uuid4().hex[:12],
                "result_type": "local_clue_found",
                "summary": f"Разведка у {node_label} даёт локальную зацепку.",
                "result_summary": "Нового выхода разведка не открывает, но место даёт полезную локальную подсказку.",
                "node_id": node_id,
                "node_label": node_label,
                "discovery_scope": "local_area",
                "discovered_node_ids": [],
                "discovered_route_ids": [],
                "discovered_notes": [clue_note],
                "reveal_applied": False,
                "source": source,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return _normalize_group_last_scout_result(
        {
            "result_id": uuid.uuid4().hex[:12],
            "result_type": "no_new_findings",
            "summary": f"Разведка у {node_label} не приносит новых открытий.",
            "result_summary": "На этой точке разведка не даёт нового маршрута, ориентира или локальной зацепки.",
            "node_id": node_id,
            "node_label": node_label,
            "discovery_scope": "none",
            "discovered_node_ids": [],
            "discovered_route_ids": [],
            "discovered_notes": [],
            "reveal_applied": False,
            "source": source,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def build_group_camp_result(
    camp_state: dict[str, Any] | None,
    *,
    node_context: dict[str, Any] | None = None,
    available_services: list[dict[str, Any]] | None = None,
    travel_event: dict[str, Any] | None = None,
    travel_state: dict[str, Any] | None = None,
    source: str = "camp",
) -> dict[str, Any] | None:
    normalized_camp_state = _normalize_group_camp_state(camp_state)
    if not normalized_camp_state:
        return None
    node_summary = dict((node_context or {}).get("node_summary") or {})
    node_id = str(node_summary.get("node_id") or "").strip()
    node_label = str(node_summary.get("label") or node_id).strip()
    if not node_id or not node_label:
        return None
    zone_band = str(node_summary.get("zone_band") or "").strip().lower()
    settlement_kind = str(node_summary.get("settlement_kind") or "").strip().lower()
    poi_kind = str(node_summary.get("poi_kind") or "").strip().lower()
    safe_rest_hint = bool(node_summary.get("safe_rest_hint"))
    normalized_travel_event = _normalize_group_travel_event(travel_event)
    normalized_travel_state = _normalize_group_travel_state(travel_state)
    services = available_services if isinstance(available_services, list) else []
    has_safe_rest_service = any(
        isinstance(item, dict) and str(item.get("service_key") or "").strip().lower() == "safe_rest"
        for item in services
    )
    has_blocking_event = bool(
        normalized_travel_event
        and normalized_travel_event.get("active") is True
        and str(normalized_travel_event.get("event_key") or "").strip().lower() == "blocked_path"
    )
    blocked_route = bool(
        normalized_travel_state
        and normalized_travel_state.get("active") is True
        and normalized_travel_state.get("paused") is True
        and str(normalized_travel_state.get("pause_reason") or "").strip().lower() == "route_blocked"
    )

    result_type = "uneasy_rest"
    rest_quality = "uneasy"
    risk_band = "medium"
    summary = f"Группа устраивает лагерь у {node_label}."
    result_summary = "Стоянка даёт передышку, но без ощущения полной безопасности."
    applied_effects = ["rest_quality:uneasy", "safety_note:open_camp"]

    if has_blocking_event or blocked_route:
        result_type = "interrupted_rest"
        rest_quality = "interrupted"
        risk_band = "high"
        summary = f"Лагерь у {node_label} постоянно сбивается дорожной преградой."
        result_summary = "Группа получает только вынужденную паузу: путь остаётся помехой и отдых выходит рваным."
        applied_effects = ["rest_quality:interrupted", "interruption_note:blocked_route"]
    elif zone_band == "danger":
        result_type = "interrupted_rest"
        rest_quality = "interrupted"
        risk_band = "high"
        summary = f"Стоянка у {node_label} слишком опасна для нормального отдыха."
        result_summary = "Группа не может по-настоящему отдохнуть: место держит всех в напряжении и вынуждает сторожить лагерь."
        applied_effects = ["rest_quality:interrupted", "safety_note:danger_zone"]
    elif has_safe_rest_service or poi_kind in {"chapel", "watchtower", "inn"}:
        result_type = "sheltered_rest"
        rest_quality = "sheltered"
        risk_band = "low" if safe_rest_hint or zone_band == "safe" else "medium"
        summary = f"У {node_label} находится укрытие для передышки."
        result_summary = "Группа устраивается в месте с укрытием и получает спокойный отдых без тяжёлой дорожной суеты."
        applied_effects = ["rest_quality:sheltered", "safety_note:shelter_found"]
    elif safe_rest_hint or settlement_kind in {"town", "village", "hamlet"}:
        result_type = "safe_rest"
        rest_quality = "restful"
        risk_band = "low"
        summary = f"У {node_label} удаётся устроить спокойный отдых."
        result_summary = "Текущее место поддерживает безопасную стоянку, и группа получает спокойный отдых без немедленного риска."
        applied_effects = ["rest_quality:restful", "safety_note:safe_node"]
    elif settlement_kind == "roadside":
        result_type = "roadside_pause"
        rest_quality = "brief"
        risk_band = "medium" if zone_band == "border" else "low"
        summary = f"У {node_label} выходит только короткий дорожный привал."
        result_summary = "Место годится для краткой передышки, но не для полноценной стоянки."
        applied_effects = ["rest_quality:brief", "safety_note:roadside_pause"]
    elif zone_band == "border" or settlement_kind in {"wilds", "ruins"}:
        result_type = "uneasy_rest"
        rest_quality = "uneasy"
        risk_band = "medium"
        summary = f"Лагерь у {node_label} остаётся настороженным."
        result_summary = "Группа отдыхает вполглаза: пограничная или дикая местность не даёт расслабиться."
        applied_effects = ["rest_quality:uneasy", "safety_note:border_watch"]

    return _normalize_group_last_camp_result(
        {
            "result_id": uuid.uuid4().hex[:12],
            "result_type": result_type,
            "summary": summary,
            "result_summary": result_summary,
            "node_id": node_id,
            "node_label": node_label,
            "rest_quality": rest_quality,
            "risk_band": risk_band,
            "source": source,
            "applied_effects": applied_effects,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    )


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
    route_id = str(route_snapshot.get("route_id") or "").strip().lower()
    target_node_id = str(route_snapshot.get("target_node_id") or "").strip()
    outcome_type = str(normalized_outcome.get("outcome_type") or "").strip().lower()
    if route_id and outcome_type == "obstacle_cleared":
        access_map = _normalize_group_route_access_state_map(group.get("route_access_states"))
        access_map[route_id] = _normalize_group_route_access_state(
            {
                "route_id": route_id,
                "access_state": "cleared",
                "summary": "Группа расчистила маршрут и может снова пройти этим путём.",
                "source": source,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ) or access_map.get(route_id) or {}
        group["route_access_states"] = access_map
    elif route_id and outcome_type == "route_still_blocked":
        access_map = _normalize_group_route_access_state_map(group.get("route_access_states"))
        access_map[route_id] = _normalize_group_route_access_state(
            {
                "route_id": route_id,
                "access_state": "blocked",
                "summary": "Маршрут остаётся заблокированным после попытки разобраться с преградой.",
                "block_reason": "route_blocked",
                "source": source,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ) or access_map.get(route_id) or {}
        group["route_access_states"] = access_map
    if resolved_player_id and target_node_id and get_static_node(target_node_id):
        if outcome_type in {"route_hint", "guidance_note"}:
            grant_player_map_knowledge(sess, resolved_player_id, target_node_id, knowledge_kind="known", source=source)
        if outcome_type == "route_hint":
            reveal_player_map_node(sess, resolved_player_id, target_node_id, source=source)
    intel_entry = _build_map_intel_entry_from_travel_event_outcome(normalized_outcome)
    if intel_entry:
        _add_group_map_intel_entry_to_group(group, intel_entry)
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


def get_current_group_last_camp_result(
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
    return _normalize_group_last_camp_result(group.get("last_camp_result"))


def get_current_group_last_scout_result(
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
    return _normalize_group_last_scout_result(group.get("last_scout_result"))


def resolve_group_scout(
    sess: Session,
    group_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "scout",
) -> tuple[dict[str, Any] | None, str | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None, "Группа не найдена."
    group_player_ids = [str(pid).strip() for pid in (group.get("player_ids") or []) if str(pid).strip()]
    if not group_player_ids:
        return None, "У группы нет участников для разведки."
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    node_context = get_current_group_node_context(sess, player_id=player_id, group_id=group_key)
    node_detail = get_current_group_node_detail(sess, player_id=player_id, group_id=group_key)
    scout_discoveries = get_static_node_scout_discoveries(current_map_position=current_map_position)
    fully_revealed_node_ids = [
        node_id
        for node_id in {
            str(node_ref).strip()
            for pid in group_player_ids
            for node_ref in get_player_revealed_node_ids(sess, pid)
            if str(node_ref or "").strip()
        }
        if all(is_player_node_revealed(sess, pid, node_id) for pid in group_player_ids)
    ]
    result = build_group_scout_result(
        node_context=node_context,
        node_detail=node_detail,
        scout_discoveries=scout_discoveries,
        fully_revealed_node_ids=fully_revealed_node_ids,
        source=source,
    )
    if not result:
        return None, "Не удалось подготовить результат разведки."
    if result.get("reveal_applied") is True:
        for pid in group_player_ids:
            for discovered_node_id in result.get("discovered_node_ids") or []:
                reveal_player_map_node(sess, pid, str(discovered_node_id), source=source)
    _set_group_last_scout_result(group, result)
    intel_entry = _build_map_intel_entry_from_scout_result(result)
    if intel_entry:
        _add_group_map_intel_entry_to_group(group, intel_entry)
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group), None


def resolve_group_camp(
    sess: Session,
    group_id: str,
    *,
    player_id: uuid.UUID | str | None = None,
    source: str = "camp",
) -> tuple[dict[str, Any] | None, str | None]:
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None, "Группа не найдена."
    camp_state = _group_camp_summary(group)
    if not camp_state:
        return None, "У группы нет активного лагеря."
    resolved_player_id = str(player_id or "").strip()
    result = build_group_camp_result(
        camp_state,
        node_context=get_current_group_node_context(sess, player_id=resolved_player_id or None, group_id=group_key),
        available_services=get_current_group_node_services(sess, player_id=resolved_player_id or None, group_id=group_key),
        travel_event=_group_travel_event_summary(group),
        travel_state=_group_travel_state_summary(group),
        source=source,
    )
    if not result:
        return None, "Не удалось подготовить результат лагеря."
    _set_group_last_camp_result(group, result)
    _apply_group_activity_state(group, status="idle")
    _persist_group_states(sess, groups)
    _sync_group_position_mirrors(sess, group)
    return dict(group), None


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
            if isinstance(item, dict)
            and str(item.get("action_id") or item.get("action_key") or "").strip().lower() == normalized_action_key
        ),
        None,
    )
    if not available_action:
        return None, "Это contextual действие сейчас недоступно."
    if str(available_action.get("action_type") or "action").strip().lower() != "action":
        return None, "Это contextual действие доступно только как подсказка."
    availability_status = str(available_action.get("availability_status") or available_action.get("status") or "").strip().lower()
    if availability_status == "locked":
        return None, str(available_action.get("unlock_hint") or available_action.get("unavailable_reason") or "Это contextual действие пока заблокировано.")
    if availability_status == "unavailable":
        return None, str(available_action.get("unlock_hint") or available_action.get("unavailable_reason") or "Это contextual действие сейчас недоступно.")

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

    return resolve_group_context_action(
        sess,
        resolved_group_id,
        action_id=normalized_action_key,
        player_id=resolved_player_id or None,
        source=source,
    )


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


def _group_last_camp_result_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_last_camp_result(group.get("last_camp_result"))


def _group_route_access_states_summary(group: dict[str, Any]) -> list[dict[str, Any]] | None:
    access_map = _normalize_group_route_access_state_map(group.get("route_access_states"))
    if not access_map:
        return None
    return [dict(access_map[key]) for key in sorted(access_map.keys())]


def _group_last_scout_result_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_last_scout_result(group.get("last_scout_result"))


def _group_last_context_action_result_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_last_context_action_result(group.get("last_context_action_result"))


def _group_last_node_entry_result_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_last_node_entry_result(group.get("last_node_entry_result"))


def _group_node_entry_states_summary(group: dict[str, Any]) -> list[dict[str, Any]] | None:
    state_map = _normalize_group_node_entry_state_map(group.get("node_entry_states"))
    if not state_map:
        return None
    return [dict(state_map[key]) for key in sorted(state_map.keys())]


def _group_last_destination_event_result_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_last_destination_event_result(group.get("last_destination_event_result"))


def _group_destination_event_states_summary(group: dict[str, Any]) -> list[dict[str, Any]] | None:
    state_map = _normalize_group_destination_event_state_map(group.get("destination_event_states"))
    if not state_map:
        return None
    return [dict(state_map[key]) for key in sorted(state_map.keys())]


def _group_active_journey_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_active_journey(group.get("active_journey"))


def _group_last_journey_result_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_last_journey_result(group.get("last_journey_result"))


def _group_last_region_entry_result_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_last_region_entry_result(group.get("last_region_entry_result"))


def _group_discovered_region_count(group: dict[str, Any]) -> int:
    return len(_normalize_group_discovered_region_map(group.get("discovered_regions")))


def _group_crossed_gateway_count(group: dict[str, Any]) -> int:
    return len(_normalize_group_gateway_traversal_state_map(group.get("gateway_traversal_states")))


def _group_discovered_region_link_count(group: dict[str, Any]) -> int:
    return len(_normalize_group_region_link_state_map(group.get("region_link_states")))


def _group_context_action_states_summary(group: dict[str, Any]) -> list[dict[str, Any]] | None:
    action_states = _normalize_group_context_action_state_map(group.get("context_action_states"))
    if not action_states:
        return None
    return [dict(action_states[key]) for key in sorted(action_states.keys())]


def _group_node_states_summary(group: dict[str, Any]) -> list[dict[str, Any]] | None:
    node_states = _normalize_group_node_state_map(group.get("node_states"))
    if not node_states:
        return None
    return [dict(node_states[key]) for key in sorted(node_states.keys())]


def _group_service_states_summary(group: dict[str, Any]) -> list[dict[str, Any]] | None:
    service_states = _normalize_group_service_state_map(group.get("service_states"))
    if not service_states:
        return None
    return [dict(service_states[key]) for key in sorted(service_states.keys())]


def _group_map_intel_count(group: dict[str, Any]) -> int:
    return len(_normalize_group_map_intel_entries(group.get("map_intel_entries")))


def _group_visited_node_count(group: dict[str, Any]) -> int:
    return len(_normalize_group_node_visit_state_map(group.get("node_visit_states")))


def _group_traversed_route_count(group: dict[str, Any]) -> int:
    return len(_normalize_group_route_traversal_state_map(group.get("route_traversal_states")))


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
    last_camp_result = _normalize_group_last_camp_result(raw.get("last_camp_result"))
    if last_camp_result:
        normalized["last_camp_result"] = last_camp_result
    route_access_states = _normalize_group_route_access_state_map(raw.get("route_access_states"))
    if route_access_states:
        normalized["route_access_states"] = route_access_states
    last_scout_result = _normalize_group_last_scout_result(raw.get("last_scout_result"))
    if last_scout_result:
        normalized["last_scout_result"] = last_scout_result
    last_context_action_result = _normalize_group_last_context_action_result(raw.get("last_context_action_result"))
    if last_context_action_result:
        normalized["last_context_action_result"] = last_context_action_result
    context_action_states = _normalize_group_context_action_state_map(raw.get("context_action_states"))
    if context_action_states:
        normalized["context_action_states"] = context_action_states
    node_states = _normalize_group_node_state_map(raw.get("node_states"))
    if node_states:
        normalized["node_states"] = node_states
    last_node_entry_result = _normalize_group_last_node_entry_result(raw.get("last_node_entry_result"))
    if last_node_entry_result:
        normalized["last_node_entry_result"] = last_node_entry_result
    node_entry_states = _normalize_group_node_entry_state_map(raw.get("node_entry_states"))
    if node_entry_states:
        normalized["node_entry_states"] = node_entry_states
    last_destination_event_result = _normalize_group_last_destination_event_result(raw.get("last_destination_event_result"))
    if last_destination_event_result:
        normalized["last_destination_event_result"] = last_destination_event_result
    destination_event_states = _normalize_group_destination_event_state_map(raw.get("destination_event_states"))
    if destination_event_states:
        normalized["destination_event_states"] = destination_event_states
    last_region_transition_result = _normalize_group_last_region_transition_result(raw.get("last_region_transition_result"))
    if last_region_transition_result:
        normalized["last_region_transition_result"] = last_region_transition_result
    region_transition_state = _normalize_group_region_transition_state(raw.get("region_transition_state"))
    if region_transition_state:
        normalized["region_transition_state"] = region_transition_state
    current_region_state = _normalize_group_current_region_state(raw.get("current_region_state"))
    if current_region_state:
        normalized["current_region_state"] = current_region_state
    discovered_regions = _normalize_group_discovered_region_map(raw.get("discovered_regions"))
    if discovered_regions:
        normalized["discovered_regions"] = discovered_regions
    last_region_entry_result = _normalize_group_last_region_entry_result(raw.get("last_region_entry_result"))
    if last_region_entry_result:
        normalized["last_region_entry_result"] = last_region_entry_result
    last_region_onboarding_result = _normalize_group_last_region_onboarding_result(raw.get("last_region_onboarding_result"))
    if last_region_onboarding_result:
        normalized["last_region_onboarding_result"] = last_region_onboarding_result
    region_onboarding_states = _normalize_group_region_onboarding_state_map(raw.get("region_onboarding_states"))
    if region_onboarding_states:
        normalized["region_onboarding_states"] = region_onboarding_states
    active_journey = _normalize_group_active_journey(raw.get("active_journey"))
    if active_journey:
        normalized["active_journey"] = active_journey
    last_journey_result = _normalize_group_last_journey_result(raw.get("last_journey_result"))
    if last_journey_result:
        normalized["last_journey_result"] = last_journey_result
    active_region_pursuit = _normalize_group_active_region_pursuit(raw.get("active_region_pursuit"))
    if active_region_pursuit:
        normalized["active_region_pursuit"] = active_region_pursuit
    last_region_pursuit_result = _normalize_group_last_region_pursuit_result(raw.get("last_region_pursuit_result"))
    if last_region_pursuit_result:
        normalized["last_region_pursuit_result"] = last_region_pursuit_result
    last_region_pursuit_step_result = _normalize_group_last_region_pursuit_step_result(raw.get("last_region_pursuit_step_result"))
    if last_region_pursuit_step_result:
        normalized["last_region_pursuit_step_result"] = last_region_pursuit_step_result
    gateway_traversal_states = _normalize_group_gateway_traversal_state_map(raw.get("gateway_traversal_states"))
    if gateway_traversal_states:
        normalized["gateway_traversal_states"] = gateway_traversal_states
    region_link_states = _normalize_group_region_link_state_map(raw.get("region_link_states"))
    if region_link_states:
        normalized["region_link_states"] = region_link_states
    last_region_link_result = _normalize_group_last_region_link_result(raw.get("last_region_link_result"))
    if last_region_link_result:
        normalized["last_region_link_result"] = last_region_link_result
    last_arrival_result = _normalize_group_last_arrival_result(raw.get("last_arrival_result"))
    if last_arrival_result:
        normalized["last_arrival_result"] = last_arrival_result
    node_visit_states = _normalize_group_node_visit_state_map(raw.get("node_visit_states"))
    if node_visit_states:
        normalized["node_visit_states"] = node_visit_states
    route_traversal_states = _normalize_group_route_traversal_state_map(raw.get("route_traversal_states"))
    if route_traversal_states:
        normalized["route_traversal_states"] = route_traversal_states
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
    service_states = _normalize_group_service_state_map(raw.get("service_states"))
    if service_states:
        normalized["service_states"] = service_states
    map_intel_entries = _normalize_group_map_intel_entries(raw.get("map_intel_entries"))
    if map_intel_entries:
        normalized["map_intel_entries"] = map_intel_entries
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
    groups = _get_group_states(sess)
    group_key = str(group_id or "").strip()
    group = groups.get(group_key)
    if not group:
        return None
    current_position = _normalize_map_position(group.get("current_map_position"))
    raw_route = dict(route_summary or {}) if isinstance(route_summary, dict) else None
    if isinstance(raw_route, dict) and not raw_route.get("route_id"):
        raw_route["route_id"] = build_static_route_id(
            (current_position or {}).get("node_id"),
            raw_route.get("target_node_id") or ((raw_route.get("target_node") or {}).get("node_id")),
            raw_route.get("action_kind"),
        )
    route = _normalize_group_route_summary(raw_route)
    if not route or route.get("allowed") is not True:
        return None
    target_node = route.get("target_node")
    if not current_position or not isinstance(target_node, dict):
        return None
    blocked_error = validate_group_route_accessibility(sess, group_key, route)
    if blocked_error:
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
    route_id = str((route_summary or {}).get("route_id") or "").strip().lower()
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
    _apply_group_arrival_pipeline(
        sess,
        group_key,
        next_map_position=next_map_position,
        route_summary=route_summary,
        route_id=route_id,
        player_ids=[str(player_id)] if player_id else [],
        source=source,
    )
    refreshed_group = _get_group_states(sess).get(group_key)
    return dict(refreshed_group) if isinstance(refreshed_group, dict) else dict(group)


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
    route_id = str((route_summary or {}).get("route_id") or "").strip().lower()
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
    _apply_group_arrival_pipeline(
        sess,
        group_key,
        next_map_position=next_map_position,
        route_summary=route_summary,
        route_id=route_id,
        player_ids=[str(player_id)] if player_id else [],
        source=source,
    )
    refreshed_group = _get_group_states(sess).get(group_key)
    return dict(refreshed_group) if isinstance(refreshed_group, dict) else dict(group)


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
