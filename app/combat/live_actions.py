from __future__ import annotations

import re
import random
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
    action: str, session_id: str, *, distance_ft: int | None = None
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
        if dist > remaining:
            return None, f"Недостаточно перемещения: осталось {remaining} фт."

        mover.move_remaining_ft = remaining - dist
        mover.move_remaining = mover.move_remaining_ft
        return (
            {
                "status": _combat_status(state),
                "open": True,
                "lines": [{"text": f"{mover.name} перемещается на {dist} фт (осталось {mover.move_remaining_ft} фт)."}],
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
        blocked = _spend_action_or_block(state, attacker)
        if blocked is not None:
            return blocked, None

        attacker.disengage_active = True
        lines: list[dict[str, Any]] = [{"text": f"Отход: {attacker.name} (до следующего хода)", "muted": True}]

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

        has_disadvantage = target.dodge_active
        has_advantage = attacker.help_attack_advantage
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
            if target.side == "pc":
                if pre_hp > 0 and target.hp_current == 0:
                    leftover = total_damage - pre_hp
                    if leftover >= target.hp_max:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Мгновенная смерть: {target.name} погибает."})
                elif pre_hp == 0 and not target.is_dead:
                    fail_step = 2 if resolution.is_crit else 1
                    target.death_failures = _clamp_death_counter(target.death_failures + fail_step)
                    if target.death_failures >= 3:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Смерть: {target.name} погибает."})
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
            {"text": f"Атака: {attacker.name} → {target.name}", "muted": True},
            {"text": f"Оружие: {profile.damage_dice} {profile.damage_type}", "muted": True},
            {"text": attack_line},
            {"text": result_line},
            {"text": damage_line},
            {"text": f"{target.name}: HP {target.hp_current}/{target.hp_max}"},
        ]
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
        state = apply_damage(session_id, target.key, final_damage, source=attacker.key)
        if state is None:
            return None, "Combat is not active"
        target = state.combatants.get(target.key, target)

        runtime["breath_weapon_used"] = True
        race_features["runtime"] = runtime
        attacker.race_features = race_features

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

        has_disadvantage = target.dodge_active
        has_advantage = attacker.help_attack_advantage
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
            if target.side == "pc":
                if pre_hp > 0 and target.hp_current == 0:
                    leftover = total_damage - pre_hp
                    if leftover >= target.hp_max:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Мгновенная смерть: {target.name} погибает."})
                elif pre_hp == 0 and not target.is_dead:
                    fail_step = 2 if resolution.is_crit else 1
                    target.death_failures = _clamp_death_counter(target.death_failures + fail_step)
                    if target.death_failures >= 3:
                        target.is_dead = True
                        target.is_stable = False
                        extra_outcome_lines.append({"text": f"Смерть: {target.name} погибает."})
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
