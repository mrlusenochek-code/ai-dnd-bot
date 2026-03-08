import asyncio
import importlib
import json
import logging
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.ai.gm import generate_from_prompt
from app.combat.apply_machine import apply_combat_machine_commands
from app.combat.combat_narration_facts import extract_combat_narration_facts
from app.combat.live_actions import handle_live_combat_action, handle_live_combat_reaction
from app.combat.state import current_turn_label, end_combat, get_combat
from app.combat.sync_pcs import sync_pcs_from_chars
from app.combat.test_actions import handle_admin_combat_test_action
from app.core.log_context import client_id_var, request_id_var, session_id_var, uid_var, ws_conn_id_var
from app.db.connection import AsyncSessionLocal
from app.db.models import Character, Player, SessionPlayer, Skill
from app.rules.phb_rest import (
    apply_long_rest,
    apply_short_rest,
    long_rest_recover_hit_dice,
)
from app.rules.phb_math import ability_mod_from_stat100, proficiency_bonus, roll_initiative
from app.gm import combat_narration as gm_combat_narration
from app.web import gm_orchestrator
from app.web.db_helpers import get_or_create_player_web, get_session, list_session_players
from app.web.dice import parse_dice, roll_dice
from app.web.gameplay_helpers import (
    CHAR_STAT_KEYS,
    GM_FINAL_NUM_PREDICT,
    GM_OLLAMA_TIMEOUT_SECONDS,
    _get_kicked,
    _normalized_stats,
    add_event,
    add_system_event,
    create_character,
    get_character,
    is_admin,
)
from app.web.session_state import (
    settings_get,
    settings_set,
    _get_ready_map,
    _set_ready,
    _get_init_map,
    _get_pc_positions,
    _touch_last_seen,
    _get_phase,
    _set_phase,
    _set_init_value,
    _set_pc_zone,
    _initiative_fixed,
)
from app.web.session_lock import get_session_lock
from app.web.state_builder import broadcast_state, _broadcast_state_unlocked, send_state_to_ws, _maybe_restore_combat_state
from app.web.combat_bridge import (
    _append_combat_patch_lines,
    _build_combat_start_preamble_lines,
    _combat_outcome_summary_from_patch,
    _combat_participants_block,
    _generate_combat_narration,
    _merge_combat_patches,
)
from app.web.check_engine import build_check_result, roll_check
from app.web.utils import _clamp, _short_text, as_int
from app.web.ws_access import COMBAT_CLARIFY_TEXT, _combat_clarify_already_sent, _event_actor_label, _load_actor_context, _player_uid
from app.web.ws_checks import SKILL_TO_ABILITY, _ability_mod_from_stats, _normalize_check_name, _skill_bonus_from_rank_and_level
from app.web.ws_combat_prompting import (
    START_INTENT_FALLBACK_TEXT,
    _COMBAT_LOCK_PROMPT,
    _build_combat_scene_facts_for_llm,
    _combat_text_mentions_forbidden_gear,
    _gender_to_pronouns,
    _has_start_intent_sanitary_markers,
    _looks_like_combat_drift,
    _sanitize_gm_output,
    _start_intent_text_needs_repair,
)
from app.web.ws_gameplay import STATE_COMMAND_ALIASES, _detect_chat_combat_action, _format_state_text_for_player, infer_zone_from_action
from app.web.regexes import (
    COMBAT_MOVE_DISTANCE_RE,
    INNATE_SPELL_KEY_PATTERNS,
    SHAPECHANGER_PERSONA_CAPTURE_RE,
)
from app.web.ws_manager import manager
from app.web.ws_turns import (
    TURN_TIMEOUT_SECONDS,
    _clear_current_action_id,
    _clear_initiative,
    _clear_paused_remaining,
    _compute_remaining,
    _get_paused_remaining,
    _get_round_actions,
    _is_free_turns,
    _new_action_id,
    _ready_active_players,
    _remove_player_from_session_settings,
    _set_current_action_id,
    _set_kicked,
    _set_paused_remaining,
    advance_turn,
    set_turn_to_order,
    utcnow,
)


logger = logging.getLogger("app.web" ".server")


def _resolve_build_player_gm_action_text():
    # Lazy import to avoid server_impl <-> ws_handlers import cycle
    server_mod = importlib.import_module("app.web" ".server")
    return getattr(server_mod, "_build_player_gm_action_text")


def _new_request_id() -> str:
    return uuid.uuid4().hex


def _lore_needs_finalize(sess: Any) -> bool:
    lore_text = str(settings_get(sess, "lore_text", "") or "").strip()
    lore_generated = bool(settings_get(sess, "lore_generated", False))
    lore_posted = bool(settings_get(sess, "lore_posted", False))
    return bool(lore_text) and lore_generated and not lore_posted


def _kickoff_lore_finalize_if_needed(session_id: str, sess: Any) -> bool:
    if not _lore_needs_finalize(sess):
        return False
    asyncio.create_task(gm_orchestrator.run_lore_generation(session_id))
    return True


def _lucky_scope_enabled(race_features: Any, scope_key: str) -> bool:
    if not isinstance(race_features, dict):
        return False
    features_raw = race_features.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    lucky_raw = features.get("reroll_ones")
    lucky = lucky_raw if isinstance(lucky_raw, dict) else {}
    scopes_raw = lucky.get("scope")
    scopes = scopes_raw if isinstance(scopes_raw, list) else []
    scope_norm = str(scope_key or "").strip().lower()
    for item in scopes:
        if str(item or "").strip().lower() == scope_norm:
            return True
    return False


def _normalize_save_tag(raw: str) -> str:
    key = str(raw or "").strip().lower()
    aliases = {
        "poison": "poison",
        "яд": "poison",
        "poisoned": "poison",
        "frightened": "frightened",
        "испуг": "frightened",
        "испуган": "frightened",
        "испуганный": "frightened",
        "fear": "frightened",
        "charmed": "charmed",
        "очарование": "charmed",
        "очарован": "charmed",
        "paralyzed": "paralyzed",
        "паралич": "paralyzed",
        "парализован": "paralyzed",
    }
    return aliases.get(key, key)


def _effective_save_mode(
    requested_mode: str,
    race_features: Any,
    ability: str,
    *,
    vs_magic: bool = False,
    vs_tag: str = "",
) -> str:
    mode = str(requested_mode or "normal").strip().lower()
    if mode not in ("normal", "advantage", "disadvantage"):
        mode = "normal"
    if mode != "normal":
        return mode

    ability_key = str(ability or "").strip().lower()
    if ability_key not in CHAR_STAT_KEYS:
        return mode
    if not isinstance(race_features, dict):
        return mode

    saves_raw = race_features.get("saves")
    saves = saves_raw if isinstance(saves_raw, dict) else {}
    adv_raw = saves.get("advantage")
    advantages = adv_raw if isinstance(adv_raw, list) else []
    for item in advantages:
        adv_key = str(item or "").strip().lower()
        if adv_key == ability_key:
            return "advantage"
    if vs_magic:
        adv_magic_raw = saves.get("advantage_vs_magic")
        advantages_vs_magic = adv_magic_raw if isinstance(adv_magic_raw, list) else []
        for item in advantages_vs_magic:
            adv_key = str(item or "").strip().lower()
            if adv_key == ability_key:
                return "advantage"
    tag = _normalize_save_tag(vs_tag)
    if tag:
        adv_conditions_raw = saves.get("advantage_conditions")
        adv_conditions = adv_conditions_raw if isinstance(adv_conditions_raw, list) else []
        for item in adv_conditions:
            cond_key = _normalize_save_tag(str(item or ""))
            if cond_key == tag:
                return "advantage"
    return mode


def _tireless_precision_bonus_for_check(
    race_features: Any,
    *,
    kind: str,
    key: str,
    rng: Any = None,
) -> tuple[int, str]:
    if not isinstance(race_features, dict):
        return 0, ""

    choices_raw = race_features.get("choices")
    choices = choices_raw if isinstance(choices_raw, dict) else {}
    tp_choice_raw = choices.get("tireless_precision")
    tp_choice = tp_choice_raw if isinstance(tp_choice_raw, dict) else {}
    selected_skill = str(tp_choice.get("skill") or "").strip().lower()
    selected_tool = str(tp_choice.get("tool") or "").strip().lower()

    key_norm = str(key or "").strip().lower()
    kind_norm = str(kind or "").strip().lower()
    if kind_norm == "skill":
        if not selected_skill or key_norm != selected_skill:
            return 0, ""
    elif kind_norm == "tool":
        if not selected_tool or key_norm != selected_tool:
            return 0, ""
    else:
        return 0, ""

    bonuses_raw = race_features.get("bonuses")
    bonuses = bonuses_raw if isinstance(bonuses_raw, dict) else {}
    tp_bonus_raw = bonuses.get("tireless_precision")
    tp_bonus = tp_bonus_raw if isinstance(tp_bonus_raw, dict) else {}
    die = str(tp_bonus.get("die") or "1d4").strip().lower()
    if die != "1d4":
        return 0, ""

    roller = rng if rng is not None else random
    value = max(1, int(roller.randint(1, 4)))
    return value, f"1d4({value})"


def _apply_short_rest_spend_hd_with_racial_reroll(
    *,
    hp: int,
    hp_max: int,
    hit_die: int,
    hit_dice_remaining: int,
    con_mod: int,
    spend: int,
    race_features: Any,
    rng: Any = None,
) -> tuple[int, int, list[int], list[str]]:
    hp_max_norm = max(1, int(hp_max))
    hp_after = _clamp(as_int(hp, 0), 0, hp_max_norm)
    hd_remaining = max(0, int(hit_dice_remaining))
    spend_norm = _clamp(int(spend), 0, hd_remaining)
    die_size = max(1, int(hit_die))
    heals: list[int] = []
    reroll_logs: list[str] = []

    reroll_on: set[int] = set()
    if isinstance(race_features, dict):
        features_raw = race_features.get("features")
        features = features_raw if isinstance(features_raw, dict) else {}
        reroll_raw = features.get("hit_dice_reroll")
        reroll_cfg = reroll_raw if isinstance(reroll_raw, dict) else {}
        for item in (reroll_cfg.get("reroll_on") if isinstance(reroll_cfg.get("reroll_on"), list) else []):
            face = as_int(item, 0)
            if 1 <= face <= die_size:
                reroll_on.add(face)

    roller = rng if rng is not None else random
    for _ in range(spend_norm):
        first_raw = max(1, min(int(roller.randint(1, die_size)), die_size))
        final_raw = first_raw
        if first_raw in reroll_on:
            second_raw = max(1, min(int(roller.randint(1, die_size)), die_size))
            final_raw = second_raw
            reroll_logs.append(f"Black Blood Healing: переброс 1d{die_size} (выпало {first_raw} → {second_raw})")
        heal = max(0, final_raw + int(con_mod))
        heals.append(heal)
        hp_after = min(hp_max_norm, hp_after + heal)

    return hp_after, hd_remaining - spend_norm, heals, reroll_logs


def _detect_innate_spell_key(text: str) -> Optional[str]:
    txt = str(text or "").strip()
    if not txt:
        return None
    for spell_key, pattern in INNATE_SPELL_KEY_PATTERNS.items():
        if pattern.search(txt):
            return spell_key
    return None


