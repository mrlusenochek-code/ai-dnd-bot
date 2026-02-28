from __future__ import annotations

import re
from typing import Any, Optional

from app.combat.machine_commands import extract_combat_machine_commands
from app.combat.resolution import AttackResolution
from app.combat.state import current_turn_label as current_combat_turn_label
from app.combat.test_runtime import CombatTestRuntime, current_turn_label as current_test_turn_label


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


def normalize_combat_log_ui_patch(
    patch: dict[str, Any] | None,
    *,
    prev_history: dict[str, Any] | None,
    combat_state: Any | None,
    actor_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(patch, dict):
        return patch

    is_reset = patch.get("reset") is True

    patch_lines_raw = patch.get("lines")
    if isinstance(patch_lines_raw, list):
        def _line_text(item: Any) -> str:
            if isinstance(item, dict):
                return str(item.get("text") or "").strip()
            if isinstance(item, str):
                return item.strip()
            return ""

        has_enemy_added_line = any(_line_text(item).startswith("Противник добавлен:") for item in patch_lines_raw)
        prev_lines_raw = prev_history.get("lines") if isinstance(prev_history, dict) else None
        prev_lines: list[Any] = prev_lines_raw if isinstance(prev_lines_raw, list) else []
        prev_texts = [_line_text(item) for item in prev_lines if _line_text(item)]
        prev_history_is_empty_or_cleared = (
            not prev_texts
            or (len(prev_texts) == 1 and prev_texts[0] == "Журнал очищен.")
        )
        has_preamble_already = any(
            _line_text(item).startswith("Бой начался между") or _line_text(item).startswith("Добавлен в бой:")
            for item in patch_lines_raw
        )

        if has_enemy_added_line and prev_history_is_empty_or_cleared and not has_preamble_already:
            preamble_lines = _build_start_preamble_lines(
                actor_context=actor_context,
                combat_state=combat_state,
            )
            if preamble_lines:
                patch = dict(patch)
                patch["lines"] = preamble_lines + patch_lines_raw

    if "status" not in patch:
        if combat_state is not None and combat_state.active and patch.get("open", True):
            patch = dict(patch)  # shallow copy
            patch["status"] = f"⚔ Бой • Раунд {combat_state.round_no} • Ход: {current_combat_turn_label(combat_state)}"

    status_text = patch.get("status")
    if isinstance(status_text, str):
        if not isinstance(patch.get("lines"), list):
            patch = dict(patch)
            patch["lines"] = []
        patch_lines = patch.get("lines")
        if isinstance(patch_lines, list):
            prev_status = None if is_reset else (prev_history.get("status") if isinstance(prev_history, dict) else None)

            prev_round_match = re.search(r"Раунд\s+(\d+)", prev_status) if isinstance(prev_status, str) else None
            next_round_match = re.search(r"Раунд\s+(\d+)", status_text)
            prev_round = int(prev_round_match.group(1)) if prev_round_match else None
            next_round = int(next_round_match.group(1)) if next_round_match else None

            if (not is_reset) and prev_round is not None and next_round is not None and prev_round != next_round:
                if not (
                    patch_lines
                    and isinstance(patch_lines[-1], dict)
                    and patch_lines[-1].get("text") == "===================="
                    and patch_lines[-1].get("muted") is True
                ):
                    patch_lines.append({"text": "====================", "muted": True})

            has_same_status_line = False
            for item in patch_lines:
                if (
                    isinstance(item, dict)
                    and item.get("kind") == "status"
                    and item.get("text") == status_text
                ):
                    has_same_status_line = True
                    break
            if not has_same_status_line:
                patch_lines.append({"text": status_text, "kind": "status"})

    return patch


def _build_start_preamble_lines(
    *,
    actor_context: dict[str, Any] | None,
    combat_state: Any | None,
) -> list[dict[str, Any]]:
    if combat_state is None or not getattr(combat_state, "active", False):
        return []

    actor_context = actor_context if isinstance(actor_context, dict) else {}
    player_uid = actor_context.get("uid")
    if not isinstance(player_uid, int):
        player_uid = actor_context.get("player_uid")
    if not isinstance(player_uid, int):
        player_uid = None

    player_name = str(actor_context.get("player_name") or "").strip() or "Игрок"
    level = 1
    class_kit = "Adventurer"
    stats = {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50}
    hp_cur = 0
    hp_max = 1
    ac = 10

    character = actor_context.get("character")
    if character is None and isinstance(player_uid, int):
        chars_by_uid = actor_context.get("chars_by_uid")
        if isinstance(chars_by_uid, dict):
            character = chars_by_uid.get(player_uid)

    if character is not None:
        char_name = str(getattr(character, "name", "") or "").strip()
        if char_name:
            player_name = char_name
        level = max(1, _as_int(getattr(character, "level", 1), 1))
        class_kit = str(getattr(character, "class_kit", "") or "").strip() or "Adventurer"
        stats = _normalized_stats(getattr(character, "stats", {}))
        hp_max = max(1, _as_int(getattr(character, "hp_max", hp_max), hp_max))
        hp_cur = _clamp(_as_int(getattr(character, "hp", hp_cur), hp_cur), 0, hp_max)

    combatants = getattr(combat_state, "combatants", {})
    if isinstance(combatants, dict) and isinstance(player_uid, int):
        player_combatant = combatants.get(f"pc_{player_uid}")
        if player_combatant is not None:
            hp_max = max(1, _as_int(getattr(player_combatant, "hp_max", hp_max), hp_max))
            hp_cur = _clamp(_as_int(getattr(player_combatant, "hp_current", hp_cur), hp_cur), 0, hp_max)
            ac = max(0, _as_int(getattr(player_combatant, "ac", ac), ac))

    enemy_name = "противником"
    if isinstance(combatants, dict):
        for combatant in combatants.values():
            if getattr(combatant, "side", "") != "enemy":
                continue
            candidate = str(getattr(combatant, "name", "") or "").strip()
            if candidate:
                enemy_name = candidate
            break

    battle_line = f'Бой начался между "{player_name}" и "{enemy_name}".'
    player_line = (
        f"Добавлен в бой: {player_name} (ур. {level}, класс {class_kit}) "
        f"HP {hp_cur}/{hp_max}, AC {ac}, "
        f"СИЛ {stats['str']} ЛОВ {stats['dex']} ТЕЛ {stats['con']} "
        f"ИНТ {stats['int']} МДР {stats['wis']} ХАР {stats['cha']}"
    )
    return [{"text": battle_line}, {"text": player_line}]


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        if s.isdigit() or (s[0] in "+-" and s[1:].isdigit()):
            try:
                return int(s)
            except Exception:
                return default
    return default


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


def _normalized_stats(raw: Any) -> dict[str, int]:
    out = {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50}
    if not isinstance(raw, dict):
        return out
    for k in out:
        out[k] = _clamp(_as_int(raw.get(k), out[k]), 1, 100)
    return out


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
    return f"⚔ Бой (тест) • Раунд {runtime.round_no} • Ход: {current_test_turn_label(runtime)}"
