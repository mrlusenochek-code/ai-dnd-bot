from __future__ import annotations

import random

from app.combat.state import CombatState, Combatant
from app.rules.phb_math import ability_mod_from_stat100


def _clear_shifter_shift_runtime(combatant: Combatant) -> bool:
    race_features = combatant.race_features if isinstance(combatant.race_features, dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    changed = False
    if bool(runtime.get("shifted_active")):
        runtime["shifted_active"] = False
        changed = True
    if max(0, int(runtime.get("shifted_rounds_left") or 0)) != 0:
        runtime["shifted_rounds_left"] = 0
        changed = True
    ac_bonus = max(0, int(runtime.get("shifting_ac_bonus_active") or 0))
    if ac_bonus > 0:
        combatant.ac = max(0, int(getattr(combatant, "ac", 0) or 0) - ac_bonus)
        runtime["shifting_ac_bonus_active"] = 0
        changed = True
    speed_bonus = max(0, int(runtime.get("shifting_speed_bonus_active_ft") or 0))
    if speed_bonus > 0:
        speeds = combatant.movement_speeds if isinstance(getattr(combatant, "movement_speeds", None), dict) else {}
        walk_speed = max(0, int(speeds.get("walk", getattr(combatant, "speed_ft", 30)) or 0))
        speeds["walk"] = max(0, walk_speed - speed_bonus)
        combatant.movement_speeds = speeds
        runtime["shifting_speed_bonus_active_ft"] = 0
        changed = True
    if bool(runtime.get("shifting_longtooth_bite_available")):
        runtime["shifting_longtooth_bite_available"] = False
        changed = True
    if bool(runtime.get("shifting_swiftstride_reaction_available")):
        runtime["shifting_swiftstride_reaction_available"] = False
        changed = True
    if changed:
        race_features["runtime"] = runtime
        combatant.race_features = race_features
    return changed


def _normalize_tabaxi_feline_agility_runtime(combatant: Combatant) -> bool:
    race_features = combatant.race_features if isinstance(combatant.race_features, dict) else {}
    features = race_features.get("features") if isinstance(race_features.get("features"), dict) else {}
    if not isinstance(features.get("feline_agility"), dict):
        return False
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    moved_ft = max(0, int(getattr(combatant, "moved_this_turn_ft", 0) or 0))
    changed = False
    if bool(runtime.get("feline_agility_active")):
        runtime["feline_agility_active"] = False
        changed = True
    if str(runtime.get("feline_agility_used_turn") or "").strip():
        runtime["feline_agility_used_turn"] = ""
        changed = True
    if moved_ft > 0:
        if bool(runtime.get("feline_agility_available")):
            runtime["feline_agility_available"] = False
            changed = True
    else:
        if not bool(runtime.get("feline_agility_available", True)):
            runtime["feline_agility_available"] = True
            changed = True
    if changed:
        race_features["runtime"] = runtime
        combatant.race_features = race_features
    return changed


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
    if ending_combatant is not None:
        race_features = ending_combatant.race_features if isinstance(ending_combatant.race_features, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        if "rabbit_hop_no_oa" in runtime:
            runtime.pop("rabbit_hop_no_oa", None)
            runtime.pop("rabbit_hop_no_oa_round", None)
            if runtime:
                race_features["runtime"] = runtime
            else:
                race_features.pop("runtime", None)
            ending_combatant.race_features = race_features
    if ending_combatant is not None:
        race_features = ending_combatant.race_features if isinstance(ending_combatant.race_features, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        conditions_raw = runtime.get("conditions")
        conditions = dict(conditions_raw) if isinstance(conditions_raw, dict) else {}
        poisoned_raw = conditions.get("poisoned")
        poisoned = dict(poisoned_raw) if isinstance(poisoned_raw, dict) else {}
        if bool(poisoned.get("active")):
            save_dc = max(1, int(poisoned.get("save_dc") or 12))
            stats = ending_combatant.stats if isinstance(ending_combatant.stats, dict) else {}
            con_stat = int(stats.get("con", 50)) if isinstance(stats.get("con"), int) else 50
            con_mod = ability_mod_from_stat100(con_stat)
            save_roll = random.randint(1, 20)
            save_total = save_roll + con_mod
            save_success = save_total >= save_dc
            remaining_rounds = max(0, int(poisoned.get("remaining_rounds") or 0))
            if save_success:
                conditions.pop("poisoned", None)
            else:
                if remaining_rounds > 0:
                    remaining_rounds -= 1
                if remaining_rounds <= 0:
                    conditions.pop("poisoned", None)
                else:
                    poisoned["remaining_rounds"] = remaining_rounds
                    poisoned["active"] = True
                    conditions["poisoned"] = poisoned
            if conditions:
                runtime["conditions"] = conditions
            else:
                runtime.pop("conditions", None)
            if runtime:
                race_features["runtime"] = runtime
            else:
                race_features.pop("runtime", None)
            ending_combatant.race_features = race_features
    if ending_combatant is not None:
        ending_combatant.turns_taken = max(0, int(getattr(ending_combatant, "turns_taken", 0))) + 1
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
        if bool(runtime.get("shifted_active")):
            rounds_left = max(0, int(runtime.get("shifted_rounds_left") or 0))
            if rounds_left > 0:
                rounds_left -= 1
            runtime["shifted_rounds_left"] = rounds_left
            race_features["runtime"] = runtime
            ending_combatant.race_features = race_features
            if rounds_left <= 0:
                _clear_shifter_shift_runtime(ending_combatant)
        _normalize_tabaxi_feline_agility_runtime(ending_combatant)
    if ending_combatant is not None:
        source_actor_key = str(getattr(ending_combatant, "key", "") or "")
        if source_actor_key:
            for combatant in state.combatants.values():
                race_features = combatant.race_features if isinstance(combatant.race_features, dict) else {}
                runtime_raw = race_features.get("runtime")
                runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
                conditions_raw = runtime.get("conditions")
                conditions = dict(conditions_raw) if isinstance(conditions_raw, dict) else {}
                frightened_raw = conditions.get("frightened")
                frightened = dict(frightened_raw) if isinstance(frightened_raw, dict) else {}
                if not bool(frightened.get("active")):
                    continue
                if str(frightened.get("source") or "").strip().lower() != "leonin_daunting_roar":
                    continue
                expires_on = str(frightened.get("expires_on_end_of_source_next_turn") or "").strip()
                if expires_on != source_actor_key:
                    continue
                turns_remaining = max(0, int(frightened.get("source_turns_remaining") or 0))
                turns_remaining -= 1
                if turns_remaining <= 0:
                    conditions.pop("frightened", None)
                else:
                    frightened["source_turns_remaining"] = turns_remaining
                    conditions["frightened"] = frightened
                if conditions:
                    runtime["conditions"] = conditions
                else:
                    runtime.pop("conditions", None)
                if runtime:
                    race_features["runtime"] = runtime
                else:
                    race_features.pop("runtime", None)
                combatant.race_features = race_features

    state.turn_index = (state.turn_index + 1) % len(state.order)
    if state.turn_index == 0:
        state.round_no += 1

    current_key = state.order[state.turn_index]
    current_combatant = state.combatants.get(current_key)
    if current_combatant is not None:
        current_actor_key = str(getattr(current_combatant, "key", "") or "")
        if current_actor_key:
            for combatant in state.combatants.values():
                race_features = combatant.race_features if isinstance(combatant.race_features, dict) else {}
                runtime_raw = race_features.get("runtime")
                runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
                taunted_raw = runtime.get("taunted")
                taunted = dict(taunted_raw) if isinstance(taunted_raw, dict) else {}
                if not bool(taunted.get("active")):
                    taunted = {}
                expires_on = str(taunted.get("expires_on_turn_start_of_actor_id") or "").strip()
                if taunted and expires_on == current_actor_key:
                    runtime.pop("taunted", None)
                groveled_raw = runtime.get("groveled")
                groveled = dict(groveled_raw) if isinstance(groveled_raw, dict) else {}
                if bool(groveled.get("active")):
                    expires_grovel = str(groveled.get("expires_on_turn_start_of_source") or "").strip()
                    if expires_grovel == current_actor_key:
                        runtime.pop("groveled", None)
                if runtime:
                    race_features["runtime"] = runtime
                else:
                    race_features.pop("runtime", None)
                combatant.race_features = race_features
    if current_combatant is not None:
        race_features = current_combatant.race_features if isinstance(current_combatant.race_features, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        runtime_changed = False
        if "goring_rush_available" in runtime:
            runtime.pop("goring_rush_available", None)
            runtime_changed = True
        if "hammering_horns_available" in runtime:
            runtime.pop("hammering_horns_available", None)
            runtime_changed = True
        if "hammering_horns_target_id" in runtime:
            runtime.pop("hammering_horns_target_id", None)
            runtime_changed = True
        if "aggressive_used_turn_id" in runtime:
            runtime.pop("aggressive_used_turn_id", None)
            runtime_changed = True
        if bool(runtime.get("shifted_active")) and str((race_features.get("subrace") or {}).get("key") or "").strip().lower() == "swiftstride":
            if not bool(runtime.get("shifting_swiftstride_reaction_available")):
                runtime["shifting_swiftstride_reaction_available"] = True
                runtime_changed = True
        if "grovel_active_until_turn_start_of_actor_id" in runtime:
            source_key = str(runtime.get("grovel_active_until_turn_start_of_actor_id") or "").strip()
            if source_key == str(getattr(current_combatant, "key", "") or ""):
                runtime.pop("grovel_active_until_turn_start_of_actor_id", None)
                runtime_changed = True
        hidden_raw = runtime.get("hidden_step")
        hidden_step = dict(hidden_raw) if isinstance(hidden_raw, dict) else {}
        if bool(hidden_step.get("active")) and bool(hidden_step.get("expires_on_owner_turn_start", True)):
            hidden_step["active"] = False
            runtime["hidden_step"] = hidden_step
            runtime_changed = True
        if runtime_changed:
            if runtime:
                race_features["runtime"] = runtime
            else:
                race_features.pop("runtime", None)
            current_combatant.race_features = race_features
        current_combatant.dodge_active = False
        current_combatant.dash_active = False
        current_combatant.disengage_active = False
        current_combatant.use_object_active = False
        current_combatant.bonus_damage_used_this_turn = False
        current_combatant.action_available = True
        current_combatant.bonus_action_available = True
        current_combatant.reaction_available = True
        current_combatant.moved_this_turn_ft = 0
        current_combatant.charge_hooves_available = False
        mode = str(getattr(current_combatant, "movement_mode", "") or "walk").strip().lower() or "walk"
        speeds = current_combatant.movement_speeds if isinstance(current_combatant.movement_speeds, dict) else {}
        mode_speed_raw = speeds.get(mode)
        mode_speed = (
            max(0, int(mode_speed_raw))
            if isinstance(mode_speed_raw, int) and not isinstance(mode_speed_raw, bool)
            else max(0, int(current_combatant.speed_ft))
        )
        current_runtime_raw = race_features.get("runtime")
        current_runtime = dict(current_runtime_raw) if isinstance(current_runtime_raw, dict) else {}
        override_speed_raw = current_runtime.get("speed_override_ft")
        if isinstance(override_speed_raw, int) and not isinstance(override_speed_raw, bool):
            mode_speed = max(0, int(override_speed_raw))
        current_combatant.move_speed_ft = mode_speed
        current_combatant.move_remaining_ft = mode_speed
        # legacy field, keep in sync
        current_combatant.move_remaining = mode_speed

    return state
