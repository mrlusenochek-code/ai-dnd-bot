from typing import Any, Optional

from app.combat.log_ui import (
    build_combat_test_attack_lines,
    build_combat_test_patch_with_lines,
    format_combat_test_status,
)
from app.combat.resolution import resolve_attack_roll
from app.combat.test_runtime import (
    advance_turn,
    apply_enemy_damage,
    apply_player_damage,
    clear_test_combat,
    current_turn_label,
    get_test_combat,
    start_test_combat,
)


def handle_admin_combat_test_action(
    action: str, session_id: str
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    if action == "admin_combat_test_start":
        runtime = start_test_combat(session_id)
        return (
            build_combat_test_patch_with_lines(
                [
                    {"text": "Тест: админ запустил боевой режим.", "muted": True},
                    {
                        "text": (
                            f"Противник: {runtime.enemy.name} "
                            f"(HP {runtime.enemy.hp_current}/{runtime.enemy.hp_max}, AC {runtime.enemy.ac})."
                        )
                    },
                ],
                status=format_combat_test_status(runtime),
                reset=True,
            ),
            None,
        )

    if action == "admin_combat_test_end":
        clear_test_combat(session_id)
        return (
            {
                "status": "Бой завершён (тест)",
                "open": False,
                "lines": [
                    {"text": "Тест: админ завершил боевой режим.", "muted": True},
                ],
            },
            None,
        )

    if action == "admin_combat_test_turn_next":
        runtime = get_test_combat(session_id)
        if runtime is None or not runtime.active:
            return None, "Test combat is not active"
        runtime = advance_turn(session_id)
        if runtime is None:
            return None, "Test combat is not active"
        return (
            build_combat_test_patch_with_lines(
                [{"text": f"Ход передан: {current_turn_label(runtime)}", "muted": True}],
                status=format_combat_test_status(runtime),
                open_panel=True,
            ),
            None,
        )

    if action == "admin_combat_test_attack_enemy":
        runtime = get_test_combat(session_id)
        if runtime is None or not runtime.active:
            return None, "Test combat is not active"
        turn_label = current_turn_label(runtime)
        if turn_label != "Персонаж #1":
            return (
                build_combat_test_patch_with_lines(
                    [{"text": f"Сейчас не ход игрока: {turn_label}"}],
                    status=format_combat_test_status(runtime),
                    open_panel=True,
                ),
                None,
            )

        scenarios = [
            {"d20_roll": 14, "attack_bonus": 3, "damage_roll": 5, "damage_bonus": 2},
            {"d20_roll": 7, "attack_bonus": 3, "damage_roll": 5, "damage_bonus": 2},
            {"d20_roll": 20, "attack_bonus": 3, "damage_roll": 6, "damage_bonus": 2},
            {"d20_roll": 1, "attack_bonus": 9, "damage_roll": 12, "damage_bonus": 5},
        ]
        scenario = scenarios[runtime.attack_seq % len(scenarios)]
        runtime.attack_seq += 1
        resolution = resolve_attack_roll(target_ac=runtime.enemy.ac, **scenario)
        if resolution.is_hit:
            runtime = apply_enemy_damage(session_id, resolution.total_damage)
            if runtime is None:
                return None, "Test combat is not active"

        attack_line = (
            f"Бросок атаки: d20({resolution.d20_roll}) + "
            f"{resolution.attack_bonus} = {resolution.total_to_hit} vs AC {resolution.target_ac}"
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

        lines = [
            {"text": f"Атака по врагу: {runtime.enemy.name}", "muted": True},
            {"text": attack_line},
            {"text": result_line},
            {"text": damage_line},
            {"text": f"{runtime.enemy.name}: HP {runtime.enemy.hp_current}/{runtime.enemy.hp_max}"},
        ]

        status = format_combat_test_status(runtime)
        if runtime.enemy.hp_current <= 0:
            clear_test_combat(session_id)
            status = "Бой завершён (тест)"
            lines.append({"text": f"{runtime.enemy.name} повержен."})
        else:
            runtime = advance_turn(session_id)
            if runtime is not None:
                lines.append({"text": f"Ход автоматически передан: {current_turn_label(runtime)}", "muted": True})
                status = format_combat_test_status(runtime)

        return (
            build_combat_test_patch_with_lines(
                lines,
                status=status,
                open_panel=True,
            ),
            None,
        )

    if action == "admin_combat_test_enemy_act":
        runtime = get_test_combat(session_id)
        if runtime is None or not runtime.active:
            return None, "Test combat is not active"
        turn_label = current_turn_label(runtime)
        if turn_label != "Разбойник":
            return (
                build_combat_test_patch_with_lines(
                    [{"text": f"Сейчас не ход врага: {turn_label}"}],
                    status=format_combat_test_status(runtime),
                    open_panel=True,
                ),
                None,
            )

        enemy_scenarios = [
            {"d20_roll": 13, "attack_bonus": 3, "damage_roll": 4, "damage_bonus": 1},
            {"d20_roll": 5, "attack_bonus": 3, "damage_roll": 4, "damage_bonus": 1},
            {"d20_roll": 20, "attack_bonus": 3, "damage_roll": 5, "damage_bonus": 1},
            {"d20_roll": 1, "attack_bonus": 6, "damage_roll": 9, "damage_bonus": 2},
        ]
        scenario = enemy_scenarios[runtime.enemy_attack_seq % len(enemy_scenarios)]
        runtime.enemy_attack_seq += 1
        resolution = resolve_attack_roll(target_ac=runtime.player_ac, **scenario)
        if resolution.is_hit:
            runtime = apply_player_damage(session_id, resolution.total_damage)
            if runtime is None:
                return None, "Test combat is not active"

        attack_line = (
            f"Бросок атаки: d20({resolution.d20_roll}) + "
            f"{resolution.attack_bonus} = {resolution.total_to_hit} vs AC {resolution.target_ac}"
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

        lines = [
            {"text": f"Атака врага: {runtime.enemy.name} → {runtime.player_name}", "muted": True},
            {"text": attack_line},
            {"text": result_line},
            {"text": damage_line},
            {"text": f"{runtime.player_name}: HP {runtime.player_hp_current}/{runtime.player_hp_max}"},
        ]

        status = format_combat_test_status(runtime)
        if runtime.player_hp_current <= 0:
            clear_test_combat(session_id)
            status = "Бой завершён (тест)"
            lines.append({"text": f"{runtime.player_name} повержен."})
        else:
            runtime = advance_turn(session_id)
            if runtime is not None:
                lines.append({"text": f"Ход автоматически передан: {current_turn_label(runtime)}", "muted": True})
                status = format_combat_test_status(runtime)

        return (
            build_combat_test_patch_with_lines(
                lines,
                status=status,
                open_panel=True,
            ),
            None,
        )

    if action in {
        "admin_combat_test_attack_hit",
        "admin_combat_test_attack_miss",
        "admin_combat_test_attack_crit",
        "admin_combat_test_attack_fumble",
    }:
        test_scenarios: dict[str, tuple[str, dict[str, int]]] = {
            "admin_combat_test_attack_hit": (
                "попадание",
                {"d20_roll": 14, "attack_bonus": 3, "target_ac": 15, "damage_roll": 5, "damage_bonus": 2},
            ),
            "admin_combat_test_attack_miss": (
                "промах",
                {"d20_roll": 7, "attack_bonus": 3, "target_ac": 15, "damage_roll": 5, "damage_bonus": 2},
            ),
            "admin_combat_test_attack_crit": (
                "крит",
                {"d20_roll": 20, "attack_bonus": 3, "target_ac": 15, "damage_roll": 6, "damage_bonus": 2},
            ),
            "admin_combat_test_attack_fumble": (
                "фатальный промах",
                {"d20_roll": 1, "attack_bonus": 9, "target_ac": 10, "damage_roll": 12, "damage_bonus": 5},
            ),
        }
        title, kwargs = test_scenarios[action]
        resolution = resolve_attack_roll(**kwargs)
        return (
            build_combat_test_patch_with_lines(
                build_combat_test_attack_lines(title, resolution),
            ),
            None,
        )

    return None, "Unknown action"
