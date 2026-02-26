from __future__ import annotations

from app.combat.state import CombatState, Combatant


def build_initiative_order(combatants: dict[str, Combatant]) -> list[str]:
    """Build stable initiative order: higher initiative first, then name/key."""
    return sorted(
        combatants.keys(),
        key=lambda key: (
            -combatants[key].initiative,
            combatants[key].name.casefold(),
            key,
        ),
    )


def advance_turn_in_state(state: CombatState) -> CombatState:
    """Advance turn index and increment round number on wraparound."""
    if not state.order:
        state.turn_index = 0
        return state

    if state.turn_index < 0 or state.turn_index >= len(state.order):
        state.turn_index = 0

    state.turn_index = (state.turn_index + 1) % len(state.order)
    if state.turn_index == 0:
        state.round_no += 1

    current_key = state.order[state.turn_index]
    current_combatant = state.combatants.get(current_key)
    if current_combatant is not None:
        current_combatant.dodge_active = False

    return state
