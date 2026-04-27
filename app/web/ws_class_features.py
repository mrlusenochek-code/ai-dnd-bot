from __future__ import annotations

from typing import Any

from app.combat.state import current_turn_label, get_combat
from app.rules.class_feature_runtime import apply_second_wind_usage


def _apply_second_wind_in_combat(
    session_id: str,
    actor_key: str,
    ch: Any,
    *,
    rng: Any = None,
) -> tuple[dict[str, Any] | None, str | None, bool]:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None, "Combat is not active", False
    if not state.order or state.turn_index < 0 or state.turn_index >= len(state.order):
        return None, "Combat state is inconsistent", False
    if state.order[state.turn_index] != actor_key:
        return None, f"Сейчас ходит {current_turn_label(state)}. Дождись своего хода.", False

    actor = state.combatants.get(actor_key)
    if actor is None:
        return None, "Боец не найден.", False
    if not bool(getattr(actor, "bonus_action_available", True)):
        return None, "Бонусное действие недоступно: бонусное действие уже потрачено.", False

    healed_hp, heal_err, changed = apply_second_wind_usage(ch, rng=rng)
    if heal_err:
        return None, heal_err, False

    actor.bonus_action_available = False
    actor_hp_max = max(0, int(getattr(actor, "hp_max", 0) or 0))
    actor.hp_current = min(actor_hp_max, max(0, int(getattr(ch, "hp", actor.hp_current) or actor.hp_current)))

    actor_name = str(getattr(ch, "name", "") or getattr(actor, "name", "") or "Персонаж").strip() or "Персонаж"
    patch = {
        "status": f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}",
        "open": True,
        "lines": [
            {"text": f"{actor_name} переводит дыхание: +{max(0, int(healed_hp or 0))} HP (Второе дыхание)."},
        ],
    }
    return patch, None, True


def apply_combat_class_feature_action(
    combat_action: str,
    session_id: str,
    actor_key: str,
    ch: Any,
    *,
    rng: Any = None,
) -> tuple[dict[str, Any] | None, str | None, bool]:
    action = str(combat_action or "").strip().lower()
    if action == "combat_second_wind":
        return _apply_second_wind_in_combat(session_id, actor_key, ch, rng=rng)
    return None, f"Неизвестная классовая особенность: {combat_action}", False
