import uuid
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
    get_static_node_service_effects,
    get_static_node_state_overlays,
    get_static_node_scout_discoveries,
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
    if result_type not in {"route_cleared", "route_still_blocked", "local_clue_found", "no_effect", "already_completed"}:
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
    if result_type and result_type not in {"route_cleared", "route_still_blocked", "local_clue_found", "no_effect", "already_completed"}:
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
    current_context = get_current_group_node_context(sess, group_id=group_key) or {}
    current_services = get_current_group_node_services(sess, group_id=group_key)
    has_active_journey = journey is not None

    def _add(lead: dict[str, Any] | None) -> None:
        normalized = _normalize_group_exploration_lead(lead)
        if not normalized:
            return
        dedupe_key = f"{normalized['lead_type']}|{normalized['source_kind']}|{normalized['source_ref']}|{normalized['target_node_id']}|{normalized['route_id']}"
        if dedupe_key in seen_keys:
            return
        seen_keys.add(dedupe_key)
        leads.append(normalized)

    if journey:
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

    for service in current_services:
        if bool(service.get("available")) is not True:
            continue
        service_id = str(service.get("service_id") or "").strip().lower()
        service_label = str(service.get("label") or service_id).strip()
        _add(
            build_group_exploration_lead(
                lead_id=f"service:{service_id}",
                lead_type="local_opportunity",
                priority_band="low",
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
                tags=["local", "service", str(service.get("service_kind") or "service")],
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
                priority_band="low",
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
                tags=["local", "action", action_kind],
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
    contextual_actions = get_current_node_context_actions(current_map_position=current_map_position)
    action_states = _normalize_group_context_action_state_map(group.get("context_action_states"))
    authored_effects = {
        str(effect.get("action_id") or "").strip().lower(): effect
        for effect in get_static_node_context_action_effects(current_map_position=current_map_position)
        if isinstance(effect, dict) and str(effect.get("action_id") or "").strip()
    }
    annotated_actions: list[dict[str, Any]] = []
    for action in contextual_actions:
        if not isinstance(action, dict):
            continue
        annotated = dict(action)
        action_id = str(annotated.get("action_id") or annotated.get("action_key") or "").strip().lower()
        state = action_states.get(action_id)
        effect = authored_effects.get(action_id)
        if action_id:
            annotated["action_id"] = action_id
        if effect:
            annotated["source"] = str(effect.get("source") or annotated.get("source") or "registry")
            annotated["one_shot"] = bool(effect.get("one_shot"))
        status = "available"
        if state and str(state.get("status") or "").strip().lower() == "completed":
            status = "completed"
        annotated["status"] = status
        annotated["available"] = status == "available" and str(annotated.get("action_type") or "action").strip().lower() == "action"
        annotated["exhausted"] = status == "completed"
        annotated_actions.append(annotated)
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
                    "status": "available",
                    "available": True,
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
                    "status": "available",
                    "available": True,
                    "exhausted": False,
                },
            )
    payload = {
        "node_summary": node_context,
        "contextual_actions": annotated_actions,
        "available_services": get_current_group_node_services(sess, player_id=resolved_player_id or None, group_id=resolved_group_id),
        "service_actions": (
            [{"action_key": "use_service", "label": "Воспользоваться услугой", "action_type": "action"}]
            if get_current_group_node_services(sess, player_id=resolved_player_id or None, group_id=resolved_group_id)
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
    if source_kind not in {"scout", "service", "context_action", "travel_event"}:
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
    current_map_position = _normalize_map_position(group.get("current_map_position"))
    if not current_map_position:
        return []
    services = get_static_node_services(current_map_position=current_map_position)
    service_states = _normalize_group_service_state_map(group.get("service_states"))
    annotated: list[dict[str, Any]] = []
    for service in services:
        if not isinstance(service, dict):
            continue
        annotated_service = dict(service)
        service_id = str(annotated_service.get("service_id") or annotated_service.get("service_key") or "").strip().lower()
        state = service_states.get(service_id)
        status = "available"
        available = True
        unavailable_reason = None
        if state and str(state.get("status") or "").strip().lower() == "completed":
            status = "completed"
            available = False
            unavailable_reason = "already_used"
        elif state and str(state.get("status") or "").strip().lower() == "resolved" and bool(annotated_service.get("one_shot")):
            status = "resolved"
        annotated_service["service_id"] = service_id or annotated_service.get("service_id") or annotated_service.get("service_key")
        annotated_service["status"] = status
        annotated_service["available"] = available
        if unavailable_reason:
            annotated_service["unavailable_reason"] = unavailable_reason
        annotated.append(annotated_service)
    return annotated


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
                    for effect in get_static_node_service_effects(current_map_position=current_map_position)
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
            for effect in get_static_node_service_effects(current_map_position=current_map_position)
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
    available_effects = {
        str(effect.get("action_id") or "").strip().lower(): effect
        for effect in get_static_node_context_action_effects(current_map_position=current_map_position)
        if isinstance(effect, dict) and str(effect.get("action_id") or "").strip()
    }
    action_effect = available_effects.get(normalized_action_id)
    if not action_effect:
        return None, "Это contextual действие недоступно в текущем узле."
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


def _group_active_journey_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_active_journey(group.get("active_journey"))


def _group_last_journey_result_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_last_journey_result(group.get("last_journey_result"))


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
    active_journey = _normalize_group_active_journey(raw.get("active_journey"))
    if active_journey:
        normalized["active_journey"] = active_journey
    last_journey_result = _normalize_group_last_journey_result(raw.get("last_journey_result"))
    if last_journey_result:
        normalized["last_journey_result"] = last_journey_result
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
    if route_id:
        record_group_route_traversal(
            sess,
            group_key,
            route_id,
            summary=f"Группа проходит маршрутом к {str(next_map_position.get('label') or target_node_id or 'цели')}.",
            traversed_at=datetime.now(timezone.utc).isoformat(),
        )
    if target_node_id:
        record_group_node_visit(
            sess,
            group_key,
            target_node_id,
            node_label=str(next_map_position.get("label") or target_node_id),
            result_type="landmark_arrival" if str(next_map_position.get("node_type") or "").strip().lower() in {"landmark", "interior_entry"} else "first_arrival",
            summary=f"Группа достигает {str(next_map_position.get('label') or target_node_id)}.",
            visited_at=datetime.now(timezone.utc).isoformat(),
        )
        resolve_group_arrival(
            sess,
            group_key,
            current_map_position=next_map_position,
            route_summary=route_summary,
            source=source,
        )
    if player_id and target_node_id and get_static_node(target_node_id):
        maybe_mark_player_node_visited(sess, player_id, target_node_id, source=source)
        maybe_reveal_nearby_static_nodes(sess, player_id, next_map_position, source=source)
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
    if route_id:
        record_group_route_traversal(
            sess,
            group_key,
            route_id,
            summary=f"Группа проходит маршрутом к {str(next_map_position.get('label') or target_node_id or 'цели')}.",
            traversed_at=datetime.now(timezone.utc).isoformat(),
        )
    if target_node_id:
        record_group_node_visit(
            sess,
            group_key,
            target_node_id,
            node_label=str(next_map_position.get("label") or target_node_id),
            result_type="landmark_arrival" if str(next_map_position.get("node_type") or "").strip().lower() in {"landmark", "interior_entry"} else "first_arrival",
            summary=f"Группа достигает {str(next_map_position.get('label') or target_node_id)}.",
            visited_at=datetime.now(timezone.utc).isoformat(),
        )
        resolve_group_arrival(
            sess,
            group_key,
            current_map_position=next_map_position,
            route_summary=route_summary,
            source=source,
        )
    if player_id and target_node_id and get_static_node(target_node_id):
        maybe_mark_player_node_visited(sess, player_id, target_node_id, source=source)
        maybe_reveal_nearby_static_nodes(sess, player_id, next_map_position, source=source)
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
