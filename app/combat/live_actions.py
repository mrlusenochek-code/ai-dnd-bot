from __future__ import annotations

import re
import random
from types import SimpleNamespace
from datetime import datetime, timezone
from typing import Any, Optional

from app.combat.resolution import resolve_attack_roll
from app.combat.state import (
    advance_turn,
    apply_damage,
    current_turn_label,
    end_combat,
    get_combat,
)
from app.rules.derived_stats import compute_attack_profile, parse_dice
from app.rules.phb_math import ability_mod_from_stat100, proficiency_bonus
from app.rules.item_catalog import ITEMS
from app.web.check_engine import roll_check


def _is_alive(hp_current: int) -> bool:
    return hp_current > 0


def _first_living_opponent(state: Any, attacker_side: str) -> Any | None:
    for key in state.order:
        combatant = state.combatants.get(key)
        if combatant is None:
            continue
        if combatant.side == attacker_side:
            continue
        if _is_alive(combatant.hp_current):
            return combatant

    for combatant in state.combatants.values():
        if combatant.side == attacker_side:
            continue
        if _is_alive(combatant.hp_current):
            return combatant

    return None


def _first_downed_ally(state: Any, actor: Any) -> Any | None:
    for key in state.order:
        combatant = state.combatants.get(key)
        if combatant is None:
            continue
        if combatant.side != actor.side:
            continue
        if combatant.hp_current != 0:
            continue
        if combatant.is_dead or combatant.is_stable:
            continue
        return combatant

    for combatant in state.combatants.values():
        if combatant.side != actor.side:
            continue
        if combatant.hp_current != 0:
            continue
        if combatant.is_dead or combatant.is_stable:
            continue
        return combatant

    return None


def _first_healing_target_ally(state: Any, actor: Any) -> Any | None:
    for prefer_exact_zero in (True, False):
        for key in state.order:
            combatant = state.combatants.get(key)
            if combatant is None:
                continue
            if combatant.side != actor.side:
                continue
            if combatant.is_dead:
                continue
            if combatant.hp_current > 0:
                continue
            if prefer_exact_zero and combatant.hp_current != 0:
                continue
            return combatant

    return None


def _is_side_alive(state: Any, side: str) -> bool:
    for combatant in state.combatants.values():
        if combatant.side == side and _is_alive(combatant.hp_current):
            return True
    return False


def _combat_status(state: Any) -> str:
    return f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}"


def _aasimar_bonus_damage_for_hit(actor: Any) -> tuple[int, str]:
    if str(getattr(actor, "side", "")).lower() != "pc":
        return 0, ""
    if bool(getattr(actor, "bonus_damage_used_this_turn", False)):
        return 0, ""
    race_features = getattr(actor, "race_features", None)
    rf = race_features if isinstance(race_features, dict) else {}
    runtime_raw = rf.get("runtime")
    runtime = runtime_raw if isinstance(runtime_raw, dict) else {}
    transform_raw = runtime.get("aasimar_transformation")
    transform = transform_raw if isinstance(transform_raw, dict) else {}
    if not bool(transform.get("active")):
        return 0, ""
    kind = str(transform.get("kind") or "").strip().lower()
    if kind not in {"protector", "fallen"}:
        return 0, ""
    damage_type = "radiant" if kind == "protector" else "necrotic"
    level = max(1, int(getattr(actor, "level", 1) or 1))
    bonus = level
    actor.bonus_damage_used_this_turn = True
    return bonus, damage_type


def _race_feature(actor: Any, feature_key: str) -> dict[str, Any] | None:
    race_features = getattr(actor, "race_features", None)
    rf = race_features if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    feature_raw = features.get(feature_key)
    return feature_raw if isinstance(feature_raw, dict) else None


def _has_reroll_ones_scope(actor: Any, scope_key: str) -> bool:
    reroll_cfg = _race_feature(actor, "reroll_ones")
    if reroll_cfg is None:
        return False
    scope = reroll_cfg.get("scope")
    scope_items = scope if isinstance(scope, list) else []
    scope_norm = str(scope_key or "").strip().lower()
    for item in scope_items:
        if str(item or "").strip().lower() == scope_norm:
            return True
    return False


def _roll_check_compat(mode: str, *, rng: Any = None, reroll_ones: bool = False) -> tuple[int, Optional[int], int]:
    try:
        if rng is None:
            return roll_check(mode, reroll_ones=reroll_ones)
        return roll_check(mode, rng=rng, reroll_ones=reroll_ones)
    except TypeError:
        # Backward-compatible path for tests monkeypatching roll_check(mode) signature only.
        if rng is not None:
            try:
                return roll_check(mode, rng=rng)
            except TypeError:
                return roll_check(mode)
        return roll_check(mode)


def _apply_savage_attacks_bonus(*, attacker: Any, profile: Any, is_crit: bool, total_damage: int) -> tuple[int, list[dict[str, Any]]]:
    extra_lines: list[dict[str, Any]] = []
    if not is_crit or str(getattr(attacker, "side", "")).lower() != "pc":
        return total_damage, extra_lines
    if not bool(getattr(profile, "is_melee_weapon", False)):
        return total_damage, extra_lines
    if _race_feature(attacker, "savage_attacks") is None:
        return total_damage, extra_lines
    parsed = parse_dice(str(getattr(profile, "damage_dice", "") or "").strip().lower())
    if parsed is None:
        return total_damage, extra_lines
    _count, sides = parsed
    if sides <= 0:
        return total_damage, extra_lines
    extra_damage = random.randint(1, sides)
    extra_lines.append({"text": f"Свирепые атаки: +{extra_damage} (доп. кость урона оружия).", "muted": True})
    return total_damage + extra_damage, extra_lines


def _apply_surprise_attack_bonus(
    *,
    state: Any,
    attacker: Any,
    target: Any,
    is_hit: bool,
    is_crit: bool,
    total_damage: int,
) -> tuple[int, list[dict[str, Any]]]:
    extra_lines: list[dict[str, Any]] = []
    if not is_hit:
        return total_damage, extra_lines
    if str(getattr(attacker, "side", "")).lower() != "pc":
        return total_damage, extra_lines
    surprise_cfg = _race_feature(attacker, "surprise_attack")
    if surprise_cfg is None:
        return total_damage, extra_lines
    if max(1, int(getattr(state, "round_no", 1))) != 1:
        return total_damage, extra_lines
    if max(0, int(getattr(target, "turns_taken", 0))) != 0:
        return total_damage, extra_lines
    if bool(getattr(attacker, "surprise_attack_used", False)):
        return total_damage, extra_lines

    dice_count = 4 if is_crit else 2
    rolls = [random.randint(1, 6) for _ in range(dice_count)]
    bonus = sum(rolls)
    attacker.surprise_attack_used = True
    extra_lines.append(
        {"text": f"Внезапное нападение: +{bonus} ({'4d6' if is_crit else '2d6'}) (1/бой).", "muted": True}
    )
    return total_damage + bonus, extra_lines


