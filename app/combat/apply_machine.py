from __future__ import annotations

from typing import Any, Optional

from app.combat.machine_commands import extract_combat_machine_commands
from app.combat.state import (
    add_enemy,
    current_turn_label,
    end_combat,
    get_combat,
    start_combat,
)


def apply_combat_machine_commands(session_id: str, text: str) -> Optional[dict[str, Any]]:
    try:
        parsed = extract_combat_machine_commands(text)
    except Exception:
        return None

    if not parsed.had_any_commands:
        return None

    patch: dict[str, Any] = {}
    enemy_lines: list[dict[str, Any]] = []

    if parsed.combat_start is not None:
        start_combat(session_id, reason=parsed.combat_start.cause)
        patch.update({"reset": True, "open": True, "status": "⚔ Бой начался"})

    if parsed.combat_enemy_add:
        state_before_add = get_combat(session_id)
        if state_before_add is None or not state_before_add.active:
            start_combat(session_id, reason="autostart")
            patch.setdefault("reset", True)
            patch["open"] = True

        for enemy_cmd in parsed.combat_enemy_add:
            hp = enemy_cmd.hp if enemy_cmd.hp is not None else 10
            ac = enemy_cmd.ac if enemy_cmd.ac is not None else 10
            add_enemy(
                session_id,
                name=enemy_cmd.name,
                hp=hp,
                ac=ac,
                enemy_id=enemy_cmd.enemy_id,
            )
            enemy_lines.append(
                {
                    "text": f"Противник добавлен: {enemy_cmd.name} (HP {hp}/{hp}, AC {ac})",
                    "muted": True,
                }
            )

        if enemy_lines:
            patch["lines"] = enemy_lines
            patch["open"] = True

    if parsed.combat_end is not None:
        end_combat(session_id)
        return {"status": "Бой завершён", "open": False}

    state = get_combat(session_id)
    if "status" not in patch and state is not None and state.active:
        patch["status"] = f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}"

    return patch or None
