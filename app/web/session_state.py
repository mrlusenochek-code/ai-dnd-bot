import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Session
from app.web.utils import as_int


DEFAULT_GROUP_ID = "main"


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
    m[str(player_id)] = datetime.utcnow().isoformat()
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
    if status == "moving":
        return "moving_intent"
    if status == "split-ready":
        return "idle"
    if status not in {"idle", "waiting", "camping", "moving_intent"}:
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


def _normalize_group_movement_intent(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    target_node = _normalize_map_target_node(raw.get("target_node") or raw.get("target"))
    target_label = str(raw.get("target_label") or "").strip()
    if not target_label and target_node:
        target_label = str(target_node.get("label") or target_node.get("node_id") or "").strip()
    if not target_label and isinstance(raw.get("target"), str):
        target_label = str(raw.get("target") or "").strip()
    movement_mode = str(raw.get("movement_mode") or raw.get("mode") or "travel").strip().lower() or "travel"
    source = str(raw.get("source") or "manual").strip() or "manual"
    if not target_label and not target_node:
        return None
    state: dict[str, Any] = {
        "target_label": target_label[:80],
        "movement_mode": movement_mode[:40],
        "source": source[:40],
    }
    if target_node:
        state["target_node"] = target_node
    return state


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
    source: str = "manual",
) -> dict[str, Any] | None:
    return _normalize_group_movement_intent(
        {
            "target_node": target_node,
            "target_label": target_label,
            "movement_mode": movement_mode,
            "source": source,
        }
    )


def _resolve_group_status(
    raw_status: Any,
    *,
    wait_state: dict[str, Any] | None,
    camp_state: dict[str, Any] | None,
    movement_intent: dict[str, Any] | None,
) -> str:
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
    group["status"] = _normalize_group_status(status)
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


def _group_movement_intent_summary(group: dict[str, Any]) -> dict[str, Any] | None:
    return _normalize_group_movement_intent(group.get("movement_intent"))


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
    status = _resolve_group_status(
        raw.get("status"),
        wait_state=wait_state,
        camp_state=camp_state,
        movement_intent=movement_intent,
    )

    normalized = {
        "group_id": group_key,
        "player_ids": player_ids,
        "current_map_position": pos,
        "area_label": area_label[:80],
        "status": status,
    }
    if wait_state:
        normalized["wait_state"] = wait_state
    if camp_state:
        normalized["camp_state"] = camp_state
    if movement_intent:
        normalized["movement_intent"] = movement_intent
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