def _apply_innate_spell_usage(ch: Character, spell_key: str) -> tuple[Optional[str], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    spells_raw = rf.get("innate_spells")
    spells = spells_raw if isinstance(spells_raw, list) else []

    spell_entry: dict[str, Any] | None = None
    for item in spells:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip().lower()
        if name and name == spell_key:
            spell_entry = item
            break
    if spell_entry is None:
        return None, "Это врождённое заклинание недоступно вашей расе.", False

    required_level_raw = spell_entry.get("min_level")
    if required_level_raw is not None:
        required_level = max(0, as_int(required_level_raw, 0))
        current_level = max(1, as_int(getattr(ch, "level", 1), 1))
        if required_level > current_level:
            return None, f"Это заклинание доступно с {required_level} уровня.", False

    frequency = str(spell_entry.get("frequency") or "").strip().lower()
    changed = False
    if frequency == "1_per_long_rest":
        runtime_raw = rf.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        uses_raw = runtime.get("innate_spell_uses")
        uses = dict(uses_raw) if isinstance(uses_raw, dict) else {}
        spell_use_raw = uses.get(spell_key)
        spell_use = dict(spell_use_raw) if isinstance(spell_use_raw, dict) else {}
        used = max(0, as_int(spell_use.get("used"), 0))
        if used >= 1:
            return None, "Это заклинание уже использовано до долгого отдыха.", False
        spell_use["used"] = 1
        uses[spell_key] = spell_use
        runtime["innate_spell_uses"] = uses
        rf["runtime"] = runtime
        ch.race_features = rf
        changed = True

    display_name = str(spell_entry.get("name_ru") or "").strip()
    if not display_name:
        display_name = str(spell_entry.get("name") or spell_key).strip()
    if display_name == spell_key:
        display_name = {
            "dancing_lights": "танцующие огни",
            "faerie_fire": "волшебный огонь",
            "darkness": "тьма",
            "thaumaturgy": "Тауматургия",
            "hellish_rebuke": "Адское возмездие",
        }.get(spell_key, display_name)
    return display_name, None, changed


def _parse_iso_datetime(raw_value: Any) -> Optional[datetime]:
    txt = str(raw_value or "").strip()
    if not txt:
        return None
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except ValueError:
        return None


def _apply_breathe_underwater_usage(ch: Character, *, now: Optional[datetime] = None) -> tuple[Optional[str], Optional[str], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    breath_raw = rf.get("breath")
    breath = dict(breath_raw) if isinstance(breath_raw, dict) else {}
    underwater_raw = breath.get("underwater")
    underwater = dict(underwater_raw) if isinstance(underwater_raw, dict) else {}
    if not underwater:
        return None, None, "Подводное дыхание недоступно вашей расе.", False

    uses = str(underwater.get("uses") or "").strip().lower()
    duration_seconds = max(1, as_int(underwater.get("duration_seconds"), 3600))
    now_dt = now if isinstance(now, datetime) else utcnow()

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if uses == "per_long_rest" and bool(runtime.get("breathe_underwater_used")):
        until_dt = _parse_iso_datetime(runtime.get("breathe_underwater_until_iso"))
        if isinstance(until_dt, datetime) and until_dt > now_dt:
            return None, None, f"Подводное дыхание уже активно до {until_dt.astimezone().strftime('%H:%M')}.", False
        return None, None, "Подводное дыхание уже использовано до долгого отдыха.", False

    until_dt = now_dt + timedelta(seconds=duration_seconds)
    runtime["breathe_underwater_used"] = True
    runtime["breathe_underwater_until_iso"] = until_dt.isoformat()
    rf["runtime"] = runtime
    ch.race_features = rf
    return until_dt.isoformat(), until_dt.astimezone().strftime("%H:%M"), None, True


def _apply_healing_hands_usage(ch: Character) -> tuple[Optional[int], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    healing_raw = features.get("healing_hands")
    healing = dict(healing_raw) if isinstance(healing_raw, dict) else {}
    if not healing:
        return None, "Исцеляющие руки недоступны вашей расе.", False

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    uses = str(healing.get("uses") or "").strip().lower()
    uses_max = max(1, as_int(healing.get("uses_max"), 1))
    changed = False
    if uses == "per_long_rest":
        if bool(runtime.get("healing_hands_used")):
            return None, "Исцеляющие руки уже использованы до долгого отдыха.", False
        if uses_max <= 1:
            runtime["healing_hands_used"] = True
            changed = True

    level = max(1, as_int(getattr(ch, "level", 1), 1))
    amount_raw = healing.get("amount")
    amount_key = str(amount_raw or "").strip().lower()
    heal = level if amount_key == "level" else max(1, as_int(amount_raw, 1))

    hp_before = max(0, as_int(getattr(ch, "hp", 0), 0))
    hp_max = max(0, as_int(getattr(ch, "hp_max", 0), 0))
    hp_after = min(hp_max, hp_before + heal)
    ch.hp = hp_after

    if changed:
        rf["runtime"] = runtime
        ch.race_features = rf

    return max(0, hp_after - hp_before), None, changed


def _apply_healing_hands_in_combat(
    session_id: str,
    actor_key: str,
    ch: Character,
) -> tuple[Optional[dict[str, Any]], Optional[str], bool]:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None, "Combat is not active", False
    if not state.order or state.turn_index < 0 or state.turn_index >= len(state.order):
        return None, "Combat state is inconsistent", False
    turn_key = state.order[state.turn_index]
    if turn_key != actor_key:
        return None, f"Сейчас ходит {current_turn_label(state)}. Дождись своего хода.", False

    actor = state.combatants.get(actor_key)
    if actor is None:
        return None, "Боец не найден.", False
    if not bool(getattr(actor, "action_available", True)):
        return None, "Действие недоступно: действие уже потрачено.", False

    healed_hp, heal_err, changed = _apply_healing_hands_usage(ch)
    if heal_err:
        return None, heal_err, False

    actor.action_available = False
    actor_hp_max = max(0, int(getattr(actor, "hp_max", 0)))
    actor.hp_current = min(actor_hp_max, max(0, as_int(getattr(ch, "hp", actor.hp_current), actor.hp_current)))

    caster_name = str(getattr(ch, "name", "") or getattr(actor, "name", "") or "Персонаж").strip() or "Персонаж"
    patch = {
        "status": f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}",
        "open": True,
        "lines": [
            {"text": f"{caster_name} исцеляет себя прикосновением: +{max(0, int(healed_hp or 0))} HP (Исцеляющие руки)."},
        ],
    }
    return patch, None, changed


def _apply_aasimar_transformation_usage(ch: Character) -> tuple[Optional[dict[str, Any]], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    transform_raw = features.get("aasimar_transformation")
    transform = dict(transform_raw) if isinstance(transform_raw, dict) else {}
    if not transform:
        return None, "Небесное преобразование недоступно вашей расе.", False

    required_level = max(0, as_int(transform.get("min_level"), 0))
    current_level = max(1, as_int(getattr(ch, "level", 1), 1))
    if required_level > current_level:
        return None, f"Небесное преобразование доступно с {required_level} уровня.", False

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    uses = str(transform.get("uses") or "").strip().lower()
    uses_max = max(1, as_int(transform.get("uses_max"), 1))
    if uses == "per_long_rest" and uses_max <= 1 and bool(runtime.get("aasimar_transform_used")):
        return None, "Небесное преобразование уже использовано до долгого отдыха.", False

    kind = str(transform.get("kind") or "").strip().lower()
    rounds_left = 10
    if uses == "per_long_rest" and uses_max <= 1:
        runtime["aasimar_transform_used"] = True
    runtime["aasimar_transformation"] = {
        "active": True,
        "kind": kind,
        "rounds_left": rounds_left,
    }
    if kind == "protector":
        fly_speed_ft = max(0, as_int(transform.get("fly_speed_ft"), 30))
        runtime["fly_speed_ft"] = fly_speed_ft
    else:
        runtime.pop("fly_speed_ft", None)
    rf["runtime"] = runtime
    ch.race_features = rf
    return dict(runtime.get("aasimar_transformation") or {}), None, True


def _apply_aasimar_transformation_in_combat(
    session_id: str,
    actor_key: str,
    ch: Character,
) -> tuple[Optional[dict[str, Any]], Optional[str], bool]:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None, "Combat is not active", False
    if not state.order or state.turn_index < 0 or state.turn_index >= len(state.order):
        return None, "Combat state is inconsistent", False
    turn_key = state.order[state.turn_index]
    if turn_key != actor_key:
        return None, f"Сейчас ходит {current_turn_label(state)}. Дождись своего хода.", False

    actor = state.combatants.get(actor_key)
    if actor is None:
        return None, "Боец не найден.", False
    if not bool(getattr(actor, "action_available", True)):
        return None, "Действие недоступно: действие уже потрачено.", False

    transform_runtime, transform_err, changed = _apply_aasimar_transformation_usage(ch)
    if transform_err:
        return None, transform_err, False

    actor.action_available = False
    actor.race_features = dict(getattr(ch, "race_features", {}) or {})

    caster_name = str(getattr(ch, "name", "") or getattr(actor, "name", "") or "Персонаж").strip() or "Персонаж"
    kind = str((transform_runtime or {}).get("kind") or "").strip().lower()
    kind_ru = {"protector": "Защитник", "scourge": "Карающий", "fallen": "Падший"}.get(kind, kind or "—")
    rounds_left = max(0, as_int((transform_runtime or {}).get("rounds_left"), 0))
    patch = {
        "status": f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}",
        "open": True,
        "lines": [
            {"text": f"{caster_name} активирует Небесное преобразование ({kind_ru}) на {rounds_left} ходов."},
        ],
    }
    return patch, None, changed


def _apply_built_for_success_arm(ch: Character) -> tuple[Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    built_cfg_raw = features.get("built_for_success")
    built_cfg = dict(built_cfg_raw) if isinstance(built_cfg_raw, dict) else {}
    if not built_cfg:
        return "Создан для успеха недоступно вашей расе.", False

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if bool(runtime.get("built_for_success_armed")):
        return "Создан для успеха уже готово: следующий бросок d20 получит +1d4.", False

    level = max(1, as_int(getattr(ch, "level", 1), 1))
    uses_max = max(1, int(proficiency_bonus(level)))
    used = max(0, as_int(runtime.get("built_for_success_used"), 0))
    if used >= uses_max:
        return "Создан для успеха уже использовано до долгого отдыха.", False

    runtime["built_for_success_armed"] = True
    rf["runtime"] = runtime
    ch.race_features = rf
    return None, True


def _consume_built_for_success_for_d20(ch: Character) -> tuple[int, Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    built_cfg_raw = features.get("built_for_success")
    built_cfg = dict(built_cfg_raw) if isinstance(built_cfg_raw, dict) else {}
    if not built_cfg:
        return 0, None, False

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if not bool(runtime.get("built_for_success_armed")):
        return 0, None, False

    level = max(1, as_int(getattr(ch, "level", 1), 1))
    uses_max = max(1, int(proficiency_bonus(level)))
    used = max(0, as_int(runtime.get("built_for_success_used"), 0))
    if used >= uses_max:
        runtime["built_for_success_armed"] = False
        rf["runtime"] = runtime
        ch.race_features = rf
        return 0, None, True

    bonus = random.randint(1, 4)
    runtime["built_for_success_used"] = used + 1
    runtime["built_for_success_armed"] = False
    rf["runtime"] = runtime
    ch.race_features = rf
    return bonus, f"1d4 (Создан для успеха: {bonus})", True


def _apply_fury_of_small_arm(ch: Character) -> tuple[Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    fury_cfg_raw = features.get("fury_of_the_small")
    fury_cfg = dict(fury_cfg_raw) if isinstance(fury_cfg_raw, dict) else {}
    if not fury_cfg:
        return "Ярость малого недоступна вашей расе.", False

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if bool(runtime.get("fury_of_small_used")):
        return "Ярость малого уже использована до отдыха.", False
    if bool(runtime.get("fury_of_small_armed")):
        return "Ярость малого уже готова: сработает на следующем попадании.", False

    runtime["fury_of_small_armed"] = True
    rf["runtime"] = runtime
    ch.race_features = rf
    return None, True


def _extract_shapechanger_persona(text: str) -> str:
    txt = str(text or "").strip()
    if not txt:
        return ""
    m = SHAPECHANGER_PERSONA_CAPTURE_RE.search(txt)
    if not m:
        return ""
    persona = str(m.group("persona") or "").strip()
    if not persona:
        return ""
    persona = re.sub(r"^(?:на|в|под|как|into|as|to)\s+", "", persona, flags=re.IGNORECASE).strip()
    if not persona:
        return ""
    if len(persona) > 120:
        persona = persona[:120].rstrip()
    return persona


def _apply_shapechanger(
    ch: Character,
    *,
    active: bool,
    persona: str | None = None,
    voice: str | None = None,
) -> tuple[Optional[str], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    shape_cfg_raw = features.get("shapechanger")
    shape_cfg = dict(shape_cfg_raw) if isinstance(shape_cfg_raw, dict) else {}
    if not shape_cfg:
        return None, "Перевёртыш недоступен вашей расе.", False

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    shape_raw = runtime.get("shapechanger")
    shape = dict(shape_raw) if isinstance(shape_raw, dict) else {}
    now_iso = datetime.now(timezone.utc).isoformat()

    if active:
        persona_value = str(persona or "").strip()
        if len(persona_value) > 120:
            persona_value = persona_value[:120].rstrip()
        voice_value = str(voice or "").strip()
        if len(voice_value) > 120:
            voice_value = voice_value[:120].rstrip()
        changed = (
            not bool(shape.get("active"))
            or str(shape.get("persona") or "").strip() != persona_value
            or str(shape.get("voice") or "").strip() != voice_value
        )
        shape["active"] = True
        shape["persona"] = persona_value
        shape["voice"] = voice_value
        shape["changed_at_iso"] = now_iso
        runtime["shapechanger"] = shape

        if persona_value:
            history_raw = runtime.get("shapechanger_history")
            history_list = history_raw if isinstance(history_raw, list) else []
            history: list[dict[str, str]] = []
            for item in history_list:
                if not isinstance(item, dict):
                    continue
                item_persona = str(item.get("persona") or "").strip()
                if not item_persona:
                    continue
                item_voice = str(item.get("voice") or "").strip()
                item_changed = str(item.get("changed_at_iso") or "").strip()
                history.append(
                    {
                        "persona": item_persona[:120],
                        "voice": item_voice[:120],
                        "changed_at_iso": item_changed,
                    }
                )
            history.append(
                {
                    "persona": persona_value,
                    "voice": voice_value,
                    "changed_at_iso": now_iso,
                }
            )
            runtime["shapechanger_history"] = history[-3:]

        rf["runtime"] = runtime
        ch.race_features = rf
        shown = persona_value or "без уточнения"
        return f"Меняет облик: {shown}.", None, changed

    if not bool(shape.get("active")):
        return "Уже в истинной форме.", None, False
    shape["active"] = False
    shape["persona"] = ""
    shape["voice"] = ""
    shape["changed_at_iso"] = now_iso
    runtime["shapechanger"] = shape
    rf["runtime"] = runtime
    ch.race_features = rf
    return "Возвращается в истинную форму.", None, True


def _apply_shapechanger_in_combat(
    session_id: str,
    actor_key: str,
    ch: Character,
    *,
    active: bool,
    persona: str | None = None,
    voice: str | None = None,
) -> tuple[Optional[dict[str, Any]], Optional[str], bool]:
    state = get_combat(session_id)
    if state is None or not state.active:
        return None, "Combat is not active", False
    if not state.order or state.turn_index < 0 or state.turn_index >= len(state.order):
        return None, "Combat state is inconsistent", False
    turn_key = state.order[state.turn_index]
    if turn_key != actor_key:
        return None, f"Сейчас ходит {current_turn_label(state)}. Дождись своего хода.", False

    actor = state.combatants.get(actor_key)
    if actor is None:
        return None, "Боец не найден.", False
    if not bool(getattr(actor, "action_available", True)):
        return None, "Действие недоступно: действие уже потрачено.", False

    msg, shape_err, changed = _apply_shapechanger(ch, active=active, persona=persona, voice=voice)
    if shape_err:
        return None, shape_err, False

    actor.action_available = False
    actor.race_features = dict(getattr(ch, "race_features", {}) or {})

    actor_name = str(getattr(ch, "name", "") or getattr(actor, "name", "") or "Персонаж").strip() or "Персонаж"
    line = f"{actor_name}: {msg or 'Меняет облик.'}"
    patch = {
        "status": f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}",
        "open": True,
        "lines": [
            {"text": line, "muted": True},
        ],
    }
    return patch, None, changed


def _reset_racial_rest_uses(ch: Character) -> bool:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    changed = False
    if "innate_spell_uses" in runtime:
        runtime.pop("innate_spell_uses", None)
        changed = True
    if "stone_endurance_used" in runtime:
        runtime.pop("stone_endurance_used", None)
        changed = True
    if "healing_hands_used" in runtime:
        runtime.pop("healing_hands_used", None)
        changed = True
    if "aasimar_transform_used" in runtime:
        runtime.pop("aasimar_transform_used", None)
        changed = True
    if "aasimar_transformation" in runtime:
        runtime.pop("aasimar_transformation", None)
        changed = True
    if "fly_speed_ft" in runtime:
        runtime.pop("fly_speed_ft", None)
        changed = True
    if "breathe_underwater_used" in runtime:
        runtime.pop("breathe_underwater_used", None)
        changed = True
    if "breathe_underwater_until_iso" in runtime:
        runtime.pop("breathe_underwater_until_iso", None)
        changed = True
    if "breath_weapon_used" in runtime:
        runtime.pop("breath_weapon_used", None)
        changed = True
    if "relentless_endurance_used" in runtime:
        runtime.pop("relentless_endurance_used", None)
        changed = True
    if "built_for_success_used" in runtime:
        runtime.pop("built_for_success_used", None)
        changed = True
    if "built_for_success_armed" in runtime:
        runtime.pop("built_for_success_armed", None)
        changed = True
    if "fury_of_small_used" in runtime:
        runtime.pop("fury_of_small_used", None)
        changed = True
    if "fury_of_small_armed" in runtime:
        runtime.pop("fury_of_small_armed", None)
        changed = True
    if not changed:
        return False
    if runtime:
        rf["runtime"] = runtime
    else:
        rf.pop("runtime", None)
    ch.race_features = rf
    return True


def _reset_combatant_racial_rest_uses(session_id: str, actor_key: str) -> bool:
    state = get_combat(session_id)
    if state is None or not state.active:
        return False
    actor = state.combatants.get(actor_key)
    if actor is None:
        return False
    race_features = actor.race_features if isinstance(actor.race_features, dict) else {}
    runtime_raw = race_features.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    changed = False
    if "innate_spell_uses" in runtime:
        runtime.pop("innate_spell_uses", None)
        changed = True
    if "stone_endurance_used" in runtime:
        runtime.pop("stone_endurance_used", None)
        changed = True
    if "healing_hands_used" in runtime:
        runtime.pop("healing_hands_used", None)
        changed = True
    if "aasimar_transform_used" in runtime:
        runtime.pop("aasimar_transform_used", None)
        changed = True
    if "aasimar_transformation" in runtime:
        runtime.pop("aasimar_transformation", None)
        changed = True
    if "fly_speed_ft" in runtime:
        runtime.pop("fly_speed_ft", None)
        changed = True
    if "breathe_underwater_used" in runtime:
        runtime.pop("breathe_underwater_used", None)
        changed = True
    if "breathe_underwater_until_iso" in runtime:
        runtime.pop("breathe_underwater_until_iso", None)
        changed = True
    if "breath_weapon_used" in runtime:
        runtime.pop("breath_weapon_used", None)
        changed = True
    if "relentless_endurance_used" in runtime:
        runtime.pop("relentless_endurance_used", None)
        changed = True
    if "built_for_success_used" in runtime:
        runtime.pop("built_for_success_used", None)
        changed = True
    if "built_for_success_armed" in runtime:
        runtime.pop("built_for_success_armed", None)
        changed = True
    if "fury_of_small_used" in runtime:
        runtime.pop("fury_of_small_used", None)
        changed = True
    if "fury_of_small_armed" in runtime:
        runtime.pop("fury_of_small_armed", None)
        changed = True
    if not changed:
        return False
    if runtime:
        race_features["runtime"] = runtime
    else:
        race_features.pop("runtime", None)
    actor.race_features = race_features
    return True


async def _persist_relentless_endurance_used_from_combat_state(db, sess, session_id: str) -> bool:
    state = get_combat(session_id)
    if state is None or not state.active:
        return False
    relentless_used_uids: set[int] = set()
    built_for_success_runtime_by_uid: dict[int, dict[str, Any]] = {}
    fury_of_small_runtime_by_uid: dict[int, dict[str, Any]] = {}
    for key, actor in (state.combatants or {}).items():
        actor_key = str(key or "").strip().lower()
        if not actor_key.startswith("pc_"):
            continue
        uid_raw = actor_key[3:]
        if not uid_raw.isdigit():
            continue
        race_features = actor.race_features if isinstance(actor.race_features, dict) else {}
        runtime = race_features.get("runtime") if isinstance(race_features.get("runtime"), dict) else {}
        if bool(runtime.get("relentless_endurance_used", False)):
            relentless_used_uids.add(int(uid_raw))
        if "built_for_success_used" in runtime or "built_for_success_armed" in runtime:
            built_runtime: dict[str, Any] = {}
            if "built_for_success_used" in runtime:
                built_runtime["built_for_success_used"] = max(0, as_int(runtime.get("built_for_success_used"), 0))
            if "built_for_success_armed" in runtime:
                built_runtime["built_for_success_armed"] = bool(runtime.get("built_for_success_armed"))
            built_for_success_runtime_by_uid[int(uid_raw)] = built_runtime
        if "fury_of_small_used" in runtime or "fury_of_small_armed" in runtime:
            fury_runtime: dict[str, Any] = {}
            if "fury_of_small_used" in runtime:
                fury_runtime["fury_of_small_used"] = bool(runtime.get("fury_of_small_used"))
            if "fury_of_small_armed" in runtime:
                fury_runtime["fury_of_small_armed"] = bool(runtime.get("fury_of_small_armed"))
            fury_of_small_runtime_by_uid[int(uid_raw)] = fury_runtime
    if not relentless_used_uids and not built_for_success_runtime_by_uid and not fury_of_small_runtime_by_uid:
        return False

    _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
    changed = False
    for uid, ch in chars_by_uid.items():
        if uid not in relentless_used_uids and uid not in built_for_success_runtime_by_uid and uid not in fury_of_small_runtime_by_uid:
            continue
        ch = chars_by_uid.get(uid)
        if ch is None:
            continue
        race_features_raw = getattr(ch, "race_features", None)
        race_features = dict(race_features_raw) if isinstance(race_features_raw, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        local_changed = False
        if uid in relentless_used_uids and not bool(runtime.get("relentless_endurance_used", False)):
            runtime["relentless_endurance_used"] = True
            local_changed = True
        built_runtime = built_for_success_runtime_by_uid.get(uid)
        if isinstance(built_runtime, dict):
            if "built_for_success_used" in built_runtime:
                value = max(0, as_int(built_runtime.get("built_for_success_used"), 0))
                if max(0, as_int(runtime.get("built_for_success_used"), 0)) != value:
                    runtime["built_for_success_used"] = value
                    local_changed = True
            if "built_for_success_armed" in built_runtime:
                value = bool(built_runtime.get("built_for_success_armed"))
                if bool(runtime.get("built_for_success_armed")) != value:
                    runtime["built_for_success_armed"] = value
                    local_changed = True
        fury_runtime = fury_of_small_runtime_by_uid.get(uid)
        if isinstance(fury_runtime, dict):
            if "fury_of_small_used" in fury_runtime:
                value = bool(fury_runtime.get("fury_of_small_used"))
                if bool(runtime.get("fury_of_small_used")) != value:
                    runtime["fury_of_small_used"] = value
                    local_changed = True
            if "fury_of_small_armed" in fury_runtime:
                value = bool(fury_runtime.get("fury_of_small_armed"))
                if bool(runtime.get("fury_of_small_armed")) != value:
                    runtime["fury_of_small_armed"] = value
                    local_changed = True
        if local_changed:
            race_features["runtime"] = runtime
            ch.race_features = race_features
            flag_modified(ch, "race_features")
            changed = True
    return changed


async def ws_room_handler(ws: WebSocket, session_id: str) -> None:
    async def ws_error(message: str, *, fatal: bool = False, request_id: Optional[str] = None) -> None:
        rid = request_id
        if rid is None:
            try:
                rid = request_id_var.get()
            except LookupError:
                rid = None
        payload = {"type": "error", "message": message, "fatal": fatal, "request_id": rid}
        await ws.send_text(json.dumps(payload, ensure_ascii=False))

    uid_raw = ws.query_params.get("uid")
    if not uid_raw or not uid_raw.isdigit():
        rid = _new_request_id()
        await ws.accept()
        await ws_error("No uid", fatal=True, request_id=rid)
        await ws.close()
        return

    uid = int(uid_raw)

    # log context for this WS connection (task-local)
    request_id_var.set(_new_request_id())
    session_id_var.set(session_id)
    uid_var.set(uid)
    ws_conn_id_var.set(uuid.uuid4().hex[:12])
    cid = ws.query_params.get("cid")
    if cid:
        client_id_var.set(str(cid))

    await manager.connect(session_id, ws)
    logger.info("ws connected")

    try:
        await send_state_to_ws(session_id, ws)

        while True:
            # Ждём входящее сообщение. State приходит через broadcast_state() по событиям,
            # а таймер рисуется локально на фронте.
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                data = {"action": "say", "text": raw}

            action = (data.get("action") or "").strip().lower()
            text = (data.get("text") or "").strip()
            msg_request_id = data.get("request_id") if isinstance(data, dict) else None

            async with AsyncSessionLocal() as db:
                sess = await get_session(db, session_id)
                if not sess:
                    await ws_error("Session not found", request_id=msg_request_id)
                    continue
                _maybe_restore_combat_state(sess, session_id)

                # don't overwrite name here; join sets it
                player = await get_or_create_player_web(db, uid, "")

                # kicked check (live)
                if str(player.id) in _get_kicked(sess):
                    await ws_error("You were kicked from this session", fatal=True)
                    await ws.close()
                    return

                q = await db.execute(
                    select(SessionPlayer).where(
                        SessionPlayer.session_id == sess.id,
                        SessionPlayer.player_id == player.id,
                    )
                )
                sp = q.scalar_one_or_none()
                if not sp:
                    await ws_error("Not joined/active. Refresh page.", request_id=msg_request_id)
                    continue
                if sp.is_active is False:
                    if action in ("leave", "quit", "exit"):
                        await ws.close()
                        return
                    await ws_error("You are offline in this session", request_id=msg_request_id)
                    continue

                async def _process_leave_and_broadcast() -> None:
                    if sess.current_player_id == player.id and bool(sess.is_active):
                        await advance_turn(db, sess)

                    sp.is_active = False
                    _remove_player_from_session_settings(sess, player.id)

                    active_left = await list_session_players(db, sess, active_only=True)
                    if not active_left:
                        sess.current_player_id = None
                        sess.turn_started_at = None
                        _clear_paused_remaining(sess)

                    await db.commit()
                    await add_system_event(db, sess, f"Игрок {player.display_name} вышел из игры.")
                    await broadcast_state(session_id)

                if action in ("leave", "quit", "exit"):
                    await _process_leave_and_broadcast()
                    await ws.close()
                    return

                _touch_last_seen(sess, player.id)
                if action == "ping":
                    await db.commit()
                    continue
                await db.commit()

                # ready/unready actions (do not require game started)
                if action in ("ready", "unready"):
                    if action == "ready":
                        my_char = await get_character(db, sess.id, player.id)
                        if not my_char:
                            await ws_error("Create character first", request_id=msg_request_id)
                            continue
                    _set_ready(sess, player.id, action == "ready")
                    await db.commit()
                    await add_system_event(db, sess, f"Готовность: игрок #{sp.join_order} — {'ГОТОВ' if action=='ready' else 'НЕ ГОТОВ'}.")
                    await broadcast_state(session_id)
                    continue

                # status: just broadcast
                if action == "status":
                    await broadcast_state(session_id)
                    continue

                # Admin-only control actions
                if action == "begin":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can start")
                        continue
                    if sess.is_active:
                        await ws_error("Already started")
                        continue

                    sps = await list_session_players(db, sess, active_only=True)
                    if not sps:
                        await ws_error("No players")
                        continue

                    active_ids = [x.player_id for x in sps]
                    missing_sps: list[SessionPlayer] = []
                    if active_ids:
                        q_chars = await db.execute(
                            select(Character).where(
                                Character.session_id == sess.id,
                                Character.player_id.in_(active_ids),
                            )
                        )
                        char_ids = {ch.player_id for ch in q_chars.scalars().all()}
                        missing_sps = [x for x in sps if x.player_id not in char_ids]
                    if missing_sps:
                        q_players = await db.execute(select(Player).where(Player.id.in_([x.player_id for x in missing_sps])))
                        names_by_id = {p.id: p.display_name for p in q_players.scalars().all()}
                        missing_names = ", ".join(
                            f"#{x.join_order} {names_by_id.get(x.player_id, str(x.player_id))}" for x in missing_sps
                        )
                        await add_system_event(db, sess, f"Нельзя стартовать: персонаж не создан у {missing_names}.")
                        await ws_error("Create character first", request_id=msg_request_id)
                        await broadcast_state(session_id)
                        continue

                    # all ready check
                    ready_map = _get_ready_map(sess)
                    if any(not bool(ready_map.get(str(x.player_id), False)) for x in sps):
                        await ws_error("Not all players are ready")
                        continue

                    sess.is_active = True
                    sess.is_paused = False
                    sess.current_player_id = None
                    sess.turn_started_at = None
                    sess.turn_index = 1
                    raw_story = settings_get(sess, "story", {}) or {}
                    if isinstance(raw_story, dict):
                        settings_set(sess, "free_turns", bool(raw_story.get("free_turns")))
                    _set_phase(sess, "lore_pending")
                    _clear_current_action_id(sess)
                    _clear_paused_remaining(sess)
                    await db.commit()
                    await add_system_event(db, sess, "Игра началась. Генерируем вступительную историю...")
                    await broadcast_state(session_id)
                    asyncio.create_task(gm_orchestrator.run_lore_generation(session_id))
                    continue

                if action == "pause":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can pause")
                        continue
                    if sess.is_paused:
                        await broadcast_state(session_id)
                        continue
                    rem = await _compute_remaining(sess)
                    if rem is not None:
                        _set_paused_remaining(sess, rem)
                    sess.is_paused = True
                    await db.commit()
                    await add_system_event(db, sess, f"Пауза. Осталось: {rem if rem is not None else '—'} сек.")
                    await broadcast_state(session_id)
                    continue

                if action == "resume":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can resume")
                        continue
                    if not sess.is_paused:
                        await broadcast_state(session_id)
                        continue

                    # continue timer from stored remaining
                    stored = _get_paused_remaining(sess)
                    if stored is not None and sess.current_player_id:
                        stored = max(0, min(TURN_TIMEOUT_SECONDS, int(stored)))
                        elapsed = TURN_TIMEOUT_SECONDS - stored
                        sess.turn_started_at = utcnow() - timedelta(seconds=elapsed)
                    else:
                        # fallback: restart timer (or clear if no current player)
                        sess.turn_started_at = utcnow() if sess.current_player_id else None

                    sess.is_paused = False
                    _clear_paused_remaining(sess)
                    await db.commit()
                    await add_system_event(db, sess, "Продолжили игру.")
                    await broadcast_state(session_id)
                    continue

                if action == "skip":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can skip")
                        continue
                    if _get_phase(sess) == "gm_pending":
                        await ws_error("Ждём ответа мастера...")
                        continue
                    if not sess.current_player_id:
                        await ws_error("Not started")
                        continue
                    if sess.is_paused:
                        await ws_error("Paused. Resume first.")
                        continue

                    nxt = await advance_turn(db, sess)
                    if not nxt:
                        await ws_error("No players")
                        continue
                    await add_system_event(db, sess, f"Ход пропущен. Следующий: #{nxt.join_order}.")
                    await broadcast_state(session_id)
                    continue

                if action.startswith("admin_combat_test_"):
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can run combat UI test")
                        continue
                    combat_patch, combat_err = handle_admin_combat_test_action(action, session_id)
                    if combat_err:
                        await ws_error(combat_err)
                        continue
                    if combat_patch is not None:
                        await broadcast_state(session_id, combat_log_ui_patch=combat_patch)
                        continue

                lock = get_session_lock(session_id)
                if action == "admin_combat_live_start":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can run live combat")
                        continue
                    bootstrap_zone = "arena"
                    bootstrap_enemies = [
                        {"id": "band1", "name": "Разбойник", "hp": 18, "ac": 13, "init_mod": 2, "threat": 2},
                    ]
                    settings_set(
                        sess,
                        "combat_live_bootstrap",
                        {
                            "zone": bootstrap_zone,
                            "enemies": bootstrap_enemies,
                        },
                    )
                    if sess.is_paused:
                        sess.is_paused = False
                        _clear_paused_remaining(sess)
                        if sess.current_player_id and not sess.turn_started_at:
                            sess.turn_started_at = utcnow()
                    await db.commit()
                    gm_text = (
                        f'@@COMBAT_START(zone="{bootstrap_zone}", cause="admin")\n'
                        '@@COMBAT_ENEMY_ADD(id=band1, name="Разбойник", hp=18, ac=13, init_mod=2, threat=2)'
                    )
                    async with lock:
                        before_state = get_combat(session_id)
                        before_active = bool(before_state and before_state.active)
                        # If a previous combat is still active (often due to persisted restore),
                        # hard-reset it so @@COMBAT_START is not ignored and we always start from round 1.
                        if before_active:
                            end_combat(session_id)
                            before_state = None
                            before_active = False
                        combat_patch = apply_combat_machine_commands(session_id, gm_text)
                        _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                        sync_pcs_from_chars(session_id, chars_by_uid)
                        if combat_patch is None:
                            combat_patch = {
                                "reset": True,
                                "open": True,
                                "lines": [{"text": "Live бой запущен админом.", "muted": True}],
                            }
                        combat_state = get_combat(session_id)
                        after_active = bool(combat_state and combat_state.active)
                        if after_active and combat_state is not None and combat_state.active:
                            preamble_lines = _build_combat_start_preamble_lines(
                                player=player,
                                chars_by_uid=chars_by_uid,
                                combat_state=combat_state,
                            )
                            if not isinstance(combat_patch, dict):
                                combat_patch = {}
                            patch_lines = combat_patch.get("lines")
                            already = False
                            if isinstance(patch_lines, list):
                                for it in patch_lines:
                                    t = None
                                    if isinstance(it, dict):
                                        t = it.get("text")
                                    elif isinstance(it, str):
                                        t = it
                                    if isinstance(t, str) and (
                                        t.startswith("Бой начался между") or t.startswith("Добавлен в бой:")
                                    ):
                                        already = True
                                        break
                            if preamble_lines and not already:
                                combat_patch = _append_combat_patch_lines(combat_patch, preamble_lines, prepend=True)
                            combat_patch["reset"] = True
                        if combat_state is not None and combat_state.active:
                            if combat_patch.get("reset") is True:
                                combat_state.round_no = 1
                                combat_state.turn_index = 0
                            combat_patch["status"] = (
                                f"⚔ Бой • Раунд {combat_state.round_no} • Ход: {current_turn_label(combat_state)}"
                            )
                        await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_patch)
                    continue

                if action == "admin_combat_live_end":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can end live combat")
                        continue
                    async with lock:
                        end_combat(session_id)
                        await _broadcast_state_unlocked(
                            session_id,
                            combat_log_ui_patch={
                                "status": "Бой завершён",
                                "open": False,
                                "lines": [{"text": "Live бой завершён админом.", "muted": True}],
                            },
                        )
                    continue

                if action == "combat_log_clear":
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can clear combat log")
                        continue
                    state = get_combat(session_id)
                    lines = [{"text": "Журнал очищен.", "muted": True}]
                    if state is not None and state.active:
                        lines.append(
                            {
                                "text": f"⚔ Бой • Раунд {state.round_no} • Ход: {current_turn_label(state)}",
                                "muted": True,
                                "kind": "status",
                            }
                        )
                    patch = {"reset": True, "open": True, "lines": lines}
                    await broadcast_state(session_id, combat_log_ui_patch=patch)
                    continue

                if action in {
                    "combat_attack",
                    "combat_hooves_attack",
                    "combat_end_turn",
                    "combat_dodge",
                    "combat_dash",
                    "combat_move",
                    "combat_disengage",
                    "combat_takeoff",
                    "combat_land",
                    "combat_mode_walk",
                    "combat_mode_swim",
                    "combat_mode_climb",
                    "combat_escape",
                    "combat_use_object",
                    "combat_help",
                }:
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can use combat actions")
                        continue
                    async with lock:
                        combat_patch, combat_err = handle_live_combat_action(action, session_id)
                        if combat_err:
                            await ws_error(combat_err)
                            continue
                        if combat_patch:
                            await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_patch)
                            continue

                # chat / command parsing
                if action != "say":
                    await ws_error("Unknown action", request_id=msg_request_id)
                    continue

                if not text:
                    continue

                # normalize leading slash for typed commands
                cmdline = text.lstrip()
                if cmdline.startswith("/"):
                    cmdline = cmdline[1:].lstrip()

                lower = cmdline.lower()
                if lower in STATE_COMMAND_ALIASES:
                    ch = await get_character(db, sess.id, player.id)
                    await add_system_event(db, sess, _format_state_text_for_player(sess, player, ch))
                    await broadcast_state(session_id)
                    continue

                combat_action = _detect_chat_combat_action(text)
                _maybe_restore_combat_state(sess, session_id)
                combat_state = get_combat(session_id)
                if combat_state is None:
                    bootstrap = settings_get(sess, "combat_live_bootstrap", None)
                    if isinstance(bootstrap, dict):
                        zone_raw = str(bootstrap.get("zone") or "arena").strip() or "arena"
                        zone = zone_raw.replace('"', '\\"')
                        enemies = bootstrap.get("enemies")
                        if isinstance(enemies, list):
                            lines = [f'@@COMBAT_START(zone="{zone}", cause="bootstrap")']
                            for enemy in enemies:
                                if not isinstance(enemy, dict):
                                    continue
                                enemy_id = str(enemy.get("id") or "").strip()
                                enemy_name = str(enemy.get("name") or "").strip()
                                if not enemy_id or not enemy_name:
                                    continue
                                enemy_id_escaped = enemy_id.replace('"', '\\"')
                                enemy_name_escaped = enemy_name.replace('"', '\\"')
                                hp = max(1, as_int(enemy.get("hp"), 1))
                                ac = max(1, as_int(enemy.get("ac"), 10))
                                init_mod = as_int(enemy.get("init_mod"), 0)
                                threat = max(0, as_int(enemy.get("threat"), 1))
                                lines.append(
                                    f'@@COMBAT_ENEMY_ADD(id={enemy_id_escaped}, name="{enemy_name_escaped}", '
                                    f"hp={hp}, ac={ac}, init_mod={init_mod}, threat={threat})"
                                )
                            if len(lines) > 1:
                                gm_text = "\n".join(lines)
                                async with lock:
                                    before_state = get_combat(session_id)
                                    before_active = bool(before_state and before_state.active)
                                    combat_patch = apply_combat_machine_commands(session_id, gm_text)
                                    _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                                    sync_pcs_from_chars(session_id, chars_by_uid)
                                    combat_state = get_combat(session_id)
                                    after_active = bool(combat_state and combat_state.active)
                                    if after_active and combat_state is not None and combat_state.active:
                                        preamble_lines = _build_combat_start_preamble_lines(
                                            player=player,
                                            chars_by_uid=chars_by_uid,
                                            combat_state=combat_state,
                                        )
                                        if not isinstance(combat_patch, dict):
                                            combat_patch = {}
                                        patch_lines = combat_patch.get("lines")
                                        already = False
                                        if isinstance(patch_lines, list):
                                            for it in patch_lines:
                                                t = None
                                                if isinstance(it, dict):
                                                    t = it.get("text")
                                                elif isinstance(it, str):
                                                    t = it
                                                if isinstance(t, str) and (
                                                    t.startswith("Бой начался между") or t.startswith("Добавлен в бой:")
                                                ):
                                                    already = True
                                                    break
                                        if preamble_lines and not already:
                                            combat_patch = _append_combat_patch_lines(combat_patch, preamble_lines, prepend=True)
                                        combat_patch["reset"] = True
                                        combat_patch["open"] = True
                                        combat_patch["status"] = (
                                            f"⚔ Бой • Раунд {combat_state.round_no} • Ход: {current_turn_label(combat_state)}"
                                        )
                                        await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_patch)
                combat_active = bool(combat_state and combat_state.active)
                start_intent = ("войти в бой" in lower) or lower.startswith("бой с") or ("начать бой" in lower)

                if start_intent and combat_active:
                    await ws_error("Бой уже идёт.")
                    continue

                if start_intent and not combat_active:
                    actor_label = await _event_actor_label(db, sess, player)
                    await add_event(
                        db,
                        sess,
                        f"{actor_label}: {text}",
                        actor_player_id=player.id,
                        result_json={
                            "type": "player_action",
                            "raw_text": text,
                            "combat_chat_action": "start",
                        },
                    )
                    await db.commit()

                    enemy_name = "Разбойник" if "разбойник" in lower else ""
                    if not enemy_name:
                        enemy_match = re.search(r"бой с\s+([^\n,.;:!?]+)", lower, flags=re.IGNORECASE)
                        if enemy_match:
                            enemy_raw = enemy_match.group(1).strip(" \"'`")
                            if enemy_raw:
                                enemy_name = enemy_raw[:40].strip()
                    if not enemy_name:
                        enemy_name = "Разбойник"
                    enemy_name = enemy_name[0].upper() + enemy_name[1:] if enemy_name else "Разбойник"

                    enemy_name_escaped = enemy_name.replace('"', '\\"')
                    gm_text = (
                        '@@COMBAT_START(zone="arena", cause="bootstrap")\n'
                        f'@@COMBAT_ENEMY_ADD(id=band1, name="{enemy_name_escaped}", hp=18, ac=13, init_mod=2, threat=2)'
                    )
                    async with lock:
                        combat_patch = apply_combat_machine_commands(session_id, gm_text)
                        _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                        sync_pcs_from_chars(session_id, chars_by_uid)
                        combat_state = get_combat(session_id)
                        if combat_patch is None:
                            combat_patch = {}
                        if combat_state and combat_state.active:
                            preamble_lines = _build_combat_start_preamble_lines(
                                player=player,
                                chars_by_uid=chars_by_uid,
                                combat_state=combat_state,
                            )
                            patch_lines = combat_patch.get("lines")
                            already = False
                            if isinstance(patch_lines, list):
                                for it in patch_lines:
                                    t = None
                                    if isinstance(it, dict):
                                        t = it.get("text")
                                    elif isinstance(it, str):
                                        t = it
                                    if isinstance(t, str) and (
                                        t.startswith("Бой начался между") or t.startswith("Добавлен в бой:")
                                    ):
                                        already = True
                                        break
                            if preamble_lines and not already:
                                combat_patch = _append_combat_patch_lines(combat_patch, preamble_lines, prepend=True)

                        combat_patch["reset"] = True
                        combat_patch["open"] = True
                        if combat_state and combat_state.active:
                            combat_patch["status"] = (
                                f"⚔ Бой • Раунд {combat_state.round_no} • Ход: {current_turn_label(combat_state)}"
                            )
                        await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_patch)

                    ch = await get_character(db, sess.id, player.id)
                    player_name = (ch.name if ch and ch.name else player.display_name)
                    facts_block = await _build_combat_scene_facts_for_llm(
                        db,
                        sess,
                        player,
                        enemy_name=enemy_name,
                        max_lines=10,
                    )
                    prompt = (
                        f"{_COMBAT_LOCK_PROMPT}\n\n"
                        "ЗАПРЕЩЕНО ДОБАВЛЯТЬ НОВЫЕ СУЩНОСТИ:\n"
                        "- никаких новых NPC (никаких 'человек', 'парень', 'толпа', 'стражник' и т.п.)\n"
                        "- никаких новых предметов/оружия/именованных артефактов\n"
                        "- можно упоминать оружие/предметы только если они есть в фактах сцены или в действии игрока\n"
                        "Разрешено только:\n"
                        "- ты\n"
                        f"- {enemy_name}\n"
                        "- нейтральное окружение (улица/двор/пыль/камни/фонари) без новых персонажей\n\n"
                        "Сейчас идёт бой. Напиши вступление к схватке здесь и сейчас.\n"
                        "Правила (строго):\n"
                        "- Только бой здесь и сейчас.\n"
                        "- НЕЛЬЗЯ: числа, кубики, HP, AC, урон, раунды, ходы, формулы.\n"
                        "- 8-12 предложений, ровно 1 абзац.\n"
                        "- Динамично, но без деталей инвентаря.\n"
                        "- Пиши во 2 лице: 'ты'.\n"
                        "- Герой текущего игрока всегда 'ты'. Нельзя писать про героя в 3-м лице по имени (запрещено 'Валерикус делает/устает/падает'). Имя героя можно упомянуть максимум 1 раз только как уточнение-метку, например: 'ты (Валерикус)...'.\n"
                        "- Нельзя упоминать броню/экипировку/оружие, если этого нет в фактах или в действии игрока.\n"
                        "- Последняя строка строго: Что делаете дальше?\n\n"
                        f"Факты сцены (не выдумывать сверх этого):\n{facts_block}\n\n"
                        f"Контекст: Ты вступаешь в бой с {enemy_name}. "
                        f"Имя героя (для ориентира): {player_name}\n"
                    )
                    resp = await generate_from_prompt(
                        prompt=prompt,
                        timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
                        num_predict=GM_FINAL_NUM_PREDICT,
                    )
                    gm_text = _sanitize_gm_output(_strip_machine_lines(str(resp.get("text") or "").strip()))
                    gm_text = re.sub(r"(?im)^\s*@@COMBAT_[A-Z_]+.*$", "", gm_text).strip()

                    has_mechanics = bool(
                        re.search(r"(?:\d|\bd20\b|\bhp\b|\bac\b|урон|бросок|раунд|ход)", gm_text, flags=re.IGNORECASE)
                    )
                    has_forbidden_gear = _combat_text_mentions_forbidden_gear(
                        gm_text,
                        action_text=text,
                        facts_block=facts_block,
                    )
                    has_markers = _has_start_intent_sanitary_markers(gm_text)
                    needs_repair = _start_intent_text_needs_repair(gm_text)
                    if has_markers or has_forbidden_gear or needs_repair:
                        reprompt = (
                            f"{prompt}\n"
                            "Перепиши расширенно на 8–12 предложений, 1 абзац. "
                            "Герой игрока всегда 'ты': не пиши про героя в 3-м лице по имени; имя можно упомянуть максимум 1 раз как метку вида 'ты (Имя)'. "
                            "Запрещено: броня/экипировка/оружие, если этого нет в фактах или в действии игрока. "
                            "Никаких новых сущностей. Только здесь-и-сейчас.\n"
                            f"Черновик для переписывания:\n{gm_text}\n"
                        )
                        repair_resp = await generate_from_prompt(
                            prompt=reprompt,
                            timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
                            num_predict=GM_FINAL_NUM_PREDICT,
                        )
                        gm_text = _sanitize_gm_output(_strip_machine_lines(str(repair_resp.get("text") or "").strip()))
                        gm_text = re.sub(r"(?im)^\s*@@COMBAT_[A-Z_]+.*$", "", gm_text).strip()
                        has_mechanics = bool(
                            re.search(r"(?:\d|\bd20\b|\bhp\b|\bac\b|урон|бросок|раунд|ход)", gm_text, flags=re.IGNORECASE)
                        )
                        has_markers = _has_start_intent_sanitary_markers(gm_text)
                        has_forbidden_gear = _combat_text_mentions_forbidden_gear(
                            gm_text,
                            action_text=text,
                            facts_block=facts_block,
                        )
                        needs_repair = _start_intent_text_needs_repair(gm_text)
                    if (
                        not gm_text
                        or has_mechanics
                        or _looks_like_combat_drift(gm_text)
                        or has_markers
                        or has_forbidden_gear
                        or needs_repair
                    ):
                        gm_text = START_INTENT_FALLBACK_TEXT

                    await add_system_event(db, sess, f"🧙 GM: {gm_text}")
                    await db.commit()
                    await broadcast_state(session_id)
                    continue

                phase_now = _get_phase(sess)
                if phase_now == "lore_pending":
                    if _kickoff_lore_finalize_if_needed(session_id, sess):
                        await ws_error("Публикую вступительную историю...")
                    else:
                        await ws_error("Ждём вступительную историю...")
                    continue
                if phase_now == "gm_pending" and not combat_active:
                    await ws_error("Ждём ответа мастера...")
                    continue

                # Race runtime actions: Tortle shell defense ("прячусь в панцирь" / "вылезаю из панциря")
                if combat_action in {"tortle_shell_in", "tortle_shell_out"}:
                    # If in combat — respect turn order (как и остальные боевые действия)
                    if combat_active:
                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        turn_key: Optional[str] = None
                        if combat_state and combat_state.order and 0 <= combat_state.turn_index < len(combat_state.order):
                            turn_key = combat_state.order[combat_state.turn_index]
                        if not turn_key or turn_key != player_key:
                            current_name = current_turn_label(combat_state) if combat_state else "другой участник"
                            await add_system_event(db, sess, f"Сейчас ходит {current_name}. Дождись своего хода.")
                            await db.commit()
                            await broadcast_state(session_id)
                            continue

                    async with lock:
                        ch = await get_character(db, sess.id, player.id)
                        if not ch:
                            await ws_error("Персонаж не найден.", request_id=msg_request_id)
                            continue

                        if str(getattr(ch, "race_kit", "") or "").lower() != "tortle":
                            await add_system_event(db, sess, "Это действие доступно только тортлу (панцирь).")
                            await db.commit()
                            await broadcast_state(session_id)
                            continue

                        rf = getattr(ch, "race_features", None)
                        rf2 = dict(rf) if isinstance(rf, dict) else {}

                        runtime = rf2.get("runtime")
                        runtime2 = dict(runtime) if isinstance(runtime, dict) else {}
                        is_active_now = bool(runtime2.get("active"))

                        if combat_action == "tortle_shell_in":
                            if is_active_now:
                                msg = "Ты уже в панцире."
                            else:
                                rf2["runtime"] = {"active": True, "ac_bonus": 4, "speed_override_ft": 0}
                                ch.race_features = rf2
                                await db.commit()
                                msg = "Ты прячешься в панцирь: +4 к КД, скорость 0."
                        else:
                            if not is_active_now:
                                msg = "Ты уже вне панциря."
                            else:
                                rf2.pop("runtime", None)
                                ch.race_features = rf2
                                await db.commit()
                                msg = "Ты вылезаешь из панциря: эффекты панциря сняты."

                        # Resync combat stats immediately (AC/speed)
                        if combat_active:
                            _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                            sync_pcs_from_chars(session_id, chars_by_uid)

                    await add_system_event(db, sess, msg)
                    await db.commit()
                    await broadcast_state(session_id)
                    continue

                if combat_action == "use_built_for_success":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    arm_err, changed = _apply_built_for_success_arm(ch)
                    if arm_err:
                        await ws_error(arm_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    await add_system_event(
                        db,
                        sess,
                        f"{actor_name}: Готово: следующий бросок d20 получит +1d4.",
                    )
                    await broadcast_state(session_id)
                    continue

                if combat_action == "combat_fury_of_small":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    arm_err, changed = _apply_fury_of_small_arm(ch)
                    if arm_err:
                        await ws_error(arm_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                        if combat_active:
                            _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                            sync_pcs_from_chars(session_id, chars_by_uid)
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    await add_system_event(
                        db,
                        sess,
                        f"{actor_name}: Готово: Ярость малого сработает на следующем попадании.",
                    )
                    await broadcast_state(session_id)
                    continue

                if combat_action in {"combat_shapechanger_shift", "combat_shapechanger_revert"}:
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    is_shift = combat_action == "combat_shapechanger_shift"
                    persona = _extract_shapechanger_persona(text) if is_shift else ""
                    if combat_active:
                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        combat_patch, shape_err, changed = _apply_shapechanger_in_combat(
                            session_id,
                            player_key,
                            ch,
                            active=is_shift,
                            persona=persona,
                            voice="",
                        )
                        if shape_err:
                            await ws_error(shape_err, request_id=msg_request_id)
                            continue
                        if changed:
                            flag_modified(ch, "race_features")
                        await db.commit()
                        if combat_patch:
                            await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_patch)
                        continue
                    msg, shape_err, changed = _apply_shapechanger(
                        ch,
                        active=is_shift,
                        persona=persona,
                        voice="",
                    )
                    if shape_err:
                        await ws_error(shape_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    await add_system_event(db, sess, f"{actor_name}: {msg or 'Меняет облик.'}")
                    await broadcast_state(session_id)
                    continue

                # Combat Lock: during active combat only combat actions are allowed.
                if combat_active:
                    is_admin_user = await is_admin(db, sess, player)
                    if lower.startswith("ooc ") or cmdline.startswith("//"):
                        pass
                    elif (lower.startswith("gm ") or lower.startswith("gm:")) and is_admin_user:
                        pass
                    elif combat_action == "rest_long":
                        await ws_error("Сейчас бой, отдых невозможен.", request_id=msg_request_id)
                        continue
                    elif combat_action:
                        innate_spell_key = _detect_innate_spell_key(text) if combat_action == "combat_innate_spell" else None
                        actor_label = await _event_actor_label(db, sess, player)
                        await add_event(
                            db,
                            sess,
                            f"{actor_label}: {text}",
                            actor_player_id=player.id,
                            result_json={
                                "type": (
                                    "combat_innate_spell"
                                    if combat_action == "combat_innate_spell"
                                    else (
                                        "combat_stone_endurance"
                                        if combat_action == "combat_stone_endurance"
                                        else (
                                            "combat_healing_hands"
                                            if combat_action == "combat_healing_hands"
                                            else (
                                                "combat_aasimar_transform"
                                                if combat_action == "combat_aasimar_transform"
                                                else (
                                                    "breathe_underwater"
                                                    if combat_action == "breathe_underwater"
                                                    else (
                                                        "combat_breath_weapon"
                                                        if combat_action == "combat_breath_weapon"
                                                        else (
                                                            "combat_shapechanger"
                                                            if combat_action in {"combat_shapechanger_shift", "combat_shapechanger_revert"}
                                                            else "player_action"
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                    )
                                ),
                                "raw_text": text,
                                "combat_chat_action": combat_action,
                                "spell_key": innate_spell_key,
                            },
                        )
                        await db.commit()

                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        if combat_action == "combat_stone_endurance":
                            combat_patch, combat_err = handle_live_combat_reaction(
                                "combat_stone_endurance",
                                session_id,
                                player_key,
                            )
                            if combat_err:
                                await ws_error(combat_err, request_id=msg_request_id)
                                continue
                            if combat_patch:
                                await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_patch)
                            continue
                        if combat_action == "breathe_underwater":
                            ch = await get_character(db, sess.id, player.id)
                            if not ch:
                                await ws_error("Персонаж не найден.", request_id=msg_request_id)
                                continue
                            _until_iso, until_hhmm, breathe_err, changed = _apply_breathe_underwater_usage(ch)
                            if breathe_err:
                                await ws_error(breathe_err, request_id=msg_request_id)
                                continue
                            if changed:
                                flag_modified(ch, "race_features")
                                await db.commit()
                            _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                            sync_pcs_from_chars(session_id, chars_by_uid)
                            actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                            await add_system_event(
                                db,
                                sess,
                                f"{actor_name} может дышать под водой 1 час (до {until_hhmm}).",
                            )
                            await broadcast_state(session_id)
                            continue
                        turn_key: Optional[str] = None
                        if combat_state and combat_state.order and 0 <= combat_state.turn_index < len(combat_state.order):
                            turn_key = combat_state.order[combat_state.turn_index]
                        if not turn_key or turn_key != player_key:
                            current_name = current_turn_label(combat_state) if combat_state else "другой участник"
                            await add_system_event(db, sess, f"Сейчас ходит {current_name}. Дождись своего хода.")
                            await broadcast_state(session_id)
                            continue

                        if combat_action == "combat_innate_spell":
                            if not innate_spell_key:
                                await ws_error("Не понял, какое врождённое заклинание вы хотите наложить.", request_id=msg_request_id)
                                continue
                            ch = await get_character(db, sess.id, player.id)
                            if not ch:
                                await ws_error("Персонаж не найден.", request_id=msg_request_id)
                                continue
                            spell_display_name, innate_err, changed = _apply_innate_spell_usage(ch, innate_spell_key)
                            if innate_err:
                                await ws_error(innate_err, request_id=msg_request_id)
                                continue
                            if changed:
                                flag_modified(ch, "race_features")
                                await db.commit()
                            caster_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                            combat_state_now = get_combat(session_id)
                            round_no = combat_state_now.round_no if combat_state_now is not None else 1
                            turn_label_now = current_turn_label(combat_state_now) if combat_state_now is not None else "-"
                            patch = {
                                "status": f"⚔ Бой • Раунд {round_no} • Ход: {turn_label_now}",
                                "open": True,
                                "lines": [
                                    {"text": f"{caster_name} использует врождённую магию: {spell_display_name}."},
                                ],
                            }
                            await _broadcast_state_unlocked(session_id, combat_log_ui_patch=patch)
                            continue

                        if combat_action == "combat_healing_hands":
                            ch = await get_character(db, sess.id, player.id)
                            if not ch:
                                await ws_error("Персонаж не найден.", request_id=msg_request_id)
                                continue
                            combat_patch, healing_err, changed = _apply_healing_hands_in_combat(session_id, player_key, ch)
                            if healing_err:
                                await ws_error(healing_err, request_id=msg_request_id)
                                continue
                            if changed:
                                flag_modified(ch, "race_features")
                            await db.commit()
                            if combat_patch:
                                await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_patch)
                            continue

                        if combat_action == "combat_aasimar_transform":
                            ch = await get_character(db, sess.id, player.id)
                            if not ch:
                                await ws_error("Персонаж не найден.", request_id=msg_request_id)
                                continue
                            combat_patch, transform_err, changed = _apply_aasimar_transformation_in_combat(session_id, player_key, ch)
                            if transform_err:
                                await ws_error(transform_err, request_id=msg_request_id)
                                continue
                            if changed:
                                flag_modified(ch, "race_features")
                            await db.commit()
                            _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                            sync_pcs_from_chars(session_id, chars_by_uid)
                            if combat_patch:
                                await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_patch)
                            continue

                        all_patches: list[dict[str, Any]] = []
                        async with lock:
                            move_distance_ft: Optional[int] = None
                            if combat_action == "combat_move":
                                m_dist = COMBAT_MOVE_DISTANCE_RE.search(cmdline)
                                move_distance_ft = as_int(m_dist.group(1), 0) if m_dist else 0
                            combat_patch, combat_err = handle_live_combat_action(
                                combat_action,
                                session_id,
                                distance_ft=move_distance_ft,
                            )
                            if combat_err:
                                await ws_error(combat_err, request_id=msg_request_id)
                                continue
                            if combat_patch:
                                all_patches.append(combat_patch)

                            while True:
                                state_now = get_combat(session_id)
                                if not state_now or not state_now.active or not state_now.order:
                                    break
                                if state_now.turn_index < 0 or state_now.turn_index >= len(state_now.order):
                                    break
                                turn_key_now = state_now.order[state_now.turn_index]
                                turn_actor = state_now.combatants.get(turn_key_now)
                                if not turn_actor or turn_actor.side != "enemy":
                                    break
                                enemy_patch, enemy_err = handle_live_combat_action("combat_attack", session_id)
                                if enemy_err:
                                    logger.warning("enemy auto combat action failed", extra={"action": {"error": enemy_err}})
                                    break
                                if enemy_patch:
                                    all_patches.append(enemy_patch)

                            merged_patch = _merge_combat_patches(all_patches) if all_patches else None
                            persist_changed = await _persist_relentless_endurance_used_from_combat_state(db, sess, session_id)
                            if persist_changed:
                                await db.commit()
                            await _broadcast_state_unlocked(session_id, combat_log_ui_patch=merged_patch)
                        facts = extract_combat_narration_facts(merged_patch)
                        if facts:
                            required_fact_count = 3 if len(facts) >= 3 else len(facts)
                            player_raw_action = str(text or "").strip()
                            ch = await get_character(db, sess.id, player.id)
                            player_name = (ch.name if ch and ch.name else player.display_name)
                            ended = any("бой заверш" in f.lower() or "победа" in f.lower() for f in facts)
                            enemy_name_for_facts = "противник"
                            state_for_facts = get_combat(session_id)
                            if state_for_facts and isinstance(state_for_facts.combatants, dict):
                                for actor in state_for_facts.combatants.values():
                                    if str(getattr(actor, "side", "")).lower() != "enemy":
                                        continue
                                    actor_name = str(getattr(actor, "name", "") or "").strip()
                                    if actor_name:
                                        enemy_name_for_facts = actor_name
                                        break
                            scene_facts_block = await _build_combat_scene_facts_for_llm(
                                db,
                                sess,
                                player,
                                enemy_name=enemy_name_for_facts,
                                max_lines=10,
                            )
                            if not str(scene_facts_block or "").strip():
                                scene_facts_block = "- Зона игрока: место рядом с тобой\n- Окружение: место рядом с тобой."
                            text = await gm_combat_narration.generate_combat_narration_from_facts(
                                combat_lock_prompt=_COMBAT_LOCK_PROMPT,
                                facts=facts,
                                required_fact_count=required_fact_count,
                                scene_facts_block=scene_facts_block,
                                player_raw_action=_short_text(player_raw_action, 180),
                                player_name=player_name,
                                ended=ended,
                                timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
                                num_predict=GM_FINAL_NUM_PREDICT,
                                mentions_forbidden_gear_fn=lambda candidate_text: _combat_text_mentions_forbidden_gear(
                                    candidate_text,
                                    action_text=player_raw_action,
                                    facts_block=scene_facts_block,
                                ),
                            )
                            if text:
                                await add_system_event(
                                    db,
                                    sess,
                                    f"🧙 GM: {text}",
                                    result_json={"type": "combat_narration", "facts": facts},
                                )
                                await db.commit()
                                await broadcast_state(session_id)
                        continue
                    else:
                        await ws_error(
                            "Combat Lock: в бою доступны только боевые команды (атака/конец хода/уклон/движение/рывок/отход/взлёт/приземление/помощь/побег/каменная выносливость/исцеляющие руки/небесное преобразование/подводное дыхание/оружие дыхания) или OOC.",
                            request_id=msg_request_id,
                        )
                        continue

                # OOC (any time, no turn)
                if combat_action == "combat_breath_weapon":
                    await ws_error("Оружие дыхания можно применить только в бою.", request_id=msg_request_id)
                    continue

                # OOC (any time, no turn)
                if combat_action == "breathe_underwater":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    _until_iso, until_hhmm, breathe_err, changed = _apply_breathe_underwater_usage(ch)
                    if breathe_err:
                        await ws_error(breathe_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                    await db.commit()
                    combat_now = get_combat(session_id)
                    if combat_now is not None and combat_now.active:
                        _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                        sync_pcs_from_chars(session_id, chars_by_uid)
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    await add_system_event(
                        db,
                        sess,
                        f"{actor_name} может дышать под водой 1 час (до {until_hhmm}).",
                    )
                    await broadcast_state(session_id)
                    continue

                # OOC (any time, no turn)
                if combat_action == "combat_aasimar_transform":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    transform_runtime, transform_err, changed = _apply_aasimar_transformation_usage(ch)
                    if transform_err:
                        await ws_error(transform_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                    await db.commit()
                    combat_now = get_combat(session_id)
                    if combat_now is not None and combat_now.active:
                        _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                        sync_pcs_from_chars(session_id, chars_by_uid)
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    kind = str((transform_runtime or {}).get("kind") or "").strip().lower()
                    kind_ru = {"protector": "Защитник", "scourge": "Карающий", "fallen": "Падший"}.get(kind, kind or "—")
                    await add_system_event(
                        db,
                        sess,
                        f"{actor_name} активирует Небесное преобразование ({kind_ru}) на 10 ходов.",
                    )
                    await broadcast_state(session_id)
                    continue

                # OOC (any time, no turn)
                if combat_action == "combat_healing_hands":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    healed_hp, healing_err, changed = _apply_healing_hands_usage(ch)
                    if healing_err:
                        await ws_error(healing_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                    await db.commit()
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    await add_system_event(
                        db,
                        sess,
                        f"{actor_name} исцеляет себя прикосновением: +{max(0, int(healed_hp or 0))} HP (Исцеляющие руки).",
                    )
                    await broadcast_state(session_id)
                    continue

                # OOC (any time, no turn)
                if combat_action == "rest_long" and lower not in {"rest", "rest long"}:
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    changed = _reset_racial_rest_uses(ch)
                    if changed:
                        flag_modified(ch, "race_features")
                    player_uid = _player_uid(player)
                    player_key = f"pc_{player_uid}" if player_uid is not None else ""
                    _reset_combatant_racial_rest_uses(session_id, player_key)
                    await db.commit()
                    await add_system_event(db, sess, "Долгий отдых: врождённые заклинания восстановлены.")
                    await broadcast_state(session_id)
                    continue

                # OOC (any time, no turn)
                if lower.startswith("ooc ") or cmdline.startswith("//"):
                    msg = cmdline[4:].strip() if lower.startswith("ooc ") else cmdline[2:].strip()
                    await add_event(db, sess, f"[OOC] {player.display_name} (#{sp.join_order}): {msg}")
                    await broadcast_state(session_id)
                    continue

                # GM (admin only, any time, no turn)
                if lower.startswith("gm ") or lower.startswith("gm:"):
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can GM")
                        continue
                    msg = cmdline[2:].lstrip(":").strip()
                    await add_system_event(db, sess, f"🧙 GM: {msg}")
                    await broadcast_state(session_id)
                    continue

                if lower == "help":
                    await add_system_event(
                        db,
                        sess,
                        "Команды: roll/adv/dis <1d20+3> (на своём ходу, не тратит ход), "
                        "pass|end (на своём ходу, заканчивает ход), "
                        "ooc <текст> или //текст (не тратит ход), "
                        "gm <текст> (только админ), "
                        "name <НовоеИмя> (не тратит ход), "
                        "leave (выйти), kick <#> (админ), turn <#> (админ), "
                        "init / init roll / init set <#> <val> / init start / init clear (админ)."
                    )
                    await broadcast_state(session_id)
                    continue

                if lower == "char":
                    await add_system_event(
                        db,
                        sess,
                        "de" "ps.Character commands: char create <Name> [Class], me, hp <+N|-N|N>, sta <+N|-N|N>, rest|rest long|rest short|rest hd <N>, "
                        "stat <str|dex|con|int|wis|cha> <0..100>, check [adv|dis] <stat_or_skill> [dc N] (ручной бросок, опционально), "
                        "toolcheck [adv|dis] <tool_key> [dc N], "
                        "save [adv|dis] <str|dex|con|int|wis|cha> [vs <poison|frightened|charmed>] [dc N], "
                        "save magic [adv|dis] <str|dex|con|int|wis|cha> [vs <poison|frightened|charmed>] [dc N].",
                    )
                    await broadcast_state(session_id)
                    continue

                m_char_create = re.match(r"^char\s+create\s+(.+)$", cmdline, re.IGNORECASE)
                if m_char_create:
                    payload = m_char_create.group(1).strip()
                    if not payload:
                        await ws_error("Usage: char create <Name> [Class]", request_id=msg_request_id)
                        continue
                    ch_existing = await get_character(db, sess.id, player.id)
                    if ch_existing:
                        await ws_error("de" "ps.Character already exists", request_id=msg_request_id)
                        continue
                    parts = payload.split()
                    ch_name = parts[0][:80]
                    ch_class = (parts[1] if len(parts) > 1 else "Adventurer")[:40]
                    await create_character(
                        db,
                        sess.id,
                        player.id,
                        name=ch_name,
                        class_kit=ch_class,
                        class_skin=ch_class,
                    )
                    await add_system_event(db, sess, f"Character created: {ch_name} ({ch_class}) for player #{sp.join_order}.")
                    await broadcast_state(session_id)
                    continue

                if lower == "me":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    stats = _normalized_stats(ch.stats)
                    await add_system_event(
                        db,
                        sess,
                        f"[ME] {ch.name} ({ch.class_kit}) lvl {int(ch.level or 1)} | "
                        f"HP {int(ch.hp or 0)}/{int(ch.hp_max or 0)} | STA {int(ch.sta or 0)}/{int(ch.sta_max or 0)} | "
                        f"STR {stats['str']} DEX {stats['dex']} CON {stats['con']} INT {stats['int']} WIS {stats['wis']} CHA {stats['cha']}",
                    )
                    await broadcast_state(session_id)
                    continue

                if lower == "rest" or lower == "rest long":
                    combat_state_now = get_combat(session_id)
                    if combat_state_now is not None and combat_state_now.active:
                        await ws_error("Нельзя отдыхать во время боя", request_id=msg_request_id)
                        continue
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    old_hp = as_int(ch.hp, 0)
                    old_sta = as_int(ch.sta, 0)
                    hd_max = max(1, as_int(getattr(ch, "hit_dice_max", 1), 1))
                    hd_before = max(0, min(as_int(getattr(ch, "hit_dice_remaining", hd_max), hd_max), hd_max))
                    hp, sta = apply_long_rest(
                        hp=old_hp,
                        hp_max=as_int(ch.hp_max, 0),
                        sta=old_sta,
                        sta_max=as_int(ch.sta_max, 0),
                    )
                    hd_after = long_rest_recover_hit_dice(hd_max, hd_before)
                    ch.hp = hp
                    ch.sta = sta
                    ch.hit_dice_remaining = hd_after
                    if _reset_racial_rest_uses(ch):
                        flag_modified(ch, "race_features")
                    player_uid = _player_uid(player)
                    player_key = f"pc_{player_uid}" if player_uid is not None else ""
                    _reset_combatant_racial_rest_uses(session_id, player_key)
                    await db.commit()
                    await add_system_event(
                        db,
                        sess,
                        f"[REST] long {ch.name}: HP {old_hp}->{int(ch.hp or 0)}/{int(ch.hp_max or 0)}, "
                        f"STA {old_sta}->{int(ch.sta or 0)}/{int(ch.sta_max or 0)}, "
                        f"HD {hd_before}->{hd_after}/{hd_max} (d{max(1, as_int(getattr(ch, 'hit_die', 8), 8))})",
                    )
                    await broadcast_state(session_id)
                    continue

                if lower == "rest short":
                    combat_state_now = get_combat(session_id)
                    if combat_state_now is not None and combat_state_now.active:
                        await ws_error("Нельзя отдыхать во время боя", request_id=msg_request_id)
                        continue
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    old_sta = as_int(ch.sta, 0)
                    hp, sta = apply_short_rest(
                        hp=as_int(ch.hp, 0),
                        hp_max=as_int(ch.hp_max, 0),
                        sta=old_sta,
                        sta_max=as_int(ch.sta_max, 0),
                    )
                    ch.hp = hp
                    ch.sta = sta
                    if _reset_racial_rest_uses(ch):
                        flag_modified(ch, "race_features")
                    player_uid = _player_uid(player)
                    player_key = f"pc_{player_uid}" if player_uid is not None else ""
                    _reset_combatant_racial_rest_uses(session_id, player_key)
                    await db.commit()
                    await add_system_event(
                        db,
                        sess,
                        f"[REST] short {ch.name}: STA {old_sta}->{int(ch.sta or 0)}/{int(ch.sta_max or 0)}",
                    )
                    await broadcast_state(session_id)
                    continue

                m_rest_hd = re.match(r"^rest\s+hd\s+(\d+)$", lower, re.IGNORECASE)
                if m_rest_hd:
                    combat_state_now = get_combat(session_id)
                    if combat_state_now is not None and combat_state_now.active:
                        await ws_error("Нельзя отдыхать во время боя", request_id=msg_request_id)
                        continue
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    requested = as_int(m_rest_hd.group(1), 0)
                    if requested <= 0 or requested > 99:
                        await ws_error("Usage: rest hd <N>, where N is 1..99", request_id=msg_request_id)
                        continue

                    hd_max = max(1, as_int(getattr(ch, "hit_dice_max", 1), 1))
                    hd_before = max(0, min(as_int(getattr(ch, "hit_dice_remaining", hd_max), hd_max), hd_max))
                    if hd_before <= 0:
                        await ws_error("No hit dice remaining", request_id=msg_request_id)
                        continue

                    stats = ch.stats if isinstance(ch.stats, dict) else {}
                    con_stat = as_int(stats.get("con"), 50) if isinstance(stats, dict) else 50
                    con_mod = ability_mod_from_stat100(con_stat)
                    hp_before = _clamp(as_int(ch.hp, 0), 0, max(1, as_int(ch.hp_max, 1)))

                    hp_after, hd_after, heals, reroll_logs = _apply_short_rest_spend_hd_with_racial_reroll(
                        hp=hp_before,
                        hp_max=as_int(ch.hp_max, 0),
                        hit_die=max(1, as_int(getattr(ch, "hit_die", 8), 8)),
                        hit_dice_remaining=hd_before,
                        con_mod=con_mod,
                        spend=requested,
                        race_features=getattr(ch, "race_features", None),
                    )

                    ch.hp = hp_after
                    ch.hit_dice_remaining = hd_after
                    await db.commit()

                    healed_total = max(0, hp_after - hp_before)
                    await add_system_event(
                        db,
                        sess,
                        f"[REST] hd x{requested} {ch.name}: +{healed_total} HP, "
                        f"HD {hd_before}->{hd_after}/{hd_max}, rolls={heals}",
                    )
                    for line in reroll_logs:
                        await add_system_event(db, sess, line)
                    await broadcast_state(session_id)
                    continue

                m_res = re.match(r"^(hp|sta)\s+([+-]?\d+)$", lower, re.IGNORECASE)
                if m_res:
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    key = m_res.group(1).lower()
                    raw_val = m_res.group(2)
                    delta_or_value = as_int(raw_val, 0)
                    cur_attr = "hp" if key == "hp" else "sta"
                    max_attr = "hp_max" if key == "hp" else "sta_max"
                    cur = as_int(getattr(ch, cur_attr), 0)
                    max_v = max(0, as_int(getattr(ch, max_attr), 0))
                    if raw_val.startswith("+") or raw_val.startswith("-"):
                        nxt = _clamp(cur + delta_or_value, 0, max_v)
                    else:
                        nxt = _clamp(delta_or_value, 0, max_v)
                    setattr(ch, cur_attr, nxt)
                    await db.commit()
                    await add_system_event(db, sess, f"{ch.name}: {key.upper()} {cur}->{nxt}/{max_v}")
                    await broadcast_state(session_id)
                    continue

                if lower.startswith("stat "):
                    parts = cmdline.split()
                    if len(parts) < 3 or len(parts) > 4:
                        await ws_error("Usage: stat <str|dex|con|int|wis|cha> <0..100>", request_id=msg_request_id)
                        continue

                    admin = await is_admin(db, sess, player)
                    target_sp = sp

                    if len(parts) == 4:
                        maybe_order = parts[1].lstrip("#")
                        if not maybe_order.isdigit():
                            await ws_error("Usage: stat #<order> <stat> <0..100>", request_id=msg_request_id)
                            continue
                        target_order = as_int(maybe_order, 0)
                        if target_order <= 0:
                            await ws_error("Usage: stat #<order> <stat> <0..100>", request_id=msg_request_id)
                            continue
                        sps_all = await list_session_players(db, sess, active_only=False)
                        target_sp = next((x for x in sps_all if int(x.join_order or 0) == target_order), None)
                        if not target_sp:
                            await ws_error("de" "ps.Player not found", request_id=msg_request_id)
                            continue
                        stat_key = parts[2].lower()
                        stat_val = as_int(parts[3], -1)
                    else:
                        stat_key = parts[1].lower()
                        stat_val = as_int(parts[2], -1)

                    if stat_key not in CHAR_STAT_KEYS:
                        await ws_error("Unknown stat key", request_id=msg_request_id)
                        continue
                    if stat_val < 0 or stat_val > 100:
                        await ws_error("Stat must be 0..100", request_id=msg_request_id)
                        continue
                    if sess.is_active and not admin:
                        await ws_error("Only admin can change stats after start", request_id=msg_request_id)
                        continue
                    if not admin and target_sp.player_id != player.id:
                        await ws_error("You can change only your own stats before start", request_id=msg_request_id)
                        continue

                    target_ch = await get_character(db, sess.id, target_sp.player_id)
                    if not target_ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue

                    stats = _normalized_stats(target_ch.stats)
                    old_val = stats.get(stat_key, 50)
                    stats[stat_key] = stat_val
                    target_ch.stats = stats
                    await db.commit()
                    await add_system_event(
                        db,
                        sess,
                        f"[STAT] #{target_sp.join_order} {target_ch.name}: {stat_key} {old_val}->{stat_val}",
                    )
                    await broadcast_state(session_id)
                    continue

                if lower.startswith("check"):
                    parts = cmdline.split()
                    if len(parts) < 2:
                        await ws_error("Usage: check [adv|dis] <stat_or_skill> [dc N]", request_id=msg_request_id)
                        continue
                    mode = "roll"
                    idx = 1
                    if idx < len(parts) and parts[idx].lower() in ("adv", "dis"):
                        mode = parts[idx].lower()
                        idx += 1
                    if idx >= len(parts):
                        await ws_error("Usage: check [adv|dis] <stat_or_skill> [dc N]", request_id=msg_request_id)
                        continue

                    key = parts[idx].lower()
                    idx += 1
                    while idx < len(parts) and not parts[idx].lower().startswith("dc"):
                        key += f" {parts[idx].lower()}"
                        idx += 1
                    key = _normalize_check_name(key)
                    dc: Optional[int] = None
                    if idx < len(parts):
                        tok = parts[idx].lower()
                        if tok.startswith("dc"):
                            if tok == "dc":
                                if idx + 1 >= len(parts):
                                    await ws_error("Usage: check ... dc <N>", request_id=msg_request_id)
                                    continue
                                dc = as_int(parts[idx + 1], -1)
                                idx += 2
                            else:
                                dc = as_int(tok[2:], -1)
                                idx += 1
                        else:
                            await ws_error("Usage: check [adv|dis] <stat_or_skill> [dc N]", request_id=msg_request_id)
                            continue
                    if idx != len(parts):
                        await ws_error("Usage: check [adv|dis] <stat_or_skill> [dc N]", request_id=msg_request_id)
                        continue
                    if dc is not None and dc < 0:
                        await ws_error("DC must be >= 0", request_id=msg_request_id)
                        continue

                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue

                    def _manual_candidate_mod(candidate: str, skills_by_key: dict[str, Skill]) -> int:
                        if candidate in CHAR_STAT_KEYS:
                            return _ability_mod_from_stats(ch.stats, candidate)
                        ability_key = SKILL_TO_ABILITY.get(candidate)
                        ability_mod = _ability_mod_from_stats(ch.stats, ability_key) if ability_key else 0
                        sk = skills_by_key.get(candidate)
                        skill_bonus = _skill_bonus_from_rank_and_level(sk.rank, ch.level) if sk else 0
                        return ability_mod + skill_bonus

                    skills_by_key: dict[str, Skill] = {}
                    if "|" in key:
                        candidates = [x.strip() for x in key.split("|") if x.strip()]
                        if not candidates:
                            mod = 0
                        else:
                            skill_candidates = [c for c in candidates if c not in CHAR_STAT_KEYS]
                            if skill_candidates:
                                q_skills = await db.execute(
                                    select(Skill).where(
                                        Skill.character_id == ch.id,
                                        Skill.skill_key.in_(skill_candidates),
                                    )
                                )
                                skills_by_key = {str(sk.skill_key or "").strip().lower(): sk for sk in q_skills.scalars().all()}
                            mod = max(_manual_candidate_mod(c, skills_by_key) for c in candidates)
                    elif key in CHAR_STAT_KEYS:
                        mod = _ability_mod_from_stats(ch.stats, key)
                    else:
                        q_skill = await db.execute(
                            select(Skill).where(
                                Skill.character_id == ch.id,
                                Skill.skill_key == key,
                            )
                        )
                        sk = q_skill.scalar_one_or_none()
                        ability_key = SKILL_TO_ABILITY.get(key)
                        ability_mod = _ability_mod_from_stats(ch.stats, ability_key) if ability_key else 0
                        skill_bonus = _skill_bonus_from_rank_and_level(sk.rank, ch.level) if sk else 0
                        mod = ability_mod + skill_bonus

                    mapped_mode = {
                        "roll": "normal",
                        "adv": "advantage",
                        "dis": "disadvantage",
                    }.get(mode, "normal")
                    ra, rb, roll = roll_check(
                        mapped_mode,
                        reroll_ones=_lucky_scope_enabled(getattr(ch, "race_features", None), "check"),
                    )
                    check_payload = {
                        "actor_uid": _player_uid(player),
                        "kind": "ability" if key in CHAR_STAT_KEYS else "skill",
                        "name": key,
                        "dc": dc if dc is not None else 0,
                        "mode": mapped_mode,
                    }
                    res = build_check_result(check_payload, mod=mod, roll_a=ra, roll_b=rb, roll=roll)
                    base_total = int(res["total"])
                    bfs_bonus, bfs_bonus_text, bfs_changed = _consume_built_for_success_for_d20(ch)
                    if bfs_changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    tp_bonus, tp_bonus_text = _tireless_precision_bonus_for_check(
                        getattr(ch, "race_features", None),
                        kind=str(check_payload["kind"]),
                        key=key,
                    )
                    total = base_total + tp_bonus + bfs_bonus
                    rolls_text = str(roll) if rb is None else f"{ra}/{rb}->{roll}"

                    msg = f"[CHECK] {ch.name}: {key} = {rolls_text} + {mod:+d} => {total}"
                    if tp_bonus > 0 and tp_bonus_text:
                        msg = f"[CHECK] {ch.name}: {key} = {rolls_text} + {mod:+d} + {tp_bonus_text} => {total}"
                    if bfs_bonus > 0 and bfs_bonus_text:
                        msg = f"[CHECK] {ch.name}: {key} = {rolls_text} + {mod:+d} + {bfs_bonus_text} => {total}"
                    if tp_bonus > 0 and tp_bonus_text and bfs_bonus > 0 and bfs_bonus_text:
                        msg = (
                            f"[CHECK] {ch.name}: {key} = {rolls_text} + {mod:+d} + {tp_bonus_text} + {bfs_bonus_text} => {total}"
                        )
                    if dc is not None:
                        ok = total >= dc
                        msg += f" (DC {dc}) {'SUCCESS' if ok else 'FAIL'}"
                    await add_system_event(db, sess, msg)
                    await broadcast_state(session_id)
                    continue

                if lower.startswith("toolcheck"):
                    parts = cmdline.split()
                    if len(parts) < 2:
                        await ws_error("Usage: toolcheck [adv|dis] <tool_key> [dc N]", request_id=msg_request_id)
                        continue
                    mode = "roll"
                    idx = 1
                    if idx < len(parts) and parts[idx].lower() in ("adv", "dis"):
                        mode = parts[idx].lower()
                        idx += 1
                    if idx >= len(parts):
                        await ws_error("Usage: toolcheck [adv|dis] <tool_key> [dc N]", request_id=msg_request_id)
                        continue

                    tool_key = parts[idx].lower()
                    idx += 1
                    if not tool_key:
                        await ws_error("Usage: toolcheck [adv|dis] <tool_key> [dc N]", request_id=msg_request_id)
                        continue

                    dc: Optional[int] = None
                    if idx < len(parts):
                        tok = parts[idx].lower()
                        if tok.startswith("dc"):
                            if tok == "dc":
                                if idx + 1 >= len(parts):
                                    await ws_error("Usage: toolcheck ... dc <N>", request_id=msg_request_id)
                                    continue
                                dc = as_int(parts[idx + 1], -1)
                                idx += 2
                            else:
                                dc = as_int(tok[2:], -1)
                                idx += 1
                        else:
                            await ws_error("Usage: toolcheck [adv|dis] <tool_key> [dc N]", request_id=msg_request_id)
                            continue
                    if idx != len(parts):
                        await ws_error("Usage: toolcheck [adv|dis] <tool_key> [dc N]", request_id=msg_request_id)
                        continue
                    if dc is not None and dc < 0:
                        await ws_error("DC must be >= 0", request_id=msg_request_id)
                        continue

                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue

                    mapped_mode = {
                        "roll": "normal",
                        "adv": "advantage",
                        "dis": "disadvantage",
                    }.get(mode, "normal")
                    mod = 0
                    ra, rb, roll = roll_check(mapped_mode)
                    check_payload = {
                        "actor_uid": _player_uid(player),
                        "kind": "tool",
                        "name": tool_key,
                        "dc": dc if dc is not None else 0,
                        "mode": mapped_mode,
                    }
                    res = build_check_result(check_payload, mod=mod, roll_a=ra, roll_b=rb, roll=roll)
                    base_total = int(res["total"])
                    tp_bonus, tp_bonus_text = _tireless_precision_bonus_for_check(
                        getattr(ch, "race_features", None),
                        kind="tool",
                        key=tool_key,
                    )
                    total = base_total + tp_bonus
                    d20_text = str(roll) if rb is None else f"{ra}/{rb}->{roll}"

                    msg = f"[TOOL] {ch.name}: {tool_key} = d20({d20_text}) + {mod:+d} => {total}"
                    if tp_bonus > 0 and tp_bonus_text:
                        msg = f"[TOOL] {ch.name}: {tool_key} = d20({d20_text}) + {mod:+d} + {tp_bonus_text} => {total}"
                    if dc is not None:
                        ok = total >= dc
                        msg += f" (DC {dc}) {'SUCCESS' if ok else 'FAIL'}"
                    await add_system_event(db, sess, msg)
                    await broadcast_state(session_id)
                    continue

                if lower.startswith("save"):
                    parts = cmdline.split()
                    if len(parts) < 2:
                        await ws_error(
                            "Usage: save [adv|dis] <str|dex|con|int|wis|cha> [vs <tag>] [dc N]",
                            request_id=msg_request_id,
                        )
                        continue
                    is_magic_save = False
                    mode = "roll"
                    idx = 1
                    if idx < len(parts) and parts[idx].lower() == "magic":
                        is_magic_save = True
                        idx += 1
                    if idx < len(parts) and parts[idx].lower() in ("adv", "dis"):
                        mode = parts[idx].lower()
                        idx += 1
                    if idx >= len(parts):
                        await ws_error(
                            "Usage: save [adv|dis] <str|dex|con|int|wis|cha> [vs <tag>] [dc N]",
                            request_id=msg_request_id,
                        )
                        continue

                    vs_tag = ""
                    ability = ""
                    if idx < len(parts) and parts[idx].lower() == "vs":
                        if idx + 2 >= len(parts):
                            await ws_error(
                                "Usage: save [adv|dis] <ability> [vs <tag>] [dc N]",
                                request_id=msg_request_id,
                            )
                            continue
                        vs_tag = _normalize_save_tag(parts[idx + 1])
                        ability = parts[idx + 2].lower()
                        idx += 3
                    else:
                        ability = parts[idx].lower()
                        idx += 1
                        if idx < len(parts) and parts[idx].lower() == "vs":
                            if idx + 1 >= len(parts):
                                await ws_error(
                                    "Usage: save [adv|dis] <ability> [vs <tag>] [dc N]",
                                    request_id=msg_request_id,
                                )
                                continue
                            vs_tag = _normalize_save_tag(parts[idx + 1])
                            idx += 2

                    if ability not in CHAR_STAT_KEYS:
                        await ws_error("Unknown ability key", request_id=msg_request_id)
                        continue

                    dc: Optional[int] = None
                    if idx < len(parts):
                        tok = parts[idx].lower()
                        if tok.startswith("dc"):
                            if tok == "dc":
                                if idx + 1 >= len(parts):
                                    await ws_error("Usage: save ... dc <N>", request_id=msg_request_id)
                                    continue
                                dc = as_int(parts[idx + 1], -1)
                                idx += 2
                            else:
                                dc = as_int(tok[2:], -1)
                                idx += 1
                        else:
                            await ws_error(
                                "Usage: save [adv|dis] <ability> [vs <tag>] [dc N]",
                                request_id=msg_request_id,
                            )
                            continue
                    if idx != len(parts):
                        await ws_error(
                            "Usage: save [adv|dis] <ability> [vs <tag>] [dc N]",
                            request_id=msg_request_id,
                        )
                        continue
                    if dc is not None and dc < 0:
                        await ws_error("DC must be >= 0", request_id=msg_request_id)
                        continue

                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue

                    requested_mode = {
                        "roll": "normal",
                        "adv": "advantage",
                        "dis": "disadvantage",
                    }.get(mode, "normal")
                    mapped_mode = _effective_save_mode(
                        requested_mode,
                        getattr(ch, "race_features", None),
                        ability,
                        vs_magic=is_magic_save,
                        vs_tag=vs_tag,
                    )
                    mod = _ability_mod_from_stats(ch.stats, ability)

                    ra, rb, roll = roll_check(
                        mapped_mode,
                        reroll_ones=_lucky_scope_enabled(getattr(ch, "race_features", None), "save"),
                    )
                    check_payload = {
                        "actor_uid": _player_uid(player),
                        "kind": "save",
                        "name": ability,
                        "dc": dc if dc is not None else 0,
                        "mode": mapped_mode,
                    }
                    res = build_check_result(check_payload, mod=mod, roll_a=ra, roll_b=rb, roll=roll)
                    base_total = int(res["total"])
                    bfs_bonus, bfs_bonus_text, bfs_changed = _consume_built_for_success_for_d20(ch)
                    if bfs_changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    total = base_total + bfs_bonus
                    d20_text = str(roll) if rb is None else f"{ra}/{rb}->{roll}"

                    save_prefix = "save magic" if is_magic_save else "save"
                    vs_suffix = f" vs {vs_tag}" if vs_tag else ""
                    msg = f"[SAVE] {ch.name}: {save_prefix} {ability}{vs_suffix} = d20({d20_text}) + {mod:+d} => {total}"
                    if bfs_bonus > 0 and bfs_bonus_text:
                        msg = (
                            f"[SAVE] {ch.name}: {save_prefix} {ability}{vs_suffix} = "
                            f"d20({d20_text}) + {mod:+d} + {bfs_bonus_text} => {total}"
                        )
                    if dc is not None:
                        ok = total >= dc
                        msg += f" (DC {dc}) {'SUCCESS' if ok else 'FAIL'}"
                    await add_system_event(db, sess, msg)
                    await broadcast_state(session_id)
                    continue

                # name change (any time)
                m_name = re.match(r"^name\s+(.+)$", lower, re.IGNORECASE)
                if m_name:
                    new_name = cmdline.split(" ", 1)[1].strip()
                    if new_name:
                        player.display_name = new_name
                        await db.commit()
                        await add_system_event(db, sess, f"Игрок #{sp.join_order} сменил имя на: {new_name}")
                        await broadcast_state(session_id)
                    continue

                # leave/quit/exit (any time)
                if lower in ("leave", "quit", "exit"):
                    await _process_leave_and_broadcast()
                    await ws.close()
                    return

                # admin: kick <#>
                if lower.startswith("kick "):
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can kick")
                        continue
                    arg = cmdline.split(" ", 1)[1].strip().lstrip("#")
                    target_order = as_int(arg, 0)
                    if target_order <= 0:
                        await ws_error("Usage: kick 2 or kick #2")
                        continue

                    # find target
                    sps_all = await list_session_players(db, sess, active_only=False)
                    target_sp = next((x for x in sps_all if int(x.join_order or 0) == target_order), None)
                    if not target_sp:
                        await ws_error("de" "ps.Player not found")
                        continue
                    if target_sp.player_id == player.id:
                        await ws_error("You can't kick yourself")
                        continue

                    # mark kicked
                    kicked = _get_kicked(sess)
                    kicked.add(str(target_sp.player_id))
                    _set_kicked(sess, kicked)

                    target_sp.is_active = False
                    await db.commit()
                    _set_ready(sess, target_sp.player_id, False)
                    await db.commit()

                    await add_system_event(db, sess, f"Игрок #{target_order} исключён (kick).")
                    # if kicked player had the turn, advance
                    if sess.current_player_id == target_sp.player_id and not sess.is_paused:
                        nxt = await advance_turn(db, sess)
                        if nxt:
                            await add_system_event(db, sess, f"Ход передан следующему: #{nxt.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # admin: turn/goto <#>
                if lower.startswith("turn ") or lower.startswith("goto "):
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can change turn")
                        continue
                    arg = cmdline.split(" ", 1)[1].strip().lstrip("#")
                    target_order = as_int(arg, 0)
                    if target_order <= 0:
                        await ws_error("Usage: turn 2 or goto #2")
                        continue
                    target = await set_turn_to_order(db, sess, target_order)
                    if not target:
                        await ws_error("de" "ps.Player not found/active")
                        continue
                    await add_system_event(db, sess, f"Админ передал ход игроку #{target.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # initiative commands (admin)
                if lower.startswith("init"):
                    if not await is_admin(db, sess, player):
                        await ws_error("Only admin can manage initiative")
                        continue
                    parts = cmdline.split()
                    sub = parts[1].lower() if len(parts) > 1 else ""

                    sps_active = await list_session_players(db, sess, active_only=True)
                    init_map = _get_init_map(sess)
                    # prefetch display names to avoid awaits in formatter
                    pids_active = [spx.player_id for spx in sps_active]
                    names: dict[str, str] = {}
                    
                    # pids_active должен быть UUID (players.id). Всё прочее игнорируем, чтобы не сломать запрос.
                    uuid_ids: list[uuid.UUID] = []
                    for x in pids_active:
                        if isinstance(x, uuid.UUID):
                            uuid_ids.append(x)
                        else:
                            try:
                                uuid_ids.append(uuid.UUID(str(x)))
                            except Exception:
                                pass
                    uuid_ids = list(dict.fromkeys(uuid_ids))  # убираем дубли, сохраняя порядок

                    if uuid_ids:
                        qn = await db.execute(select(Player).where(Player.id.in_(uuid_ids)))
                        for p in qn.scalars().all():
                            names[str(p.id)] = p.display_name
                            if p.web_user_id is not None:
                                names[str(p.web_user_id)] = p.display_name
                    def _format_init(fixed: bool) -> str:
                        rows = []
                        header = ""
                        if fixed:
                            rnd = as_int(settings_get(sess, "round", 1), 1)
                            header = f"Раунд: {rnd}\n"
                        # order for display: if fixed, show initiative_order else by join_order
                        if fixed:
                            pids = _get_initiative_order(sess)
                            # keep only active
                            pids = [pid for pid in pids if pid in {spx.player_id for spx in sps_active}]
                            # append missing actives
                            for spx in sps_active:
                                if spx.player_id not in pids:
                                    pids.append(spx.player_id)
                            for pid in pids:
                                spx = next((x for x in sps_active if x.player_id == pid), None)
                                if not spx:
                                    continue
                                nm = names.get(str(pid), str(pid))
                                val = init_map.get(str(pid), 0)
                                cur = " ← ход" if sess.current_player_id == pid else ""
                                rows.append(f"  #{spx.join_order} {nm}: {val}{cur}")
                        else:
                            for spx in sps_active:
                                nm = names.get(str(spx.player_id), str(spx.player_id))
                                val = init_map.get(str(spx.player_id), 0)
                                cur = " ← ход" if sess.current_player_id == spx.player_id else ""
                                rows.append(f"  #{spx.join_order} {nm}: {val}{cur}")
                        return (header + "\n".join(rows)) if rows else (header + "  (нет игроков)")

                    if sub == "" or sub == "show":
                        fixed = _initiative_fixed(sess)
                        await add_system_event(
                            db,
                            sess,
                            f"Инициатива ({'зафиксирована' if fixed else 'не зафиксирована'}):\n{_format_init(fixed)}",
                        )
                        await broadcast_state(session_id)
                        continue

                    if sub == "roll":
                        chars_by_pid: dict[uuid.UUID, Character] = {}
                        if uuid_ids:
                            qc = await db.execute(
                                select(Character).where(
                                    Character.session_id == sess.id,
                                    Character.player_id.in_(uuid_ids),
                                )
                            )
                            chars_by_pid = {ch.player_id: ch for ch in qc.scalars().all()}
                        for spx in sps_active:
                            ch = chars_by_pid.get(spx.player_id)
                            dex = 50
                            stats = ch.stats if ch is not None else None
                            if isinstance(stats, dict):
                                dex_raw = stats.get("dex", 50)
                                if isinstance(dex_raw, int):
                                    dex = int(dex_raw)
                            val = roll_initiative(dex, rng=random)
                            _set_init_value(sess, spx.player_id, val)
                        await db.commit()
                        init_map = _get_init_map(sess)
                        lines = []
                        for spx in sps_active:
                            nm = names.get(str(spx.player_id), str(spx.player_id))
                            lines.append(f"  #{spx.join_order} {nm}: {init_map.get(str(spx.player_id), 0)}")
                        await add_system_event(
                            db,
                            sess,
                            "Инициатива: всем брошено 1d20 + мод ЛОВ:\n" + "\n".join(lines),
                        )
                        await broadcast_state(session_id)
                        continue

                    if sub == "set" and len(parts) >= 4:
                        target_order = as_int(parts[2].lstrip("#"), 0)
                        val = as_int(parts[3], 0)
                        target_sp = next((x for x in sps_active if int(x.join_order or 0) == target_order), None)
                        if not target_sp:
                            await ws_error("de" "ps.Player not found/active")
                            continue
                        _set_init_value(sess, target_sp.player_id, val)
                        await db.commit()
                        nm = names.get(str(target_sp.player_id), str(target_sp.player_id))
                        await add_system_event(db, sess, f"Инициатива: игрок #{target_order} ({nm}) = {val}.")
                        await broadcast_state(session_id)
                        continue

                    if sub == "start":
                        # fix order by initiative desc, then join_order asc
                        init_map = _get_init_map(sess)
                        scored = []
                        for spx in sps_active:
                            scored.append((init_map.get(str(spx.player_id), 0), int(spx.join_order or 0), spx.player_id))
                        scored.sort(key=lambda x: (-x[0], x[1]))
                        order = [pid for _, _, pid in scored]
                        _set_initiative_order(sess, order)
                        settings_set(sess, "initiative_fixed", True)
                        settings_set(sess, "round", 1)
                        await db.commit()

                        # move turn to first in initiative
                        first_pid = order[0] if order else None
                        if first_pid:
                            sess.is_active = True
                            sess.current_player_id = first_pid
                            sess.turn_started_at = utcnow()
                            sess.turn_index = (sess.turn_index or 0) + 1 if sess.turn_index else 1
                            _clear_paused_remaining(sess)
                            await db.commit()

                        # log
                        lines = []
                        for pid in order:
                            spx = next((x for x in sps_active if x.player_id == pid), None)
                            if not spx:
                                continue
                            nm = names.get(str(pid), str(pid))
                            lines.append(f"  #{spx.join_order} {nm}: {init_map.get(str(pid), 0)}")
                        await add_system_event(db, sess, "Инициатива зафиксирована. Порядок:\n" + "\n".join(lines))
                        if first_pid:
                            sp_first = next((x for x in sps_active if x.player_id == first_pid), None)
                            if sp_first:
                                await add_system_event(db, sess, f"Ход по инициативе: игрок #{sp_first.join_order}.")
                        await broadcast_state(session_id)
                        continue

                    if sub == "clear":
                        _clear_initiative(sess)
                        await db.commit()
                        await add_system_event(db, sess, "Инициатива сброшена.")
                        await broadcast_state(session_id)
                        continue

                    await ws_error("Unknown init command")
                    continue

                if combat_action == "use_built_for_success":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    arm_err, changed = _apply_built_for_success_arm(ch)
                    if arm_err:
                        await ws_error(arm_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    await add_system_event(
                        db,
                        sess,
                        f"{actor_name}: Готово: следующий бросок d20 получит +1d4.",
                    )
                    await broadcast_state(session_id)
                    continue

                if combat_action == "combat_fury_of_small":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    arm_err, changed = _apply_fury_of_small_arm(ch)
                    if arm_err:
                        await ws_error(arm_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                        if combat_active:
                            _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                            sync_pcs_from_chars(session_id, chars_by_uid)
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    await add_system_event(
                        db,
                        sess,
                        f"{actor_name}: Готово: Ярость малого сработает на следующем попадании.",
                    )
                    await broadcast_state(session_id)
                    continue

                if combat_action in {"combat_shapechanger_shift", "combat_shapechanger_revert"}:
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    is_shift = combat_action == "combat_shapechanger_shift"
                    persona = _extract_shapechanger_persona(text) if is_shift else ""
                    if combat_active:
                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        combat_patch, shape_err, changed = _apply_shapechanger_in_combat(
                            session_id,
                            player_key,
                            ch,
                            active=is_shift,
                            persona=persona,
                            voice="",
                        )
                        if shape_err:
                            await ws_error(shape_err, request_id=msg_request_id)
                            continue
                        if changed:
                            flag_modified(ch, "race_features")
                        await db.commit()
                        if combat_patch:
                            await broadcast_state(session_id, combat_log_ui_patch=combat_patch)
                        continue
                    msg, shape_err, changed = _apply_shapechanger(
                        ch,
                        active=is_shift,
                        persona=persona,
                        voice="",
                    )
                    if shape_err:
                        await ws_error(shape_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    await add_system_event(db, sess, f"{actor_name}: {msg or 'Меняет облик.'}")
                    await broadcast_state(session_id)
                    continue

                if combat_active:
                    innate_spell_key = _detect_innate_spell_key(text) if combat_action == "combat_innate_spell" else None
                    actor_label = await _event_actor_label(db, sess, player)
                    pid = str(player.id)
                    current_zone = _get_pc_positions(sess).get(pid, "стартовая локация")
                    new_zone_preview = current_zone
                    payload = {
                        "type": (
                            "combat_innate_spell"
                            if combat_action == "combat_innate_spell"
                            else (
                                "combat_stone_endurance"
                                if combat_action == "combat_stone_endurance"
                                else (
                                    "combat_healing_hands"
                                    if combat_action == "combat_healing_hands"
                                    else (
                                        "combat_aasimar_transform"
                                        if combat_action == "combat_aasimar_transform"
                                        else (
                                            "breathe_underwater"
                                            if combat_action == "breathe_underwater"
                                            else (
                                                "combat_breath_weapon"
                                                if combat_action == "combat_breath_weapon"
                                                else (
                                                    "combat_shapechanger"
                                                    if combat_action in {"combat_shapechanger_shift", "combat_shapechanger_revert"}
                                                    else "player_action"
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        ),
                        "actor_uid": _player_uid(player),
                        "actor_player_id": str(player.id),
                        "join_order": int(sp.join_order or 0),
                        "raw_text": text,
                        "mode": "free_turns" if _is_free_turns(sess) else "turns",
                        "phase": _get_phase(sess),
                        "zone_before": current_zone,
                        "zone_after": new_zone_preview,
                        "turn_index": int(sess.turn_index or 0),
                        "combat_chat_action": combat_action,
                        "spell_key": innate_spell_key,
                    }
                    await add_event(
                        db,
                        sess,
                        f"{actor_label}: {text}",
                        actor_player_id=player.id,
                        result_json=payload,
                    )
                    await db.commit()
                    await broadcast_state(session_id)

                    if combat_action == "rest_long":
                        await ws_error("Сейчас бой, отдых невозможен.")
                        continue

                    if combat_action:
                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        if combat_action == "combat_stone_endurance":
                            combat_patch, combat_err = handle_live_combat_reaction(
                                "combat_stone_endurance",
                                session_id,
                                player_key,
                            )
                            if combat_err:
                                await ws_error(combat_err)
                                continue
                            if combat_patch:
                                await broadcast_state(session_id, combat_log_ui_patch=combat_patch)
                            continue
                        if combat_action == "breathe_underwater":
                            ch = await get_character(db, sess.id, player.id)
                            if not ch:
                                await ws_error("Персонаж не найден.")
                                continue
                            _until_iso, until_hhmm, breathe_err, changed = _apply_breathe_underwater_usage(ch)
                            if breathe_err:
                                await ws_error(breathe_err)
                                continue
                            if changed:
                                flag_modified(ch, "race_features")
                                await db.commit()
                            _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                            sync_pcs_from_chars(session_id, chars_by_uid)
                            actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                            await add_system_event(
                                db,
                                sess,
                                f"{actor_name} может дышать под водой 1 час (до {until_hhmm}).",
                            )
                            await broadcast_state(session_id)
                            continue
                        turn_key: Optional[str] = None
                        if combat_state and combat_state.order and 0 <= combat_state.turn_index < len(combat_state.order):
                            turn_key = combat_state.order[combat_state.turn_index]
                        if not turn_key or turn_key != player_key:
                            current_name = current_turn_label(combat_state) if combat_state else "другой участник"
                            await add_system_event(db, sess, f"Сейчас ходит {current_name}. Дождись своего хода.")
                            await broadcast_state(session_id)
                            continue

                        if combat_action == "combat_innate_spell":
                            if not innate_spell_key:
                                await ws_error("Не понял, какое врождённое заклинание вы хотите наложить.")
                                continue
                            ch = await get_character(db, sess.id, player.id)
                            if not ch:
                                await ws_error("Персонаж не найден.")
                                continue
                            spell_display_name, innate_err, changed = _apply_innate_spell_usage(ch, innate_spell_key)
                            if innate_err:
                                await ws_error(innate_err)
                                continue
                            if changed:
                                flag_modified(ch, "race_features")
                                await db.commit()
                            caster_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                            combat_state_now = get_combat(session_id)
                            round_no = combat_state_now.round_no if combat_state_now is not None else 1
                            turn_label_now = current_turn_label(combat_state_now) if combat_state_now is not None else "-"
                            patch = {
                                "status": f"⚔ Бой • Раунд {round_no} • Ход: {turn_label_now}",
                                "open": True,
                                "lines": [
                                    {"text": f"{caster_name} использует врождённую магию: {spell_display_name}."},
                                ],
                            }
                            await broadcast_state(session_id, combat_log_ui_patch=patch)
                            continue

                        if combat_action == "combat_healing_hands":
                            ch = await get_character(db, sess.id, player.id)
                            if not ch:
                                await ws_error("Персонаж не найден.")
                                continue
                            combat_patch, healing_err, changed = _apply_healing_hands_in_combat(session_id, player_key, ch)
                            if healing_err:
                                await ws_error(healing_err)
                                continue
                            if changed:
                                flag_modified(ch, "race_features")
                            await db.commit()
                            if combat_patch:
                                await broadcast_state(session_id, combat_log_ui_patch=combat_patch)
                            continue

                        if combat_action == "combat_aasimar_transform":
                            ch = await get_character(db, sess.id, player.id)
                            if not ch:
                                await ws_error("Персонаж не найден.")
                                continue
                            combat_patch, transform_err, changed = _apply_aasimar_transformation_in_combat(session_id, player_key, ch)
                            if transform_err:
                                await ws_error(transform_err)
                                continue
                            if changed:
                                flag_modified(ch, "race_features")
                            await db.commit()
                            _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                            sync_pcs_from_chars(session_id, chars_by_uid)
                            if combat_patch:
                                await broadcast_state(session_id, combat_log_ui_patch=combat_patch)
                            continue

                        all_patches: list[dict[str, Any]] = []
                        outcome_summary: list[str] = []
                        move_distance_ft: Optional[int] = None
                        if combat_action == "combat_move":
                            m_dist = COMBAT_MOVE_DISTANCE_RE.search(cmdline)
                            move_distance_ft = as_int(m_dist.group(1), 0) if m_dist else 0
                        combat_patch, combat_err = handle_live_combat_action(
                            combat_action,
                            session_id,
                            distance_ft=move_distance_ft,
                        )
                        if combat_err:
                            await ws_error(combat_err)
                            continue
                        if combat_patch:
                            all_patches.append(combat_patch)
                            outcome_summary.extend(_combat_outcome_summary_from_patch(combat_action, combat_patch))

                        while True:
                            state_now = get_combat(session_id)
                            if not state_now or not state_now.active or not state_now.order:
                                break
                            if state_now.turn_index < 0 or state_now.turn_index >= len(state_now.order):
                                break
                            turn_key_now = state_now.order[state_now.turn_index]
                            turn_actor = state_now.combatants.get(turn_key_now)
                            if not turn_actor or turn_actor.side != "enemy":
                                break
                            enemy_patch, enemy_err = handle_live_combat_action("combat_attack", session_id)
                            if enemy_err:
                                logger.warning("enemy auto combat action failed", extra={"action": {"error": enemy_err}})
                                break
                            if enemy_patch:
                                all_patches.append(enemy_patch)
                                outcome_summary.extend(_combat_outcome_summary_from_patch("combat_attack", enemy_patch))

                        state_after_actions = get_combat(session_id)
                        if state_after_actions is None:
                            # Keep combat_live_bootstrap in settings until explicit reset
                            # (admin_combat_live_end or a dedicated reset command).
                            pass

                        merged_patch = _merge_combat_patches(all_patches) if all_patches else None
                        persist_changed = await _persist_relentless_endurance_used_from_combat_state(db, sess, session_id)
                        if persist_changed:
                            await db.commit()
                        await broadcast_state(session_id, combat_log_ui_patch=merged_patch)
                        state_for_prompt = state_after_actions
                        story = settings_get(sess, "story", {}) or {}
                        if not isinstance(story, dict):
                            story = {}
                        campaign_title = str(story.get("story_title") or "").strip() or str(sess.title or "Campaign").strip() or "Campaign"
                        turn_label = current_turn_label(state_for_prompt) if state_for_prompt else "-"
                        participants_block = _combat_participants_block(state_for_prompt)
                        ch = await get_character(db, sess.id, player.id)
                        meta = _character_meta_from_stats(ch.stats) if ch else {"gender": "", "race": "", "description": ""}
                        actor_gender = meta["gender"]
                        actor_pronouns = _gender_to_pronouns(actor_gender) or "unknown"
                        actor_name = str(ch.name).strip() if ch and str(ch.name or "").strip() else actor_label
                        gm_text = await _generate_combat_narration(
                            campaign_title=campaign_title,
                            outcome_summary=outcome_summary,
                            player_action=combat_action,
                            current_turn=turn_label,
                            participants_block=participants_block,
                            actor_name=actor_name,
                            actor_gender=actor_gender,
                            actor_pronouns=actor_pronouns,
                        )
                        await add_system_event(
                            db,
                            sess,
                            f"🧙 GM: {gm_text}",
                            result_json={
                                "type": "combat_chat_gm_reply",
                                "combat_action": combat_action,
                                "combat_summary": outcome_summary,
                            },
                        )
                        await broadcast_state(session_id)
                        continue

                    player_uid = _player_uid(player)
                    player_key = f"pc_{player_uid}" if player_uid is not None else ""
                    state_now = get_combat(session_id)
                    turn_key_now = ""
                    if state_now and state_now.order and 0 <= state_now.turn_index < len(state_now.order):
                        turn_key_now = state_now.order[state_now.turn_index]
                    if not turn_key_now or turn_key_now != player_key:
                        current_name = current_turn_label(state_now) if state_now else "другой участник"
                        await add_system_event(db, sess, f"Сейчас ходит {current_name}. Дождись своего хода.")
                        await broadcast_state(session_id)
                        continue

                    already_sent = await _combat_clarify_already_sent(db, sess, msg_request_id)
                    settings = sess.settings if isinstance(sess.settings, dict) else {}
                    if not isinstance(sess.settings, dict):
                        sess.settings = settings
                    marker_player_key = player_key or f"player_{player.id}"
                    marker = f"{turn_key_now}:{marker_player_key}"
                    previous_marker = str(settings.get("combat_clarify_marker") or "")
                    if marker != previous_marker and not already_sent:
                        settings["combat_clarify_marker"] = marker
                        flag_modified(sess, "settings")
                        await db.commit()
                        await add_system_event(
                            db,
                            sess,
                            COMBAT_CLARIFY_TEXT,
                            result_json={
                                "type": "combat_chat_gm_reply",
                                "combat_action": None,
                                "combat_summary": ["Схватка продолжается в текущем темпе."],
                                "request_id": str(msg_request_id or ""),
                            },
                        )
                        await broadcast_state(session_id)
                    continue

                if combat_action == "combat_healing_hands":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...")
                        continue
                    healed_hp, healing_err, changed = _apply_healing_hands_usage(ch)
                    if healing_err:
                        await ws_error(healing_err)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                    await db.commit()
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    await add_system_event(
                        db,
                        sess,
                        f"{actor_name} исцеляет себя прикосновением: +{max(0, int(healed_hp or 0))} HP (Исцеляющие руки).",
                    )
                    await broadcast_state(session_id)
                    continue

                if combat_action == "combat_breath_weapon":
                    await ws_error("Оружие дыхания можно применить только в бою.")
                    continue

                if combat_action == "breathe_underwater":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...")
                        continue
                    _until_iso, until_hhmm, breathe_err, changed = _apply_breathe_underwater_usage(ch)
                    if breathe_err:
                        await ws_error(breathe_err)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                    await db.commit()
                    combat_now = get_combat(session_id)
                    if combat_now is not None and combat_now.active:
                        _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                        sync_pcs_from_chars(session_id, chars_by_uid)
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    await add_system_event(
                        db,
                        sess,
                        f"{actor_name} может дышать под водой 1 час (до {until_hhmm}).",
                    )
                    await broadcast_state(session_id)
                    continue

                if combat_action == "combat_aasimar_transform":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...")
                        continue
                    transform_runtime, transform_err, changed = _apply_aasimar_transformation_usage(ch)
                    if transform_err:
                        await ws_error(transform_err)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                    await db.commit()
                    combat_now = get_combat(session_id)
                    if combat_now is not None and combat_now.active:
                        _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                        sync_pcs_from_chars(session_id, chars_by_uid)
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    kind = str((transform_runtime or {}).get("kind") or "").strip().lower()
                    kind_ru = {"protector": "Защитник", "scourge": "Карающий", "fallen": "Падший"}.get(kind, kind or "—")
                    await add_system_event(
                        db,
                        sess,
                        f"{actor_name} активирует Небесное преобразование ({kind_ru}) на 10 ходов.",
                    )
                    await broadcast_state(session_id)
                    continue

                # DICE (must be started, not paused, your turn) — does NOT end turn
                dice = parse_dice(cmdline)
                if dice:
                    if not sess.current_player_id:
                        await ws_error("Game not started. Press Start.")
                        continue
                    if sess.is_paused:
                        await ws_error("Paused.")
                        continue
                    if player.id != sess.current_player_id:
                        await ws_error("Not your turn.")
                        continue

                    mode, n, sides, mod, expr = dice
                    if mode == "roll":
                        rolls = roll_dice(n, sides)
                        total = sum(rolls) + mod
                        detail = ",".join(str(x) for x in rolls)
                        await add_system_event(db, sess, f"🎲 Игрок #{sp.join_order}: {expr} → {n}d{sides}({detail}){('+'+str(mod)) if mod>0 else (str(mod) if mod<0 else '')} = {total}")
                        await add_system_event(db, sess, "(ход не закончен)")
                        await broadcast_state(session_id)
                        continue

                    # adv/dis only meaningful for 1d20-ish but we allow any NdS as whole formula twice
                    rolls_a = roll_dice(n, sides)
                    rolls_b = roll_dice(n, sides)
                    tot_a = sum(rolls_a) + mod
                    tot_b = sum(rolls_b) + mod
                    chosen = max(tot_a, tot_b) if mode == "adv" else min(tot_a, tot_b)
                    da = ",".join(str(x) for x in rolls_a)
                    dbb = ",".join(str(x) for x in rolls_b)
                    tag = "adv" if mode == "adv" else "dis"
                    pick = "большее" if mode == "adv" else "меньшее"
                    await add_system_event(
                        db,
                        sess,
                        f"🎲 Игрок #{sp.join_order} ({tag}): {expr} → A: {n}d{sides}({da}){('+'+str(mod)) if mod>0 else (str(mod) if mod<0 else '')} = {tot_a}; "
                        f"B: {n}d{sides}({dbb}){('+'+str(mod)) if mod>0 else (str(mod) if mod<0 else '')} = {tot_b}; ✅ берём {pick} = {chosen}"
                    )
                    await add_system_event(db, sess, "(ход не закончен)")
                    await broadcast_state(session_id)
                    continue

                # PASS/END — ends turn
                if lower in ("pass", "end"):
                    if not sess.current_player_id:
                        await ws_error("Game not started. Press Start.")
                        continue
                    if sess.is_paused:
                        await ws_error("Paused.")
                        continue
                    if player.id != sess.current_player_id:
                        await ws_error("Not your turn.")
                        continue
                    nxt = await advance_turn(db, sess)
                    if not nxt:
                        await ws_error("No players")
                        continue
                    await add_system_event(db, sess, f"Игрок #{sp.join_order} пропустил ход. Следующий: #{nxt.join_order}.")
                    await broadcast_state(session_id)
                    continue

                # Normal SAY — ends turn
                if _is_free_turns(sess):
                    phase = _get_phase(sess)
                    if phase == "lore_pending":
                        if _kickoff_lore_finalize_if_needed(session_id, sess):
                            await ws_error("Публикую вступительную историю...")
                        else:
                            await ws_error("Ждём вступительную историю...")
                        continue
                    if phase == "gm_pending":
                        await ws_error("Ждём ответа мастера...")
                        continue
                    if phase != "collecting_actions":
                        await ws_error("Сейчас нельзя отправлять действие.")
                        continue

                    sps_active = await list_session_players(db, sess, active_only=True)
                    active_ids = {spx.player_id for spx in sps_active}
                    if player.id not in active_ids:
                        await ws_error("You are offline in this session", request_id=msg_request_id)
                        continue
                    ready_sps = _ready_active_players(sess, sps_active)
                    ready_ids = {spx.player_id for spx in ready_sps}
                    if player.id not in ready_ids:
                        await ws_error("В этом раунде действие принимается только от READY игроков.")
                        continue

                    round_actions = _get_round_actions(sess)
                    pid = str(player.id)
                    if pid in round_actions:
                        await ws_error("В этом раунде вы уже отправили действие.")
                        continue

                    build_player_gm_action_text = _resolve_build_player_gm_action_text()
                    gm_action_text, _moved, _encounter_patch = await build_player_gm_action_text(
                        db,
                        sess,
                        session_id,
                        text,
                        include_encounter_after_move=False,
                    )
                    round_actions[pid] = gm_action_text
                    settings_set(sess, "round_actions", round_actions)
                    current_zone = _get_pc_positions(sess).get(pid, "стартовая локация")
                    new_zone = infer_zone_from_action(text, current_zone)
                    _set_pc_zone(sess, player.id, new_zone)
                    actor_label = await _event_actor_label(db, sess, player)
                    payload = {
                        "type": "player_action",
                        "actor_uid": _player_uid(player),
                        "actor_player_id": str(player.id),
                        "join_order": int(sp.join_order or 0),
                        "raw_text": gm_action_text,
                        "mode": "free_turns",
                        "phase": phase,
                        "zone_before": current_zone,
                        "zone_after": new_zone,
                        "turn_index": int(sess.turn_index or 0),
                        "combat_chat_action": combat_action,
                    }
                    await add_event(
                        db,
                        sess,
                        f"{actor_label}: {text}",
                        actor_player_id=player.id,
                        result_json=payload,
                    )
                    await db.commit()

                    all_collected = bool(ready_sps) and all(str(spx.player_id) in round_actions for spx in ready_sps)
                    if all_collected:
                        action_id = _new_action_id()
                        _set_current_action_id(sess, action_id)
                        _set_phase(sess, "gm_pending")
                        await db.commit()
                        await add_system_event(db, sess, "Мастер обрабатывает действия...")
                        await broadcast_state(session_id)
                        asyncio.create_task(gm_orchestrator.run_round_gm(session_id, action_id))
                    else:
                        await broadcast_state(session_id)
                    continue

                if not sess.current_player_id:
                    await ws_error("Game not started. Press Start.")
                    continue
                if sess.is_paused:
                    await ws_error("Paused.")
                    continue
                if player.id != sess.current_player_id:
                    await ws_error("Not your turn.")
                    continue

                actor_label = await _event_actor_label(db, sess, player)
                pid = str(player.id)
                phase = _get_phase(sess)
                current_zone = _get_pc_positions(sess).get(pid, "стартовая локация")
                new_zone = infer_zone_from_action(text, current_zone)
                _set_pc_zone(sess, player.id, new_zone)
                build_player_gm_action_text = _resolve_build_player_gm_action_text()
                gm_action_text, _moved, encounter_patch = await build_player_gm_action_text(
                    db,
                    sess,
                    session_id,
                    text,
                    include_encounter_after_move=True,
                )
                payload = {
                    "type": "player_action",
                    "actor_uid": _player_uid(player),
                    "actor_player_id": str(player.id),
                    "join_order": int(sp.join_order or 0),
                    "raw_text": gm_action_text,
                    "mode": "free_turns" if _is_free_turns(sess) else "turns",
                    "phase": phase,
                    "zone_before": current_zone,
                    "zone_after": new_zone,
                    "turn_index": int(sess.turn_index or 0),
                    "combat_chat_action": combat_action,
                }
                await add_event(
                    db,
                    sess,
                    f"{actor_label}: {text}",
                    actor_player_id=player.id,
                    result_json=payload,
                )
                action_id = _new_action_id()
                _set_current_action_id(sess, action_id)
                _set_phase(sess, "gm_pending")
                sess.turn_started_at = None
                await db.commit()
                await add_system_event(db, sess, "Мастер обрабатывает действие...")
                await broadcast_state(session_id, combat_log_ui_patch=encounter_patch)
                asyncio.create_task(gm_orchestrator.run_turn_gm(session_id, action_id))
                continue

    except WebSocketDisconnect:
        manager.disconnect(session_id, ws)
    except Exception:
        manager.disconnect(session_id, ws)
        raise
