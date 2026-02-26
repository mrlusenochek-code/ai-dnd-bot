from __future__ import annotations

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


def _is_side_alive(state: Any, side: str) -> bool:
    for combatant in state.combatants.values():
        if combatant.side == side and _is_alive(combatant.hp_current):
            return True
    return False


def _combat_status(state: Any) -> str:
    return f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}"


def handle_live_combat_action(
    action: str, session_id: str
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
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

        resolution = resolve_attack_roll(
            target_ac=target.ac,
            d20_roll=d20_roll,
            attack_bonus=3,
            damage_roll=random.randint(1, 6),
            damage_bonus=2,
        )
        attacker.help_attack_advantage = False
        if resolution.is_hit:
            state = apply_damage(session_id, target.key, resolution.total_damage)
            if state is None:
                return None, "Combat is not active"
            target = state.combatants.get(target.key, target)

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
            {"text": attack_line},
            {"text": result_line},
            {"text": damage_line},
            {"text": f"{target.name}: HP {target.hp_current}/{target.hp_max}"},
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

    return None, "Unknown action"