def _apply_relentless_endurance_if_needed(*, target: Any, incoming_damage: int) -> tuple[int, list[dict[str, Any]]]:
    extra_lines: list[dict[str, Any]] = []
    if str(getattr(target, "side", "")).lower() != "pc":
        return incoming_damage, extra_lines
    relentless = _race_feature(target, "relentless_endurance")
    if relentless is None:
        return incoming_damage, extra_lines
    pre_hp = max(0, int(getattr(target, "hp_current", 0)))
    hp_max = max(0, int(getattr(target, "hp_max", 0)))
    if pre_hp <= 0 or incoming_damage < pre_hp:
        return incoming_damage, extra_lines
    would_instant_die = (incoming_damage - pre_hp) >= hp_max
    if would_instant_die:
        return incoming_damage, extra_lines
    race_features = target.race_features if isinstance(target.race_features, dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if bool(runtime.get("relentless_endurance_used", False)):
        return incoming_damage, extra_lines
    runtime["relentless_endurance_used"] = True
    race_features["runtime"] = runtime
    target.race_features = race_features
    extra_lines.append({"text": "Неукротимая стойкость: вместо 0 HP остаётся 1 (1/дл отдых).", "muted": True})
    return max(0, pre_hp - 1), extra_lines


def _revert_shapechanger_on_death(target: Any, lines: list[dict[str, Any]]) -> None:
    if str(getattr(target, "side", "")).lower() != "pc":
        return
    race_features = target.race_features if isinstance(getattr(target, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    shape_raw = runtime.get("shapechanger")
    shape = dict(shape_raw) if isinstance(shape_raw, dict) else {}
    if not bool(shape.get("active")):
        return
    shape["active"] = False
    shape["persona"] = ""
    shape["voice"] = ""
    shape["changed_at_iso"] = datetime.now(timezone.utc).isoformat()
    runtime["shapechanger"] = shape
    race_features["runtime"] = runtime
    target.race_features = race_features
    lines.append({"text": "Перевёртыш: смерть — возвращение в истинную форму.", "muted": True})


def _maybe_apply_built_for_success(actor: Any, d20_roll: int, lines: list[dict[str, Any]]) -> int:
    roll_out = int(d20_roll)
    extra_lines: list[dict[str, Any]] = []
    if str(getattr(actor, "side", "")).lower() != "pc":
        return roll_out
    built_cfg = _race_feature(actor, "built_for_success")
    if built_cfg is None:
        return roll_out
    race_features = actor.race_features if isinstance(actor.race_features, dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if not bool(runtime.get("built_for_success_armed")):
        return roll_out
    level = max(1, int(getattr(actor, "level", 1) or 1))
    uses_max = max(1, int(proficiency_bonus(level)))
    used = max(0, int(runtime.get("built_for_success_used") or 0))
    if used >= uses_max:
        runtime["built_for_success_armed"] = False
        race_features["runtime"] = runtime
        actor.race_features = race_features
        extra_lines.append({"text": "Создан для успеха: заряды исчерпаны до долгого отдыха.", "muted": True})
        lines.extend(extra_lines)
        return roll_out
    bonus = random.randint(1, 4)
    runtime["built_for_success_used"] = used + 1
    runtime["built_for_success_armed"] = False
    race_features["runtime"] = runtime
    actor.race_features = race_features
    extra_lines.append({"text": f"Создан для успеха: +{bonus} (1d4).", "muted": True})
    lines.extend(extra_lines)
    return roll_out + bonus


def _maybe_apply_vampiric_bite_bonus(actor: Any, d20_roll: int, lines: list[dict[str, Any]]) -> int:
    roll_out = int(d20_roll)
    if str(getattr(actor, "side", "")).lower() != "pc":
        return roll_out
    race_features = actor.race_features if isinstance(actor.race_features, dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if not bool(runtime.get("vampiric_bite_bonus_armed")):
        return roll_out
    bonus = max(0, int(runtime.get("vampiric_bite_bonus_value") or 0))
    runtime["vampiric_bite_bonus_armed"] = False
    runtime["vampiric_bite_bonus_value"] = 0
    race_features["runtime"] = runtime
    actor.race_features = race_features
    if bonus > 0:
        lines.append({"text": f"Укус вампира: бонус к следующему d20 +{bonus}.", "muted": True})
    return max(1, min(20, roll_out + bonus))


def _has_nimble_escape(actor: Any) -> bool:
    race_features = getattr(actor, "race_features", None)
    rf = race_features if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    return bool(features.get("nimble_escape") is True)


_SIZE_RANK = {
    "tiny": 0,
    "small": 1,
    "medium": 2,
    "large": 3,
    "huge": 4,
    "gargantuan": 5,
}


def _combatant_size_key(combatant: Any) -> str:
    size_raw = str(getattr(combatant, "size", "") or "").strip().lower()
    if size_raw in _SIZE_RANK:
        return size_raw
    race_features = getattr(combatant, "race_features", None)
    rf = race_features if isinstance(race_features, dict) else {}
    rf_size = str(rf.get("size") or "").strip().lower()
    if rf_size in _SIZE_RANK:
        return rf_size
    return "medium"


def _is_target_larger_than_actor(*, actor: Any, target: Any) -> bool:
    actor_size = _combatant_size_key(actor)
    target_size = _combatant_size_key(target)
    return _SIZE_RANK.get(target_size, _SIZE_RANK["medium"]) > _SIZE_RANK.get(actor_size, _SIZE_RANK["medium"])


def _nimble_hide_runtime(actor: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    hide_raw = runtime.get("nimble_escape_hide")
    hide_cfg = dict(hide_raw) if isinstance(hide_raw, dict) else {}
    return race_features, runtime, hide_cfg


def _is_nimble_escape_hide_active(actor: Any) -> bool:
    _rf, _runtime, hide_cfg = _nimble_hide_runtime(actor)
    return bool(hide_cfg.get("active"))


def _arm_nimble_escape_hide(actor: Any) -> None:
    race_features, runtime, hide_cfg = _nimble_hide_runtime(actor)
    hide_cfg["active"] = True
    hide_cfg["source"] = "nimble_escape_hide"
    runtime["nimble_escape_hide"] = hide_cfg
    race_features["runtime"] = runtime
    actor.race_features = race_features


def _consume_nimble_escape_hide(actor: Any) -> bool:
    race_features, runtime, hide_cfg = _nimble_hide_runtime(actor)
    if not bool(hide_cfg.get("active")):
        return False
    hide_cfg["active"] = False
    runtime["nimble_escape_hide"] = hide_cfg
    race_features["runtime"] = runtime
    actor.race_features = race_features
    return True


def _maybe_apply_fury_of_small(*, actor: Any, target: Any, lines: list[dict[str, Any]]) -> int:
    if str(getattr(actor, "side", "")).lower() != "pc":
        return 0
    fury_cfg = _race_feature(actor, "fury_of_the_small")
    if fury_cfg is None:
        return 0
    race_features = actor.race_features if isinstance(actor.race_features, dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if not bool(runtime.get("fury_of_small_armed")):
        return 0
    if bool(runtime.get("fury_of_small_used")):
        runtime["fury_of_small_armed"] = False
        race_features["runtime"] = runtime
        actor.race_features = race_features
        lines.append({"text": "Разъярённая мелкота: уже использована до отдыха.", "muted": True})
        return 0
    if not _is_target_larger_than_actor(actor=actor, target=target):
        return 0
    bonus = max(1, int(getattr(actor, "level", 1) or 1))
    runtime["fury_of_small_used"] = True
    runtime["fury_of_small_armed"] = False
    race_features["runtime"] = runtime
    actor.race_features = race_features
    lines.append({"text": f"Разъярённая мелкота: +{bonus} урона.", "muted": True})
    return bonus


def _has_damage_immunity(actor: Any, damage_type: str) -> bool:
    race_features = getattr(actor, "race_features", None)
    rf = race_features if isinstance(race_features, dict) else {}
    immunities_raw = rf.get("immunities")
    immunities = immunities_raw if isinstance(immunities_raw, dict) else {}
    damage_raw = immunities.get("damage")
    damage_items = damage_raw if isinstance(damage_raw, list) else []
    needle = str(damage_type or "").strip().lower()
    if not needle:
        return False
    for item in damage_items:
        if str(item or "").strip().lower() == needle:
            return True
    return False


def _has_condition_immunity(actor: Any, condition_key: str) -> bool:
    race_features = getattr(actor, "race_features", None)
    rf = race_features if isinstance(race_features, dict) else {}
    immunities_raw = rf.get("immunities")
    immunities = immunities_raw if isinstance(immunities_raw, dict) else {}
    cond_raw = immunities.get("conditions")
    cond_items = cond_raw if isinstance(cond_raw, list) else []
    needle = str(condition_key or "").strip().lower()
    if not needle:
        return False
    for item in cond_items:
        if str(item or "").strip().lower() == needle:
            return True
    return False


def _conditions_runtime(actor: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    conditions_raw = runtime.get("conditions")
    conditions = dict(conditions_raw) if isinstance(conditions_raw, dict) else {}
    return race_features, runtime, conditions


def _is_poisoned_condition_active(actor: Any) -> bool:
    _rf, _runtime, conditions = _conditions_runtime(actor)
    poisoned_raw = conditions.get("poisoned")
    poisoned = dict(poisoned_raw) if isinstance(poisoned_raw, dict) else {}
    if bool(poisoned.get("active")):
        return True
    return max(0, int(poisoned.get("remaining_rounds") or 0)) > 0


def _is_prone_condition_active(actor: Any) -> bool:
    race_features, runtime, conditions = _conditions_runtime(actor)
    _ = race_features
    _ = runtime
    prone_raw = conditions.get("prone")
    prone = dict(prone_raw) if isinstance(prone_raw, dict) else {}
    if bool(prone.get("active")):
        return True
    return max(0, int(prone.get("remaining_rounds") or 0)) > 0


def _actor_current_speed_ft(actor: Any) -> int:
    move_speed = max(0, int(getattr(actor, "move_speed_ft", 0) or 0))
    if move_speed > 0:
        return move_speed
    return max(0, int(getattr(actor, "speed_ft", 0) or 0))


def _proficiency_bonus_for_actor(actor: Any) -> int:
    level = max(1, int(getattr(actor, "level", 1) or 1))
    return max(2, int(proficiency_bonus(level)))


def _set_poisoned_condition(actor: Any, *, save_dc: int, rounds: int, source: str) -> None:
    race_features, runtime, conditions = _conditions_runtime(actor)
    poisoned_raw = conditions.get("poisoned")
    poisoned = dict(poisoned_raw) if isinstance(poisoned_raw, dict) else {}
    poisoned["active"] = True
    poisoned["save_dc"] = max(1, int(save_dc))
    poisoned["remaining_rounds"] = max(1, int(rounds))
    poisoned["repeat_save"] = "end_of_turn"
    poisoned["source"] = str(source or "effect").strip().lower() or "effect"
    conditions["poisoned"] = poisoned
    runtime["conditions"] = conditions
    race_features["runtime"] = runtime
    actor.race_features = race_features


def _consume_grung_weapon_poison_on_hit(
    *,
    session_id: str,
    attacker: Any,
    target: Any,
    profile: Any,
    lines: list[dict[str, Any]],
) -> tuple[Any, Any]:
    race_features = attacker.race_features if isinstance(attacker.race_features, dict) else {}
    features_raw = race_features.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    poison_skin_raw = features.get("poisonous_skin")
    poison_skin = poison_skin_raw if isinstance(poison_skin_raw, dict) else {}
    weapon_poison_raw = poison_skin.get("weapon_poison")
    weapon_poison = weapon_poison_raw if isinstance(weapon_poison_raw, dict) else {}
    if not weapon_poison:
        return get_combat(session_id), target

    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if not bool(runtime.get("grung_weapon_poison_armed")):
        return get_combat(session_id), target

    damage_type = str(getattr(profile, "damage_type", "") or "").strip().lower()
    if damage_type != "piercing":
        return get_combat(session_id), target

    runtime["grung_weapon_poison_armed"] = False
    race_features["runtime"] = runtime
    attacker.race_features = race_features

    dc = max(1, int(weapon_poison.get("save_dc") or 12))
    target_stats = target.stats if isinstance(getattr(target, "stats", None), dict) else {}
    con_stat = int(target_stats.get("con", 50)) if isinstance(target_stats.get("con"), int) else 50
    con_mod = ability_mod_from_stat100(con_stat)
    save_roll = random.randint(1, 20)
    save_total = save_roll + con_mod
    save_success = save_total >= dc
    lines.append(
        {
            "text": f"Яд грунга (оружие): спасбросок ТЕЛ цели d20({save_roll}) {con_mod:+d} = {save_total} vs DC {dc} -> {'успех' if save_success else 'провал'}.",
            "muted": True,
        }
    )
    if save_success:
        return get_combat(session_id), target

    damage_expr = str(weapon_poison.get("damage") or "2d4").strip().lower()
    parsed = parse_dice(damage_expr)
    if parsed is None:
        n, sides = 2, 4
    else:
        n, sides = parsed
    poison_rolls = [random.randint(1, max(1, sides)) for _ in range(max(1, n))]
    poison_damage = sum(poison_rolls)
    poison_damage_type = str(weapon_poison.get("damage_type") or "poison").strip().lower() or "poison"
    if _has_damage_immunity(target, poison_damage_type):
        poison_damage = 0
        lines.append({"text": "Цель иммунна к урону ядом: доп. урон = 0.", "muted": True})
    else:
        lines.append({"text": f"Яд грунга (оружие): +{poison_damage} ({damage_expr}) урона ядом.", "muted": True})
    if poison_damage <= 0:
        return get_combat(session_id), target
    state = apply_damage(session_id, target.key, poison_damage, source=attacker.key)
    if state is None:
        return None, target
    return state, state.combatants.get(target.key, target)


def _maybe_apply_grung_contact_poison_on_melee_hit(
    *,
    attacker: Any,
    target: Any,
    is_melee_hit: bool,
    lines: list[dict[str, Any]],
) -> None:
    if not is_melee_hit:
        return
    target_features_raw = getattr(target, "race_features", None)
    target_features = target_features_raw if isinstance(target_features_raw, dict) else {}
    target_race_features_raw = target_features.get("features")
    target_race_features = target_race_features_raw if isinstance(target_race_features_raw, dict) else {}
    poison_skin_raw = target_race_features.get("poisonous_skin")
    poison_skin = poison_skin_raw if isinstance(poison_skin_raw, dict) else {}
    if not poison_skin:
        return
    contact_raw = poison_skin.get("contact_condition")
    contact = contact_raw if isinstance(contact_raw, dict) else {}
    if not contact:
        return
    dc = max(1, int(poison_skin.get("contact_save_dc") or 12))
    if _has_condition_immunity(attacker, "poisoned"):
        lines.append({"text": "Ядовитая кожа: атакующий иммунен к состоянию «отравлен».", "muted": True})
        return
    attacker_stats = attacker.stats if isinstance(getattr(attacker, "stats", None), dict) else {}
    con_stat = int(attacker_stats.get("con", 50)) if isinstance(attacker_stats.get("con"), int) else 50
    con_mod = ability_mod_from_stat100(con_stat)
    save_roll = random.randint(1, 20)
    save_total = save_roll + con_mod
    save_success = save_total >= dc
    lines.append(
        {
            "text": f"Ядовитая кожа (контакт): спасбросок ТЕЛ d20({save_roll}) {con_mod:+d} = {save_total} vs DC {dc} -> {'успех' if save_success else 'провал'}.",
            "muted": True,
        }
    )
    if save_success:
        return
    duration_key = str(contact.get("duration") or "").strip().lower()
    rounds = 10 if duration_key == "1_minute" else max(1, int(contact.get("rounds") or 10))
    _set_poisoned_condition(attacker, save_dc=dc, rounds=rounds, source="grung_contact_poison")
    lines.append({"text": f"{attacker.name} получает состояние «отравлен» (до {rounds} раундов, повторы в конце хода).", "muted": True})


def _rabbit_hop_runtime(actor: Any) -> tuple[dict[str, Any], dict[str, Any], int]:
    race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    used = max(0, int(runtime.get("rabbit_hop_uses_used") or 0))
    return race_features, runtime, used


def _eerie_token_runtime(actor: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    return race_features, runtime


def _saving_face_allies_within_30ft(state: Any, actor: Any) -> int:
    side = str(getattr(actor, "side", "")).strip().lower()
    if not side:
        return 0
    allies = 0
    actor_key = str(getattr(actor, "key", "") or "")
    for key, combatant in (state.combatants or {}).items():
        if combatant is None:
            continue
        if str(getattr(combatant, "side", "")).strip().lower() != side:
            continue
        if str(key or "") == actor_key:
            continue
        if int(getattr(combatant, "hp_current", 0) or 0) <= 0 or bool(getattr(combatant, "is_dead", False)):
            continue
        allies += 1
    return allies


def _saving_face_state(actor: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    pending_raw = runtime.get("saving_face_pending")
    pending = dict(pending_raw) if isinstance(pending_raw, dict) else {}
    return race_features, runtime, pending


def _fearless_state(actor: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    pending_raw = runtime.get("fearless_pending_failed_frightened_save")
    pending = dict(pending_raw) if isinstance(pending_raw, dict) else {}
    return race_features, runtime, pending


def _can_offer_fearless(actor: Any) -> bool:
    if str(getattr(actor, "side", "")).strip().lower() != "pc":
        return False
    if not bool(getattr(actor, "reaction_available", True)):
        return False
    fearless_cfg = _race_feature(actor, "fearless_vs_frightened")
    if fearless_cfg is None:
        return False
    _race_features, runtime, _pending = _fearless_state(actor)
    uses_used = max(0, int(runtime.get("fearless_auto_success_used") or 0))
    uses_max = max(1, int(fearless_cfg.get("auto_success_max") or 1))
    return uses_used < uses_max


def _is_taunted_attack_disadvantage(attacker: Any, target: Any) -> bool:
    race_features = attacker.race_features if isinstance(getattr(attacker, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    taunted_raw = runtime.get("taunted")
    taunted = dict(taunted_raw) if isinstance(taunted_raw, dict) else {}
    if not bool(taunted.get("active")):
        return False
    taunter_key = str(taunted.get("by_actor_id") or "").strip()
    if not taunter_key:
        return False
    return str(getattr(target, "key", "") or "").strip() != taunter_key


def _select_taunt_target(state: Any, actor: Any, raw_text: str | None) -> Any | None:
    opponents: list[Any] = []
    actor_side = str(getattr(actor, "side", "") or "")
    for key in state.order:
        combatant = state.combatants.get(key)
        if combatant is None:
            continue
        if combatant.side == actor_side:
            continue
        if int(getattr(combatant, "hp_current", 0) or 0) <= 0:
            continue
        opponents.append(combatant)
    if not opponents:
        return None
    text_norm = str(raw_text or "").strip().lower()
    if text_norm:
        best = None
        best_len = -1
        for candidate in opponents:
            name = str(getattr(candidate, "name", "") or "").strip().lower()
            if not name:
                continue
            if name in text_norm and len(name) > best_len:
                best = candidate
                best_len = len(name)
        if best is not None:
            return best
    return opponents[0]


def _actor_ability_mod(actor: Any, ability_key: str) -> int:
    key = str(ability_key or "").strip().lower()
    if key not in {"str", "dex", "con", "int", "wis", "cha"}:
        return 0
    stats = getattr(actor, "stats", None)
    stats_dict = stats if isinstance(stats, dict) else {}
    score = int(stats_dict.get(key, 50)) if isinstance(stats_dict.get(key), int) else 50
    return ability_mod_from_stat100(score)


def _can_offer_saving_face(actor: Any) -> bool:
    if str(getattr(actor, "side", "")).strip().lower() != "pc":
        return False
    if not bool(getattr(actor, "reaction_available", True)):
        return False
    saving_face_cfg = _race_feature(actor, "saving_face")
    if saving_face_cfg is None:
        return False
    _race_features, runtime, _pending = _saving_face_state(actor)
    uses_used = max(0, int(runtime.get("saving_face_uses_used") or 0))
    uses_max = max(1, int(saving_face_cfg.get("uses_max") or 1))
    return uses_used < uses_max


def _set_saving_face_pending(actor: Any, pending: dict[str, Any]) -> None:
    race_features, runtime, _ = _saving_face_state(actor)
    runtime["saving_face_pending"] = pending
    race_features["runtime"] = runtime
    actor.race_features = race_features


def _extract_eerie_message_text(raw_text: str) -> str:
    txt = str(raw_text or "").strip()
    if not txt:
        return ""
    m = re.search(
        r"(?:переда\w+\s+сообщени\w+\s+сувенир\w*|телепатическ\w+\s+сообщени\w*|send\s+message)\s*[:\-]?\s*(.*)$",
        txt,
        flags=re.IGNORECASE,
    )
    if m:
        return str(m.group(1) or "").strip().strip("\"'«»")
    return ""


def _breath_weapon_dice_for_level(progression: list[dict[str, Any]], level: int) -> str:
    lvl = max(1, int(level))
    out = "2d6"
    for step in progression:
        if not isinstance(step, dict):
            continue
        level_from = max(1, int(step.get("level_from") or 1))
        dice = str(step.get("dice") or "").strip().lower()
        if not dice:
            continue
        if lvl >= level_from:
            out = dice
    return out


def _breath_area_text(area: dict[str, Any]) -> str:
    shape = str(area.get("shape") or "").strip().lower()
    if shape == "cone":
        cone_ft = max(0, int(area.get("cone_ft") or 0))
        if cone_ft > 0:
            return f"конус {cone_ft} фт"
    if shape == "line":
        line_ft = max(0, int(area.get("line_ft") or 0))
        width_ft = max(0, int(area.get("line_width_ft") or 0))
        if line_ft > 0 and width_ft > 0:
            return f"линия {line_ft}x{width_ft} фт"
        if line_ft > 0:
            return f"линия {line_ft} фт"
    return shape or "область"


def _spend_action_or_block(state: Any, actor: Any) -> dict[str, Any] | None:
    if actor.action_available:
        actor.action_available = False
        return None
    return {
        "status": _combat_status(state),
        "open": True,
        "lines": [{"text": "Действие недоступно: действие уже потрачено.", "muted": True}],
    }


def _spend_bonus_action_or_block(state: Any, actor: Any) -> dict[str, Any] | None:
    if actor.bonus_action_available:
        actor.bonus_action_available = False
        return None
    return {
        "status": _combat_status(state),
        "open": True,
        "lines": [{"text": "Бонусное действие недоступно: бонусное действие уже потрачено.", "muted": True}],
    }


def _spend_reaction_or_block(state: Any, actor: Any) -> dict[str, Any] | None:
    if actor.reaction_available:
        actor.reaction_available = False
        return None
    return {
        "status": _combat_status(state),
        "open": True,
        "lines": [{"text": "Реакция недоступна: реакция уже потрачена.", "muted": True}],
    }


def _hidden_step_state(actor: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    hidden_raw = runtime.get("hidden_step")
    hidden_step = dict(hidden_raw) if isinstance(hidden_raw, dict) else {}
    return race_features, runtime, hidden_step


def _is_hidden_step_active(actor: Any) -> bool:
    _rf, _runtime, hidden_step = _hidden_step_state(actor)
    return bool(hidden_step.get("active"))


def _break_hidden_step(actor: Any) -> bool:
    race_features, runtime, hidden_step = _hidden_step_state(actor)
    if not bool(hidden_step.get("active")):
        return False
    hidden_step["active"] = False
    runtime["hidden_step"] = hidden_step
    race_features["runtime"] = runtime
    actor.race_features = race_features
    return True


def _clamp_death_counter(value: int) -> int:
    return max(0, min(int(value), 3))


def _movement_budget_for_actor(actor: Any) -> tuple[int, int]:
    speed_ft = max(0, int(getattr(actor, "speed_ft", 30)))
    move_speed_ft = max(0, int(getattr(actor, "move_speed_ft", speed_ft)))
    move_remaining_ft = max(0, int(getattr(actor, "move_remaining_ft", move_speed_ft)))
    legacy_remaining = max(0, int(getattr(actor, "move_remaining", move_remaining_ft)))

    # Backward compatibility for tests/old snapshots that only filled legacy move_remaining/speed_ft.
    if move_speed_ft == 30 and speed_ft != 30:
        move_speed_ft = speed_ft
    if move_remaining_ft == max(0, int(getattr(actor, "move_speed_ft", 30))) and legacy_remaining != move_remaining_ft:
        move_remaining_ft = legacy_remaining

    return move_speed_ft, move_remaining_ft


def _resolve_actor_mode_speed(actor: Any, movement_mode: str) -> int:
    speed_ft = max(0, int(getattr(actor, "speed_ft", 30)))
    speeds = actor.movement_speeds if isinstance(getattr(actor, "movement_speeds", None), dict) else {}
    mode_speed_raw = speeds.get(movement_mode)
    if isinstance(mode_speed_raw, int) and not isinstance(mode_speed_raw, bool):
        return max(0, int(mode_speed_raw))
    return speed_ft


def _set_movement_mode_without_budget_reset(actor: Any, mode: str) -> None:
    mover_mode = str(mode or "").strip().lower() or "walk"
    _, remaining = _movement_budget_for_actor(actor)
    actor.movement_mode = mover_mode
    actor.move_speed_ft = _resolve_actor_mode_speed(actor, mover_mode)
    actor.move_remaining_ft = remaining
    actor.move_remaining = remaining


def _charge_hooves_text() -> str:
    return "Разбег: можно бонусным действием ударить копытами (напиши 'копыта')."


def _has_charge_feature(actor: Any) -> bool:
    cfg = _race_feature(actor, "charge")
    return isinstance(cfg, dict) and bool(cfg)


def _has_equine_climb_penalty(actor: Any) -> int:
    race_features = getattr(actor, "race_features", None)
    rf = race_features if isinstance(race_features, dict) else {}
    movement = rf.get("movement") if isinstance(rf.get("movement"), dict) else {}
    extra = movement.get("climb_extra_cost_ft_per_ft")
    if isinstance(extra, int) and not isinstance(extra, bool) and extra > 0:
        return int(extra)
    return 0


def handle_live_combat_reaction(
    action: str, session_id: str, actor_key: str
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None, "Combat is not active"
    if action != "combat_stone_endurance":
        return None, "Unknown combat reaction"

    actor = state.combatants.get(actor_key)
    if actor is None:
        return None, "Combatant not found"
    if actor.side != "pc":
        return None, "Реакция доступна только персонажу игрока."
    if not bool(getattr(actor, "reaction_available", True)):
        return None, "Реакция недоступна: реакция уже потрачена."

    race_features = actor.race_features if isinstance(actor.race_features, dict) else {}
    features = race_features.get("features") if isinstance(race_features.get("features"), dict) else {}
    stone_endurance = (
        features.get("stone_endurance")
        if isinstance(features, dict) and isinstance(features.get("stone_endurance"), dict)
        else None
    )
    if stone_endurance is None:
        return None, "Каменная выносливость недоступна."

    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if bool(runtime.get("stone_endurance_used", False)):
        return None, "Каменная выносливость уже использована до короткого/долгого отдыха."

    last_damage = max(0, int(getattr(actor, "last_damage_taken", 0)))
    last_damage_round = max(0, int(getattr(actor, "last_damage_taken_round", 0)))
    if last_damage <= 0 or last_damage_round != max(1, int(state.round_no)):
        return None, "Нет свежего полученного урона для применения реакции."

    stats = actor.stats if isinstance(actor.stats, dict) else {}
    con_raw = stats.get("con", 50)
    con_score = int(con_raw) if isinstance(con_raw, int) and not isinstance(con_raw, bool) else 50
    con_mod = ability_mod_from_stat100(con_score)
    roll = random.randint(1, 12)
    reduction = max(0, roll + con_mod)
    actual_reduction = min(reduction, last_damage)

    actor.hp_current = min(max(0, int(actor.hp_max)), max(0, int(actor.hp_current)) + actual_reduction)
    actor.reaction_available = False
    runtime["stone_endurance_used"] = True
    race_features["runtime"] = runtime
    actor.race_features = race_features

    return (
        {
            "status": _combat_status(state),
            "open": True,
            "lines": [
                {
                    "text": (
                        "Каменная выносливость: снижает урон на "
                        f"{actual_reduction} ({roll}+{con_mod})."
                    )
                },
                {"text": f"HP восстановлено: +{actual_reduction}."},
                {"text": f"{actor.name}: HP {actor.hp_current}/{actor.hp_max}"},
            ],
        },
        None,
    )


def parse_heal_dice(expr: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"\s*(\d+)[dD](\d+)(?:\+(\d+))?\s*", expr)
    if match is None:
        return None
    n = int(match.group(1))
    sides = int(match.group(2))
    bonus = int(match.group(3)) if match.group(3) is not None else 0
    if n <= 0 or sides <= 0:
        return None
    return n, sides, bonus


def _select_weakest_healing_consumable(actor: Any) -> tuple[int, dict[str, Any], Any] | None:
    inventory = actor.inventory if isinstance(actor.inventory, list) else []
    candidates: list[tuple[float, str, str, int, dict[str, Any], Any]] = []

    for idx, entry in enumerate(inventory):
        if not isinstance(entry, dict):
            continue
        def_key = entry.get("def")
        if not isinstance(def_key, str):
            continue
        item_def = ITEMS.get(def_key)
        if item_def is None:
            continue
        consume = item_def.consume
        if consume is None:
            continue
        has_healing = bool(consume.heal_dice) or int(consume.heal_flat) > 0
        if not has_healing:
            continue
        qty_raw = entry.get("qty", 0)
        qty = qty_raw if isinstance(qty_raw, int) else 0
        if qty < 1:
            continue

        expected_heal = float(int(consume.heal_flat))
        parsed_heal = parse_heal_dice(consume.heal_dice) if isinstance(consume.heal_dice, str) else None
        if parsed_heal is not None:
            n, sides, bonus = parsed_heal
            expected_heal += (n * (sides + 1) / 2) + bonus

        item_id_raw = entry.get("id")
        item_id = item_id_raw if isinstance(item_id_raw, str) else ""
        candidates.append((expected_heal, def_key, item_id, idx, entry, item_def))

    if not candidates:
        return None

    _, _, _, idx, entry, item_def = min(candidates, key=lambda value: (value[0], value[1], value[2]))
    return idx, entry, item_def


def _consume_healing_item(actor: Any, consumable_idx: int, consumable_entry: dict[str, Any], consumable_def: Any) -> int:
    inventory = actor.inventory if isinstance(actor.inventory, list) else []
    qty_now = int(consumable_entry.get("qty", 0)) - 1
    if qty_now <= 0:
        inventory.pop(consumable_idx)
    else:
        consumable_entry["qty"] = qty_now

    consume = consumable_def.consume
    assert consume is not None
    heal_from_dice = 0
    parsed_heal = parse_heal_dice(consume.heal_dice) if isinstance(consume.heal_dice, str) else None
    if parsed_heal is not None:
        n, sides, bonus = parsed_heal
        heal_from_dice = sum(random.randint(1, sides) for _ in range(n)) + bonus

    heal_amount = max(0, heal_from_dice + int(consume.heal_flat))
    pre_hp = actor.hp_current
    actor.hp_current = min(actor.hp_max, max(0, actor.hp_current) + heal_amount)
    if pre_hp <= 0 and actor.hp_current > 0 and not actor.is_dead:
        actor.is_stable = False
        actor.death_successes = 0
        actor.death_failures = 0

    return heal_amount


def _auto_resolve_zero_hp_turns(session_id: str, state: Any) -> dict[str, Any] | None:
    if not state.order:
        return None

    lines: list[dict[str, Any]] = []
    max_iterations = len(state.order) + 1
    iterations_done = 0
    while iterations_done < max_iterations:
        if not state.order:
            break

        current_key = state.order[state.turn_index]
        current = state.combatants.get(current_key)
        if current is None:
            iterations_done += 1
            state = advance_turn(session_id)
            if state is None:
                return None
            continue

        if current.hp_current > 0 and not current.is_dead:
            break

        if current.side == "enemy" and current.hp_current <= 0:
            lines.append({"text": f"Ход пропущен: {current.name} (повержен).", "muted": True})
            iterations_done += 1
            state = advance_turn(session_id)
            if state is None:
                return None
            continue

        if current.side == "pc" and current.hp_current <= 0:
            if current.is_dead:
                lines.append({"text": f"Ход пропущен: {current.name} (мёртв).", "muted": True})
            elif current.is_stable:
                lines.append({"text": f"Ход пропущен: {current.name} (без сознания, стабилен).", "muted": True})
            else:
                consumable = _select_weakest_healing_consumable(current)
                if consumable is not None:
                    consumable_idx, consumable_entry, consumable_def = consumable
                    heal_amount = _consume_healing_item(current, consumable_idx, consumable_entry, consumable_def)
                    lines.append({"text": f"Авто-предмет: {consumable_def.name_ru} (подняться с 0 HP)", "muted": True})
                    lines.append({"text": f"Лечение: {heal_amount} HP"})
                    lines.append({"text": f"{current.name}: HP {current.hp_current}/{current.hp_max}"})
                else:
                    _roll_a, _roll_b, roll = _roll_check_compat(
                        "normal",
                        reroll_ones=_has_reroll_ones_scope(current, "save"),
                    )
                    roll_extras: list[dict[str, Any]] = []
                    roll = _maybe_apply_built_for_success(current, roll, roll_extras)
                    lines.append({"text": f"Спасбросок смерти: d20({roll})"})
                    lines.extend(roll_extras)
                    if roll == 20:
                        current.hp_current = 1
                        current.is_stable = False
                        current.death_successes = 0
                        current.death_failures = 0
                        lines.append({"text": "Результат: 20 — ты приходишь в себя (1 HP)."})
                    elif roll == 1:
                        current.death_failures = _clamp_death_counter(current.death_failures + 2)
                        lines.append({"text": "Результат: 1 — два провала."})
                    elif roll >= 10:
                        current.death_successes = _clamp_death_counter(current.death_successes + 1)
                        lines.append({"text": "Результат: успех."})
                    else:
                        current.death_failures = _clamp_death_counter(current.death_failures + 1)
                        lines.append({"text": "Результат: провал."})

                    if roll != 20:
                        current.death_successes = _clamp_death_counter(current.death_successes)
                        current.death_failures = _clamp_death_counter(current.death_failures)
                        if current.death_failures >= 3:
                            current.is_dead = True
                            current.is_stable = False
                            lines.append({"text": f"Смерть: {current.name} погибает."})
                            _revert_shapechanger_on_death(current, lines)
                        elif current.death_successes >= 3:
                            current.is_stable = True
                            lines.append({"text": f"Стабилизация: {current.name} стабилен (без сознания)."})

            iterations_done += 1
            state = advance_turn(session_id)
            if state is None:
                return None
            lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
            continue

        break

    if not lines:
        return None

    side_pc_alive = any(c.side == "pc" and c.hp_current > 0 and not c.is_dead for c in state.combatants.values())
    side_enemy_alive = any(c.side == "enemy" and c.hp_current > 0 for c in state.combatants.values())
    if not side_pc_alive or not side_enemy_alive:
        if not side_enemy_alive:
            lines.append({"text": "Победа: противники повержены.", "muted": True})
        if not side_pc_alive:
            lines.append({"text": "Поражение: все герои выбыли.", "muted": True})
        end_combat(session_id)
        return {
            "status": "Бой завершён",
            "open": False,
            "lines": lines,
        }

    return {
        "status": _combat_status(state),
        "open": True,
        "lines": lines,
    }


def handle_live_combat_action(
    action: str,
    session_id: str,
    *,
    distance_ft: int | None = None,
    empower: str | None = None,
    raw_text: str | None = None,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    state = get_combat(session_id)
    if state is not None and state.active:
        auto_skip_patch = _auto_resolve_zero_hp_turns(session_id, state)
        if auto_skip_patch is not None:
            return auto_skip_patch, None

    if action == "combat_end_turn":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"

        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [{"text": f"Ход передан: {current_turn_label(state)}", "muted": True}],
            },
            None,
        )

    if action == "combat_takeoff":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"

        movement_speeds = actor.movement_speeds if isinstance(actor.movement_speeds, dict) else {}
        fly_speed = int(movement_speeds.get("fly", 0)) if isinstance(movement_speeds.get("fly", 0), int) else 0
        if fly_speed <= 0:
            return None, "Полёт недоступен (броня/нет крыльев)"

        actor.movement_mode = "fly"
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [{"text": f"{actor.name} взлетает."}],
            },
            None,
        )

    if action in {"combat_mode_walk", "combat_mode_swim", "combat_mode_climb"}:
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )
        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        mode = action.replace("combat_mode_", "", 1)
        mode_ru = {"walk": "ходьбы", "swim": "плавания", "climb": "лазания"}.get(mode, mode)
        _set_movement_mode_without_budget_reset(actor, mode)
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [{"text": f"{actor.name} переключается в режим {mode_ru}.", "muted": True}],
            },
            None,
        )

    if action == "combat_land":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"

        actor.movement_mode = "walk"
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [{"text": f"{actor.name} приземляется."}],
            },
            None,
        )

    if action == "combat_dodge":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        attacker.dodge_active = True
        lines: list[dict[str, Any]] = [{"text": f"Уклонение: {attacker.name} (до следующего хода)", "muted": True}]

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_dash":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        attacker.dash_active = True
        base_move_speed, remaining_ft = _movement_budget_for_actor(attacker)
        attacker.move_speed_ft = base_move_speed
        attacker.move_remaining_ft = remaining_ft + base_move_speed
        attacker.move_remaining = attacker.move_remaining_ft
        lines: list[dict[str, Any]] = [
            {"text": f"Рывок: {attacker.name} (до следующего хода)", "muted": True},
            {"text": f"Движение: +{base_move_speed} (итого {attacker.move_remaining_ft})", "muted": True},
        ]

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_move":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        mover_key = state.order[state.turn_index]
        mover = state.combatants.get(mover_key)
        if mover is None:
            return None, "Combat state is inconsistent"

        dist = int(distance_ft) if isinstance(distance_ft, int) and not isinstance(distance_ft, bool) else 0
        if dist <= 0:
            return None, "Укажи расстояние перемещения в футах (больше 0)."

        _mode_speed, remaining = _movement_budget_for_actor(mover)
        mover.move_speed_ft = _mode_speed
        mode = str(getattr(mover, "movement_mode", "") or "walk").strip().lower() or "walk"
        climb_extra_cost = _has_equine_climb_penalty(mover)
        move_cost = dist
        extra_lines: list[dict[str, Any]] = []
        if mode == "climb" and climb_extra_cost > 0:
            move_cost = dist * (1 + climb_extra_cost)
            extra_lines.append(
                {
                    "text": (
                        f"Лошадиное телосложение: лазание стоит +{climb_extra_cost} фт за 1 фт "
                        f"(потрачено {move_cost} фт)."
                    ),
                    "muted": True,
                }
            )
        if move_cost > remaining:
            return None, f"Недостаточно перемещения: осталось {remaining} фт."

        mover.move_remaining_ft = remaining - move_cost
        mover.move_remaining = mover.move_remaining_ft
        mover.moved_this_turn_ft = max(0, int(getattr(mover, "moved_this_turn_ft", 0))) + dist
        lines = [{"text": f"{mover.name} перемещается на {dist} фт (осталось {mover.move_remaining_ft} фт)."}]
        lines.extend(extra_lines)
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_disengage":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        blocked = None
        used_bonus_action = False
        if _has_nimble_escape(attacker) and bool(getattr(attacker, "bonus_action_available", False)):
            blocked = _spend_bonus_action_or_block(state, attacker)
            used_bonus_action = blocked is None
        else:
            blocked = _spend_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        attacker.disengage_active = True
        lines: list[dict[str, Any]] = [{"text": f"Отход: {attacker.name} (до следующего хода)", "muted": True}]
        if used_bonus_action:
            lines.append({"text": "Ловкое бегство: потрачено бонусное действие.", "muted": True})

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_hide":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        if not _has_nimble_escape(attacker):
            return None, "Скрытность бонусным действием доступна только через «Шустрый побег»."
        blocked = _spend_bonus_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None
        _arm_nimble_escape_hide(attacker)
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [
                    {"text": f"{attacker.name} прячется (Шустрый побег).", "muted": True},
                    {"text": "Скрытность: преимущество на следующую атаку.", "muted": True},
                ],
            },
            None,
        )

    if action == "combat_rabbit_hop":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        if str(getattr(attacker, "side", "")).lower() != "pc":
            return None, "Кроличий прыжок доступен только персонажу игрока."
        rabbit_cfg = _race_feature(attacker, "rabbit_hop")
        if rabbit_cfg is None:
            return None, "Кроличий прыжок недоступен."
        if _actor_current_speed_ft(attacker) <= 0:
            return None, "Кроличий прыжок недоступен: скорость должна быть больше 0."
        uses_max = _proficiency_bonus_for_actor(attacker)
        race_features, runtime, used = _rabbit_hop_runtime(attacker)
        if used >= uses_max:
            return None, "Кроличий прыжок исчерпан до долгого отдыха."
        blocked = _spend_bonus_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None
        used += 1
        runtime["rabbit_hop_uses_used"] = used
        runtime["rabbit_hop_no_oa"] = True
        runtime["rabbit_hop_no_oa_round"] = max(1, int(getattr(state, "round_no", 1) or 1))
        race_features["runtime"] = runtime
        attacker.race_features = race_features

        distance_ft = 5 * _proficiency_bonus_for_actor(attacker)
        remaining = max(0, uses_max - used)
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [
                    {"text": f"Кроличий прыжок: {attacker.name} перемещается на {distance_ft} фт (без провоцированных атак)."},
                    {"text": f"Осталось: {remaining}/{uses_max}.", "muted": True},
                ],
            },
            None,
        )

    if action == "combat_lucky_footwork":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        if str(getattr(actor, "side", "")).lower() != "pc":
            return None, "Сильные ноги доступны только персонажу игрока."
        lucky_cfg = _race_feature(actor, "lucky_footwork")
        if lucky_cfg is None:
            return None, "Сильные ноги недоступны."
        if _is_prone_condition_active(actor):
            return None, "Сильные ноги недоступны: вы сбиты с ног."
        if _actor_current_speed_ft(actor) <= 0:
            return None, "Сильные ноги недоступны: скорость должна быть больше 0."

        race_features = actor.race_features if isinstance(actor.race_features, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        failed_raw = runtime.get("last_failed_dex_save")
        failed = dict(failed_raw) if isinstance(failed_raw, dict) else {}
        dc = max(0, int(failed.get("dc") or 0))
        total = int(failed.get("total") or 0)
        if dc <= 0:
            return None, "Нет проваленного спасброска Ловкости для «Сильных ног»."
        blocked = _spend_reaction_or_block(state, actor)
        if blocked is not None:
            return blocked, None
        bonus = random.randint(1, 4)
        new_total = total + bonus
        success = new_total >= dc
        failed["bonus"] = bonus
        failed["new_total"] = new_total
        failed["used_reaction"] = True
        failed["resolved"] = True
        failed["success"] = success
        runtime["last_dex_save_result"] = failed
        runtime.pop("last_failed_dex_save", None)
        race_features["runtime"] = runtime
        actor.race_features = race_features
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [
                    {
                        "text": (
                            f"Сильные ноги: +{bonus} (1d4) к спасброску Ловкости -> "
                            f"{new_total} vs DC {dc} ({'успех' if success else 'провал'})."
                        )
                    }
                ],
            },
            None,
        )

    if action == "combat_saving_face":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )
        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        selected_actor = actor
        selected_cfg = _race_feature(selected_actor, "saving_face")
        _, _, selected_pending = _saving_face_state(selected_actor)
        if (
            str(getattr(selected_actor, "side", "")).lower() != "pc"
            or selected_cfg is None
            or not selected_pending
        ):
            fallback_candidates: list[Any] = []
            for candidate in state.combatants.values():
                if str(getattr(candidate, "side", "")).lower() != "pc":
                    continue
                candidate_cfg = _race_feature(candidate, "saving_face")
                if candidate_cfg is None:
                    continue
                _, _, candidate_pending = _saving_face_state(candidate)
                if candidate_pending:
                    fallback_candidates.append(candidate)
            if len(fallback_candidates) == 1:
                selected_actor = fallback_candidates[0]
                selected_cfg = _race_feature(selected_actor, "saving_face")
            elif len(fallback_candidates) > 1:
                return None, "У нескольких союзников есть «Сохранить лицо»: используйте реакцию сразу после своего провала."
            else:
                if str(getattr(actor, "side", "")).lower() != "pc":
                    return None, "Сохранить лицо доступно только персонажу игрока."
                if selected_cfg is None:
                    return None, "Сохранить лицо недоступно."
                return None, "Нет подходящего провала для «Сохранить лицо»."

        actor = selected_actor
        saving_face_cfg = selected_cfg if isinstance(selected_cfg, dict) else None
        if saving_face_cfg is None:
            return None, "Сохранить лицо недоступно."
        race_features, runtime, pending = _saving_face_state(actor)
        if not pending:
            return None, "Нет подходящего провала для «Сохранить лицо»."
        uses_used = max(0, int(runtime.get("saving_face_uses_used") or 0))
        uses_max = max(1, int(saving_face_cfg.get("uses_max") or 1))
        if uses_used >= uses_max:
            return None, "«Сохранить лицо» уже использовано до отдыха."
        allies = _saving_face_allies_within_30ft(state, actor)
        bonus = min(max(0, allies), 5)
        if bonus <= 0:
            return None, "Нет союзников в пределах 30 фт: «Сохранить лицо» не срабатывает."
        blocked = _spend_reaction_or_block(state, actor)
        if blocked is not None:
            return blocked, None

        kind = str(pending.get("kind") or "").strip().lower()
        total_before = int(pending.get("total") or 0)
        total_after = total_before + bonus
        dc = max(0, int(pending.get("dc") or 0))
        ac = max(0, int(pending.get("ac") or 0))
        lines: list[dict[str, Any]] = []
        runtime["saving_face_uses_used"] = uses_used + 1
        runtime.pop("saving_face_pending", None)

        if kind == "attack":
            target_key = str(pending.get("target_key") or "").strip()
            target = state.combatants.get(target_key) if target_key else None
            if target is None or int(getattr(target, "hp_current", 0) or 0) <= 0:
                lines.append({"text": "Сохранить лицо: цель атаки недоступна.", "muted": True})
            else:
                became_hit = total_after >= ac
                lines.append(
                    {
                        "text": (
                            f"Сохранить лицо: +{bonus} к броску атаки ({total_before} -> {total_after}) "
                            f"vs AC {ac} ({'попадание' if became_hit else 'промах'})."
                        )
                    }
                )
                if became_hit:
                    damage_roll = max(0, int(pending.get("damage_roll") or 0))
                    damage_bonus = int(pending.get("damage_bonus") or 0)
                    damage_type = str(pending.get("damage_type") or "").strip().lower() or "physical"
                    total_damage = max(0, damage_roll + damage_bonus)
                    total_damage, surprise_lines = _apply_surprise_attack_bonus(
                        state=state,
                        attacker=actor,
                        target=target,
                        is_hit=True,
                        is_crit=False,
                        total_damage=total_damage,
                    )
                    lines.extend(surprise_lines)
                    fury_bonus = _maybe_apply_fury_of_small(actor=actor, target=target, lines=lines)
                    if fury_bonus > 0:
                        total_damage += fury_bonus
                    bonus_damage, bonus_damage_type = _aasimar_bonus_damage_for_hit(actor)
                    if bonus_damage > 0:
                        total_damage += bonus_damage
                        lines.append(
                            {"text": f"Доп. урон трансформации: +{bonus_damage} {bonus_damage_type} (1/ход).", "muted": True}
                        )
                    pre_hp = target.hp_current
                    damage_to_apply, relentless_lines = _apply_relentless_endurance_if_needed(target=target, incoming_damage=total_damage)
                    lines.extend(relentless_lines)
                    state = apply_damage(session_id, target.key, damage_to_apply, source=actor.key)
                    if state is None:
                        return None, "Combat is not active"
                    target = state.combatants.get(target.key, target)
                    profile = SimpleNamespace(
                        damage_type=damage_type,
                        is_melee_weapon=bool(pending.get("is_melee_weapon")),
                    )
                    state_after_poison, target_after_poison = _consume_grung_weapon_poison_on_hit(
                        session_id=session_id,
                        attacker=actor,
                        target=target,
                        profile=profile,
                        lines=lines,
                    )
                    if state_after_poison is None:
                        return None, "Combat is not active"
                    state = state_after_poison
                    target = target_after_poison
                    _maybe_apply_grung_contact_poison_on_melee_hit(
                        attacker=actor,
                        target=target,
                        is_melee_hit=bool(pending.get("is_melee_weapon")),
                        lines=lines,
                    )
                    lines.append(
                        {
                            "text": f"Урон (Сохранить лицо): {max(0, int(damage_to_apply))} {damage_type}. {target.name}: HP {target.hp_current}/{target.hp_max}",
                            "muted": True,
                        }
                    )
                    if target.side == "pc" and pre_hp > 0 and target.hp_current == 0:
                        leftover = total_damage - pre_hp
                        if leftover >= target.hp_max:
                            target.is_dead = True
                            target.is_stable = False
                            lines.append({"text": f"Мгновенная смерть: {target.name} погибает.", "muted": True})
                            _revert_shapechanger_on_death(target, lines)
        elif kind in {"check", "save"}:
            success = total_after >= dc
            lines.append(
                {
                    "text": (
                        f"Сохранить лицо: +{bonus} к {kind} ({total_before} -> {total_after}) "
                        f"vs DC {dc} ({'успех' if success else 'провал'})."
                    )
                }
            )
        else:
            lines.append({"text": "Сохранить лицо: неподдерживаемый тип контекста.", "muted": True})

        race_features["runtime"] = runtime
        actor.race_features = race_features
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_taunt":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )
        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        if str(getattr(actor, "side", "")).lower() != "pc":
            return None, "Насмешка доступна только персонажу игрока."
        taunt_cfg = _race_feature(actor, "taunt")
        if taunt_cfg is None:
            return None, "Насмешка недоступна."
        blocked = _spend_bonus_action_or_block(state, actor)
        if blocked is not None:
            return blocked, None
        target = _select_taunt_target(state, actor, raw_text)
        if target is None:
            return None, "Нет подходящей цели для «Насмешки»."
        chosen_ability = str(taunt_cfg.get("chosen_ability") or "cha").strip().lower()
        if chosen_ability not in {"int", "wis", "cha"}:
            chosen_ability = "cha"
        dc = 8 + _proficiency_bonus_for_actor(actor) + _actor_ability_mod(actor, chosen_ability)
        wis_mod = _actor_ability_mod(target, "wis")
        save_roll = random.randint(1, 20)
        save_total = save_roll + wis_mod
        save_success = save_total >= dc
        lines: list[dict[str, Any]] = [
            {"text": f"Насмешка: {actor.name} выбирает целью {target.name}.", "muted": True},
            {
                "text": (
                    f"Спасбросок МДР цели: d20({save_roll}) {wis_mod:+d} = {save_total} vs DC {dc} "
                    f"({'успех' if save_success else 'провал'})."
                ),
                "muted": True,
            },
        ]
        if save_success:
            lines.append({"text": "Насмешка: цель устояла (успех спасброска)."})
        else:
            target_rf = target.race_features if isinstance(target.race_features, dict) else {}
            target_runtime_raw = target_rf.get("runtime")
            target_runtime = dict(target_runtime_raw) if isinstance(target_runtime_raw, dict) else {}
            target_runtime["taunted"] = {
                "active": True,
                "by_actor_id": str(getattr(actor, "key", "") or ""),
                "expires_on_turn_start_of_actor_id": str(getattr(actor, "key", "") or ""),
                "source": "kender_taunt",
            }
            target_rf["runtime"] = target_runtime
            target.race_features = target_rf
            lines.append(
                {
                    "text": (
                        "Насмешка: цель провалила спасбросок Мудрости "
                        f"(Сл {dc}) — атаки по другим с помехой до начала вашего следующего хода."
                    )
                }
            )
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_fearless":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )
        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        selected_actor = actor
        selected_cfg = _race_feature(selected_actor, "fearless_vs_frightened")
        _, _, selected_pending = _fearless_state(selected_actor)
        if (
            str(getattr(selected_actor, "side", "")).lower() != "pc"
            or selected_cfg is None
            or not selected_pending
        ):
            fallback_candidates: list[Any] = []
            for candidate in state.combatants.values():
                if str(getattr(candidate, "side", "")).lower() != "pc":
                    continue
                candidate_cfg = _race_feature(candidate, "fearless_vs_frightened")
                if candidate_cfg is None:
                    continue
                _, _, candidate_pending = _fearless_state(candidate)
                if candidate_pending:
                    fallback_candidates.append(candidate)
            if len(fallback_candidates) == 1:
                selected_actor = fallback_candidates[0]
                selected_cfg = _race_feature(selected_actor, "fearless_vs_frightened")
            elif len(fallback_candidates) > 1:
                return None, "У нескольких союзников есть «Бесстрашие»: используйте реакцию сразу после своего провала."
            else:
                if str(getattr(actor, "side", "")).lower() != "pc":
                    return None, "Бесстрашие доступно только персонажу игрока."
                if selected_cfg is None:
                    return None, "Бесстрашие недоступно."
                return None, "Нет проваленного спасброска против испуга для «Бесстрашия»."

        actor = selected_actor
        fearless_cfg = selected_cfg if isinstance(selected_cfg, dict) else None
        if fearless_cfg is None:
            return None, "Бесстрашие недоступно."
        race_features, runtime, pending = _fearless_state(actor)
        if not pending:
            return None, "Нет проваленного спасброска против испуга для «Бесстрашия»."
        uses_used = max(0, int(runtime.get("fearless_auto_success_used") or 0))
        uses_max = max(1, int(fearless_cfg.get("auto_success_max") or 1))
        if uses_used >= uses_max:
            return None, "«Бесстрашие» уже использовано до долгого отдыха."
        blocked = _spend_reaction_or_block(state, actor)
        if blocked is not None:
            return blocked, None
        dc = max(0, int(pending.get("dc") or 0))
        total = int(pending.get("total") or 0)
        runtime["fearless_auto_success_used"] = uses_used + 1
        pending["resolved"] = True
        pending["forced_success"] = True
        pending["used_reaction"] = True
        pending["new_total"] = max(total, dc)
        runtime["fearless_last_result"] = pending
        runtime.pop("fearless_pending_failed_frightened_save", None)
        race_features["runtime"] = runtime
        actor.race_features = race_features
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [
                    {
                        "text": (
                            "Бесстрашие: проваленный спасбросок против испуга становится успешным "
                            f"(DC {dc}, было {total}, стало успех)."
                        )
                    }
                ],
            },
            None,
        )

    if action == "combat_eerie_token_create":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        if str(getattr(actor, "side", "")).lower() != "pc":
            return None, "Жуткий сувенир доступен только персонажу игрока."
        eerie_cfg = _race_feature(actor, "eerie_token")
        if eerie_cfg is None:
            return None, "Жуткий сувенир недоступен."
        uses_max = max(1, int(eerie_cfg.get("uses_max") or 1))
        race_features, runtime = _eerie_token_runtime(actor)
        used = max(0, int(runtime.get("eerie_token_uses_used") or 0))
        if used >= uses_max:
            return None, "Жуткий сувенир уже использован до долгого отдыха."
        blocked = _spend_bonus_action_or_block(state, actor)
        if blocked is not None:
            return blocked, None
        runtime["eerie_token_uses_used"] = used + 1
        runtime["eerie_token_active"] = True
        runtime["eerie_token_consumed"] = False
        runtime["eerie_token_created_at"] = datetime.now(timezone.utc).isoformat()
        runtime["eerie_token_expires_on_next_long_rest"] = True
        race_features["runtime"] = runtime
        actor.race_features = race_features
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [
                    {"text": f"{actor.name} создаёт Жуткий сувенир.", "muted": True},
                    {"text": f"Жуткий сувенир: активен. Осталось использований: {max(0, uses_max - used - 1)}/{uses_max}.", "muted": True},
                ],
            },
            None,
        )

    if action == "combat_eerie_token_message":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        if str(getattr(actor, "side", "")).lower() != "pc":
            return None, "Жуткий сувенир доступен только персонажу игрока."
        eerie_cfg = _race_feature(actor, "eerie_token")
        if eerie_cfg is None:
            return None, "Жуткий сувенир недоступен."
        race_features, runtime = _eerie_token_runtime(actor)
        if not bool(runtime.get("eerie_token_active")) or bool(runtime.get("eerie_token_consumed")):
            return None, "Нет активного Жуткого сувенира."
        message = _extract_eerie_message_text(raw_text or "")
        if not message:
            return None, "Укажите текст сообщения после команды (до 25 слов)."
        words = [w for w in re.findall(r"\S+", message) if w.strip()]
        max_words = max(1, int(eerie_cfg.get("message_words_max") or 25))
        if len(words) > max_words:
            return None, f"Сообщение слишком длинное: максимум {max_words} слов."
        blocked = _spend_action_or_block(state, actor)
        if blocked is not None:
            return blocked, None
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [
                    {"text": "Жуткий сувенир: сообщение (<=25 слов) отправлено носителю (до 10 миль).", "muted": True},
                ],
            },
            None,
        )

    if action == "combat_eerie_token_view":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        if str(getattr(actor, "side", "")).lower() != "pc":
            return None, "Жуткий сувенир доступен только персонажу игрока."
        eerie_cfg = _race_feature(actor, "eerie_token")
        if eerie_cfg is None:
            return None, "Жуткий сувенир недоступен."
        race_features, runtime = _eerie_token_runtime(actor)
        if not bool(runtime.get("eerie_token_active")) or bool(runtime.get("eerie_token_consumed")):
            return None, "Нет активного Жуткого сувенира."
        blocked = _spend_action_or_block(state, actor)
        if blocked is not None:
            return blocked, None
        runtime["eerie_token_active"] = False
        runtime["eerie_token_consumed"] = True
        race_features["runtime"] = runtime
        actor.race_features = race_features
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [
                    {"text": "Жуткий сувенир: вы видите/слышите вокруг сувенира 1 минуту (до 10 миль). Сувенир уничтожен.", "muted": True},
                ],
            },
            None,
        )

    if action in {"combat_fury_of_small", "combat_fury_of_the_small"}:
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )
        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        if str(getattr(attacker, "side", "")).lower() != "pc":
            return None, "Разъярённая мелкота доступна только персонажу игрока."
        fury_cfg = _race_feature(attacker, "fury_of_the_small")
        if fury_cfg is None:
            return None, "Разъярённая мелкота недоступна."
        race_features = attacker.race_features if isinstance(attacker.race_features, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        if bool(runtime.get("fury_of_small_used")):
            return None, "Разъярённая мелкота уже использована до отдыха."
        if bool(runtime.get("fury_of_small_armed")):
            return None, "Разъярённая мелкота уже готова: сработает при следующем подходящем уроне."
        runtime["fury_of_small_armed"] = True
        race_features["runtime"] = runtime
        attacker.race_features = race_features
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [
                    {"text": f"{attacker.name}: Разъярённая мелкота подготовлена.", "muted": True},
                    {"text": "Сработает при следующем уроне по существу больше вас.", "muted": True},
                ],
            },
            None,
        )

    if action == "combat_grung_poison_weapon":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        if str(getattr(attacker, "side", "")).lower() != "pc":
            return None, "Яд грунга на оружии доступен только персонажу игрока."
        poison_skin = _race_feature(attacker, "poisonous_skin")
        if poison_skin is None:
            return None, "Ядовитая кожа недоступна."
        weapon_poison_raw = poison_skin.get("weapon_poison")
        weapon_poison = weapon_poison_raw if isinstance(weapon_poison_raw, dict) else {}
        if not weapon_poison:
            return None, "Яд на оружии недоступен."
        blocked = _spend_bonus_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        stats = attacker.stats if isinstance(attacker.stats, dict) else {}
        inventory = attacker.inventory if isinstance(attacker.inventory, list) else []
        equip_map = attacker.equip if isinstance(attacker.equip, dict) else {}
        profile = compute_attack_profile(
            stats=stats,
            inventory=inventory,
            equip_map=equip_map,
            level=attacker.level,
            race_features=getattr(attacker, "race_features", None),
        )
        if str(getattr(profile, "damage_type", "") or "").strip().lower() != "piercing":
            return None, "Нужно колющее оружие в экипировке."

        race_features = attacker.race_features if isinstance(attacker.race_features, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        runtime["grung_weapon_poison_armed"] = True
        race_features["runtime"] = runtime
        attacker.race_features = race_features
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [
                    {"text": f"{attacker.name} наносит яд грунга на оружие.", "muted": True},
                    {"text": "Следующее попадание колющей атакой: цель делает спасбросок ТЕЛ (DC 12) или получает 2d4 урона ядом.", "muted": True},
                ],
            },
            None,
        )

    if action == "combat_use_object":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        if attacker.side != "pc":
            lines: list[dict[str, Any]] = [
                {"text": "Использовать предмет: недоступно для противника.", "muted": True}
            ]
            state = advance_turn(session_id)
            if state is None:
                return None, "Combat is not active"
            lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
            return (
                {
                    "status": _combat_status(state),
                    "open": True,
                    "lines": lines,
                },
                None,
            )

        consumable = _select_weakest_healing_consumable(attacker)
        consumable_idx: int | None = None
        consumable_entry: dict[str, Any] | None = None
        consumable_def = None
        if consumable is not None:
            consumable_idx, consumable_entry, consumable_def = consumable

        if consumable_idx is None or consumable_entry is None or consumable_def is None:
            lines = [{"text": "Использовать предмет: нет подходящего предмета лечения.", "muted": True}]
            state = advance_turn(session_id)
            if state is None:
                return None, "Combat is not active"
            lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
            return (
                {
                    "status": _combat_status(state),
                    "open": True,
                    "lines": lines,
                },
                None,
            )

        consume = consumable_def.consume
        assert consume is not None
        heal_amount = _consume_healing_item(attacker, consumable_idx, consumable_entry, consumable_def)

        heal_repr = consume.heal_dice or str(consume.heal_flat)
        lines = [
            {"text": f"Предмет: {consumable_def.name_ru} (лечение {heal_repr})", "muted": True},
            {"text": f"Лечение: {heal_amount} HP"},
            {"text": f"{attacker.name}: HP {attacker.hp_current}/{attacker.hp_max}"},
        ]

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_use_object_on_ally":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_action_or_block(state, actor)
        if blocked is not None:
            return blocked, None

        if actor.side != "pc":
            lines = [{"text": "Использовать предмет: недоступно.", "muted": True}]
            state = advance_turn(session_id)
            if state is None:
                return None, "Combat is not active"
            lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
            return (
                {
                    "status": _combat_status(state),
                    "open": True,
                    "lines": lines,
                },
                None,
            )

        if actor.hp_current <= 0 or actor.is_dead:
            return (
                {
                    "status": _combat_status(state),
                    "open": True,
                    "lines": [{"text": "Действие недоступно: ты без сознания (0 HP).", "muted": True}],
                },
                None,
            )

        target = _first_healing_target_ally(state, actor)
        if target is None:
            lines = [{"text": "Использовать предмет: нет цели для лечения.", "muted": True}]
            state = advance_turn(session_id)
            if state is None:
                return None, "Combat is not active"
            lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
            return (
                {
                    "status": _combat_status(state),
                    "open": True,
                    "lines": lines,
                },
                None,
            )

        consumable = _select_weakest_healing_consumable(actor)
        consumable_idx: int | None = None
        consumable_entry: dict[str, Any] | None = None
        consumable_def = None
        if consumable is not None:
            consumable_idx, consumable_entry, consumable_def = consumable

        if consumable_idx is None or consumable_entry is None or consumable_def is None:
            lines = [{"text": "Использовать предмет: нет лечащего предмета.", "muted": True}]
            state = advance_turn(session_id)
            if state is None:
                return None, "Combat is not active"
            lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
            return (
                {
                    "status": _combat_status(state),
                    "open": True,
                    "lines": lines,
                },
                None,
            )

        inventory = actor.inventory if isinstance(actor.inventory, list) else []
        qty_now = int(consumable_entry.get("qty", 0)) - 1
        if qty_now <= 0:
            inventory.pop(consumable_idx)
        else:
            consumable_entry["qty"] = qty_now

        consume = consumable_def.consume
        assert consume is not None
        heal_from_dice = 0
        parsed_heal = parse_heal_dice(consume.heal_dice) if isinstance(consume.heal_dice, str) else None
        if parsed_heal is not None:
            n, sides, bonus = parsed_heal
            heal_from_dice = sum(random.randint(1, sides) for _ in range(n)) + bonus

        heal_amount = max(0, heal_from_dice + int(consume.heal_flat))
        pre_hp = target.hp_current
        target.hp_current = min(target.hp_max, max(0, target.hp_current) + heal_amount)
        if pre_hp <= 0 and target.hp_current > 0 and not target.is_dead:
            target.is_stable = False
            target.death_successes = 0
            target.death_failures = 0

        lines = [
            {"text": f"Предмет: {consumable_def.name_ru} → {target.name}", "muted": True},
            {"text": f"Лечение: {heal_amount} HP"},
            {"text": f"{target.name}: HP {target.hp_current}/{target.hp_max}"},
        ]

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_help":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_bonus_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        attacker.help_attack_advantage = True
        lines: list[dict[str, Any]] = [
            {"text": f"Помощь: {attacker.name} (следующая атака с преимуществом)", "muted": True}
        ]

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_hidden_step":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_bonus_action_or_block(state, actor)
        if blocked is not None:
            return blocked, None
        if str(getattr(actor, "side", "")).lower() != "pc":
            return None, "Незримая поступь доступна только персонажу игрока."

        race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
        features_raw = race_features.get("features")
        features = features_raw if isinstance(features_raw, dict) else {}
        hidden_raw = features.get("hidden_step")
        hidden_cfg = hidden_raw if isinstance(hidden_raw, dict) else {}
        if not hidden_cfg:
            return None, "Незримая поступь недоступна."

        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        hidden_runtime_raw = runtime.get("hidden_step")
        hidden_runtime = dict(hidden_runtime_raw) if isinstance(hidden_runtime_raw, dict) else {}
        uses_max = max(1, int(hidden_cfg.get("uses_max") or 1))
        used = max(0, int(hidden_runtime.get("used") or 0))
        if used >= uses_max:
            return None, "Незримая поступь уже использована до короткого/долгого отдыха."

        hidden_runtime["used"] = used + 1
        hidden_runtime["active"] = True
        hidden_runtime["source"] = "hidden_step"
        hidden_runtime["expires_on_owner_turn_start"] = True
        runtime["hidden_step"] = hidden_runtime
        race_features["runtime"] = runtime
        actor.race_features = race_features

        lines: list[dict[str, Any]] = [
            {"text": f"Незримая поступь: {actor.name} становится невидимым (до начала следующего хода или до атакующего действия)."},
            {"text": "Состояние: invisible (source=hidden_step)", "muted": True},
        ]
        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_escape":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        _, _, roll = roll_check("normal")
        bfs_lines: list[dict[str, Any]] = []
        roll = _maybe_apply_built_for_success(attacker, roll, bfs_lines)
        dex = attacker.stats.get("dex", 50) if isinstance(attacker.stats, dict) else 50
        dex_mod = ability_mod_from_stat100(dex)
        dc = 13
        total = roll + dex_mod
        success = total >= dc
        lines: list[dict[str, Any]] = [
            {"text": f"Побег: {attacker.name} пытается выйти из боя", "muted": True},
            {"text": f"Бросок побега: d20({roll}) + {dex_mod:+d} = {total} vs DC {dc}", "muted": True},
        ]
        lines.extend(bfs_lines)

        if success:
            lines.append({"text": "Результат: побег успешен", "muted": True})
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": lines,
                },
                None,
            )

        lines.append({"text": "Результат: побег не удался", "muted": True})
        if advance_turn(session_id) is None:
            return None, "Combat is not active"

        enemy_patch, enemy_err = handle_live_combat_action("combat_attack", session_id)
        if isinstance(enemy_patch, dict):
            enemy_lines = enemy_patch.get("lines")
            if isinstance(enemy_lines, list):
                lines.extend(enemy_lines)
            return (
                {
                    "status": enemy_patch.get("status"),
                    "open": enemy_patch.get("open"),
                    "lines": lines,
                },
                None,
            )

        if enemy_err:
            state_now = get_combat(session_id)
            status = _combat_status(state_now) if state_now is not None and state_now.active and state_now.order else "Бой завершён"
            lines.append({"text": "Реакция врага: ошибка", "muted": True})
            return (
                {
                    "status": status,
                    "open": bool(state_now is not None and state_now.active),
                    "lines": lines,
                },
                None,
            )

        return None, "Combat state is inconsistent"

    if action == "combat_vampiric_bite":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None
        if str(getattr(attacker, "side", "")).lower() != "pc":
            return None, "Укус вампира доступен только персонажу игрока."

        target = _first_living_opponent(state, attacker.side)
        if target is None:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        race_features = attacker.race_features if isinstance(attacker.race_features, dict) else {}
        features_raw = race_features.get("features")
        features = features_raw if isinstance(features_raw, dict) else {}
        bite_raw = features.get("vampiric_bite")
        bite_cfg = bite_raw if isinstance(bite_raw, dict) else {}
        weapon_raw = bite_cfg.get("weapon")
        weapon = weapon_raw if isinstance(weapon_raw, dict) else {}
        damage_dice = str(weapon.get("damage_dice") or "1d4").strip().lower()
        damage_type = str(weapon.get("damage_type") or "piercing").strip().lower()

        attacker_stats = attacker.stats if isinstance(attacker.stats, dict) else {}
        con_raw = attacker_stats.get("con")
        con_stat = int(con_raw) if isinstance(con_raw, int) else 50
        con_mod = ability_mod_from_stat100(con_stat)
        prof = proficiency_bonus(max(1, int(getattr(attacker, "level", 1) or 1)))
        attack_bonus = con_mod + prof
        damage_bonus = con_mod

        hp_current = max(0, int(getattr(attacker, "hp_current", 0)))
        hp_max = max(1, int(getattr(attacker, "hp_max", 1)))
        low_hp_advantage = bool(bite_cfg.get("advantage_when_hp_below_half")) and (hp_current * 2 <= hp_max)
        has_disadvantage = target.dodge_active or _is_poisoned_condition_active(attacker) or _is_taunted_attack_disadvantage(attacker, target)
        hidden_step_advantage = _is_hidden_step_active(attacker)
        has_advantage = attacker.help_attack_advantage or low_hp_advantage or hidden_step_advantage
        roll_mode = "normal"
        if has_advantage and not has_disadvantage:
            roll_mode = "advantage"
        elif has_disadvantage and not has_advantage:
            roll_mode = "disadvantage"
        roll_a, roll_b, d20_roll = _roll_check_compat(
            roll_mode,
            rng=random,
            reroll_ones=_has_reroll_ones_scope(attacker, "attack"),
        )
        bonus_lines: list[dict[str, Any]] = []
        d20_roll = _maybe_apply_built_for_success(attacker, d20_roll, bonus_lines)
        d20_roll = _maybe_apply_vampiric_bite_bonus(attacker, d20_roll, bonus_lines)
        attack_roll_repr = f"d20({roll_a})" if roll_b is None else f"d20({roll_a},{roll_b}) -> {d20_roll}"

        parsed = parse_dice(damage_dice)
        if parsed is None:
            n, sides = 1, 4
        else:
            n, sides = parsed
        damage_roll = sum(random.randint(1, max(1, sides)) for _ in range(max(1, n)))

        resolution = resolve_attack_roll(
            target_ac=target.ac,
            d20_roll=d20_roll,
            attack_bonus=attack_bonus,
            damage_roll=damage_roll,
            damage_bonus=damage_bonus,
        )
        hidden_step_broken = _break_hidden_step(attacker)
        attacker.help_attack_advantage = False
        total_damage = int(resolution.total_damage)
        extra_outcome_lines: list[dict[str, Any]] = []
        extra_outcome_lines.extend(bonus_lines)
        damage_done = 0
        if resolution.is_hit:
            fury_bonus = _maybe_apply_fury_of_small(actor=attacker, target=target, lines=extra_outcome_lines)
            if fury_bonus > 0:
                total_damage += fury_bonus
            pre_hp = target.hp_current
            damage_to_apply, relentless_lines = _apply_relentless_endurance_if_needed(target=target, incoming_damage=total_damage)
            extra_outcome_lines.extend(relentless_lines)
            state = apply_damage(session_id, target.key, damage_to_apply, source=attacker.key)
            if state is None:
                return None, "Combat is not active"
            target = state.combatants.get(target.key, target)
            _maybe_apply_grung_contact_poison_on_melee_hit(
                attacker=attacker,
                target=target,
                is_melee_hit=True,
                lines=extra_outcome_lines,
            )
            damage_done = max(0, int(damage_to_apply))
            if target.side == "pc":
                if pre_hp > 0 and target.hp_current == 0:
                    leftover = total_damage - pre_hp
                    if leftover >= target.hp_max:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Мгновенная смерть: {target.name} погибает."})
                        _revert_shapechanger_on_death(target, extra_outcome_lines)
                elif pre_hp == 0 and not target.is_dead:
                    fail_step = 2 if resolution.is_crit else 1
                    target.death_failures = _clamp_death_counter(target.death_failures + fail_step)
                    if target.death_failures >= 3:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Смерть: {target.name} погибает."})
                        _revert_shapechanger_on_death(target, extra_outcome_lines)
                    else:
                        extra_outcome_lines.append({"text": "Смертельный урон при 0 HP: провал спасброска смерти."})

        attack_line = (
            f"Бросок атаки (Укус вампира): {attack_roll_repr} + {resolution.attack_bonus} = "
            f"{resolution.total_to_hit} vs AC {resolution.target_ac}"
        )
        if resolution.is_crit:
            result_line = "Результат: критическое попадание"
        elif resolution.is_hit:
            result_line = "Результат: попадание"
        else:
            result_line = "Результат: промах"
        if resolution.is_hit:
            roll_damage = resolution.damage_roll * 2 if resolution.is_crit else resolution.damage_roll
            damage_line = f"Урон: {roll_damage} + {resolution.damage_bonus} = {total_damage} {damage_type}"
        else:
            damage_line = "Урон: 0 (промах)"

        lines: list[dict[str, Any]] = [
            {"text": f"Атака: {attacker.name} → {target.name}", "muted": True},
            {"text": f"Укус вампира: {damage_dice} {damage_type} (CON, +PROF к атаке).", "muted": True},
            {"text": attack_line},
            {"text": result_line},
            {"text": damage_line},
            {"text": f"{target.name}: HP {target.hp_current}/{target.hp_max}"},
        ]
        if hidden_step_broken:
            lines.append({"text": "Незримая поступь прерывается: невидимость спадает.", "muted": True})
        lines.extend(extra_outcome_lines)

        empower_key = str(empower or "").strip().lower()
        if empower_key and empower_key not in {"heal", "bonus"}:
            empower_key = ""
        if empower_key:
            race_features = attacker.race_features if isinstance(attacker.race_features, dict) else {}
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            level = max(1, int(getattr(attacker, "level", 1) or 1))
            uses_max = max(1, int(proficiency_bonus(level)))
            uses_used = max(0, int(runtime.get("vampiric_bite_uses_used") or 0))
            target_rf = target.race_features if isinstance(getattr(target, "race_features", None), dict) else {}
            target_type = str(target_rf.get("creature_type") or "").strip().lower()
            blocked_by_type = target_type in {"construct", "undead"}
            if not resolution.is_hit or damage_done <= 0:
                lines.append({"text": "Усиление укуса не сработало: нужно попасть по цели.", "muted": True})
            elif blocked_by_type:
                lines.append({"text": "Усиление укуса не сработало: цель — construct/undead.", "muted": True})
            elif uses_used >= uses_max:
                lines.append({"text": "Усиление укуса недоступно: лимит БМ/дл отдых исчерпан.", "muted": True})
            else:
                runtime["vampiric_bite_uses_used"] = uses_used + 1
                if empower_key == "heal":
                    pre_hp = max(0, int(getattr(attacker, "hp_current", 0)))
                    hp_max_actor = max(1, int(getattr(attacker, "hp_max", 1)))
                    healed_to = min(hp_max_actor, pre_hp + damage_done)
                    healed = max(0, healed_to - pre_hp)
                    attacker.hp_current = healed_to
                    lines.append({"text": f"Усиление укуса: восстановлено {healed} HP.", "muted": True})
                    lines.append({"text": f"{attacker.name}: HP {attacker.hp_current}/{attacker.hp_max}"})
                elif empower_key == "bonus":
                    runtime["vampiric_bite_bonus_armed"] = True
                    runtime["vampiric_bite_bonus_value"] = max(0, int(damage_done))
                    lines.append(
                        {"text": f"Усиление укуса: +{int(damage_done)} к следующей проверке/атаке.", "muted": True}
                    )
                race_features["runtime"] = runtime
                attacker.race_features = race_features

        if target.hp_current <= 0:
            lines.append({"text": f"{target.name} повержен."})

        side_pc_alive = _is_side_alive(state, "pc")
        side_enemy_alive = _is_side_alive(state, "enemy")
        if not side_pc_alive or not side_enemy_alive:
            if not side_enemy_alive:
                lines.append({"text": "Победа: противники повержены.", "muted": True})
            if not side_pc_alive:
                lines.append({"text": "Поражение: все герои выбыли.", "muted": True})
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": lines,
                },
                None,
            )

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_attack":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        target = _first_living_opponent(state, attacker.side)
        if target is None:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        has_disadvantage = target.dodge_active or _is_poisoned_condition_active(attacker) or _is_taunted_attack_disadvantage(attacker, target)
        nimble_escape_hide_advantage = _is_nimble_escape_hide_active(attacker)
        hidden_step_advantage = _is_hidden_step_active(attacker)
        has_advantage = attacker.help_attack_advantage or hidden_step_advantage or nimble_escape_hide_advantage
        roll_mode = "normal"
        if has_advantage and not has_disadvantage:
            roll_mode = "advantage"
        elif has_disadvantage and not has_advantage:
            roll_mode = "disadvantage"
        roll_a, roll_b, d20_roll = _roll_check_compat(
            roll_mode,
            rng=random,
            reroll_ones=_has_reroll_ones_scope(attacker, "attack"),
        )
        bfs_lines: list[dict[str, Any]] = []
        d20_roll = _maybe_apply_built_for_success(attacker, d20_roll, bfs_lines)
        d20_roll = _maybe_apply_vampiric_bite_bonus(attacker, d20_roll, bfs_lines)
        attack_roll_repr = f"d20({roll_a})" if roll_b is None else f"d20({roll_a},{roll_b}) -> {d20_roll}"

        stats = attacker.stats if isinstance(attacker.stats, dict) else {}
        inventory = attacker.inventory if isinstance(attacker.inventory, list) else []
        equip_map = attacker.equip if isinstance(attacker.equip, dict) else {}
        profile = compute_attack_profile(
            stats=stats,
            inventory=inventory,
            equip_map=equip_map,
            level=attacker.level,
            race_features=getattr(attacker, "race_features", None),
        )
        parsed = parse_dice(profile.damage_dice)
        if parsed is None:
            n, sides = 1, 6
        else:
            n, sides = parsed
        damage_roll = sum(random.randint(1, sides) for _ in range(n))

        resolution = resolve_attack_roll(
            target_ac=target.ac,
            d20_roll=d20_roll,
            attack_bonus=profile.attack_bonus,
            damage_roll=damage_roll,
            damage_bonus=profile.damage_bonus,
        )
        nimble_hide_broken = _consume_nimble_escape_hide(attacker) if nimble_escape_hide_advantage else False
        hidden_step_broken = _break_hidden_step(attacker)
        attacker.help_attack_advantage = False
        extra_outcome_lines: list[dict[str, Any]] = []
        extra_outcome_lines.extend(bfs_lines)
        if nimble_hide_broken:
            extra_outcome_lines.append({"text": "Скрытность: преимущество на эту атаку из «Шустрого побега».", "muted": True})
        total_damage = int(resolution.total_damage)
        if resolution.is_hit:
            total_damage, surprise_lines = _apply_surprise_attack_bonus(
                state=state,
                attacker=attacker,
                target=target,
                is_hit=bool(resolution.is_hit),
                is_crit=bool(resolution.is_crit),
                total_damage=total_damage,
            )
            extra_outcome_lines.extend(surprise_lines)
            total_damage, savage_lines = _apply_savage_attacks_bonus(
                attacker=attacker,
                profile=profile,
                is_crit=bool(resolution.is_crit),
                total_damage=total_damage,
            )
            extra_outcome_lines.extend(savage_lines)
            fury_bonus = _maybe_apply_fury_of_small(actor=attacker, target=target, lines=extra_outcome_lines)
            if fury_bonus > 0:
                total_damage += fury_bonus
            moved_this_turn_ft = max(0, int(getattr(attacker, "moved_this_turn_ft", 0)))
            if (
                _has_charge_feature(attacker)
                and moved_this_turn_ft >= 30
                and bool(profile.is_melee_weapon)
                and bool(getattr(attacker, "bonus_action_available", False))
            ):
                attacker.charge_hooves_available = True
                extra_outcome_lines.append({"text": _charge_hooves_text(), "muted": True})
            bonus_damage, bonus_damage_type = _aasimar_bonus_damage_for_hit(attacker)
            if bonus_damage > 0:
                total_damage += bonus_damage
                extra_outcome_lines.append(
                    {"text": f"Доп. урон трансформации: +{bonus_damage} {bonus_damage_type} (1/ход).", "muted": True}
                )
            pre_hp = target.hp_current
            damage_to_apply, relentless_lines = _apply_relentless_endurance_if_needed(target=target, incoming_damage=total_damage)
            extra_outcome_lines.extend(relentless_lines)
            state = apply_damage(session_id, target.key, damage_to_apply, source=attacker.key)
            if state is None:
                return None, "Combat is not active"
            target = state.combatants.get(target.key, target)
            state_after_poison, target_after_poison = _consume_grung_weapon_poison_on_hit(
                session_id=session_id,
                attacker=attacker,
                target=target,
                profile=profile,
                lines=extra_outcome_lines,
            )
            if state_after_poison is None:
                return None, "Combat is not active"
            if state_after_poison is not None:
                state = state_after_poison
                target = target_after_poison
            _maybe_apply_grung_contact_poison_on_melee_hit(
                attacker=attacker,
                target=target,
                is_melee_hit=bool(getattr(profile, "is_melee_weapon", False)),
                lines=extra_outcome_lines,
            )
            if target.side == "pc":
                if pre_hp > 0 and target.hp_current == 0:
                    leftover = total_damage - pre_hp
                    if leftover >= target.hp_max:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Мгновенная смерть: {target.name} погибает."})
                        _revert_shapechanger_on_death(target, extra_outcome_lines)
                elif pre_hp == 0 and not target.is_dead:
                    fail_step = 2 if resolution.is_crit else 1
                    target.death_failures = _clamp_death_counter(target.death_failures + fail_step)
                    if target.death_failures >= 3:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Смерть: {target.name} погибает."})
                        _revert_shapechanger_on_death(target, extra_outcome_lines)
                    else:
                        extra_outcome_lines.append({"text": "Смертельный урон при 0 HP: провал спасброска смерти."})

        attack_line = (
            f"Бросок атаки: {attack_roll_repr} + {resolution.attack_bonus} = "
            f"{resolution.total_to_hit} vs AC {resolution.target_ac}"
        )
        if resolution.is_crit:
            result_line = "Результат: критическое попадание"
        elif resolution.is_hit:
            result_line = "Результат: попадание"
        else:
            result_line = "Результат: промах"
        if resolution.is_hit:
            roll_damage = resolution.damage_roll * 2 if resolution.is_crit else resolution.damage_roll
            damage_line = f"Урон: {roll_damage} + {resolution.damage_bonus} = {total_damage}"
        else:
            damage_line = "Урон: 0 (промах)"
            if _can_offer_saving_face(attacker):
                pending = {
                    "kind": "attack",
                    "total": int(resolution.total_to_hit),
                    "ac": int(resolution.target_ac),
                    "target_key": str(getattr(target, "key", "") or ""),
                    "damage_roll": int(resolution.damage_roll),
                    "damage_bonus": int(resolution.damage_bonus),
                    "damage_type": str(getattr(profile, "damage_type", "") or "").strip().lower(),
                    "is_melee_weapon": bool(getattr(profile, "is_melee_weapon", False)),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                _set_saving_face_pending(attacker, pending)
                allies = _saving_face_allies_within_30ft(state, attacker)
                bonus_preview = min(max(0, allies), 5)
                extra_outcome_lines.append(
                    {
                        "text": (
                            f"Можно реакцией «Сохранить лицо» добавить +{bonus_preview} "
                            f"(союзники в 30 фт, макс 5)."
                        ),
                        "muted": True,
                    }
                )

        lines: list[dict[str, Any]] = [
            {"text": f"Атака: {attacker.name} → {target.name}", "muted": True},
            {"text": f"Оружие: {profile.damage_dice} {profile.damage_type}", "muted": True},
            {"text": attack_line},
            {"text": result_line},
            {"text": damage_line},
            {"text": f"{target.name}: HP {target.hp_current}/{target.hp_max}"},
        ]
        if hidden_step_broken:
            lines.append({"text": "Незримая поступь прерывается: невидимость спадает.", "muted": True})
        lines.extend(extra_outcome_lines)
        if target.hp_current <= 0:
            lines.append({"text": f"{target.name} повержен."})

        side_pc_alive = _is_side_alive(state, "pc")
        side_enemy_alive = _is_side_alive(state, "enemy")
        if not side_pc_alive or not side_enemy_alive:
            if not side_enemy_alive:
                lines.append({"text": "Победа: противники повержены.", "muted": True})
            if not side_pc_alive:
                lines.append({"text": "Поражение: все герои выбыли.", "muted": True})
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": lines,
                },
                None,
            )

        if bool(getattr(attacker, "charge_hooves_available", False)):
            return (
                {
                    "status": _combat_status(state),
                    "open": True,
                    "lines": lines,
                },
                None,
            )

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_breath_weapon":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None
        if attacker.side != "pc":
            return None, "Оружие дыхания доступно только персонажу игрока."

        race_features = attacker.race_features if isinstance(attacker.race_features, dict) else {}
        features_raw = race_features.get("features")
        features = features_raw if isinstance(features_raw, dict) else {}
        breath_weapon_raw = features.get("breath_weapon")
        breath_weapon = breath_weapon_raw if isinstance(breath_weapon_raw, dict) else {}
        if not breath_weapon:
            return None, "Оружие дыхания недоступно."

        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        if bool(runtime.get("breath_weapon_used")):
            return None, "Оружие дыхания уже использовано до короткого/долгого отдыха."

        target = _first_living_opponent(state, attacker.side)
        if target is None:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        progression_raw = breath_weapon.get("damage_progression")
        progression = progression_raw if isinstance(progression_raw, list) else []
        damage_dice = _breath_weapon_dice_for_level(progression, getattr(attacker, "level", 1))
        parsed = parse_dice(damage_dice)
        if parsed is None:
            n, sides = 2, 6
        else:
            n, sides = parsed
        rolls = [random.randint(1, sides) for _ in range(max(1, n))]
        base_damage = sum(rolls)

        attacker_stats = attacker.stats if isinstance(attacker.stats, dict) else {}
        con_stat = int(attacker_stats.get("con", 50)) if isinstance(attacker_stats.get("con"), int) else 50
        con_mod = ability_mod_from_stat100(con_stat)
        prof = proficiency_bonus(max(1, int(getattr(attacker, "level", 1) or 1)))
        dc = 8 + con_mod + prof

        save_ability = str(breath_weapon.get("save_ability") or "").strip().lower()
        target_stats = target.stats if isinstance(target.stats, dict) else {}
        if save_ability and isinstance(target_stats.get(save_ability), int):
            save_mod = ability_mod_from_stat100(int(target_stats.get(save_ability)))
        else:
            save_mod = 0
        save_roll = random.randint(1, 20)
        save_total = save_roll + save_mod
        save_success = save_total >= dc

        final_damage = base_damage // 2 if save_success else base_damage
        extra_outcome_lines: list[dict[str, Any]] = []
        if final_damage > 0:
            fury_bonus = _maybe_apply_fury_of_small(actor=attacker, target=target, lines=extra_outcome_lines)
            if fury_bonus > 0:
                final_damage += fury_bonus
        state = apply_damage(session_id, target.key, final_damage, source=attacker.key)
        if state is None:
            return None, "Combat is not active"
        target = state.combatants.get(target.key, target)

        runtime["breath_weapon_used"] = True
        race_features["runtime"] = runtime
        attacker.race_features = race_features
        hidden_step_broken = _break_hidden_step(attacker)

        damage_type = str(breath_weapon.get("damage_type") or "").strip().lower() or "energy"
        area_raw = breath_weapon.get("area")
        area = area_raw if isinstance(area_raw, dict) else {}
        area_text = _breath_area_text(area)
        lines: list[dict[str, Any]] = [
            {"text": f"Оружие дыхания: {damage_type} ({area_text})"},
            {"text": f"Сл спасброска: DC {dc} (8 + CON mod + PROF)"},
            {
                "text": (
                    f"Спасбросок врага: d20({save_roll}) + {save_mod:+d} = {save_total} "
                    f"→ {'SUCCESS' if save_success else 'FAIL'}"
                )
            },
            {
                "text": (
                    f"Урон: {damage_dice} = {rolls} → "
                    f"{'half' if save_success else 'full'} = {final_damage}"
                )
            },
            {"text": f"HP врага: {target.hp_current}/{target.hp_max}"},
        ]
        lines.extend(extra_outcome_lines)
        if hidden_step_broken:
            lines.append({"text": "Незримая поступь прерывается: невидимость спадает.", "muted": True})
        if target.hp_current <= 0:
            lines.append({"text": f"{target.name} повержен."})

        side_pc_alive = _is_side_alive(state, "pc")
        side_enemy_alive = _is_side_alive(state, "enemy")
        if not side_pc_alive or not side_enemy_alive:
            if not side_enemy_alive:
                lines.append({"text": "Победа: противники повержены.", "muted": True})
            if not side_pc_alive:
                lines.append({"text": "Поражение: все герои выбыли.", "muted": True})
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": lines,
                },
                None,
            )

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_hooves_attack":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        if not bool(getattr(attacker, "charge_hooves_available", False)):
            return None, "Копыта недоступны: сначала нужен Разбег."
        blocked = _spend_bonus_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        target = _first_living_opponent(state, attacker.side)
        if target is None:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        has_disadvantage = target.dodge_active or _is_poisoned_condition_active(attacker) or _is_taunted_attack_disadvantage(attacker, target)
        hidden_step_advantage = _is_hidden_step_active(attacker)
        has_advantage = attacker.help_attack_advantage or hidden_step_advantage
        roll_mode = "normal"
        if has_advantage and not has_disadvantage:
            roll_mode = "advantage"
        elif has_disadvantage and not has_advantage:
            roll_mode = "disadvantage"
        roll_a, roll_b, d20_roll = _roll_check_compat(
            roll_mode,
            rng=random,
            reroll_ones=_has_reroll_ones_scope(attacker, "attack"),
        )
        bfs_lines: list[dict[str, Any]] = []
        d20_roll = _maybe_apply_built_for_success(attacker, d20_roll, bfs_lines)
        d20_roll = _maybe_apply_vampiric_bite_bonus(attacker, d20_roll, bfs_lines)
        attack_roll_repr = f"d20({roll_a})" if roll_b is None else f"d20({roll_a},{roll_b}) -> {d20_roll}"

        stats = attacker.stats if isinstance(attacker.stats, dict) else {}
        profile = compute_attack_profile(
            stats=stats,
            inventory=[],
            equip_map={},
            level=attacker.level,
            race_features=getattr(attacker, "race_features", None),
        )
        parsed = parse_dice(profile.damage_dice)
        if parsed is None:
            n, sides = 1, 4
        else:
            n, sides = parsed
        damage_roll = sum(random.randint(1, sides) for _ in range(n))

        resolution = resolve_attack_roll(
            target_ac=target.ac,
            d20_roll=d20_roll,
            attack_bonus=profile.attack_bonus,
            damage_roll=damage_roll,
            damage_bonus=profile.damage_bonus,
        )
        hidden_step_broken = _break_hidden_step(attacker)
        attacker.help_attack_advantage = False
        attacker.charge_hooves_available = False

        total_damage = int(resolution.total_damage)
        extra_outcome_lines: list[dict[str, Any]] = []
        extra_outcome_lines.extend(bfs_lines)
        if resolution.is_hit:
            fury_bonus = _maybe_apply_fury_of_small(actor=attacker, target=target, lines=extra_outcome_lines)
            if fury_bonus > 0:
                total_damage += fury_bonus
            pre_hp = target.hp_current
            damage_to_apply, relentless_lines = _apply_relentless_endurance_if_needed(target=target, incoming_damage=total_damage)
            extra_outcome_lines.extend(relentless_lines)
            state = apply_damage(session_id, target.key, damage_to_apply, source=attacker.key)
            if state is None:
                return None, "Combat is not active"
            target = state.combatants.get(target.key, target)
            _maybe_apply_grung_contact_poison_on_melee_hit(
                attacker=attacker,
                target=target,
                is_melee_hit=True,
                lines=extra_outcome_lines,
            )
            if target.side == "pc":
                if pre_hp > 0 and target.hp_current == 0:
                    leftover = total_damage - pre_hp
                    if leftover >= target.hp_max:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Мгновенная смерть: {target.name} погибает."})
                        _revert_shapechanger_on_death(target, extra_outcome_lines)
                elif pre_hp == 0 and not target.is_dead:
                    fail_step = 2 if resolution.is_crit else 1
                    target.death_failures = _clamp_death_counter(target.death_failures + fail_step)
                    if target.death_failures >= 3:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Смерть: {target.name} погибает."})
                        _revert_shapechanger_on_death(target, extra_outcome_lines)
                    else:
                        extra_outcome_lines.append({"text": "Смертельный урон при 0 HP: провал спасброска смерти."})

        attack_line = (
            f"Бросок атаки (Копыта): {attack_roll_repr} + {resolution.attack_bonus} = "
            f"{resolution.total_to_hit} vs AC {resolution.target_ac}"
        )
        if resolution.is_crit:
            attack_line += " (крит)"
        elif resolution.is_hit:
            attack_line += " (попадание)"
        else:
            attack_line += " (промах)"
        lines: list[dict[str, Any]] = [
            {"text": f"Атака: {attacker.name} -> {target.name}"},
            {"text": "Копыта: бонусная атака после Разбега.", "muted": True},
            {"text": attack_line, "muted": True},
        ]
        if hidden_step_broken:
            lines.append({"text": "Незримая поступь прерывается: невидимость спадает.", "muted": True})
        lines.extend(extra_outcome_lines)
        if resolution.is_hit:
            lines.extend(
                [
                    {"text": f"Урон: {profile.damage_dice} + {resolution.damage_bonus:+d} = {total_damage} {profile.damage_type}"},
                    {"text": f"HP врага: {target.hp_current}/{target.hp_max}"},
                ]
            )
            if target.hp_current <= 0:
                lines.append({"text": f"{target.name} повержен."})

        side_pc_alive = _is_side_alive(state, "pc")
        side_enemy_alive = _is_side_alive(state, "enemy")
        if not side_pc_alive or not side_enemy_alive:
            if not side_enemy_alive:
                lines.append({"text": "Победа: противники повержены.", "muted": True})
            if not side_pc_alive:
                lines.append({"text": "Поражение: все герои выбыли.", "muted": True})
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": lines,
                },
                None,
            )

        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_opportunity_attack":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        attacker_key = state.order[state.turn_index]
        attacker = state.combatants.get(attacker_key)
        if attacker is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_reaction_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        target = _first_living_opponent(state, attacker.side)
        if target is None:
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": [{"text": "Бой завершён: целей не осталось.", "muted": True}],
                },
                None,
            )

        has_disadvantage = target.dodge_active or _is_poisoned_condition_active(attacker) or _is_taunted_attack_disadvantage(attacker, target)
        hidden_step_advantage = _is_hidden_step_active(attacker)
        has_advantage = attacker.help_attack_advantage or hidden_step_advantage
        roll_mode = "normal"
        if has_advantage and not has_disadvantage:
            roll_mode = "advantage"
        elif has_disadvantage and not has_advantage:
            roll_mode = "disadvantage"
        roll_a, roll_b, d20_roll = _roll_check_compat(
            roll_mode,
            rng=random,
            reroll_ones=_has_reroll_ones_scope(attacker, "attack"),
        )
        bfs_lines: list[dict[str, Any]] = []
        d20_roll = _maybe_apply_built_for_success(attacker, d20_roll, bfs_lines)
        attack_roll_repr = f"d20({roll_a})" if roll_b is None else f"d20({roll_a},{roll_b}) -> {d20_roll}"

        stats = attacker.stats if isinstance(attacker.stats, dict) else {}
        inventory = attacker.inventory if isinstance(attacker.inventory, list) else []
        equip_map = attacker.equip if isinstance(attacker.equip, dict) else {}
        profile = compute_attack_profile(
            stats=stats,
            inventory=inventory,
            equip_map=equip_map,
            level=attacker.level,
            race_features=getattr(attacker, "race_features", None),
        )
        parsed = parse_dice(profile.damage_dice)
        if parsed is None:
            n, sides = 1, 6
        else:
            n, sides = parsed
        damage_roll = sum(random.randint(1, sides) for _ in range(n))

        resolution = resolve_attack_roll(
            target_ac=target.ac,
            d20_roll=d20_roll,
            attack_bonus=profile.attack_bonus,
            damage_roll=damage_roll,
            damage_bonus=profile.damage_bonus,
        )
        hidden_step_broken = _break_hidden_step(attacker)
        attacker.help_attack_advantage = False
        extra_outcome_lines: list[dict[str, Any]] = []
        extra_outcome_lines.extend(bfs_lines)
        total_damage = int(resolution.total_damage)
        if resolution.is_hit:
            total_damage, surprise_lines = _apply_surprise_attack_bonus(
                state=state,
                attacker=attacker,
                target=target,
                is_hit=bool(resolution.is_hit),
                is_crit=bool(resolution.is_crit),
                total_damage=total_damage,
            )
            extra_outcome_lines.extend(surprise_lines)
            total_damage, savage_lines = _apply_savage_attacks_bonus(
                attacker=attacker,
                profile=profile,
                is_crit=bool(resolution.is_crit),
                total_damage=total_damage,
            )
            extra_outcome_lines.extend(savage_lines)
            fury_bonus = _maybe_apply_fury_of_small(actor=attacker, target=target, lines=extra_outcome_lines)
            if fury_bonus > 0:
                total_damage += fury_bonus
            bonus_damage, bonus_damage_type = _aasimar_bonus_damage_for_hit(attacker)
            if bonus_damage > 0:
                total_damage += bonus_damage
                extra_outcome_lines.append(
                    {"text": f"Доп. урон трансформации: +{bonus_damage} {bonus_damage_type} (1/ход).", "muted": True}
                )
            pre_hp = target.hp_current
            damage_to_apply, relentless_lines = _apply_relentless_endurance_if_needed(target=target, incoming_damage=total_damage)
            extra_outcome_lines.extend(relentless_lines)
            state = apply_damage(session_id, target.key, damage_to_apply, source=attacker.key)
            if state is None:
                return None, "Combat is not active"
            target = state.combatants.get(target.key, target)
            state_after_poison, target_after_poison = _consume_grung_weapon_poison_on_hit(
                session_id=session_id,
                attacker=attacker,
                target=target,
                profile=profile,
                lines=extra_outcome_lines,
            )
            if state_after_poison is None:
                return None, "Combat is not active"
            if state_after_poison is not None:
                state = state_after_poison
                target = target_after_poison
            _maybe_apply_grung_contact_poison_on_melee_hit(
                attacker=attacker,
                target=target,
                is_melee_hit=bool(getattr(profile, "is_melee_weapon", False)),
                lines=extra_outcome_lines,
            )
            if target.side == "pc":
                if pre_hp > 0 and target.hp_current == 0:
                    leftover = total_damage - pre_hp
                    if leftover >= target.hp_max:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Мгновенная смерть: {target.name} погибает."})
                        _revert_shapechanger_on_death(target, extra_outcome_lines)
                elif pre_hp == 0 and not target.is_dead:
                    fail_step = 2 if resolution.is_crit else 1
                    target.death_failures = _clamp_death_counter(target.death_failures + fail_step)
                    if target.death_failures >= 3:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Смерть: {target.name} погибает."})
                        _revert_shapechanger_on_death(target, extra_outcome_lines)
                    else:
                        extra_outcome_lines.append({"text": "Смертельный урон при 0 HP: провал спасброска смерти."})

        attack_line = (
            f"Бросок атаки: {attack_roll_repr} + {resolution.attack_bonus} = "
            f"{resolution.total_to_hit} vs AC {resolution.target_ac}"
        )
        if resolution.is_crit:
            result_line = "Результат: критическое попадание"
        elif resolution.is_hit:
            result_line = "Результат: попадание"
        else:
            result_line = "Результат: промах"
        if resolution.is_hit:
            roll_damage = resolution.damage_roll * 2 if resolution.is_crit else resolution.damage_roll
            damage_line = f"Урон: {roll_damage} + {resolution.damage_bonus} = {total_damage}"
        else:
            damage_line = "Урон: 0 (промах)"

        lines: list[dict[str, Any]] = [
            {"text": f"Атака возможности: {attacker.name} → {target.name}", "muted": True},
            {"text": f"Оружие: {profile.damage_dice} {profile.damage_type}", "muted": True},
            {"text": attack_line},
            {"text": result_line},
            {"text": damage_line},
            {"text": f"{target.name}: HP {target.hp_current}/{target.hp_max}"},
        ]
        if hidden_step_broken:
            lines.append({"text": "Незримая поступь прерывается: невидимость спадает.", "muted": True})
        lines.extend(extra_outcome_lines)
        if target.hp_current <= 0:
            lines.append({"text": f"{target.name} повержен."})

        side_pc_alive = _is_side_alive(state, "pc")
        side_enemy_alive = _is_side_alive(state, "enemy")
        if not side_pc_alive or not side_enemy_alive:
            if not side_enemy_alive:
                lines.append({"text": "Победа: противники повержены.", "muted": True})
            if not side_pc_alive:
                lines.append({"text": "Поражение: все герои выбыли.", "muted": True})
            end_combat(session_id)
            return (
                {
                    "status": "Бой завершён",
                    "open": False,
                    "lines": lines,
                },
                None,
            )

        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    if action == "combat_stabilize":
        state = get_combat(session_id)
        if state is None or not state.active:
            return None, "Combat is not active"
        if not state.order:
            return None, "Combat state is inconsistent"

        actor_key = state.order[state.turn_index]
        actor = state.combatants.get(actor_key)
        if actor is None:
            return None, "Combat state is inconsistent"
        blocked = _spend_action_or_block(state, actor)
        if blocked is not None:
            return blocked, None

        target = _first_downed_ally(state, actor)
        if target is None:
            return (
                {
                    "status": _combat_status(state),
                    "open": True,
                    "lines": [{"text": "Стабилизация: нет подходящей цели.", "muted": True}],
                },
                None,
            )

        _, _, roll = roll_check("normal")
        bfs_lines: list[dict[str, Any]] = []
        roll = _maybe_apply_built_for_success(actor, roll, bfs_lines)
        wis = actor.stats.get("wis", 50) if isinstance(actor.stats, dict) else 50
        wis_mod = ability_mod_from_stat100(wis)
        total = roll + wis_mod

        lines: list[dict[str, Any]] = [
            {"text": f"Стабилизация: {actor.name} пытается помочь {target.name}."},
            {"text": f"Проверка Medicine: d20({roll}) + {wis_mod:+d} = {total} vs DC 10"},
        ]
        lines.extend(bfs_lines)

        if total >= 10:
            target.is_stable = True
            target.death_successes = 0
            target.death_failures = 0
            lines.append({"text": f"Результат: успех — {target.name} стабилен (без сознания)."})
        else:
            lines.append({"text": "Результат: провал — не удалось стабилизировать."})

        state = advance_turn(session_id)
        if state is None:
            return None, "Combat is not active"
        lines.append({"text": f"Ход автоматически передан: {current_turn_label(state)}", "muted": True})
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": lines,
            },
            None,
        )

    return None, "Unknown action"
