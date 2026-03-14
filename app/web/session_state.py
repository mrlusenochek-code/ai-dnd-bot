import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Session
from app.web.utils import as_int


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

    return {
        "v": 1,
        "map_level": map_level[:32],
        "node_type": node_type[:32],
        "node_id": node_id[:120],
        "label": label[:80] or node_id[:80],
    }


def _normalize_map_target_node(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, str):
        pos = _default_map_position(raw)
        return {**pos, "zone_label": pos["label"]}

    pos = _normalize_map_position(raw)
    if not pos:
        return None

    zone_label = ""
    if isinstance(raw, dict):
        zone_label = str(raw.get("zone_label") or "").strip()
    if not zone_label:
        zone_label = str(pos.get("label") or pos.get("node_id") or "").strip()
    if not zone_label:
        return None

    return {
        **pos,
        "zone_label": zone_label[:80],
    }


def _apply_map_position_transition(
    current_map_position: Any,
    target_node: Any,
    movement_reason: str | None = None,
) -> tuple[dict[str, Any] | None, str, bool, str | None]:
    current_pos = _normalize_map_position(current_map_position)
    current_zone = _format_map_position_label(current_pos)
    target = _normalize_map_target_node(target_node)
    if not target:
        return current_pos, current_zone, False, "invalid_target_node"

    next_position = {
        "v": 1,
        "map_level": str(target.get("map_level") or "region"),
        "node_type": str(target.get("node_type") or "zone"),
        "node_id": str(target.get("node_id") or "")[:120],
        "label": str(target.get("label") or "")[:80],
    }
    next_zone = str(target.get("zone_label") or _format_map_position_label(next_position)).strip() or current_zone
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


def _get_player_map_position(sess: Session, player_id: uuid.UUID | str) -> dict[str, Any] | None:
    positions = _get_map_positions(sess)
    return positions.get(str(player_id))


def _get_player_position_context(sess: Session, player_id: uuid.UUID | str) -> dict[str, Any]:
    pid = str(player_id)
    pos = _get_player_map_position(sess, pid)
    if pos:
        return {
            "zone_label": _format_map_position_label(pos),
            "map_position": dict(pos),
        }

    legacy_positions = settings_get(sess, "pc_positions", {}) or {}
    zone_label = "стартовая локация"
    if isinstance(legacy_positions, dict):
        raw_zone = legacy_positions.get(pid)
        zone_text = str(raw_zone or "").strip()
        if zone_text:
            zone_label = zone_text[:80]
    return {
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


def _same_player_map_position(
    sess: Session,
    left_player_id: uuid.UUID | str,
    right_player_id: uuid.UUID | str,
) -> bool:
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
    positions = dict(_get_map_positions(sess))
    positions[pid] = pos
    settings_set(sess, "map_positions", positions)

    # legacy mirror for old zone-based code
    legacy = dict(_get_pc_positions(sess))
    legacy[pid] = _format_map_position_label(pos)
    settings_set(sess, "pc_positions", legacy)


def _clear_player_map_position(sess: Session, player_id: uuid.UUID | str) -> None:
    pid = str(player_id)
    positions = dict(_get_map_positions(sess))
    if pid in positions:
        positions.pop(pid, None)
    settings_set(sess, "map_positions", positions)

    legacy = settings_get(sess, "pc_positions", {}) or {}
    legacy_positions = dict(legacy) if isinstance(legacy, dict) else {}
    if pid in legacy_positions:
        legacy_positions.pop(pid, None)
    settings_set(sess, "pc_positions", legacy_positions)


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
        legacy_positions[pid_str] = _format_map_position_label(pos)
    settings_set(sess, "map_positions", map_positions)
    settings_set(sess, "pc_positions", legacy_positions)


def _get_pc_positions(sess: Session) -> dict[str, str]:
    # Prefer new structured positions if they already exist.
    map_positions = _get_map_positions(sess)
    if map_positions:
        return {pid: _format_map_position_label(pos) for pid, pos in map_positions.items()}

    # Legacy fallback.
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
