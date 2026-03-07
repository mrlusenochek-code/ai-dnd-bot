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

    ending_key = state.order[state.turn_index]
    ending_combatant = state.combatants.get(ending_key)
    if ending_combatant is not None and str(getattr(ending_combatant, "side", "")).lower() == "pc":
        race_features = ending_combatant.race_features if isinstance(ending_combatant.race_features, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        transform_raw = runtime.get("aasimar_transformation")
        transform = dict(transform_raw) if isinstance(transform_raw, dict) else {}
        if bool(transform.get("active")):
            rounds_left = max(0, int(transform.get("rounds_left") or 0))
            if rounds_left > 0:
                rounds_left -= 1
            transform["rounds_left"] = rounds_left
            if rounds_left <= 0:
                transform["active"] = False
                runtime.pop("fly_speed_ft", None)
            runtime["aasimar_transformation"] = transform
            if runtime:
                race_features["runtime"] = runtime
            else:
                race_features.pop("runtime", None)
            ending_combatant.race_features = race_features

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
        current_combatant.bonus_damage_used_this_turn = False
        current_combatant.action_available = True
        current_combatant.bonus_action_available = True
        current_combatant.reaction_available = True
        mode = str(getattr(current_combatant, "movement_mode", "") or "walk").strip().lower() or "walk"
        speeds = current_combatant.movement_speeds if isinstance(current_combatant.movement_speeds, dict) else {}
        mode_speed_raw = speeds.get(mode)
        mode_speed = (
            max(0, int(mode_speed_raw))
            if isinstance(mode_speed_raw, int) and not isinstance(mode_speed_raw, bool)
            else max(0, int(current_combatant.speed_ft))
        )
        current_combatant.move_speed_ft = mode_speed
        current_combatant.move_remaining_ft = mode_speed
        # legacy field, keep in sync
        current_combatant.move_remaining = mode_speed

    return state
