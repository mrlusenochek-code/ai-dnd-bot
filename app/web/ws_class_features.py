from __future__ import annotations

from typing import Any

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import current_turn_label, get_combat
from app.rules.class_feature_runtime import (
    apply_action_surge_usage,
    apply_indomitable_usage,
    apply_second_wind_usage,
    get_cunning_action_mechanics,
)


def _format_d20_roll(mode: str, roll_a: int, roll_b: int | None, chosen: int) -> str:
    normalized = str(mode or "normal").strip().lower()
    if roll_b is None:
        return f"d20({chosen})"
    prefix = "adv" if normalized == "advantage" else "dis"
    return f"{prefix} d20({roll_a}, {roll_b}) -> {chosen}"


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
    if int(getattr(actor, "hp_current", 0) or 0) <= 0 or bool(getattr(actor, "is_dead", False)) or bool(getattr(actor, "defeated", False)) or bool(getattr(actor, "is_defeated", False)):
        return None, "Второе дыхание недоступно: персонаж не может действовать.", False
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


def _apply_action_surge_in_combat(
    session_id: str,
    actor_key: str,
    ch: Any,
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

    ok, err, changed = apply_action_surge_usage(ch)
    if err:
        return None, err, False
    if not ok:
        return None, "Всплеск действий не сработал.", False

    actor_class_features = actor.class_features if isinstance(getattr(actor, "class_features", None), dict) else {}
    actor_runtime_raw = actor_class_features.get("runtime")
    actor_runtime = dict(actor_runtime_raw) if isinstance(actor_runtime_raw, dict) else {}
    if bool(getattr(actor, "action_available", False)):
        actor_runtime["extra_attack_action_bank"] = max(0, int(actor_runtime.get("extra_attack_action_bank") or 0)) + 1
    if actor_runtime:
        actor_class_features["runtime"] = actor_runtime
        actor.class_features = actor_class_features

    actor.action_available = True
    actor_name = str(getattr(ch, "name", "") or getattr(actor, "name", "") or "Персонаж").strip() or "Персонаж"
    patch = {
        "status": f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}",
        "open": True,
        "lines": [
            {"text": f"{actor_name} использует Всплеск действий и получает дополнительное действие."},
        ],
    }
    return patch, None, changed


def _apply_indomitable_in_combat(
    session_id: str,
    actor_key: str,
    ch: Any,
    *,
    rng: Any = None,
) -> tuple[dict[str, Any] | None, str | None, bool]:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None, "Несгибаемый сейчас доступен только в бою.", False

    actor = state.combatants.get(actor_key)
    if actor is None:
        return None, "Боец не найден.", False

    payload, err, changed = apply_indomitable_usage(ch, rng=rng)
    if err:
        return None, err, False
    if not isinstance(payload, dict):
        return None, "Несгибаемый не сработал.", False

    actor_name = str(getattr(ch, "name", "") or getattr(actor, "name", "") or "Персонаж").strip() or "Персонаж"
    ability = str(payload.get("ability") or "").strip().lower()
    vs_tag = str(payload.get("vs_tag") or "").strip().lower()
    dc = int(payload.get("dc") or 0)
    mod = int(payload.get("mod") or 0)
    new_total = int(payload.get("new_total") or 0)
    success = bool(payload.get("success"))
    roll_text = _format_d20_roll(
        str(payload.get("mode") or "normal"),
        int(payload.get("roll_a") or payload.get("new_roll") or 0),
        int(payload.get("roll_b")) if payload.get("roll_b") is not None else None,
        int(payload.get("new_roll") or 0),
    )
    vs_suffix = f" vs {vs_tag}" if vs_tag else ""
    outcome = "SUCCESS" if success else "FAIL"
    patch = {
        "status": f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}",
        "open": True,
        "lines": [
            {
                "text": (
                    f"{actor_name} использует Несгибаемый и перебрасывает спасбросок: "
                    f"{roll_text} + {mod:+d} = {new_total} {ability}{vs_suffix} vs DC {dc} -> {outcome}."
                )
            },
        ],
    }
    return patch, None, changed


def _apply_cunning_action_in_combat(
    session_id: str,
    actor_key: str,
    ch: Any,
    *,
    target_action: str,
) -> tuple[dict[str, Any] | None, str | None, bool]:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None, "Combat is not active", False
    if not state.order or state.turn_index < 0 or state.turn_index >= len(state.order):
        return None, "Combat state is inconsistent", False
    if state.order[state.turn_index] != actor_key:
        return None, f"Сейчас ходит {current_turn_label(state)}. Дождись своего хода.", False

    mechanics, err = get_cunning_action_mechanics(ch)
    if err:
        return None, err, False

    allowed_actions_raw = mechanics.get("allowed_actions")
    allowed_actions = [
        str(item or "").strip().lower()
        for item in allowed_actions_raw
        if str(item or "").strip()
    ] if isinstance(allowed_actions_raw, list) else []
    normalized_target = str(target_action or "").strip().lower()
    if normalized_target not in allowed_actions:
        return None, "Это действие не входит в «Хитрое действие».", False

    patch, live_err = handle_live_combat_action(
        normalized_target,
        session_id,
        use_bonus_action=True,
    )
    if live_err:
        return None, live_err, False
    line_items = patch.get("lines") if isinstance(patch, dict) else []
    if isinstance(line_items, list) and line_items and isinstance(line_items[0], dict):
        first_text = str(line_items[0].get("text") or "")
        if "бонусное действие уже потрачено" in first_text.lower():
            return None, first_text, False
    return patch, None, False


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
    if action == "combat_action_surge":
        return _apply_action_surge_in_combat(session_id, actor_key, ch)
    if action == "combat_indomitable":
        return _apply_indomitable_in_combat(session_id, actor_key, ch, rng=rng)
    if action == "combat_cunning_dash":
        return _apply_cunning_action_in_combat(session_id, actor_key, ch, target_action="combat_dash")
    if action == "combat_cunning_disengage":
        return _apply_cunning_action_in_combat(session_id, actor_key, ch, target_action="combat_disengage")
    if action == "combat_cunning_hide":
        return _apply_cunning_action_in_combat(session_id, actor_key, ch, target_action="combat_hide")
    return None, f"Неизвестная классовая особенность: {combat_action}", False
