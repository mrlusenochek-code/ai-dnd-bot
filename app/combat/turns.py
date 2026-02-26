from __future__ import annotations

from app.combat.state import CombatState, Combatant


def build_initiative_order(combatants: dict[str, Combatant]) -> list[str]:
    """Build stable initiative order: initiative desc, pc before enemy, then name/key."""
    side_priority = {"pc": 0, "enemy": 1}
    return sorted(
        combatants.keys(),
        key=lambda key: (
            -combatants[key].initiative,
            side_priority.get(combatants[key].side, 99),
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
        current_combatant.dash_active = False
        current_combatant.disengage_active = False
        current_combatant.use_object_active = False

    return state
