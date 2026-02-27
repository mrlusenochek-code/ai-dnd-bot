from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass
class Combatant:
    key: str
    name: str
    side: Literal["pc", "enemy"]
    hp_current: int
    hp_max: int
    ac: int
    initiative: int
    dodge_active: bool = False
    dash_active: bool = False
    disengage_active: bool = False
    use_object_active: bool = False
    help_attack_advantage: bool = False


@dataclass
class CombatState:
    active: bool
    round_no: int
    turn_index: int
    order: list[str]
    combatants: dict[str, Combatant]
    started_at_iso: str | None


_COMBAT_BY_SESSION: dict[str, CombatState] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_turn_index(state: CombatState, previous_key: str | None = None) -> None:
    if not state.order:
        state.turn_index = 0
        return

    if previous_key is not None and previous_key in state.order:
        state.turn_index = state.order.index(previous_key)
        return

    if state.turn_index < 0 or state.turn_index >= len(state.order):
        state.turn_index = 0


def _next_enemy_key(combatants: dict[str, Combatant]) -> str:
    idx = 1
    while True:
        candidate = f"enemy_{idx}"
        if candidate not in combatants:
            return candidate
        idx += 1


def start_combat(session_id: str, *, reason: str | None = None) -> CombatState:
    _ = reason
    state = CombatState(
        active=True,
        round_no=1,
        turn_index=0,
        order=[],
        combatants={},
        started_at_iso=_now_iso(),
    )
    _COMBAT_BY_SESSION[session_id] = state
    return state


def end_combat(session_id: str) -> None:
    _COMBAT_BY_SESSION.pop(session_id, None)


def get_combat(session_id: str) -> CombatState | None:
    return _COMBAT_BY_SESSION.get(session_id)


def add_enemy(
    session_id: str,
    *,
    name: str,
    hp: int,
    ac: int,
    enemy_id: str | None = None,
) -> CombatState | None:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None

    key = enemy_id if enemy_id else _next_enemy_key(state.combatants)
    previous_key = state.order[state.turn_index] if state.order and 0 <= state.turn_index < len(state.order) else None
    if state.round_no == 1 and state.turn_index == 0:
        previous_key = None

    hp_max = max(0, int(hp))
    state.combatants[key] = Combatant(
        key=key,
        name=name,
        side="enemy",
        hp_current=hp_max,
        hp_max=hp_max,
        ac=max(0, int(ac)),
        initiative=0,
    )

    from app.combat.turns import build_initiative_order

    state.order = build_initiative_order(state.combatants)
    _normalize_turn_index(state, previous_key=previous_key)
    return state


def upsert_pc(
    session_id: str,
    *,
    pc_key: str,
    name: str,
    hp: int,
    hp_max: int,
    ac: int,
    initiative: int = 0,
) -> CombatState | None:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None

    previous_key = state.order[state.turn_index] if state.order and 0 <= state.turn_index < len(state.order) else None
    if state.round_no == 1 and state.turn_index == 0:
        previous_key = None

    hp_max_norm = max(0, int(hp_max))
    hp_norm = max(0, int(hp))
    ac_norm = max(0, int(ac))
    initiative_norm = int(initiative)

    existing = state.combatants.get(pc_key)
    if existing is not None:
        existing.name = name
        existing.hp_max = hp_max_norm
        existing.ac = ac_norm
        existing.initiative = initiative_norm
        existing.side = "pc"
        existing.hp_current = max(0, min(existing.hp_current, hp_max_norm))
    else:
        state.combatants[pc_key] = Combatant(
            key=pc_key,
            name=name,
            side="pc",
            hp_current=max(0, min(hp_norm, hp_max_norm)),
            hp_max=hp_max_norm,
            ac=ac_norm,
            initiative=initiative_norm,
        )

    from app.combat.turns import build_initiative_order

    state.order = build_initiative_order(state.combatants)
    _normalize_turn_index(state, previous_key=previous_key)
    return state


def apply_damage(session_id: str, combatant_key: str, damage: int) -> CombatState | None:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None

    combatant = state.combatants.get(combatant_key)
    if combatant is None:
        return None

    combatant.hp_current = max(0, combatant.hp_current - max(0, int(damage)))
    return state


def current_turn_label(state: CombatState) -> str:
    if not state.order:
        return "-"
    if state.turn_index < 0 or state.turn_index >= len(state.order):
        return "-"

    key = state.order[state.turn_index]
    combatant = state.combatants.get(key)
    return combatant.name if combatant is not None else key


