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
from app.rules.item_catalog import ITEMS


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


def _is_side_alive(state: Any, side: str) -> bool:
    for combatant in state.combatants.values():
        if combatant.side == side and _is_alive(combatant.hp_current):
            return True
    return False


def _combat_status(state: Any) -> str:
    return f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}"


def _clamp_death_counter(value: int) -> int:
    return max(0, min(int(value), 3))


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
                roll = random.randint(1, 20)
                lines.append({"text": f"Спасбросок смерти: d20({roll})"})
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
    action: str, session_id: str
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    state = get_combat(session_id)
    if state is not None and state.active and state.order:
        current_key = state.order[state.turn_index]
        current = state.combatants.get(current_key)
        if (
            current is not None
            and current.side == "pc"
            and current.hp_current <= 0
            and not current.is_dead
            and action not in {"combat_use_object", "combat_end_turn"}
        ):
            return (
                {
                    "status": _combat_status(state),
                    "open": True,
                    "lines": [
                        {
                            "text": "Действие недоступно: ты без сознания (0 HP).",
                            "muted": True,
                        }
                    ],
                },
                None,
            )
    if state is not None and state.active and action != "combat_use_object":
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

        attacker.dash_active = True
        lines: list[dict[str, Any]] = [{"text": f"Рывок: {attacker.name} (до следующего хода)", "muted": True}]

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

        inventory = attacker.inventory if isinstance(attacker.inventory, list) else []
        consumable_idx: int | None = None
        consumable_entry: dict[str, Any] | None = None
        consumable_def = None
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
            consumable_idx = idx
            consumable_entry = entry
            consumable_def = item_def
            break

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

        pre_hp = attacker.hp_current
        attacker.hp_current = min(attacker.hp_max, max(0, attacker.hp_current) + heal_amount)
        if pre_hp <= 0 and attacker.hp_current > 0 and not attacker.is_dead:
            attacker.is_stable = False
            attacker.death_successes = 0
            attacker.death_failures = 0

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

        roll = random.randint(1, 20)
        dc = 13
        success = roll >= dc
        lines: list[dict[str, Any]] = [
            {"text": f"Побег: {attacker.name} пытается выйти из боя", "muted": True},
            {"text": f"Бросок побега: d20({roll}) vs DC {dc}", "muted": True},
        ]

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
        d20_roll: int
        attack_roll_repr: str
        if has_advantage and not has_disadvantage:
            d20_roll_adv_1 = random.randint(1, 20)
            d20_roll_adv_2 = random.randint(1, 20)
            d20_roll = max(d20_roll_adv_1, d20_roll_adv_2)
            attack_roll_repr = f"d20({d20_roll_adv_1},{d20_roll_adv_2}) -> {d20_roll}"
        elif has_disadvantage and not has_advantage:
            d20_roll_dis_1 = random.randint(1, 20)
            d20_roll_dis_2 = random.randint(1, 20)
            d20_roll = min(d20_roll_dis_1, d20_roll_dis_2)
            attack_roll_repr = f"d20({d20_roll_dis_1},{d20_roll_dis_2}) -> {d20_roll}"
        else:
            d20_roll = random.randint(1, 20)
            attack_roll_repr = f"d20({d20_roll})"

        stats = attacker.stats if isinstance(attacker.stats, dict) else {}
        inventory = attacker.inventory if isinstance(attacker.inventory, list) else []
        equip_map = attacker.equip if isinstance(attacker.equip, dict) else {}
        profile = compute_attack_profile(stats=stats, inventory=inventory, equip_map=equip_map)
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
        if resolution.is_hit:
            pre_hp = target.hp_current
            state = apply_damage(session_id, target.key, resolution.total_damage)
            if state is None:
                return None, "Combat is not active"
            target = state.combatants.get(target.key, target)
            if target.side == "pc":
                if pre_hp > 0 and target.hp_current == 0:
                    leftover = resolution.total_damage - pre_hp
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
            damage_line = f"Урон: {roll_damage} + {resolution.damage_bonus} = {resolution.total_damage}"
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

        roll = random.randint(1, 20)
        wis = actor.stats.get("wis", 50) if isinstance(actor.stats, dict) else 50
        wis_mod = int((wis - 50) // 20)
        total = roll + wis_mod

        lines: list[dict[str, Any]] = [
            {"text": f"Стабилизация: {actor.name} пытается помочь {target.name}."},
            {"text": f"Проверка Medicine: d20({roll}) + {wis_mod} = {total} vs DC 10"},
        ]

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
