from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal


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