def advance_turn(session_id: str) -> CombatState | None:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None

    from app.combat.turns import advance_turn_in_state

    return advance_turn_in_state(state)


def combatant_to_dict(c: Combatant) -> dict[str, Any]:
    return {
        "key": c.key,
        "name": c.name,
        "side": c.side,
        "hp_current": max(0, int(c.hp_current)),
        "hp_max": max(0, int(c.hp_max)),
        "ac": max(0, int(c.ac)),
        "initiative": int(c.initiative),
        "dodge_active": bool(c.dodge_active),
        "dash_active": bool(c.dash_active),
        "disengage_active": bool(c.disengage_active),
        "use_object_active": bool(c.use_object_active),
        "help_attack_advantage": bool(c.help_attack_advantage),
    }


def combat_state_to_dict(state: CombatState) -> dict[str, Any]:
    return {
        "v": 1,
        "active": bool(state.active),
        "round_no": max(1, int(state.round_no)),
        "turn_index": int(state.turn_index),
        "order": [key for key in state.order if key in state.combatants],
        "combatants": {key: combatant_to_dict(c) for key, c in state.combatants.items()},
        "started_at_iso": state.started_at_iso if isinstance(state.started_at_iso, str) else None,
    }


def snapshot_combat_state(session_id: str) -> dict[str, Any] | None:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None
    return combat_state_to_dict(state)


def combatant_from_dict(raw: Any) -> Combatant | None:
    if not isinstance(raw, dict):
        return None

    key = raw.get("key")
    name = raw.get("name")
    side = raw.get("side")
    hp_current = raw.get("hp_current")
    hp_max = raw.get("hp_max")
    ac = raw.get("ac")
    initiative = raw.get("initiative")

    if not isinstance(key, str) or not key:
        return None
    if not isinstance(name, str):
        return None
    if side not in ("pc", "enemy"):
        return None
    if not isinstance(hp_current, int) or not isinstance(hp_max, int):
        return None
    if not isinstance(ac, int) or not isinstance(initiative, int):
        return None

    hp_max_norm = max(0, hp_max)
    hp_current_norm = max(0, min(hp_current, hp_max_norm))

    return Combatant(
        key=key,
        name=name,
        side=side,
        hp_current=hp_current_norm,
        hp_max=hp_max_norm,
        ac=max(0, ac),
        initiative=initiative,
        dodge_active=bool(raw.get("dodge_active", False)),
        dash_active=bool(raw.get("dash_active", False)),
        disengage_active=bool(raw.get("disengage_active", False)),
        use_object_active=bool(raw.get("use_object_active", False)),
        help_attack_advantage=bool(raw.get("help_attack_advantage", False)),
    )


def combat_state_from_dict(raw: Any) -> CombatState | None:
    if not isinstance(raw, dict):
        return None

    active = raw.get("active")
    round_no = raw.get("round_no")
    turn_index = raw.get("turn_index")
    combatants_raw = raw.get("combatants")
    order_raw = raw.get("order")
    started_at_iso = raw.get("started_at_iso")

    if not isinstance(active, bool):
        return None
    if not isinstance(round_no, int) or not isinstance(turn_index, int):
        return None
    if not isinstance(combatants_raw, dict):
        return None

    combatants: dict[str, Combatant] = {}
    for key, item in combatants_raw.items():
        if not isinstance(key, str):
            return None
        combatant = combatant_from_dict(item)
        if combatant is None:
            return None
        if combatant.key != key:
            combatant.key = key
        combatants[key] = combatant

    from app.combat.turns import build_initiative_order

    order_valid = isinstance(order_raw, list) and all(isinstance(item, str) for item in order_raw)
    if order_valid:
        order_clean: list[str] = []
        seen: set[str] = set()
        for key in order_raw:
            if key in combatants and key not in seen:
                order_clean.append(key)
                seen.add(key)
        if len(order_clean) != len(combatants):
            # Broken order payload: rebuild from initiative so all combatants are present.
            order_clean = build_initiative_order(combatants)
    else:
        order_clean = build_initiative_order(combatants)

    state = CombatState(
        active=active,
        round_no=max(1, round_no),
        turn_index=turn_index,
        order=order_clean,
        combatants=combatants,
        started_at_iso=started_at_iso if isinstance(started_at_iso, str) else None,
    )
    _normalize_turn_index(state)
    return state


def restore_combat_state(session_id: str, payload: Any) -> CombatState | None:
    state = combat_state_from_dict(payload)
    if state is None or not state.active:
        end_combat(session_id)
        return None

    _COMBAT_BY_SESSION[session_id] = state
    return state
