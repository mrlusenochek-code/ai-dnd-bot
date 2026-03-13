from __future__ import annotations

from typing import Any


def apply_shifter_shift_start_runtime(
    actor: Any,
    *,
    uses_used: int,
    temp_hp_gain: int,
    subrace_key: str,
) -> None:
    race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    runtime["shifted_active"] = True
    runtime["shifted_rounds_left"] = 10
    runtime["shifting_uses_used"] = max(0, uses_used) + 1
    runtime["shifting_temp_hp_granted"] = max(0, temp_hp_gain)
    runtime["shifting_longtooth_bite_available"] = subrace_key == "longtooth"
    runtime["shifting_swiftstride_reaction_available"] = subrace_key == "swiftstride"
    race_features["runtime"] = runtime
    actor.race_features = race_features


def apply_shifter_beasthide_shift_effects(
    actor: Any,
    *,
    runtime: dict[str, object],
    ac_bonus: int,
    extra_temp_hp_roll: int,
    temp_hp_gain: int,
) -> int:
    next_temp_hp_gain = max(0, temp_hp_gain) + max(0, extra_temp_hp_roll)
    if ac_bonus > 0:
        actor.ac += ac_bonus
        runtime["shifting_ac_bonus_active"] = ac_bonus
    return next_temp_hp_gain


def clear_shifter_shift_runtime(actor: Any, *, sync_active_walk_movement: bool) -> bool:
    if str(getattr(actor, "side", "")).lower() != "pc":
        return False
    race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if not runtime:
        return False
    changed = False
    if bool(runtime.get("shifted_active")):
        runtime["shifted_active"] = False
        changed = True
    if max(0, int(runtime.get("shifted_rounds_left") or 0)) != 0:
        runtime["shifted_rounds_left"] = 0
        changed = True
    ac_bonus = max(0, int(runtime.get("shifting_ac_bonus_active") or 0))
    if ac_bonus > 0:
        actor.ac = max(0, int(getattr(actor, "ac", 0) or 0) - ac_bonus)
        runtime["shifting_ac_bonus_active"] = 0
        changed = True
    speed_bonus = max(0, int(runtime.get("shifting_speed_bonus_active_ft") or 0))
    if speed_bonus > 0:
        speeds = actor.movement_speeds if isinstance(getattr(actor, "movement_speeds", None), dict) else {}
        walk_speed = max(0, int(speeds.get("walk", getattr(actor, "speed_ft", 30)) or 0))
        speeds["walk"] = max(0, walk_speed - speed_bonus)
        actor.movement_speeds = speeds
        if sync_active_walk_movement and str(getattr(actor, "movement_mode", "") or "walk").strip().lower() == "walk":
            actor.move_speed_ft = max(0, int(getattr(actor, "move_speed_ft", speeds["walk"]) or 0) - speed_bonus)
            actor.move_remaining_ft = min(max(0, int(getattr(actor, "move_remaining_ft", 0) or 0)), actor.move_speed_ft)
            actor.move_remaining = actor.move_remaining_ft
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
        actor.race_features = race_features
    return changed
