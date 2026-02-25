from __future__ import annotations

from typing import Any, Optional

from app.combat.machine_commands import extract_combat_machine_commands
from app.combat.resolution import AttackResolution
from app.combat.test_runtime import CombatTestRuntime, current_turn_label


def build_combat_log_ui_patch_from_text(text: str) -> Optional[dict[str, Any]]:
    """
    Мини-патч для UI боевого журнала на основе машинных команд @@COMBAT_*.

    Поведение (как сейчас в server.py):
      - @@COMBAT_END   -> закрыть панель, статус "Бой завершён"
      - @@COMBAT_START -> открыть + reset, статус "⚔ Бой начался"
      - иначе          -> None
    """
    try:
        parsed = extract_combat_machine_commands(text)
    except Exception:
        return None

    if parsed.combat_end is not None:
        return {"status": "Бой завершён", "open": False}

    if parsed.combat_start is not None:
        return {"reset": True, "open": True, "status": "⚔ Бой начался"}

    return None


def build_combat_test_patch_with_lines(
    lines: list[dict[str, Any]],
    *,
    status: str = "⚔ Бой (тест)",
    open_panel: bool = True,
    reset: bool = False,
) -> dict[str, Any]:
    patch: dict[str, Any] = {"open": open_panel, "status": status, "lines": lines}
    if reset:
        patch["reset"] = True
    return patch


def build_combat_test_attack_lines(title: str, res: AttackResolution) -> list[dict[str, Any]]:
    attack_line = f"Бросок атаки: d20({res.d20_roll}) + {res.attack_bonus} = {res.total_to_hit} vs AC {res.target_ac}"

    if res.is_crit:
        result_line = "Результат: критическое попадание"
    elif res.is_hit:
        result_line = "Результат: попадание"
    else:
        result_line = "Результат: промах"

    if res.is_hit:
        roll_damage = res.damage_roll * 2 if res.is_crit else res.damage_roll
        damage_line = f"Урон: {roll_damage} + {res.damage_bonus} = {res.total_damage}"
    else:
        damage_line = "Урон: 0 (промах)"

    return [
        {"text": f"Тест-атака: {title}", "muted": True},
        {"text": attack_line},
        {"text": result_line},
        {"text": damage_line},
    ]


def format_combat_test_status(runtime: CombatTestRuntime | None) -> str:
    if runtime is None:
        return "Бой не начат"
    if not runtime.active:
        return "Бой завершён (тест)"
    return f"⚔ Бой (тест) • Раунд {runtime.round_no} • Ход: {current_turn_label(runtime)}"
