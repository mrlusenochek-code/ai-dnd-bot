from __future__ import annotations

import re
from typing import Any, Optional

from app.combat.machine_commands import extract_combat_machine_commands
from app.combat.state import (
    add_enemy,
    current_turn_label,
    end_combat,
    get_combat,
    start_combat,
)

_FALLBACK_COMBAT_RE = re.compile(
    r"\b(?:атак\w*|удар\w*|напал\w*|в\s+бой|дерус\w*|бь[юе]\w*|рубл\w*|стреля\w*|меч\w*|нож\w*)\b",
    flags=re.IGNORECASE,
)


def _is_combat_fallback_text(text: str) -> bool:
    return _FALLBACK_COMBAT_RE.search(text) is not None


def _fallback_enemy_from_text(text: str) -> tuple[str, int, int]:
    lowered = text.lower()
    if "разбойник" in lowered:
        return ("Разбойник", 18, 13)
    if "орк" in lowered:
        return ("Орк", 15, 13)
    if "гоблин" in lowered:
        return ("Гоблин", 12, 13)
    return ("Противник", 10, 10)


def apply_combat_machine_commands(session_id: str, text: str) -> Optional[dict[str, Any]]:
    try:
        parsed = extract_combat_machine_commands(text)
    except Exception:
        return None
    existing = get_combat(session_id)
    already_active = bool(existing and existing.active)
    allowed_start_causes = {"admin", "bootstrap"}
    allowed_start = (
        parsed.combat_start is not None and parsed.combat_start.cause in allowed_start_causes
    )
    allowed_enemy_add = bool(parsed.combat_enemy_add) and allowed_start
    allowed_end = parsed.combat_end is not None
    allowed_random = bool(parsed.random_events)
    effective_has_any = allowed_start or allowed_enemy_add or allowed_end or allowed_random

    if not effective_has_any:
        if already_active:
            return None
        if not _is_combat_fallback_text(text):
            return None

        start_combat(session_id, reason="fallback")
        enemy_name, hp, ac = _fallback_enemy_from_text(text)
        add_enemy(session_id, name=enemy_name, hp=hp, ac=ac)
        state = get_combat(session_id)
        if state is None or not state.active:
            return None

        return {
            "reset": True,
            "open": True,
            "lines": [
                {
                    "text": f"Противник добавлен: {enemy_name} (HP {hp}/{hp}, AC {ac})",
                    "muted": True,
                }
            ],
            "status": f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}",
        }

    patch: dict[str, Any] = {}
    enemy_lines: list[dict[str, Any]] = []

    if allowed_start and parsed.combat_start is not None:
        start_combat(session_id, reason=parsed.combat_start.cause)
        patch.update({"reset": True, "open": True, "status": "⚔ Бой начался"})

    enemy_add_commands = parsed.combat_enemy_add if allowed_enemy_add else []

    if enemy_add_commands:
        state_before_add = get_combat(session_id)
        if state_before_add is None or not state_before_add.active:
            start_combat(session_id, reason="autostart")
            patch.setdefault("reset", True)
            patch["open"] = True

        for enemy_cmd in enemy_add_commands:
            hp = enemy_cmd.hp if enemy_cmd.hp is not None else 10
            ac = enemy_cmd.ac if enemy_cmd.ac is not None else 10
            add_enemy(
                session_id,
                name=enemy_cmd.name,
                hp=hp,
                ac=ac,
                enemy_id=enemy_cmd.enemy_id,
            )
            threat_text = (
                f", угроза {enemy_cmd.threat}"
                if enemy_cmd.threat is not None
                else ""
            )
            enemy_lines.append(
                {
                    "text": f"Противник добавлен: {enemy_cmd.name} (HP {hp}/{hp}, AC {ac}{threat_text})",
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
