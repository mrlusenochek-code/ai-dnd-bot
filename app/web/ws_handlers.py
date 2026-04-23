import asyncio
import importlib
import json
import logging
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

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
    _apply_map_position_transition,
    _default_map_position,
    _get_player_group_id,
    _get_ready_map,
    _get_group_states,
    _set_ready,
    _get_init_map,
    _get_player_map_position,
    _get_player_position_context,
    _map_position_area_label,
    apply_group_route,
    apply_group_move_target,
    apply_group_merge,
    apply_group_split,
    clear_group_movement_intent,
    clear_group_travel_activity,
    complete_group_travel,
    confirm_group_enter,
    evaluate_group_travel_pause,
    execute_current_group_context_action,
    execute_current_group_service,
    execute_group_navigation_option,
    get_current_group_map_intel,
    get_current_group_recent_map_intel,
    get_current_group_last_node_entry_result,
    get_current_group_current_node_entry_state,
    get_current_group_last_destination_event_result,
    get_current_group_current_node_destination_event_state,
    get_current_group_journey_state,
    get_current_group_last_journey_result,
    get_current_group_region_pursuit,
    get_current_group_last_region_pursuit_result,
    get_current_group_multi_region_pursuit,
    get_current_group_last_multi_region_pursuit_result,
    get_current_group_last_region_pursuit_step_result,
    get_current_group_route_planning,
    get_group_route_plan_to_node,
    get_current_group_exploration_leads,
    get_current_group_primary_exploration_lead,
    get_current_group_local_interaction_surface,
    get_current_group_node_detail,
    get_current_group_node_services,
    get_current_group_last_inspect_result,
    get_current_group_current_node_progress,
    get_current_group_region_exploration_summary,
    get_current_group_region_frontier_summary,
    get_current_group_region_gateways,
    get_current_group_primary_region_gateway,
    get_current_group_current_region_state,
    get_current_group_discovered_regions,
    get_current_group_discovered_region_summaries,
    get_current_group_last_region_entry_result,
    get_current_group_last_region_onboarding_result,
    get_current_group_primary_region_focus,
    get_current_group_primary_region_focus_plan,
    get_current_group_primary_region_route,
    get_current_group_last_region_transition_result,
    get_current_group_region_onboarding_states,
    get_current_group_region_target_plan,
    get_current_group_region_target_options,
    get_current_group_region_world_overview,
    get_current_group_region_transition_state,
    get_current_group_gateway_traversal_states,
    get_current_group_region_link_states,
    get_current_group_last_region_link_result,
    get_current_group_known_region_route,
    get_current_group_known_region_route_options,
    set_group_multi_region_pursuit,
    set_group_region_pursuit,
    clear_group_region_pursuit,
    advance_group_region_pursuit,
    resolve_group_region_transition,
    set_group_journey_target,
    advance_group_journey,
    clear_group_journey,
    get_current_group_node_visit_states,
    get_current_group_route_traversal_states,
    get_player_known_node_ids,
    get_current_group_travel_event,
    get_group_movement_mode,
    get_group_travel_activity,
    inspect_group_travel_target,
    interrupt_group_travel,
    maybe_apply_group_enter_target,
    bypass_group_travel_pause,
    pause_group_travel,
    request_group_merge,
    request_group_split,
    resolve_group_camp,
    resolve_group_scout,
    resolve_group_travel_event,
    resolve_group_travel_pause,
    resume_group_travel,
    start_group_travel,
    set_group_movement_intent,
    set_group_movement_mode,
    set_group_travel_activity,
    set_group_camp,
    set_group_wait,
    validate_group_route_accessibility,
    _touch_last_seen,
    _get_phase,
    _set_phase,
    _set_init_value,
    _set_player_map_position,
    _initiative_fixed,
)
from app.web.session_lock import get_session_lock
from app.web.state_builder import broadcast_state, _broadcast_state_unlocked, send_state_to_ws, _maybe_restore_combat_state
from app.web.map_targeting import resolve_action_target_node, resolve_group_target_route, validate_group_target_transition
from app.web.map_registry import resolve_static_map_node
from app.web.combat_bridge import (
    _append_combat_patch_lines,
    _build_combat_start_preamble_lines,
    _build_combat_narration_inputs,
    _combat_outcome_summary_from_patch,
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
    _has_start_intent_sanitary_markers,
    _looks_like_combat_drift,
    _sanitize_gm_output,
    _start_intent_text_needs_repair,
)
from app.web.ws_gameplay import STATE_COMMAND_ALIASES, _detect_chat_combat_action, _format_state_text_for_player, infer_zone_from_action
from app.web.regexes import (
    COMBAT_MOVE_DISTANCE_RE,
    INNATE_SPELL_KEY_PATTERNS,
    MIND_LINK_REPLY_CAPTURE_RE,
    MIND_LINK_SAY_CAPTURE_RE,
    MIND_LINK_SET_CAPTURE_RE,
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

TOOL_LABELS_RU: dict[str, str] = {
    "thieves_tools": "Воровские инструменты",
    "smith_tools": "Инструменты кузнеца",
    "mason_tools": "Инструменты каменщика",
    "brewer_supplies": "Принадлежности пивовара",
    "tinkers_tools": "Инструменты жестянщика",
    "herbalism_kit": "Набор травника",
    "disguise_kit": "Набор для грима",
    "forgery_kit": "Набор фальсификатора",
    "navigator_tools": "Инструменты навигатора",
    "alchemists_supplies": "Принадлежности алхимика",
    "calligraphers_supplies": "Принадлежности каллиграфа",
    "carpenters_tools": "Инструменты плотника",
    "cartographers_tools": "Инструменты картографа",
    "cobblers_tools": "Инструменты сапожника",
    "cooks_utensils": "Кухонная утварь",
    "glassblowers_tools": "Инструменты стеклодува",
    "jewelers_tools": "Инструменты ювелира",
    "leatherworkers_tools": "Инструменты кожевника",
    "painters_supplies": "Принадлежности художника",
    "potters_tools": "Инструменты гончара",
    "weavers_tools": "Инструменты ткача",
    "woodcarvers_tools": "Инструменты резчика по дереву",
    "bagpipes": "Волынка",
    "drum": "Барабан",
    "dulcimer": "Цимбалы",
    "flute": "Флейта",
    "horn": "Рожок",
    "lute": "Лютня",
    "lyre": "Лира",
    "pan_flute": "Свирель Пана",
    "shawm": "Шалмей",
    "viol": "Виола",
}


def _build_player_action_position_payload(
    sess: Any,
    player_id: uuid.UUID | str,
    *,
    zone_after: str | None = None,
    map_position_after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    position_context = _get_player_position_context(sess, player_id)
    zone_before = str(position_context.get("zone_label") or "стартовая локация")
    position_before = position_context.get("map_position")
    return {
        "zone_before": zone_before,
        "zone_after": str(zone_after or zone_before),
        "map_position_before": dict(position_before) if isinstance(position_before, dict) else None,
        "map_position_after": dict(map_position_after) if isinstance(map_position_after, dict) else None,
    }


def _infer_action_position_update(
    current_map_position: dict[str, Any] | None,
    current_zone_label: str,
    text: str,
) -> tuple[str, dict[str, Any]]:
    zone_before = str(current_zone_label or "стартовая локация").strip() or "стартовая локация"
    next_zone_label = infer_zone_from_action(text, zone_before)
    target_node = resolve_action_target_node(
        action_text=text,
        current_map_position=current_map_position,
        current_area_label=zone_before,
        action_kind="enter" if any(token in str(text or "").lower() for token in ("захожу", "вхожу", "войти", "внутрь", "внутри")) else "move",
    )
    next_map_position, resolved_zone_label, ok, _error = _apply_map_position_transition(
        current_map_position,
        target_node,
        "player_action",
    )
    if ok and next_map_position:
        return resolved_zone_label, next_map_position
    return next_zone_label, _default_map_position(next_zone_label)


def _infer_action_target_node(
    text: str,
    inferred_zone_label: str,
    current_map_position: dict[str, Any] | None = None,
    current_zone_label: str = "стартовая локация",
) -> dict[str, Any]:
    resolved = resolve_action_target_node(
        action_text=text,
        current_map_position=current_map_position,
        current_area_label=current_zone_label,
        action_kind="enter" if any(token in str(text or "").lower() for token in ("захожу", "вхожу", "войти", "внутрь", "внутри")) else "move",
    )
    return dict(resolved or {})


def _apply_player_action_position_update(
    sess: Any,
    player_id: uuid.UUID,
    text: str,
) -> dict[str, Any]:
    position_context = _get_player_position_context(sess, player_id)
    current_zone_label = str(position_context.get("zone_label") or "стартовая локация")
    current_map_position = position_context.get("map_position")
    next_zone_label, next_map_position = _infer_action_position_update(
        current_map_position if isinstance(current_map_position, dict) else None,
        current_zone_label,
        text,
    )
    _set_player_map_position(sess, player_id, next_map_position)
    return {
        "zone_before": current_zone_label,
        "zone_after": next_zone_label,
        "map_position_before": dict(current_map_position) if isinstance(current_map_position, dict) else None,
        "map_position_after": _get_player_map_position(sess, player_id),
    }
VALID_TOOL_KEYS = set(TOOL_LABELS_RU)
TINKER_DEVICE_LABELS_RU: dict[str, str] = {
    "clockwork_toy": "Заводная игрушка",
    "fire_starter": "Зажигалка",
    "music_box": "Музыкальная шкатулка",
}


def _resolve_build_player_gm_action_text():
    # Lazy import to avoid server_impl <-> ws_handlers import cycle
    server_mod = importlib.import_module("app.web" ".server")
    return getattr(server_mod, "_build_player_gm_action_text")


def _new_request_id() -> str:
    return uuid.uuid4().hex


_LORE_PENDING_TASKS: set[str] = set()


def _lore_needs_finalize(sess: Any) -> bool:
    lore_text = str(settings_get(sess, "lore_text", "") or "").strip()
    lore_generated = bool(settings_get(sess, "lore_generated", False))
    lore_posted = bool(settings_get(sess, "lore_posted", False))
    return bool(lore_text) and lore_generated and not lore_posted


def _lore_needs_restart(sess: Any) -> bool:
    if _get_phase(sess) != "lore_pending":
        return False
    story = settings_get(sess, "story", {}) or {}
    if not (isinstance(story, dict) and story.get("story_configured") is True):
        return False
    lore_text = str(settings_get(sess, "lore_text", "") or "").strip()
    lore_generated = bool(settings_get(sess, "lore_generated", False))
    lore_posted = bool(settings_get(sess, "lore_posted", False))
    return not lore_text and not lore_generated and not lore_posted


async def _run_lore_generation_task(session_id: str) -> None:
    try:
        await gm_orchestrator.run_lore_generation(session_id)
    finally:
        _LORE_PENDING_TASKS.discard(session_id)


def _kickoff_lore_finalize_if_needed(session_id: str, sess: Any) -> bool:
    if session_id in _LORE_PENDING_TASKS:
        return False
    if not (_lore_needs_finalize(sess) or _lore_needs_restart(sess)):
        return False
    _LORE_PENDING_TASKS.add(session_id)
    asyncio.create_task(_run_lore_generation_task(session_id))
    return True


async def _auto_recover_lore_pending_on_connect(session_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess or _get_phase(sess) != "lore_pending":
            return False
        return _kickoff_lore_finalize_if_needed(session_id, sess)


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
        "disease": "disease",
        "болезнь": "disease",
        "болезни": "disease",
        "diseased": "disease",
        "frightened": "frightened",
        "испуг": "frightened",
        "испуган": "frightened",
        "испуганный": "frightened",
        "fear": "frightened",
        "charmed": "charmed",
        "очарование": "charmed",
        "очарован": "charmed",
        "stunned": "stunned",
        "оглушение": "stunned",
        "ошеломление": "stunned",
        "ошеломлен": "stunned",
        "paralyzed": "paralyzed",
        "паралич": "paralyzed",
        "парализован": "paralyzed",
        "sleep": "sleep",
        "сон": "sleep",
        "усыпление": "sleep",
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

    runtime_raw = race_features.get("runtime")
    runtime = runtime_raw if isinstance(runtime_raw, dict) else {}
    if bool(runtime.get("shell_defense_active")):
        if ability_key in {"str", "con"}:
            return "advantage"
        if ability_key == "dex":
            return "disadvantage"

    saves_raw = race_features.get("saves")
    saves = saves_raw if isinstance(saves_raw, dict) else {}
    adv_raw = saves.get("advantage")
    advantages = adv_raw if isinstance(adv_raw, list) else []
    for item in advantages:
        adv_key = str(item or "").strip().lower()
        if adv_key == ability_key:
            return "advantage"
    features_raw = race_features.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    if vs_magic:
        if isinstance(features.get("magic_resistance"), dict):
            return "advantage"
        adv_magic_raw = saves.get("advantage_vs_magic")
        advantages_vs_magic = adv_magic_raw if isinstance(adv_magic_raw, list) else []
        for item in advantages_vs_magic:
            adv_key = str(item or "").strip().lower()
            if adv_key == ability_key:
                return "advantage"
    tag = _normalize_save_tag(vs_tag)
    deathless_nature = features.get("deathless_nature")
    if isinstance(deathless_nature, dict) and tag:
        adv_tags_raw = deathless_nature.get("advantage_on_saves")
        adv_tags = adv_tags_raw if isinstance(adv_tags_raw, list) else []
        normalized_tags = {_normalize_save_tag(str(item or "")) for item in adv_tags}
        normalized_tags.discard("")
        if tag in normalized_tags or (tag == "poison" and "poisoned" in normalized_tags):
            return "advantage"
    if tag:
        adv_conditions_raw = saves.get("advantage_conditions")
        adv_conditions = adv_conditions_raw if isinstance(adv_conditions_raw, list) else []
        for item in adv_conditions:
            cond_key = _normalize_save_tag(str(item or ""))
            if cond_key == tag:
                return "advantage"
    return mode


def _auto_save_advantage_reason(
    race_features: Any,
    ability: str,
    *,
    vs_magic: bool = False,
    vs_tag: str = "",
) -> str:
    ability_key = str(ability or "").strip().lower()
    if ability_key not in CHAR_STAT_KEYS or not isinstance(race_features, dict):
        return ""

    runtime_raw = race_features.get("runtime")
    runtime = runtime_raw if isinstance(runtime_raw, dict) else {}
    if bool(runtime.get("shell_defense_active")) and ability_key in {"str", "con"}:
        return "Защита панцирем"

    features_raw = race_features.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    dispassion = features.get("vedalken_dispassion")
    if isinstance(dispassion, dict):
        abilities_raw = dispassion.get("abilities")
        abilities = abilities_raw if isinstance(abilities_raw, list) else []
        normalized = [str(item or "").strip().lower() for item in abilities]
        if ability_key in normalized:
            return "Vedalken Dispassion"
    dual_mind = features.get("dual_mind")
    if isinstance(dual_mind, dict):
        abilities_raw = dual_mind.get("abilities")
        abilities = abilities_raw if isinstance(abilities_raw, list) else []
        normalized = [str(item or "").strip().lower() for item in abilities]
        if ability_key in normalized:
            return "Kalashtar Dual Mind"
    brave = features.get("brave")
    if isinstance(brave, dict) and _normalize_save_tag(vs_tag) == "frightened":
        return "Brave"
    serenity = features.get("serenity")
    if isinstance(serenity, dict) and _normalize_save_tag(vs_tag) in {"charmed", "frightened"}:
        conditions_raw = serenity.get("conditions")
        conditions = conditions_raw if isinstance(conditions_raw, list) else []
        normalized = [_normalize_save_tag(str(item or "")) for item in conditions]
        if _normalize_save_tag(vs_tag) in normalized:
            return "Loxodon Serenity"
    leviathan_will = features.get("leviathan_will")
    if isinstance(leviathan_will, dict):
        conditions_raw = leviathan_will.get("conditions")
        conditions = conditions_raw if isinstance(conditions_raw, list) else []
        normalized = {_normalize_save_tag(str(item or "")) for item in conditions}
        normalized.discard("")
        tag = _normalize_save_tag(vs_tag)
        if tag and (tag in normalized or (tag == "poison" and "poisoned" in normalized)):
            return "Leviathan Will"
    dwarven_resilience = features.get("dwarven_resilience")
    if isinstance(dwarven_resilience, dict) and _normalize_save_tag(vs_tag) in {"poison", "poisoned"}:
        return "Dwarven Resilience"
    deathless_nature = features.get("deathless_nature")
    if isinstance(deathless_nature, dict):
        adv_tags_raw = deathless_nature.get("advantage_on_saves")
        adv_tags = adv_tags_raw if isinstance(adv_tags_raw, list) else []
        normalized_tags = {_normalize_save_tag(str(item or "")) for item in adv_tags}
        normalized_tags.discard("")
        tag = _normalize_save_tag(vs_tag)
        if tag and (tag in normalized_tags or (tag == "poison" and "poisoned" in normalized_tags)):
            return "Deathless Nature"
    fey_ancestry = features.get("fey_ancestry")
    if isinstance(fey_ancestry, dict) and _normalize_save_tag(vs_tag) == "charmed":
        return "Fey Ancestry"

    saves_raw = race_features.get("saves")
    saves = saves_raw if isinstance(saves_raw, dict) else {}
    if vs_magic:
        if isinstance(features.get("magic_resistance"), dict):
            return "Magic Resistance"
        gnome_cunning = features.get("gnome_cunning")
        if isinstance(gnome_cunning, dict):
            abilities_raw = gnome_cunning.get("abilities")
            abilities = abilities_raw if isinstance(abilities_raw, list) else []
            normalized = [str(item or "").strip().lower() for item in abilities]
            if ability_key in normalized:
                return "Gnome Cunning"
        adv_magic_raw = saves.get("advantage_vs_magic")
        advantages_vs_magic = adv_magic_raw if isinstance(adv_magic_raw, list) else []
        if ability_key in [str(item or "").strip().lower() for item in advantages_vs_magic]:
            return "Магическое преимущество"

    tag = _normalize_save_tag(vs_tag)
    if tag:
        adv_conditions_raw = saves.get("advantage_conditions")
        adv_conditions = adv_conditions_raw if isinstance(adv_conditions_raw, list) else []
        for item in adv_conditions:
            cond_key = _normalize_save_tag(str(item or ""))
            if cond_key == tag:
                return f"Преимущество против: {tag}"
    return ""


def _tireless_precision_bonus_for_check(
    race_features: Any,
    *,
    kind: str,
    key: str,
    proficient: bool = True,
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
        if not proficient:
            return 0, ""
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


def _tool_label_ru(tool_key: str) -> str:
    key = str(tool_key or "").strip().lower()
    return TOOL_LABELS_RU.get(key, key)


def _character_tool_proficiencies(ch: Any) -> set[str]:
    race_features = getattr(ch, "race_features", None)
    rf = race_features if isinstance(race_features, dict) else {}
    proficiencies_raw = rf.get("proficiencies")
    proficiencies = proficiencies_raw if isinstance(proficiencies_raw, dict) else {}
    tools_raw = proficiencies.get("tools")
    tools = tools_raw if isinstance(tools_raw, list) else []
    return {str(item or "").strip().lower() for item in tools if str(item or "").strip()}


def _toolcheck_access_error(ch: Any, tool_key: str) -> str | None:
    key = str(tool_key or "").strip().lower()
    if key not in VALID_TOOL_KEYS:
        return f"Неизвестный инструмент: {key}"
    if key not in _character_tool_proficiencies(ch):
        return f"У персонажа нет владения инструментом: {_tool_label_ru(key)}"
    return None


def _parse_check_command(
    cmdline: str,
) -> tuple[str | None, str | None, bool, str | None, int | None, str, str | None]:
    parts = str(cmdline or "").split()
    usage = "Использование: check|statcheck|skillcheck [adv|dis] [pastlife] <цель> [dc N]"
    if len(parts) < 2:
        return None, None, False, None, None, "", usage

    command = str(parts[0] or "").strip().lower()
    if command not in {"check", "statcheck", "skillcheck"}:
        return None, None, False, None, None, "", usage

    mode = "roll"
    idx = 1
    if idx < len(parts) and parts[idx].lower() in {"adv", "dis"}:
        mode = parts[idx].lower()
        idx += 1
    use_past_life = False
    if idx < len(parts) and parts[idx].lower() == "pastlife":
        use_past_life = True
        idx += 1
    if idx >= len(parts):
        return None, None, False, None, None, "", usage

    key_tokens: list[str] = [parts[idx].lower()]
    idx += 1
    while idx < len(parts) and not parts[idx].lower().startswith("dc"):
        key_tokens.append(parts[idx].lower())
        idx += 1
    check_tag = ""
    if key_tokens and key_tokens[-1] == "smell":
        check_tag = "smell"
        key_tokens = key_tokens[:-1]
    key = _normalize_check_name(" ".join(key_tokens))
    if not key:
        return None, None, False, None, None, "", usage

    dc: int | None = None
    if idx < len(parts):
        tok = parts[idx].lower()
        if tok.startswith("dc"):
            if tok == "dc":
                if idx + 1 >= len(parts):
                    return None, None, False, None, None, "", "Использование: ... dc <N>"
                dc = as_int(parts[idx + 1], -1)
                idx += 2
            else:
                dc = as_int(tok[2:], -1)
                idx += 1
        else:
            return None, None, False, None, None, "", usage
    if idx != len(parts):
        return None, None, False, None, None, "", usage
    if dc is not None and dc < 0:
        return None, None, False, None, None, "", "DC должен быть не меньше 0"

    return command, mode, use_past_life, key, dc, check_tag, None


def _parse_toolcheck_command(cmdline: str) -> tuple[str | None, str | None, int | None, bool, str | None]:
    parts = str(cmdline or "").split()
    usage = "Использование: toolcheck [adv|dis] [pastlife] <tool_key> [dc N]"
    if len(parts) < 2:
        return None, None, None, False, usage

    mode = "normal"
    idx = 1
    if idx < len(parts) and parts[idx].lower() in {"adv", "dis"}:
        mode = "advantage" if parts[idx].lower() == "adv" else "disadvantage"
        idx += 1
    use_past_life = False
    if idx < len(parts) and parts[idx].lower() == "pastlife":
        use_past_life = True
        idx += 1
    if idx >= len(parts):
        return None, None, None, False, usage

    tool_key = str(parts[idx] or "").strip().lower()
    idx += 1
    if not tool_key:
        return None, None, None, False, usage

    dc: int | None = None
    if idx < len(parts):
        tok = parts[idx].lower()
        if tok.startswith("dc"):
            if tok == "dc":
                if idx + 1 >= len(parts):
                    return None, None, None, False, "Использование: toolcheck ... dc <N>"
                dc = as_int(parts[idx + 1], -1)
                idx += 2
            else:
                dc = as_int(tok[2:], -1)
                idx += 1
        else:
            return None, None, None, False, usage
    if idx != len(parts):
        return None, None, None, False, usage
    if dc is not None and dc < 0:
        return None, None, None, False, "DC должен быть не меньше 0"
    return mode, tool_key, dc, use_past_life, None


def _format_d20_roll(mode: str, roll_a: int, roll_b: Optional[int], chosen: int) -> str:
    normalized = str(mode or "normal").strip().lower()
    if roll_b is None:
        return f"d20({chosen})"
    prefix = "adv" if normalized == "advantage" else "dis"
    return f"{prefix} d20({roll_a}, {roll_b}) -> {chosen}"


def _format_toolcheck_log(
    *,
    tool_name_ru: str,
    mode: str,
    roll_a: int,
    roll_b: Optional[int],
    roll: int,
    mod: int,
    tp_bonus: int,
    tp_bonus_text: str,
    extra_bonus_texts: list[str],
    past_life_uses_text: str = "",
    total: int,
    dc: Optional[int],
) -> str:
    lines = [
        f"[TOOL] Проверка инструмента: {tool_name_ru}",
        f"Бросок: {_format_d20_roll(mode, roll_a, roll_b, roll)}",
        f"Бонус: {mod:+d}",
    ]
    if tp_bonus > 0 and tp_bonus_text:
        lines.append(f"Tireless Precision: +{tp_bonus_text}")
    for text in extra_bonus_texts:
        if text:
            lines.append(text if ":" in text else f"Доп. бонус: +{text}")
    lines.append(f"Итого: {total}")
    if dc is not None:
        lines.append(f"DC {dc} -> {'успех' if total >= dc else 'провал'}")
    if past_life_uses_text:
        lines.append(past_life_uses_text)
    return "\n".join(lines)


def _format_check_log(
    *,
    character_name: str,
    key: str,
    roll_a: int,
    roll_b: Optional[int],
    roll: int,
    mod: int,
    tp_bonus_text: str,
    extra_bonus_texts: list[str],
    past_life_uses_text: str = "",
    total: int,
    dc: Optional[int],
) -> str:
    rolls_text = str(roll) if roll_b is None else f"{roll_a}/{roll_b}->{roll}"
    bonus_texts: list[str] = []
    if tp_bonus_text:
        bonus_texts.append(f"Tireless Precision {tp_bonus_text}")
    bonus_texts.extend([text for text in extra_bonus_texts if isinstance(text, str) and text])

    msg = f"[CHECK] {character_name}: {key} = {rolls_text} + {mod:+d}"
    if bonus_texts:
        msg += " + " + " + ".join(bonus_texts)
    msg += f" => {total}"
    if dc is not None:
        ok = total >= dc
        msg += f" (DC {dc}) {'SUCCESS' if ok else 'FAIL'}"
    if past_life_uses_text:
        msg += f" | {past_life_uses_text}"
    return msg


def _parse_save_command(
    cmdline: str,
) -> tuple[bool, str, bool, str, str, int | None, str | None]:
    parts = str(cmdline or "").split()
    usage = "Использование: save [magic] [adv|dis] [footwork] <str|dex|con|int|wis|cha> [vs <tag>] [dc N]"
    if len(parts) < 2:
        return False, "roll", False, "", "", None, usage

    is_magic_save = False
    mode = "roll"
    idx = 1
    if idx < len(parts) and parts[idx].lower() == "magic":
        is_magic_save = True
        idx += 1
    if idx < len(parts) and parts[idx].lower() in ("adv", "dis"):
        mode = parts[idx].lower()
        idx += 1
    use_footwork = False
    if idx < len(parts) and parts[idx].lower() == "footwork":
        use_footwork = True
        idx += 1
    if idx >= len(parts):
        return False, "roll", False, "", "", None, usage

    vs_tag = ""
    ability = ""
    if idx < len(parts) and parts[idx].lower() == "vs":
        if idx + 2 >= len(parts):
            return False, "roll", False, "", "", None, "Использование: save [magic] [adv|dis] [footwork] <ability> [vs <tag>] [dc N]"
        vs_tag = _normalize_save_tag(parts[idx + 1])
        ability = parts[idx + 2].lower()
        idx += 3
    else:
        ability = parts[idx].lower()
        idx += 1
        if idx < len(parts) and parts[idx].lower() == "vs":
            if idx + 1 >= len(parts):
                return False, "roll", False, "", "", None, "Использование: save [magic] [adv|dis] [footwork] <ability> [vs <tag>] [dc N]"
            vs_tag = _normalize_save_tag(parts[idx + 1])
            idx += 2

    if ability not in CHAR_STAT_KEYS:
        return False, "roll", False, "", "", None, "Unknown ability key"

    dc: Optional[int] = None
    if idx < len(parts):
        tok = parts[idx].lower()
        if tok.startswith("dc"):
            if tok == "dc":
                if idx + 1 >= len(parts):
                    return False, "roll", False, "", "", None, "Usage: save ... dc <N>"
                dc = as_int(parts[idx + 1], -1)
                idx += 2
            else:
                dc = as_int(tok[2:], -1)
                idx += 1
        else:
            return False, "roll", False, "", "", None, usage
    if idx != len(parts):
        return False, "roll", False, "", "", None, usage
    if dc is not None and dc < 0:
        return False, "roll", False, "", "", None, "DC must be >= 0"

    return is_magic_save, mode, use_footwork, ability, vs_tag, dc, None


def _runtime_has_active_prone(race_features: Any) -> bool:
    if not isinstance(race_features, dict):
        return False
    runtime_raw = race_features.get("runtime")
    runtime = runtime_raw if isinstance(runtime_raw, dict) else {}
    conditions_raw = runtime.get("conditions")
    conditions = conditions_raw if isinstance(conditions_raw, dict) else {}
    prone_raw = conditions.get("prone")
    prone = prone_raw if isinstance(prone_raw, dict) else {}
    if bool(prone.get("active")):
        return True
    return max(0, as_int(prone.get("remaining_rounds"), 0)) > 0


def _harengon_effective_speed_ft(
    ch: Character,
    *,
    session_id: str,
    player_uid: int | None,
) -> int:
    if player_uid is not None:
        state = get_combat(session_id)
        if state is not None and state.active:
            actor = state.combatants.get(f"pc_{player_uid}")
            if actor is not None:
                move_speed = max(0, as_int(getattr(actor, "move_speed_ft", 0), 0))
                if move_speed > 0:
                    return move_speed
                return max(0, as_int(getattr(actor, "speed_ft", 0), 0))

    race_features = getattr(ch, "race_features", None)
    rf = race_features if isinstance(race_features, dict) else {}
    runtime_raw = rf.get("runtime")
    runtime = runtime_raw if isinstance(runtime_raw, dict) else {}
    override = runtime.get("speed_override_ft")
    if override is not None:
        return max(0, as_int(override, 0))
    speeds_raw = rf.get("speeds")
    speeds = speeds_raw if isinstance(speeds_raw, dict) else {}
    walk_ft = as_int(speeds.get("walk_ft"), as_int(rf.get("speed_ft"), 0))
    return max(0, int(walk_ft))


def _harengon_is_prone(
    ch: Character,
    *,
    session_id: str,
    player_uid: int | None,
) -> bool:
    if player_uid is not None:
        state = get_combat(session_id)
        if state is not None and state.active:
            actor = state.combatants.get(f"pc_{player_uid}")
            if actor is not None:
                actor_rf = actor.race_features if isinstance(actor.race_features, dict) else {}
                return _runtime_has_active_prone(actor_rf)
    return _runtime_has_active_prone(getattr(ch, "race_features", None))


def _consume_harengon_lucky_footwork_for_save(
    ch: Character,
    *,
    session_id: str,
    player_uid: int | None,
    requested: bool,
    ability: str,
    base_total: int,
    dc: int | None,
    rng: Any = None,
) -> tuple[int, str, str, bool, str | None]:
    if not requested:
        return 0, "", "", False, None
    if str(ability or "").strip().lower() != "dex":
        return 0, "", "", False, "Сильные ноги можно применять только к спасброску Ловкости."
    if dc is None:
        return 0, "", "", False, "Для Сильных ног укажите DC спасброска."

    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    lucky_cfg = features.get("lucky_footwork")
    if not isinstance(lucky_cfg, dict):
        return 0, "", "", False, "Сильные ноги недоступны вашей расе."
    if _harengon_is_prone(ch, session_id=session_id, player_uid=player_uid):
        return 0, "", "", False, "Сильные ноги недоступны: вы сбиты с ног."
    if _harengon_effective_speed_ft(ch, session_id=session_id, player_uid=player_uid) <= 0:
        return 0, "", "", False, "Сильные ноги недоступны: скорость должна быть больше 0."
    if base_total >= dc:
        return 0, "", "Lucky Footwork не понадобилась.", False, None

    roller = rng if rng is not None else random
    bonus = max(1, int(roller.randint(1, 4)))
    new_total = base_total + bonus
    runtime = dict(rf.get("runtime")) if isinstance(rf.get("runtime"), dict) else {}
    runtime["last_dex_save_result"] = {
        "dc": max(0, int(dc)),
        "total": int(base_total),
        "bonus": bonus,
        "new_total": new_total,
        "resolved": True,
        "success": new_total >= dc,
        "via_footwork": True,
    }
    runtime.pop("last_failed_dex_save", None)
    rf["runtime"] = runtime
    ch.race_features = rf
    return bonus, f"1d4({bonus})", "", True, None


def _format_save_log(
    *,
    character_name: str,
    save_prefix: str,
    ability: str,
    vs_tag: str,
    mode: str,
    roll_a: int,
    roll_b: Optional[int],
    roll: int,
    mod: int,
    extra_bonus_texts: list[str],
    auto_advantage_reason: str,
    total: int,
    dc: Optional[int],
    footwork_note: str = "",
    footwork_bonus_text: str = "",
    footwork_new_total: int | None = None,
) -> str:
    vs_suffix = f" vs {vs_tag}" if vs_tag else ""
    msg = (
        f"[SAVE] {character_name}: {save_prefix} {ability}{vs_suffix} = "
        f"{_format_d20_roll(mode, roll_a, roll_b, roll)} + {mod:+d}"
    )
    bonus_texts = [text for text in extra_bonus_texts if isinstance(text, str) and text]
    if bonus_texts:
        msg += " + " + " + ".join(bonus_texts)
    msg += f" => {total}"
    if auto_advantage_reason and str(mode or "").strip().lower() == "advantage":
        msg += f" [Источник преимущества: {auto_advantage_reason}]"
    if dc is not None:
        ok = total >= dc
        msg += f" (DC {dc}) {'SUCCESS' if ok else 'FAIL'}"
    if footwork_note:
        msg += f" | {footwork_note}"
    elif footwork_bonus_text and footwork_new_total is not None and dc is not None:
        msg += (
            f" | Lucky Footwork: +{footwork_bonus_text}"
            f" | Новый итог: {footwork_new_total} (DC {dc}) {'SUCCESS' if footwork_new_total >= dc else 'FAIL'}"
        )
    return msg


def _detect_vampiric_bite_empower(text: str) -> str | None:
    src = str(text or "").strip().lower()
    if not src:
        return None
    if re.search(r"(леч|исцел|восстанов)", src, re.IGNORECASE):
        return "heal"
    if re.search(r"(усил|бонус|сосред)", src, re.IGNORECASE):
        return "bonus"
    return None


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
    elif frequency in {"shared_1_per_short_or_long_rest", "shared_1_per_long_rest"}:
        runtime_raw = rf.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        shared_raw = runtime.get("innate_shared_uses")
        shared_uses = dict(shared_raw) if isinstance(shared_raw, dict) else {}
        shared_group = str(spell_entry.get("shared_group") or "").strip().lower()
        if not shared_group:
            shared_group = "innate_shared"
        shared_used = max(0, as_int(shared_uses.get(shared_group), 0))
        if shared_used >= 1:
            if frequency == "shared_1_per_long_rest":
                return None, "Это заклинание уже использовано до долгого отдыха.", False
            return None, "Это заклинание уже использовано до короткого/долгого отдыха.", False
        shared_uses[shared_group] = 1
        runtime["innate_shared_uses"] = shared_uses
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
            "detect_magic": "Обнаружение магии",
            "disguise_self": "Маскировка",
            "druidcraft": "Искусство друидов",
            "enlarge": "Увеличение",
            "invisibility": "Невидимость",
            "enlarge_reduce": "Увеличение/уменьшение",
            "darkness": "тьма",
            "thaumaturgy": "Тауматургия",
            "hellish_rebuke": "Адское возмездие",
            "mage_hand": "Волшебная рука",
            "shield": "Щит",
            "detect_thoughts": "Обнаружение мыслей",
            "jump": "Прыжок",
            "misty_step": "Туманный шаг",
            "hex": "Сглаз",
            "create_or_destroy_water": "Создание/уничтожение воды",
            "gust_of_wind": "Порыв ветра",
            "wall_of_water": "Стена воды",
            "poison_spray": "Ядовитые брызги",
            "animal_friendship": "Дружба с животными",
            "suggestion": "Внушение",
            "fire_bolt": "Огненный снаряд",
            "ray_of_frost": "Луч холода",
            "shocking_grasp": "Электрошок",
            "mage_hand": "Волшебная рука",
            "minor_illusion": "Малая иллюзия",
            "prestidigitation": "Фокусы",
            "light": "Свет",
            "dancing_lights": "Пляшущие огоньки",
        }.get(spell_key, display_name)

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    triton_changed = False
    yuanti_changed = False
    race_key = str(rf.get("race_key") or "").strip().lower()
    subrace_key = str((((rf.get("subrace") or {}).get("key")) or "")).strip().lower()
    if race_key == "triton":
        if spell_key == "gust_of_wind":
            if bool(runtime.get("triton_gust_of_wind_used")) is not changed:
                runtime["triton_gust_of_wind_used"] = changed
                triton_changed = True
        elif spell_key == "wall_of_water":
            if bool(runtime.get("triton_wall_of_water_used")) is not changed:
                runtime["triton_wall_of_water_used"] = changed
                triton_changed = True
            marker = datetime.now(timezone.utc).isoformat() if changed else None
            if runtime.get("triton_active_water_wall") != marker:
                runtime["triton_active_water_wall"] = marker
                triton_changed = True
        elif spell_key == "create_or_destroy_water":
            if "triton_active_water_wall" not in runtime:
                runtime["triton_active_water_wall"] = None
                triton_changed = True
        if triton_changed:
            rf["runtime"] = runtime
            ch.race_features = rf
            changed = True or changed
    if race_key == "dwarf" and subrace_key == "duergar":
        duergar_changed = False
        if spell_key == "enlarge":
            if bool(runtime.get("duergar_enlarge_used")) is not changed:
                runtime["duergar_enlarge_used"] = changed
                duergar_changed = True
        elif spell_key == "invisibility":
            if bool(runtime.get("duergar_invisibility_used")) is not changed:
                runtime["duergar_invisibility_used"] = changed
                duergar_changed = True
        if duergar_changed:
            rf["runtime"] = runtime
            ch.race_features = rf
            changed = True or changed
    if race_key == "gith":
        gith_changed = False
        if subrace_key == "githyanki":
            if spell_key == "jump":
                if bool(runtime.get("githyanki_jump_used")) is not changed:
                    runtime["githyanki_jump_used"] = changed
                    gith_changed = True
            elif spell_key == "misty_step":
                if bool(runtime.get("githyanki_misty_step_used")) is not changed:
                    runtime["githyanki_misty_step_used"] = changed
                    gith_changed = True
        elif subrace_key == "githzerai":
            if spell_key == "shield":
                if bool(runtime.get("githzerai_shield_used")) is not changed:
                    runtime["githzerai_shield_used"] = changed
                    gith_changed = True
            elif spell_key == "detect_thoughts":
                if bool(runtime.get("githzerai_detect_thoughts_used")) is not changed:
                    runtime["githzerai_detect_thoughts_used"] = changed
                    gith_changed = True
        if gith_changed:
            rf["runtime"] = runtime
            ch.race_features = rf
            changed = True or changed
    if race_key == "tiefling":
        tiefling_changed = False
        if spell_key == "hellish_rebuke":
            if bool(runtime.get("tiefling_hellish_rebuke_used")) is not changed:
                runtime["tiefling_hellish_rebuke_used"] = changed
                tiefling_changed = True
        elif spell_key == "darkness":
            if bool(runtime.get("tiefling_darkness_used")) is not changed:
                runtime["tiefling_darkness_used"] = changed
                tiefling_changed = True
        if tiefling_changed:
            rf["runtime"] = runtime
            ch.race_features = rf
            changed = True or changed
    if race_key == "elf" and str(((rf.get("subrace") or {}).get("key") or "")).strip().lower() == "drow":
        drow_changed = False
        if spell_key == "faerie_fire":
            if bool(runtime.get("drow_faerie_fire_used")) is not changed:
                runtime["drow_faerie_fire_used"] = changed
                drow_changed = True
        elif spell_key == "darkness":
            if bool(runtime.get("drow_darkness_used")) is not changed:
                runtime["drow_darkness_used"] = changed
                drow_changed = True
        if drow_changed:
            rf["runtime"] = runtime
            ch.race_features = rf
            changed = True or changed
    if race_key == "yuan_ti_pureblood":
        if runtime.get("yuanti_last_innate_spell") != spell_key:
            runtime["yuanti_last_innate_spell"] = spell_key
            yuanti_changed = True
        if spell_key == "suggestion":
            if bool(runtime.get("yuanti_suggestion_used")) is not changed:
                runtime["yuanti_suggestion_used"] = changed
                yuanti_changed = True
        if yuanti_changed:
            rf["runtime"] = runtime
            ch.race_features = rf
            changed = True or changed
    return display_name, None, changed


def _parse_iso_datetime(raw_value: Any) -> Optional[datetime]:
    txt = str(raw_value or "").strip()
    if not txt:
        return None
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except ValueError:
        return None


def _rock_gnome_tinker_feature(race_features: Any) -> dict[str, Any]:
    rf = race_features if isinstance(race_features, dict) else {}
    if str(rf.get("race_key") or "").strip().lower() != "gnome":
        return {}
    subrace_raw = rf.get("subrace")
    subrace = subrace_raw if isinstance(subrace_raw, dict) else {}
    if str(subrace.get("key") or "").strip().lower() != "rock_gnome":
        return {}
    features_raw = rf.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    tinker_raw = features.get("tinker")
    tinker = tinker_raw if isinstance(tinker_raw, dict) else {}
    return dict(tinker) if tinker else {}


def _tinker_runtime_devices(ch: Any) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    devices_raw = runtime.get("tinker_devices")
    devices = [dict(item) for item in devices_raw] if isinstance(devices_raw, list) else []
    return rf, runtime, devices


def _tinker_device_name_ru(device_type: str) -> str:
    key = str(device_type or "").strip().lower()
    return TINKER_DEVICE_LABELS_RU.get(key, key)


def _cleanup_tinker_devices(ch: Any, *, now: Optional[datetime] = None) -> tuple[list[dict[str, Any]], bool]:
    rf, runtime, devices = _tinker_runtime_devices(ch)
    now_dt = now if isinstance(now, datetime) else utcnow()
    keep: list[dict[str, Any]] = []
    changed = False
    for item in devices:
        expires_at = _parse_iso_datetime(item.get("expires_at"))
        active = bool(item.get("active", True))
        if not active:
            changed = True
            continue
        if isinstance(expires_at, datetime) and expires_at <= now_dt:
            changed = True
            continue
        keep.append(item)
    if changed or runtime.get("tinker_devices") != keep:
        runtime["tinker_devices"] = keep
        rf["runtime"] = runtime
        ch.race_features = rf
        changed = True
    return keep, changed


def _tinker_access_error(ch: Any) -> str | None:
    rf = getattr(ch, "race_features", None)
    tinker = _rock_gnome_tinker_feature(rf)
    if not tinker:
        return "Гномий механик доступен только скальному гному."
    return None


def _create_tinker_device(
    ch: Any,
    device_type: str,
    *,
    now: Optional[datetime] = None,
) -> tuple[str | None, str | None, bool]:
    access_error = _tinker_access_error(ch)
    if access_error:
        return access_error, None, False
    tinker = _rock_gnome_tinker_feature(getattr(ch, "race_features", None))
    option_keys = {
        str((item or {}).get("key") or "").strip().lower()
        for item in (tinker.get("options") if isinstance(tinker.get("options"), list) else [])
        if isinstance(item, dict)
    }
    device_key = str(device_type or "").strip().lower()
    if device_key not in option_keys:
        return "Неизвестный тип устройства. Доступно: clockwork_toy, fire_starter, music_box.", None, False

    devices, cleaned = _cleanup_tinker_devices(ch, now=now)
    max_active = max(1, as_int(tinker.get("max_active_devices"), 3))
    if len(devices) >= max_active:
        return "У вас уже есть 3 активных устройства гномьего механика. Сначала разберите одно из них.", None, cleaned

    rf, runtime, fresh_devices = _tinker_runtime_devices(ch)
    now_dt = now if isinstance(now, datetime) else utcnow()
    duration_hours = max(1, as_int(tinker.get("duration_hours"), 24))
    expires_at = now_dt + timedelta(hours=duration_hours)
    device_id = f"tk_{uuid.uuid4().hex[:4]}"
    fresh_devices.append(
        {
            "id": device_id,
            "type": device_key,
            "name_ru": _tinker_device_name_ru(device_key),
            "created_at": now_dt.isoformat(),
            "expires_at": expires_at.isoformat(),
            "active": True,
        }
    )
    runtime["tinker_devices"] = fresh_devices
    rf["runtime"] = runtime
    ch.race_features = rf
    msg = (
        f"[TINKER] Создано устройство: {_tinker_device_name_ru(device_key)}\n"
        f"ID: {device_id}\n"
        f"Будет работать 24 часа."
    )
    return None, msg, True


def _list_tinker_devices(ch: Any, *, now: Optional[datetime] = None) -> tuple[str | None, str | None, bool]:
    access_error = _tinker_access_error(ch)
    if access_error:
        return access_error, None, False
    devices, changed = _cleanup_tinker_devices(ch, now=now)
    if not devices:
        return None, "[TINKER] Активных устройств нет.", changed
    lines = ["[TINKER] Активные устройства:"]
    for item in devices:
        expires_at = _parse_iso_datetime(item.get("expires_at"))
        expires_text = expires_at.astimezone().strftime("%Y-%m-%d %H:%M") if isinstance(expires_at, datetime) else "—"
        lines.append(
            f"- {str(item.get('id') or '').strip()} — {str(item.get('name_ru') or _tinker_device_name_ru(item.get('type') or ''))} — активно до {expires_text}"
        )
    return None, "\n".join(lines), changed


def _remove_tinker_device(ch: Any, device_id: str, *, now: Optional[datetime] = None) -> tuple[str | None, str | None, bool]:
    access_error = _tinker_access_error(ch)
    if access_error:
        return access_error, None, False
    _devices, cleaned = _cleanup_tinker_devices(ch, now=now)
    rf, runtime, devices = _tinker_runtime_devices(ch)
    needle = str(device_id or "").strip().lower()
    keep: list[dict[str, Any]] = []
    removed: dict[str, Any] | None = None
    for item in devices:
        item_id = str(item.get("id") or "").strip().lower()
        if not removed and item_id == needle:
            removed = item
            continue
        keep.append(item)
    if removed is None:
        return "Устройство с таким ID не найдено.", None, cleaned
    runtime["tinker_devices"] = keep
    rf["runtime"] = runtime
    ch.race_features = rf
    msg = f"[TINKER] Устройство разобрано: {str(removed.get('name_ru') or _tinker_device_name_ru(removed.get('type') or ''))} ({str(removed.get('id') or '').strip()})"
    return None, msg, True


def _kalashtar_mind_link_feature(race_features: Any) -> dict[str, Any]:
    rf = race_features if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    mind_link_raw = features.get("mind_link")
    mind_link = mind_link_raw if isinstance(mind_link_raw, dict) else {}
    if mind_link:
        return dict(mind_link)
    senses_raw = rf.get("senses")
    senses = senses_raw if isinstance(senses_raw, dict) else {}
    telepathy_raw = senses.get("telepathy")
    telepathy = telepathy_raw if isinstance(telepathy_raw, dict) else {}
    if str(telepathy.get("range_formula") or "").strip().lower() == "level*10":
        return dict(telepathy)
    return {}


def _verdan_limited_telepathy_feature(race_features: Any) -> dict[str, Any]:
    rf = race_features if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    limited_raw = features.get("limited_telepathy")
    limited = limited_raw if isinstance(limited_raw, dict) else {}
    if limited:
        return dict(limited)
    senses_raw = rf.get("senses")
    senses = senses_raw if isinstance(senses_raw, dict) else {}
    telepathy_raw = senses.get("telepathy")
    telepathy = telepathy_raw if isinstance(telepathy_raw, dict) else {}
    if int(as_int(telepathy.get("range_ft"), 0)) > 0 and str(telepathy.get("bandwidth") or "").strip().lower() == "simple_ideas":
        return dict(telepathy)
    return {}


def _firbolg_speech_feature(race_features: Any) -> dict[str, Any]:
    rf = race_features if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    speech_raw = features.get("speech_of_beast_and_leaf")
    speech = speech_raw if isinstance(speech_raw, dict) else {}
    if speech:
        return dict(speech)
    return {}


def _kenku_mimicry_feature(race_features: Any) -> dict[str, Any]:
    rf = race_features if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    mimicry_raw = features.get("mimicry")
    mimicry = mimicry_raw if isinstance(mimicry_raw, dict) else {}
    if mimicry:
        return dict(mimicry)
    return {}


def _kenku_expert_forgery_feature(race_features: Any) -> dict[str, Any]:
    rf = race_features if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    forgery_raw = features.get("expert_forgery")
    forgery = forgery_raw if isinstance(forgery_raw, dict) else {}
    if forgery:
        return dict(forgery)
    return {}


def _loxodon_trunk_feature(race_features: Any) -> dict[str, Any]:
    rf = race_features if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    trunk_raw = features.get("trunk")
    trunk = trunk_raw if isinstance(trunk_raw, dict) else {}
    if trunk:
        return dict(trunk)
    return {}


def _clear_kalashtar_reply_grant(target_ch: Character, *, owner_player_id: str = "") -> bool:
    race_features = getattr(target_ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    grant_owner = str(runtime.get("mind_link_can_reply_to") or "").strip()
    if owner_player_id and grant_owner and grant_owner != owner_player_id:
        return False
    changed = False
    for key in ("mind_link_can_reply_to", "mind_link_can_reply_until", "mind_link_can_reply_to_name"):
        if key in runtime:
            runtime.pop(key, None)
            changed = True
    if not changed:
        return False
    if runtime:
        rf["runtime"] = runtime
    else:
        rf.pop("runtime", None)
    target_ch.race_features = rf
    return True


def _extract_mind_link_target(text: str) -> str:
    txt = str(text or "").strip()
    m = MIND_LINK_SET_CAPTURE_RE.search(txt)
    if not m:
        return ""
    return str(m.group("target") or "").strip().strip(".,!?")


def _extract_mind_link_text(text: str, *, reply: bool = False) -> str:
    txt = str(text or "").strip()
    pattern = MIND_LINK_REPLY_CAPTURE_RE if reply else MIND_LINK_SAY_CAPTURE_RE
    m = pattern.search(txt)
    if not m:
        return ""
    if reply:
        return str(m.group("text") or "").strip()
    value = str((m.groupdict().get("text") or m.groupdict().get("text_alt") or "")).strip()
    return value


def _mind_link_until_hhmm(iso_value: str) -> str:
    dt = _parse_iso_datetime(iso_value)
    if not isinstance(dt, datetime):
        return ""
    return dt.astimezone().strftime("%H:%M")


def _parse_mind_link_command(cmdline: str) -> tuple[str | None, str | None]:
    txt = str(cmdline or "").strip()
    if not txt:
        return None, None
    lowered = txt.lower()
    if lowered == "mindlink status":
        return "mind_link_status", None
    if lowered == "mindlink close":
        return "mind_link_clear", None
    if lowered == "мысленная связь статус":
        return "mind_link_status", None
    if lowered == "мысленная связь закрыть":
        return "mind_link_clear", None
    if lowered.startswith("mindlink open "):
        return "mind_link_set", txt[len("mindlink open "):].strip()
    if lowered.startswith("mindlink send "):
        return "mind_link_say", txt[len("mindlink send "):].strip()
    if lowered.startswith("мысленная связь открыть "):
        return "mind_link_set", txt[len("мысленная связь открыть "):].strip()
    if lowered.startswith("мысленная связь отправить "):
        return "mind_link_say", txt[len("мысленная связь отправить "):].strip()
    return None, None


def _parse_verdan_telepathy_command(cmdline: str) -> tuple[str | None, str | None, str | None]:
    txt = str(cmdline or "").strip()
    if not txt:
        return None, None, None
    lowered = txt.lower()
    if lowered == "telepathy status" or lowered == "телепатия статус":
        return "verdan_telepathy_status", None, None
    payload = ""
    if lowered.startswith("telepathy send "):
        payload = txt[len("telepathy send "):].strip()
    elif lowered.startswith("телепатия отправить "):
        payload = txt[len("телепатия отправить "):].strip()
    if not payload:
        return None, None, None
    target, sep, message = payload.partition(":")
    target_name = str(target or "").strip().strip(".,!?")
    message_text = str(message or "").strip()
    return "verdan_telepathy_send", target_name, message_text


def _parse_firbolg_speech_command(cmdline: str) -> tuple[str | None, str | None]:
    txt = str(cmdline or "").strip()
    if not txt:
        return None, None
    lowered = txt.lower()
    if lowered in {"speech status", "речь статус"}:
        return "firbolg_speech_status", None
    prefixes = (
        ("speech beast:", "beast"),
        ("speech plant:", "plant"),
        ("речь зверю:", "beast"),
        ("речь растению:", "plant"),
    )
    for prefix, target_kind in prefixes:
        if lowered.startswith(prefix):
            return f"firbolg_speech_{target_kind}", txt[len(prefix):].strip()
    return None, None


def _parse_kenku_mimicry_command(cmdline: str) -> tuple[str | None, str | None]:
    txt = str(cmdline or "").strip()
    if not txt:
        return None, None
    lowered = txt.lower()
    if lowered in {"mimicry status", "подражание статус"}:
        return "kenku_mimicry_status", None
    prefixes = (
        ("mimicry voice:", "voice"),
        ("mimicry sound:", "sound"),
        ("подражание голос:", "voice"),
        ("подражание звук:", "sound"),
    )
    for prefix, target_kind in prefixes:
        if lowered.startswith(prefix):
            return f"kenku_mimicry_{target_kind}", txt[len(prefix):].strip()
    return None, None


def _parse_kenku_expert_forgery_command(cmdline: str) -> tuple[str | None, str | None]:
    txt = str(cmdline or "").strip()
    if not txt:
        return None, None
    lowered = txt.lower()
    if lowered in {"forgery status", "подлог статус"}:
        return "kenku_forgery_status", None
    prefixes = (
        "forgery copy:",
        "подлог:",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return "kenku_forgery_copy", txt[len(prefix):].strip()
    return None, None


def _parse_loxodon_trunk_command(cmdline: str) -> tuple[str | None, str | None]:
    txt = str(cmdline or "").strip()
    if not txt:
        return None, None
    lowered = txt.lower()
    if lowered in {"trunk status", "хобот статус"}:
        return "loxodon_trunk_status", None
    prefixes = (
        "trunk use:",
        "хобот:",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return "loxodon_trunk_use", txt[len(prefix):].strip()
    return None, None


def _parse_group_command(cmdline: str) -> tuple[str | None, dict[str, Any]]:
    txt = str(cmdline or "").strip()
    if not txt:
        return None, {}
    lowered = txt.lower()

    if lowered in {"group camp resolve", "group_camp_resolve"}:
        return "group_camp_resolve", {}

    if lowered in {"group rest", "group_rest"}:
        return "group_rest", {}

    if lowered in {"group scout", "group_scout", "group search", "group_search"}:
        return "group_scout", {}

    for prefix in ("group wait", "group_wait"):
        if lowered == prefix:
            return "group_wait", {}
        if lowered.startswith(prefix + ":"):
            return "group_wait", {"reason": txt[len(prefix) + 1:].strip()}
        if lowered.startswith(prefix + " "):
            return "group_wait", {"reason": txt[len(prefix):].strip()}

    for prefix in ("group camp", "group_camp"):
        if lowered == prefix:
            return "group_camp", {}
        if lowered.startswith(prefix + ":"):
            return "group_camp", {"reason": txt[len(prefix) + 1:].strip()}
        if lowered.startswith(prefix + " "):
            return "group_camp", {"reason": txt[len(prefix):].strip()}

    for prefix in ("group move ", "group_move "):
        if lowered.startswith(prefix):
            return "group_move", {"target_hint": txt[len(prefix):].strip()}

    for prefix in ("group navigate ", "group_navigate "):
        if lowered.startswith(prefix):
            return "group_navigate", {"target_node_id": txt[len(prefix):].strip()}

    for prefix in ("group go ", "group_go "):
        if lowered.startswith(prefix):
            return "group_journey_set", {"target_node_id": txt[len(prefix):].strip()}

    if lowered in {"group continue", "group_continue"}:
        return "group_journey_advance", {}

    if lowered in {"group journey", "group_journey"}:
        return "group_journey_status", {}

    for prefix in ("group do ", "group_do ", "group action ", "group_action "):
        if lowered.startswith(prefix):
            payload = txt[len(prefix):].strip()
            action_key, _, action_arg = payload.partition(" ")
            parsed_action_id = action_key.strip()
            parsed_payload: dict[str, Any] = {"action_key": parsed_action_id, "action_id": parsed_action_id}
            if str(action_key or "").strip().lower() == "navigate" and action_arg.strip():
                parsed_payload["target_node_id"] = action_arg.strip()
            return "group_context_action", parsed_payload

    for prefix in ("group use service ", "group_use_service ", "group service ", "group_service ", "group use ", "group_use "):
        if lowered.startswith(prefix):
            service_id = txt[len(prefix):].strip()
            return "group_service_use", {"service_id": service_id, "service_key": service_id}

    for prefix in ("group enter ", "group_enter "):
        if lowered.startswith(prefix):
            return "group_enter", {"target_hint": txt[len(prefix):].strip()}

    for prefix in ("group mode ", "group_mode "):
        if lowered.startswith(prefix):
            return "group_set_mode", {"movement_mode": txt[len(prefix):].strip()}

    for prefix in ("group activity ", "group_activity "):
        if lowered.startswith(prefix):
            return "group_set_activity", {"activity": txt[len(prefix):].strip()}

    if lowered in {"group clear activity", "group_clear_activity"}:
        return "group_clear_activity", {}

    if lowered in {"group event resolve", "group_event_resolve"}:
        return "group_event_resolve", {}

    if lowered in {"group event ignore", "group_event_ignore"}:
        return "group_event_ignore", {}

    if lowered in {"group local", "group_local", "group event", "group_destination_event"}:
        return "group_destination_event", {}

    if lowered in {"group options", "group_options", "group interact", "group_interact"}:
        return "group_local_interactions", {}

    if lowered in {"group progress", "group_progress", "group place", "group_place"}:
        return "group_node_progress", {}

    if lowered in {"group region", "group_region", "group frontier", "group_frontier"}:
        return "group_region_progress", {}

    if lowered in {"group exits", "group_exits", "group gateways", "group_gateways"}:
        return "group_region_gateways", {}

    if lowered in {"group here", "group_here"}:
        return "group_region_status", {}

    if lowered in {"group regions", "group_regions"}:
        return "group_discovered_regions", {}

    if lowered in {"group world", "group_world"}:
        return "group_region_world", {}

    if lowered in {"group links", "group_links"}:
        return "group_region_links", {}

    if lowered in {"group crossings", "group_crossings"}:
        return "group_gateway_history", {}

    if lowered in {"group focus", "group_focus"}:
        return "group_region_focus", {}

    if lowered in {"group focus-route", "group_focus_route"}:
        return "group_primary_region_route", {}

    if lowered in {"group focus-path", "group_focus_path"}:
        return "group_primary_region_focus_plan", {}

    if lowered in {"group region-pursuit", "group_region_pursuit"}:
        return "group_region_pursuit_status", {}

    if lowered in {"group known-region-pursuit", "group_known_region_pursuit"}:
        return "group_multi_region_pursuit_status", {}

    if lowered in {"group region-step", "group_region_step"}:
        return "group_region_pursuit_step_status", {}

    if lowered in {"group continue-region", "group_continue_region"}:
        return "group_region_pursuit_advance", {}

    if lowered in {"group arrival-region", "group_arrival_region", "group region-entry", "group_region_entry"}:
        return "group_region_onboarding", {}

    if lowered in {"group transition", "group_region_transition_status"}:
        return "group_region_transition_status", {}

    for prefix in ("group exit ", "group_exit ", "group cross ", "group_cross "):
        if lowered.startswith(prefix):
            return "group_region_transition", {"gateway_id": txt[len(prefix):].strip()}

    for prefix in ("group route-region ", "group_route_region ", "group region-path ", "group_region_path "):
        if lowered.startswith(prefix):
            return "group_region_target_plan", {"target_region_id": txt[len(prefix):].strip()}

    for prefix in ("group route-known-region ", "group_route_known_region ", "group known-path ", "group_known_path "):
        if lowered.startswith(prefix):
            return "group_known_region_route", {"target_region_id": txt[len(prefix):].strip()}

    for prefix in ("group pursue-region ", "group_pursue_region "):
        if lowered.startswith(prefix):
            return "group_region_pursuit_set", {"target_region_id": txt[len(prefix):].strip()}

    for prefix in ("group pursue-known-region ", "group_pursue_known_region "):
        if lowered.startswith(prefix):
            return "group_multi_region_pursuit_set", {"target_region_id": txt[len(prefix):].strip()}

    if lowered in {"group stop-region", "group_stop_region"}:
        return "group_region_pursuit_clear", {}

    if lowered in {"group arrive", "group_arrive"}:
        return "group_arrive", {}

    if lowered in {"group interrupt", "group_interrupt"}:
        return "group_interrupt", {}

    if lowered in {"group pause", "group_pause"}:
        return "group_pause", {}

    if lowered in {"group resume", "group_resume"}:
        return "group_resume", {}

    if lowered in {"group confirm enter", "group_confirm_enter"}:
        return "group_confirm_enter", {}

    if lowered in {"group inspect", "group_inspect_target"}:
        return "group_inspect_target", {}

    if lowered in {"group bypass", "group_bypass"}:
        return "group_bypass", {}

    if lowered in {"group resolve", "group_resolve_pause"}:
        return "group_resolve_pause", {}

    if lowered in {"group stop", "group_stop"}:
        return "group_stop", {}

    if lowered in {"group intel", "group_intel", "group journal", "group_journal"}:
        return "group_map_intel", {}

    if lowered in {"group entry", "group_entry", "group arrival", "group_arrival"}:
        return "group_node_entry", {}

    if lowered in {"group leads", "group_leads", "group next", "group_next"}:
        return "group_exploration_leads", {}

    if lowered in {"group routes", "group_route_planning", "group_routes"}:
        return "group_route_planning", {}

    for prefix in ("group path ", "group_path ", "group route ", "group_route "):
        if lowered.startswith(prefix):
            return "group_route_plan_to", {"target_node_id": txt[len(prefix):].strip()}

    if lowered in {"group trail", "group_trail", "group visits", "group_visit_history", "group_visits"}:
        return "group_visit_history", {}

    for prefix in ("group split ", "group_split "):
        if lowered.startswith(prefix):
            payload = txt[len(prefix):].strip()
            members_part = payload
            new_group_id = ""
            split_marker = " as "
            marker_index = members_part.lower().find(split_marker)
            if marker_index >= 0:
                new_group_id = members_part[marker_index + len(split_marker):].strip()
                members_part = members_part[:marker_index].strip()
            member_ids = [item.strip() for item in re.split(r"[\s,]+", members_part) if item.strip()]
            return "group_split", {
                "member_player_ids": member_ids,
                "new_group_id": new_group_id or None,
            }

    for prefix in ("group merge ", "group_merge "):
        if lowered.startswith(prefix):
            payload = txt[len(prefix):].strip()
            source_group_id = payload
            target_group_id = ""
            merge_marker = " into "
            marker_index = payload.lower().find(merge_marker)
            if marker_index >= 0:
                source_group_id = payload[:marker_index].strip()
                target_group_id = payload[marker_index + len(merge_marker):].strip()
            result = {"source_group_id": source_group_id}
            if target_group_id:
                result["target_group_id"] = target_group_id
            return "group_merge", result

    return None, {}


_LOCAL_ACTION_TEXT_ALIASES: dict[str, tuple[str, ...]] = {
    "inspect": (
        "осмотреться",
        "осмотрюсь",
        "оглядеться",
        "огляжусь",
        "посмотреть вокруг",
        "осмотреть место",
    ),
    "wait": (
        "подождать",
        "ждать",
        "переждать",
        "подожду",
    ),
    "navigate": (
        "пойти дальше",
        "идти дальше",
        "пройти вперед",
        "двинуться дальше",
        "двигаться дальше",
    ),
}


def _normalize_local_action_text(text: str) -> str:
    normalized = str(text or "").strip().lower().replace("ё", "е")
    if not normalized:
        return ""
    normalized = re.sub(r"[^\w\s]+", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _surface_action_identity(item: Any) -> tuple[str, str]:
    if not isinstance(item, dict):
        return "", ""
    action_key = str(item.get("action_id") or item.get("action_key") or item.get("interaction_id") or "").strip().lower()
    label = str(item.get("action_label") or item.get("label") or item.get("title") or "").strip()
    return action_key, label


def _match_simple_text_local_action(cmdline: str, surface: dict[str, Any] | None) -> tuple[str | None, dict[str, Any]]:
    normalized_text = _normalize_local_action_text(cmdline)
    if not normalized_text or not isinstance(surface, dict):
        return None, {}
    for item in list(surface.get("available_actions") or []):
        action_key, label = _surface_action_identity(item)
        if not action_key:
            continue
        if str((item or {}).get("action_type") or "action").strip().lower() != "action":
            continue
        aliases = _LOCAL_ACTION_TEXT_ALIASES.get(action_key, ())
        normalized_label = _normalize_local_action_text(label)
        if normalized_text not in aliases and normalized_text != normalized_label:
            continue
        payload: dict[str, Any] = {"action_id": action_key, "action_key": action_key}
        if action_key == "navigate":
            target_node_id = str(item.get("target_node_id") or "").strip()
            if not target_node_id:
                return None, {}
            payload["target_node_id"] = target_node_id
        return "group_context_action", payload
    return None, {}


def _resolve_group_action_target(
    sess,
    *,
    actor_group_id: str,
    actor_player_id: uuid.UUID | str,
    payload: dict[str, Any],
    enter: bool,
) -> dict[str, Any] | None:
    group = _get_group_states(sess).get(actor_group_id)
    current_map_position = group.get("current_map_position") if isinstance(group, dict) else None
    current_zone_label = str((group or {}).get("area_label") or "стартовая локация")

    direct_target = payload.get("target_node") or payload.get("target")
    target_hint = str(payload.get("target_hint") or payload.get("target_label") or "").strip()
    return resolve_action_target_node(
        action_text=target_hint,
        target_text=target_hint,
        current_map_position=current_map_position if isinstance(current_map_position, dict) else None,
        current_area_label=current_zone_label,
        action_kind="enter" if enter else "move",
        target_node=direct_target,
        known_node_ids=get_player_known_node_ids(sess, actor_player_id),
        require_known_static=True,
    )


def _handle_group_action_request(
    sess,
    *,
    action: str,
    actor_player_id: uuid.UUID | str,
    payload: dict[str, Any] | None = None,
    source: str = "ws",
) -> tuple[bool, Optional[str], Optional[str]]:
    if action not in {
        "group_wait",
        "group_camp",
        "group_camp_resolve",
        "group_rest",
        "group_scout",
        "group_split",
        "group_merge",
        "group_move",
        "group_navigate",
        "group_context_action",
        "group_service",
        "group_service_use",
        "group_map_intel",
        "group_node_entry",
        "group_destination_event",
        "group_local_interactions",
        "group_node_progress",
        "group_region_progress",
        "group_region_gateways",
        "group_region_status",
        "group_discovered_regions",
        "group_region_world",
        "group_region_links",
        "group_gateway_history",
        "group_region_focus",
        "group_known_region_route",
        "group_region_target_plan",
        "group_primary_region_focus_plan",
        "group_primary_region_route",
        "group_region_pursuit_set",
        "group_multi_region_pursuit_set",
        "group_region_pursuit_clear",
        "group_region_pursuit_status",
        "group_multi_region_pursuit_status",
        "group_region_pursuit_advance",
        "group_region_pursuit_step_status",
        "group_region_onboarding",
        "group_region_transition",
        "group_region_transition_status",
        "group_exploration_leads",
        "group_journey_set",
        "group_journey_advance",
        "group_journey_status",
        "group_route_planning",
        "group_route_plan_to",
        "group_visit_history",
        "group_enter",
        "group_stop",
        "group_event_resolve",
        "group_event_ignore",
        "group_arrive",
        "group_interrupt",
        "group_pause",
        "group_resume",
        "group_confirm_enter",
        "group_inspect_target",
        "group_bypass",
        "group_resolve_pause",
        "group_set_mode",
        "group_set_activity",
        "group_clear_activity",
    }:
        return False, None, None

    payload = payload if isinstance(payload, dict) else {}
    actor_group_id = _get_player_group_id(sess, actor_player_id)
    actor_group_key = str(actor_group_id or "").strip()
    actor_id = str(actor_player_id)

    if action in {"group_set_mode", "group_set_activity", "group_clear_activity"}:
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        if action == "group_set_mode":
            movement_mode = str(payload.get("movement_mode") or "").strip().lower()
            updated = set_group_movement_mode(sess, actor_group_key, movement_mode)
            if not updated:
                return True, "Не удалось изменить режим движения группы.", None
            return True, None, f"Режим движения группы {actor_group_key}: {updated.get('movement_mode')}."
        if action == "group_clear_activity":
            updated = clear_group_travel_activity(sess, actor_group_key)
            if not updated:
                return True, "Не удалось очистить походную активность группы.", None
            return True, None, f"Походная активность группы {actor_group_key} очищена."
        updated = set_group_travel_activity(
            sess,
            actor_group_key,
            activity=str(payload.get("activity") or "").strip().lower(),
            assigned_actor_id=payload.get("assigned_actor_id") or actor_id,
            source=source,
        )
        if not updated:
            return True, "Не удалось установить походную активность группы.", None
        activity = get_group_travel_activity(sess, actor_group_key) or {}
        return True, None, f"Походная активность группы {actor_group_key}: {activity.get('activity')}."

    if action == "group_scout":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        updated, error = resolve_group_scout(
            sess,
            actor_group_key,
            player_id=actor_player_id,
            source=source,
        )
        if error:
            return True, error, None
        scout_result = (updated or {}).get("last_scout_result") or {}
        return True, None, str(scout_result.get("result_summary") or f"Группа {actor_group_key} провела разведку.")

    if action == "group_map_intel":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        recent_entries = get_current_group_recent_map_intel(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        all_entries = get_current_group_map_intel(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not all_entries:
            return True, None, f"У группы {actor_group_key} пока нет записей в журнале разведки."
        latest = recent_entries[-1] if recent_entries else all_entries[-1]
        latest = latest or {}
        title = str(latest.get("title") or "журнал разведки").strip() or "журнал разведки"
        detail = str(latest.get("result_summary") or latest.get("summary") or title).strip() or title
        node_label = str(latest.get("node_label") or "").strip()
        latest_details = f"{node_label}: {detail}" if node_label else detail
        if latest_details[-1:] not in {".", "!", "?"}:
            latest_details = f"{latest_details}."
        count = len(all_entries)
        return True, None, f"Журнал разведки группы {actor_group_key}: {count} записей. Последняя запись: {title}. {latest_details}"

    if action == "group_node_entry":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        result = get_current_group_last_node_entry_result(sess, player_id=actor_player_id, group_id=actor_group_key)
        entry_state = get_current_group_current_node_entry_state(sess, player_id=actor_player_id, group_id=actor_group_key)
        if not result and not entry_state:
            return True, None, f"У группы {actor_group_key} пока нет node-entry результата."
        title = str((result or {}).get("title") or (entry_state or {}).get("node_label") or "entry")
        entry_type = str((result or {}).get("result_type") or (entry_state or {}).get("last_entry_type") or "entry")
        return True, None, f"Node entry группы {actor_group_key}: {title} ({entry_type})."

    if action == "group_destination_event":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        result = get_current_group_last_destination_event_result(sess, player_id=actor_player_id, group_id=actor_group_key)
        event_state = get_current_group_current_node_destination_event_state(sess, player_id=actor_player_id, group_id=actor_group_key)
        if not result and not event_state:
            return True, None, f"У группы {actor_group_key} пока нет destination event результата."
        title = str((result or {}).get("title") or (event_state or {}).get("event_id") or "local event")
        result_type = str((result or {}).get("result_type") or (event_state or {}).get("result_type") or "destination_event")
        return True, None, f"Destination event группы {actor_group_key}: {title} ({result_type})."

    if action == "group_local_interactions":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        surface = get_current_group_local_interaction_surface(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not surface:
            return True, None, f"У группы {actor_group_key} нет локальных взаимодействий в текущем узле."
        available_actions = list(surface.get("available_actions") or [])
        available_services = list(surface.get("available_services") or [])
        locked_actions = list(surface.get("locked_actions") or [])
        locked_services = list(surface.get("locked_services") or [])

        def _surface_item_label(item: Any, fallback_prefix: str, index: int) -> str:
            if not isinstance(item, dict):
                return f"{fallback_prefix} {index}"
            label = str(
                item.get("action_label")
                or item.get("service_label")
                or item.get("label")
                or item.get("title")
                or item.get("action_id")
                or item.get("action_key")
                or item.get("service_id")
                or item.get("service_key")
                or ""
            ).strip()
            return label or f"{fallback_prefix} {index}"

        def _surface_item_list(items: list[Any], fallback_prefix: str) -> str:
            labels: list[str] = []
            for index, item in enumerate(items, start=1):
                labels.append(_surface_item_label(item, fallback_prefix, index))
            return ", ".join(labels) if labels else "—"

        available_action_text = _surface_item_list(available_actions, "действие")
        available_service_text = _surface_item_list(available_services, "услуга")
        locked_action_text = _surface_item_list(locked_actions, "ограниченное действие")
        locked_service_text = _surface_item_list(locked_services, "ограниченная услуга")
        return True, None, (
            f"Локальные взаимодействия группы {actor_group_key}: "
            f"{len(available_actions)} действий и {len(available_services)} услуг доступны, "
            f"{len(locked_actions)} действий и {len(locked_services)} услуг ограничены. "
            f"Доступные действия: {available_action_text}. "
            f"Доступные услуги: {available_service_text}. "
            f"Ограниченные действия: {locked_action_text}. "
            f"Ограниченные услуги: {locked_service_text}."
        )

    if action == "group_node_progress":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        progress = get_current_group_current_node_progress(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not progress:
            return True, "Не удалось определить текущий узел группы.", None
        return True, None, (
            f"Локальный прогресс группы {actor_group_key}: "
            f"{str(progress.get('node_label') or 'узел')} "
            f"({str(progress.get('progression_status') or 'unknown')}). "
            f"{str(progress.get('summary') or '')}"
        ).strip()

    if action == "group_region_progress":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        summary = get_current_group_region_exploration_summary(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        frontier = get_current_group_region_frontier_summary(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not summary:
            return True, "Не удалось определить региональный exploration summary группы.", None
        return True, None, (
            f"Региональный прогресс группы {actor_group_key}: "
            f"{str(summary.get('region_label') or 'регион')} "
            f"({str(summary.get('progression_status') or 'unknown')}). "
            f"{str(summary.get('summary') or '')} "
            f"{str((frontier or {}).get('summary') or '')}"
        ).strip()

    if action == "group_region_gateways":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        gateways = get_current_group_region_gateways(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not gateways:
            return True, None, f"У группы {actor_group_key} пока нет видимых выходов из текущего региона."
        primary_gateway = get_current_group_primary_region_gateway(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        ) or gateways[0]
        open_count = sum(1 for item in gateways if str(item.get("gateway_status") or "") == "open")
        blocked_count = sum(1 for item in gateways if str(item.get("gateway_status") or "") == "blocked")
        locked_count = sum(1 for item in gateways if str(item.get("gateway_status") or "") == "locked")
        future_count = sum(1 for item in gateways if str(item.get("gateway_status") or "") == "future_stub")
        return True, None, (
            f"Региональные выходы группы {actor_group_key}: "
            f"{open_count} открытых, {blocked_count} заблокированных, "
            f"{locked_count} закрытых и {future_count} будущих. "
            f"Главный выход: {str(primary_gateway.get('gateway_label') or 'gateway')} "
            f"({str(primary_gateway.get('gateway_status') or 'unknown')})."
        )

    if action == "group_region_status":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        current_region = get_current_group_current_region_state(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        last_entry = get_current_group_last_region_entry_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not current_region and not last_entry:
            return True, None, f"У группы {actor_group_key} пока нет region residency истории."
        group = _get_group_states(sess).get(actor_group_key)
        current_map_position = group.get("current_map_position") if isinstance(group, dict) else None
        place_label = ""
        place_detail = ""
        if isinstance(current_map_position, dict):
            place_label = str(
                current_map_position.get("label")
                or current_map_position.get("node_id")
                or ""
            ).strip()
            node_type = str(current_map_position.get("node_type") or "").strip()
            map_level = str(current_map_position.get("map_level") or "").strip()
            if node_type and node_type != "zone":
                place_detail_parts = [f"тип точки: {node_type}"]
                if map_level:
                    place_detail_parts.append(f"уровень: {map_level}")
                place_detail = f" ({', '.join(place_detail_parts)})"
        region_label = str((current_region or last_entry or {}).get("region_label") or "регион")
        visit_count = as_int((current_region or last_entry or {}).get("visit_count"), 0)
        status_note = str((last_entry or {}).get("result_type") or "current_region_confirmed")
        summary_parts = [
            f"Текущее место группы {actor_group_key}: {place_label}{place_detail}." if place_label else "",
            f"Текущий регион: {region_label}.",
            f"Входов в регион: {visit_count}." if visit_count > 0 else "",
            f"Последний region-entry: {status_note}." if status_note else "",
        ]
        return True, None, " ".join(part for part in summary_parts if part).strip()

    if action == "group_discovered_regions":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        regions = get_current_group_discovered_regions(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not regions:
            return True, None, f"У группы {actor_group_key} пока нет discovered regions."
        current_region = get_current_group_current_region_state(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        current_region_label = str((current_region or {}).get("region_label") or "")
        return True, None, (
            f"Открытые регионы группы {actor_group_key}: {len(regions)}. "
            f"Текущий регион: {current_region_label or str(regions[-1].get('region_label') or 'регион')}."
        )

    if action == "group_region_world":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        overview = get_current_group_region_world_overview(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not overview:
            return True, None, f"У группы {actor_group_key} пока слишком мало discovered-region данных для world overview."
        return True, None, (
            f"Мировой обзор регионов группы {actor_group_key}: "
            f"{str(overview.get('summary') or '')} "
            f"Текущий регион: {str(overview.get('current_region_label') or 'регион')}."
        ).strip()

    if action == "group_region_links":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        links = get_current_group_region_link_states(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        result = get_current_group_last_region_link_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not links and not result:
            return True, None, f"У группы {actor_group_key} пока нет discovered region links."
        if result:
            return True, None, str(result.get("result_summary") or result.get("summary") or "Последняя region-link запись сохранена.")
        primary = links[0]
        return True, None, (
            f"Region links группы {actor_group_key}: {len(links)}. "
            f"Главная связка: {str(primary.get('region_a_label') or 'регион')} <-> {str(primary.get('region_b_label') or 'регион')}."
        )

    if action == "group_gateway_history":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        crossings = get_current_group_gateway_traversal_states(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not crossings:
            return True, None, f"У группы {actor_group_key} пока нет истории gateway crossings."
        latest = crossings[0]
        return True, None, (
            f"Gateway history группы {actor_group_key}: {len(crossings)} crossing record(s). "
            f"Последний выход: {str(latest.get('gateway_label') or 'gateway')} "
            f"({str(latest.get('traversal_count') or 0)} traversal)."
        )

    if action == "group_region_focus":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        focus = get_current_group_primary_region_focus(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        summaries = get_current_group_discovered_region_summaries(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not focus and not summaries:
            return True, None, f"У группы {actor_group_key} пока нет выраженного region focus."
        focus = focus or summaries[0]
        return True, None, (
            f"Region focus группы {actor_group_key}: "
            f"{str((focus or {}).get('region_label') or 'регион')} "
            f"({str((focus or {}).get('region_status') or 'unknown')}). "
            f"{str((focus or {}).get('summary') or '')}"
        ).strip()

    if action == "group_region_target_plan":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        target_region_id = str(payload.get("target_region_id") or "").strip()
        if not target_region_id:
            return True, "Нужно указать target_region_id для target-region guidance.", None
        plan = get_current_group_region_target_plan(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
            target_region_id=target_region_id,
        )
        if not plan:
            return True, "Не удалось собрать target-region guidance для этой цели.", None
        options = get_current_group_region_target_options(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        summary = str(plan.get("summary") or "").strip()
        suggested_command = str(plan.get("suggested_command") or "").strip()
        if suggested_command:
            summary = f"{summary} Подсказка: {suggested_command}."
        if not summary and options:
            summary = str(options.get("summary") or "").strip()
        return True, None, summary or f"Target-region plan группы {actor_group_key} собран."

    if action == "group_known_region_route":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        target_region_id = str(payload.get("target_region_id") or "").strip()
        if not target_region_id:
            return True, "Нужно указать target_region_id для known-region route.", None
        route = get_current_group_known_region_route(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
            target_region_id=target_region_id,
        )
        if not route:
            return True, "Не удалось собрать known-region route для этой цели.", None
        options = get_current_group_known_region_route_options(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        summary = str(route.get("summary") or "").strip()
        suggested_command = str(route.get("suggested_command") or "").strip()
        if suggested_command:
            summary = f"{summary} Подсказка: {suggested_command}."
        if not summary and options:
            summary = str(options.get("summary") or "").strip()
        return True, None, summary or f"Known-region route группы {actor_group_key} собран."

    if action == "group_primary_region_focus_plan":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        plan = get_current_group_primary_region_focus_plan(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not plan:
            return True, None, f"У группы {actor_group_key} пока нет выраженного primary region focus plan."
        summary = str(plan.get("summary") or "").strip()
        suggested_command = str(plan.get("suggested_command") or "").strip()
        if suggested_command:
            summary = f"{summary} Подсказка: {suggested_command}."
        return True, None, summary or f"Primary region focus plan группы {actor_group_key} собран."

    if action == "group_primary_region_route":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        route = get_current_group_primary_region_route(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not route:
            return True, None, f"У группы {actor_group_key} пока нет выраженного primary region route."
        summary = str(route.get("summary") or "").strip()
        suggested_command = str(route.get("suggested_command") or "").strip()
        if suggested_command:
            summary = f"{summary} Подсказка: {suggested_command}."
        return True, None, summary or f"Primary region route группы {actor_group_key} собран."

    if action == "group_region_pursuit_set":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        target_region_id = str(payload.get("target_region_id") or "").strip()
        if not target_region_id:
            return True, "Нужно указать target_region_id для region pursuit.", None
        updated, error = set_group_region_pursuit(
            sess,
            actor_group_key,
            target_region_id,
            player_id=actor_player_id,
            source=source,
        )
        result = (updated or {}).get("last_region_pursuit_result") or get_current_group_last_region_pursuit_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        ) or {}
        if error:
            return True, error, None
        return True, None, str(result.get("result_summary") or f"Region pursuit группы {actor_group_key} обновлён.")

    if action == "group_multi_region_pursuit_set":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        target_region_id = str(payload.get("target_region_id") or "").strip()
        if not target_region_id:
            return True, "Нужно указать target_region_id для multi-region pursuit.", None
        updated, error = set_group_multi_region_pursuit(
            sess,
            actor_group_key,
            target_region_id,
            player_id=actor_player_id,
            source=source,
        )
        result = (updated or {}).get("last_region_pursuit_result") or get_current_group_last_multi_region_pursuit_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        ) or {}
        if error:
            return True, error, None
        return True, None, str(result.get("result_summary") or f"Multi-region pursuit группы {actor_group_key} обновлён.")

    if action == "group_region_pursuit_clear":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        cleared = clear_group_region_pursuit(
            sess,
            actor_group_key,
            source=source,
        )
        result = (cleared or {}).get("last_region_pursuit_result") or get_current_group_last_region_pursuit_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        ) or {}
        if not cleared and not result:
            return True, None, f"У группы {actor_group_key} сейчас нет активного region pursuit."
        return True, None, str(result.get("result_summary") or f"Region pursuit группы {actor_group_key} очищен.")

    if action == "group_region_pursuit_status":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        pursuit = get_current_group_region_pursuit(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        result = get_current_group_last_region_pursuit_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not pursuit and not result:
            return True, None, f"У группы {actor_group_key} сейчас нет активного region pursuit."
        if pursuit:
            return True, None, (
                f"Region pursuit группы {actor_group_key}: "
                f"{str(pursuit.get('target_region_label') or 'регион')} "
                f"({str(pursuit.get('pursuit_status') or 'unknown')}). "
                f"Следующий шаг: {str(pursuit.get('suggested_next_command') or 'нет')}."
            )
        return True, None, (
            f"Последний region pursuit группы {actor_group_key}: "
            f"{str((result or {}).get('target_region_label') or 'регион')} "
            f"({str((result or {}).get('result_type') or 'unknown')})."
        )

    if action == "group_multi_region_pursuit_status":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        pursuit = get_current_group_multi_region_pursuit(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        result = get_current_group_last_multi_region_pursuit_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not pursuit and not result:
            return True, None, f"У группы {actor_group_key} сейчас нет активного multi-region pursuit."
        if pursuit:
            path_labels = " -> ".join(str(item) for item in (pursuit.get("target_region_path_labels") or []) if str(item).strip())
            return True, None, (
                f"Multi-region pursuit группы {actor_group_key}: "
                f"{str(pursuit.get('target_region_label') or 'регион')} "
                f"({str(pursuit.get('known_route_status') or pursuit.get('pursuit_status') or 'unknown')}). "
                f"Следующий hop: {str(pursuit.get('next_hop_region_id') or 'нет')}. "
                f"Маршрут: {path_labels or 'нет'}."
            )
        return True, None, (
            f"Последний multi-region pursuit группы {actor_group_key}: "
            f"{str((result or {}).get('target_region_label') or 'регион')} "
            f"({str((result or {}).get('result_type') or 'unknown')})."
        )

    if action == "group_region_pursuit_advance":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        updated, error = advance_group_region_pursuit(
            sess,
            actor_group_key,
            player_id=actor_player_id,
            source=source,
        )
        result = (updated or {}).get("last_region_pursuit_step_result") or get_current_group_last_region_pursuit_step_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        ) or {}
        if error and not result:
            return True, error, None
        return True, error, str(result.get("result_summary") or error or f"Region pursuit группы {actor_group_key} продвинут на один шаг.")

    if action == "group_region_pursuit_step_status":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        step_result = get_current_group_last_region_pursuit_step_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        pursuit = get_current_group_region_pursuit(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if step_result:
            return True, None, str(step_result.get("result_summary") or step_result.get("summary") or "Последний region pursuit step сохранён.")
        if pursuit:
            return True, None, (
                f"Region pursuit группы {actor_group_key}: "
                f"{str(pursuit.get('target_region_label') or 'регион')} "
                f"({str(pursuit.get('pursuit_status') or 'unknown')}). "
                f"Следующий шаг: {str(pursuit.get('suggested_next_command') or 'нет')}."
            )
        return True, None, f"У группы {actor_group_key} пока нет region pursuit step результата."

    if action == "group_region_onboarding":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        result = get_current_group_last_region_onboarding_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        states = get_current_group_region_onboarding_states(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not result and not states:
            return True, None, f"У группы {actor_group_key} пока нет region onboarding результата."
        latest_state = states[-1] if states else {}
        region_label = str((result or {}).get("region_label") or latest_state.get("region_label") or "регион")
        result_type = str((result or {}).get("result_type") or latest_state.get("status") or "unknown")
        summary = str((result or {}).get("result_summary") or (result or {}).get("summary") or latest_state.get("summary") or "").strip()
        response = f"Region onboarding группы {actor_group_key}: {region_label} ({result_type})."
        if summary:
            response = f"{response} {summary}"
        return True, None, response

    if action == "group_region_transition_status":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        result = get_current_group_last_region_transition_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        state = get_current_group_region_transition_state(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not result and not state:
            return True, None, f"У группы {actor_group_key} пока нет region transition результата."
        return True, None, (
            f"Region transition группы {actor_group_key}: "
            f"{str((result or {}).get('gateway_label') or (state or {}).get('last_gateway_id') or 'gateway')} "
            f"({str((result or {}).get('transition_status') or (state or {}).get('last_result_type') or 'unknown')})."
        )

    if action == "group_region_transition":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        updated, error = resolve_group_region_transition(
            sess,
            actor_group_key,
            str(payload.get("gateway_id") or ""),
            player_id=actor_player_id,
            source=source,
        )
        result = (updated or {}).get("last_region_transition_result") or get_current_group_last_region_transition_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        ) or {}
        if error:
            return True, error, None
        return True, None, str(result.get("result_summary") or f"Переход группы {actor_group_key} выполнен.")

    if action == "group_exploration_leads":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        leads = get_current_group_exploration_leads(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        if not leads:
            return True, None, f"У группы {actor_group_key} сейчас нет явных exploration leads."
        primary = get_current_group_primary_exploration_lead(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        ) or leads[0]
        return True, None, (
            f"Exploration leads группы {actor_group_key}: {len(leads)}. "
            f"Главная зацепка: {str(primary.get('title') or 'lead')}."
        )

    if action == "group_journey_status":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        journey = get_current_group_journey_state(sess, player_id=actor_player_id, group_id=actor_group_key)
        if not journey:
            return True, None, f"У группы {actor_group_key} сейчас нет активного путешествия."
        return True, None, (
            f"Путешествие группы {actor_group_key}: "
            f"{journey.get('journey_status')} к {journey.get('target_node_label')}, "
            f"{journey.get('completed_step_count')}/{journey.get('total_step_count')} шагов."
        )

    if action == "group_journey_set":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        updated, error = set_group_journey_target(
            sess,
            actor_group_key,
            str(payload.get("target_node_id") or ""),
            player_id=actor_player_id,
            source=source,
        )
        if error:
            return True, error, None
        result = (updated or {}).get("last_journey_result") or get_current_group_last_journey_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        ) or {}
        return True, None, str(result.get("result_summary") or f"Путешествие группы {actor_group_key} запланировано.")

    if action == "group_journey_advance":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        updated, error = advance_group_journey(
            sess,
            actor_group_key,
            player_id=actor_player_id,
            source=source,
        )
        if error:
            return True, error, None
        result = (updated or {}).get("last_journey_result") or get_current_group_last_journey_result(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        ) or {}
        return True, None, str(result.get("result_summary") or f"Путешествие группы {actor_group_key} продвинулось.")

    if action == "group_visit_history":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        node_visits = get_current_group_node_visit_states(sess, player_id=actor_player_id, group_id=actor_group_key)
        route_traversals = get_current_group_route_traversal_states(sess, player_id=actor_player_id, group_id=actor_group_key)
        if not node_visits and not route_traversals:
            return True, None, f"У группы {actor_group_key} пока нет истории посещений."
        latest_node = node_visits[-1] if node_visits else None
        latest_route = route_traversals[-1] if route_traversals else None
        latest_label = str((latest_node or {}).get("node_label") or (latest_route or {}).get("route_id") or "история пути")
        return True, None, (
            f"История пути группы {actor_group_key}: "
            f"{len(node_visits)} посещённых точек, {len(route_traversals)} пройденных маршрутов. "
            f"Последнее: {latest_label}."
        )

    if action == "group_route_planning":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        planning = get_current_group_route_planning(
            sess,
            player_id=actor_player_id,
            group_id=actor_group_key,
        )
        reachable = list(planning.get("reachable_destinations") or [])
        frontiers = list(planning.get("route_frontiers") or [])
        if not reachable and not frontiers:
            return True, None, f"У группы {actor_group_key} пока нет доступных маршрутных планов."
        return True, None, (
            f"Маршрутный план группы {actor_group_key}: "
            f"{len(reachable)} достижимых точек, {len(frontiers)} frontier-веток."
        )

    if action == "group_route_plan_to":
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        target_node_id = str(payload.get("target_node_id") or "").strip()
        if not target_node_id:
            return True, "Нужно указать target_node_id для route plan.", None
        plan = get_group_route_plan_to_node(sess, actor_group_key, target_node_id)
        if not plan:
            return True, "Не удалось построить маршрутный план для этой цели.", None
        status = str(plan.get("plan_status") or "").strip()
        target_label = str(plan.get("target_node_label") or target_node_id).strip()
        if status == "current_location":
            return True, None, f"Группа {actor_group_key} уже находится в точке {target_label}."
        if status == "reachable":
            return True, None, (
                f"Путь к {target_label} доступен: "
                f"{int(plan.get('step_count') or 0)} шаг(а/ов), route_ids={plan.get('path_route_ids') or []}."
            )
        if status == "blocked":
            block_reason = str(plan.get("blocked_reason") or "route_blocked").strip()
            return True, None, f"Путь к {target_label} заблокирован: {block_reason}."
        if status == "unrevealed":
            return True, None, f"Точка {target_label} ещё не раскрыта для текущей группы."
        return True, None, str(plan.get("summary") or f"Для точки {target_label} нет корректного route plan.")

    if action in {"group_camp_resolve", "group_rest"}:
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        if action == "group_rest":
            camped = set_group_camp(sess, actor_group_key, source=source, requested_by=actor_id)
            if not camped:
                return True, "Не удалось подготовить группу к отдыху.", None
        updated, error = resolve_group_camp(
            sess,
            actor_group_key,
            player_id=actor_player_id,
            source=source,
        )
        if error:
            return True, error, None
        camp_result = (updated or {}).get("last_camp_result") or {}
        return True, None, str(camp_result.get("result_summary") or f"Группа {actor_group_key} завершила стоянку.")

    if action in {
        "group_move",
        "group_navigate",
        "group_context_action",
        "group_service",
        "group_service_use",
        "group_map_intel",
        "group_node_entry",
        "group_destination_event",
        "group_local_interactions",
        "group_node_progress",
        "group_region_progress",
        "group_exploration_leads",
        "group_journey_set",
        "group_journey_advance",
        "group_journey_status",
        "group_route_planning",
        "group_route_plan_to",
        "group_visit_history",
        "group_enter",
        "group_stop",
        "group_event_resolve",
        "group_event_ignore",
        "group_arrive",
        "group_interrupt",
        "group_pause",
        "group_resume",
        "group_confirm_enter",
        "group_inspect_target",
        "group_bypass",
        "group_resolve_pause",
    }:
        if not actor_group_key:
            return True, "Группа игрока не найдена.", None
        current_group = _get_group_states(sess).get(actor_group_key, {})
        current_travel = current_group.get("travel_state") if isinstance(current_group, dict) else None
        has_active_travel = isinstance(current_travel, dict) and bool(current_travel.get("active"))
        is_paused_travel = has_active_travel and bool(current_travel.get("paused"))
        if action == "group_confirm_enter":
            updated = confirm_group_enter(sess, actor_group_key, player_id=actor_player_id, source=source)
            if not updated:
                return True, "Нечего подтверждать: группе нужен paused travel с требованием enter.", None
            label = str(updated.get("last_travel_resolution", {}).get("target_label") or updated.get("area_label") or "цель")
            return True, None, f"Группа {actor_group_key} подтверждает вход в {label}."
        if action == "group_inspect_target":
            updated = inspect_group_travel_target(sess, actor_group_key, player_id=actor_player_id, source=source)
            if not updated:
                return True, "Нечего осматривать: группе нужен paused travel у точки интереса.", None
            label = str(updated.get("last_travel_resolution", {}).get("target_label") or "цель")
            return True, None, f"Группа {actor_group_key} осматривает {label}."
        if action == "group_bypass":
            updated = bypass_group_travel_pause(sess, actor_group_key, source=source)
            if not updated:
                return True, "Нечего обходить: группе нужен paused travel с blocked route.", None
            label = str(updated.get("last_travel_resolution", {}).get("target_label") or "препятствие")
            return True, None, f"Группа {actor_group_key} обходит препятствие на пути к {label}."
        if action == "group_resolve_pause":
            updated = resolve_group_travel_pause(sess, actor_group_key, source=source)
            if not updated:
                return True, "Не удалось разрешить paused travel группы.", None
            resolution_kind = str(updated.get("last_travel_resolution", {}).get("resolution_kind") or "")
            if resolution_kind == "confirm_enter":
                label = str(updated.get("last_travel_resolution", {}).get("target_label") or updated.get("area_label") or "цель")
                return True, None, f"Группа {actor_group_key} подтверждает вход в {label}."
            if resolution_kind == "inspect_target":
                label = str(updated.get("last_travel_resolution", {}).get("target_label") or "цель")
                return True, None, f"Группа {actor_group_key} осматривает {label}."
            if resolution_kind == "bypass":
                label = str(updated.get("last_travel_resolution", {}).get("target_label") or "препятствие")
                return True, None, f"Группа {actor_group_key} обходит препятствие на пути к {label}."
            return True, None, f"Paused travel группы {actor_group_key} разрешён."
        if action == "group_pause":
            updated = pause_group_travel(sess, actor_group_key, reason="manual", pause_details={"source": source}, resume_allowed=True)
            if not updated:
                return True, "У группы нет активного путешествия для паузы.", None
            return True, None, f"Путешествие группы {actor_group_key} приостановлено."
        if action == "group_resume":
            if not is_paused_travel:
                return True, "У группы нет приостановленного путешествия для возобновления.", None
            updated = resume_group_travel(sess, actor_group_key)
            if not updated:
                return True, "Не удалось возобновить путешествие группы.", None
            return True, None, f"Группа {actor_group_key} продолжает путь."
        if action in {"group_event_resolve", "group_event_ignore"}:
            resolution = "resolve" if action == "group_event_resolve" else "ignore"
            updated, error = resolve_group_travel_event(
                sess,
                actor_group_key,
                resolution=resolution,
                player_id=actor_player_id,
                source=source,
            )
            if error:
                return True, error, None
            event_summary = get_current_group_travel_event(sess, group_id=actor_group_key) or {}
            event_key = str(event_summary.get("event_key") or "travel_event")
            if resolution == "resolve":
                return True, None, f"Группа {actor_group_key} разбирается с дорожным событием: {event_key}."
            return True, None, f"Группа {actor_group_key} игнорирует дорожное событие: {event_key}."
        if action == "group_arrive":
            if is_paused_travel:
                pause_reason = str(current_travel.get("pause_reason") or "").strip().lower()
                if pause_reason == "target_requires_enter":
                    return True, "Путешествие приостановлено: цель требует явного входа. Сначала возобновите движение группы.", None
                return True, "Путешествие группы приостановлено. Сначала возобновите движение группы.", None
            updated = complete_group_travel(sess, actor_group_key, player_id=actor_player_id, source=source)
            if not updated:
                return True, "У группы нет активного путешествия для завершения.", None
            label = str((current_travel or {}).get("route_summary", {}).get("target_label") or updated.get("area_label") or "цель")
            return True, None, f"Группа {actor_group_key} прибыла в {label}."
        if action == "group_interrupt":
            updated = interrupt_group_travel(sess, actor_group_key)
            if not updated:
                return True, "У группы нет активного путешествия для прерывания.", None
            return True, None, f"Группа {actor_group_key} прервала движение."
        if action == "group_stop":
            journey = get_current_group_journey_state(sess, player_id=actor_player_id, group_id=actor_group_key)
            if journey:
                if has_active_travel:
                    interrupt_group_travel(sess, actor_group_key)
                clear_group_movement_intent(sess, actor_group_key)
                cleared = clear_group_journey(sess, actor_group_key, source=source)
                if not cleared:
                    return True, "Не удалось остановить путешествие группы.", None
                return True, None, f"Путешествие группы {actor_group_key} остановлено."
            cleared = interrupt_group_travel(sess, actor_group_key) if has_active_travel else clear_group_movement_intent(sess, actor_group_key)
            if not cleared:
                return True, "Не удалось остановить движение группы.", None
            return True, None, f"Группа {actor_group_key} остановилась."
        if action == "group_navigate":
            target_node_id = str(payload.get("target_node_id") or "").strip()
            updated, error = execute_group_navigation_option(
                sess,
                target_node_id=target_node_id,
                player_id=actor_player_id,
                group_id=actor_group_key,
                movement_mode=payload.get("movement_mode"),
                source=source,
            )
            if error:
                return True, error, None
            label = str((updated or {}).get("movement_intent", {}).get("target_label") or (updated or {}).get("area_label") or "цель")
            action_kind = str((updated or {}).get("movement_intent", {}).get("action_kind") or "move")
            if action_kind == "enter":
                return True, None, f"Группа {actor_group_key} входит в {label}."
            return True, None, f"Группа {actor_group_key} движется к {label}."
        if action == "group_context_action":
            action_key = str(payload.get("action_id") or payload.get("action_key") or "").strip().lower()
            updated, error = execute_current_group_context_action(
                sess,
                action_key=action_key,
                player_id=actor_player_id,
                group_id=actor_group_key,
                payload=payload,
                source=source,
            )
            if error:
                return True, error, None
            if action_key == "navigate":
                label = str((updated or {}).get("movement_intent", {}).get("target_label") or (updated or {}).get("area_label") or "цель")
                action_kind = str((updated or {}).get("movement_intent", {}).get("action_kind") or "move")
                if action_kind == "enter":
                    return True, None, f"Группа {actor_group_key} входит в {label}."
                return True, None, f"Группа {actor_group_key} движется к {label}."
            if action_key == "enter":
                label = str(
                    (updated or {}).get("last_travel_resolution", {}).get("target_label")
                    or (updated or {}).get("area_label")
                    or "цель"
                )
                return True, None, f"Группа {actor_group_key} подтверждает вход в {label}."
            if action_key == "inspect":
                inspect_result = get_current_group_last_inspect_result(
                    sess,
                    player_id=actor_player_id,
                    group_id=actor_group_key,
                ) or {}
                detail = get_current_group_node_detail(
                    sess,
                    player_id=actor_player_id,
                    group_id=actor_group_key,
                ) or {}
                surface = get_current_group_local_interaction_surface(
                    sess,
                    player_id=actor_player_id,
                    group_id=actor_group_key,
                ) or {}
                services = get_current_group_node_services(
                    sess,
                    player_id=actor_player_id,
                    group_id=actor_group_key,
                ) or []
                exploration_leads = get_current_group_exploration_leads(
                    sess,
                    player_id=actor_player_id,
                    group_id=actor_group_key,
                ) or []

                label = str(
                    inspect_result.get("label")
                    or detail.get("label")
                    or (updated or {}).get("last_travel_resolution", {}).get("target_label")
                    or (updated or {}).get("current_map_position", {}).get("label")
                    or (updated or {}).get("area_label")
                    or "место"
                ).strip()

                short_description = str(
                    detail.get("short_description")
                    or inspect_result.get("short_description")
                    or ""
                ).strip()
                inspect_summary = str(inspect_result.get("inspect_summary") or "").strip()
                travel_note = str(
                    inspect_result.get("travel_note")
                    or detail.get("travel_note")
                    or ""
                ).strip()

                service_hints = [
                    str(item).strip()
                    for item in (inspect_result.get("service_hints") or detail.get("service_hints") or [])
                    if str(item or "").strip()
                ]
                state_notes = [
                    str(item).strip()
                    for item in (inspect_result.get("state_notes") or detail.get("state_notes") or [])
                    if str(item or "").strip()
                ]
                visible_npcs = [
                    str(item).strip()
                    for item in (inspect_result.get("visible_npcs") or detail.get("visible_npcs") or [])
                    if str(item or "").strip()
                ]
                visible_objects = [
                    str(item).strip()
                    for item in (inspect_result.get("visible_objects") or detail.get("visible_objects") or [])
                    if str(item or "").strip()
                ]
                visible_threats = [
                    str(item).strip()
                    for item in (inspect_result.get("visible_threats") or detail.get("visible_threats") or [])
                    if str(item or "").strip()
                ]

                available_actions: list[str] = []
                for item in surface.get("available_actions") or []:
                    if not isinstance(item, dict) or item.get("available") is False:
                        continue
                    action_id = str(item.get("action_id") or item.get("action_key") or "").strip().lower()
                    if not action_id:
                        continue
                    if action_id == "inspect":
                        continue
                    title = str(item.get("label") or item.get("action_label") or item.get("title") or "").strip()
                    if not title:
                        title = action_id.replace("_", " ")
                    if title not in available_actions:
                        available_actions.append(title)

                available_services: list[str] = []
                for item in services:
                    if not isinstance(item, dict) or item.get("available") is False:
                        continue
                    service_label = str(item.get("label") or item.get("service_id") or "").strip()
                    if not service_label:
                        continue
                    if service_label not in available_services:
                        available_services.append(service_label)

                current_position = (updated or {}).get("current_map_position")
                current_node_id = ""
                if isinstance(current_position, dict):
                    current_node_id = str(current_position.get("node_id") or "").strip()
                if not current_node_id:
                    current_node_id = str(
                        inspect_result.get("node_id")
                        or detail.get("node_id")
                        or ""
                    ).strip()

                nearby_targets: list[str] = []
                for item in exploration_leads:
                    if not isinstance(item, dict):
                        continue
                    if bool(item.get("blocked")):
                        continue
                    target_node_id = str(item.get("target_node_id") or "").strip()
                    if target_node_id and current_node_id and target_node_id == current_node_id:
                        continue
                    target_label = str(item.get("target_node_label") or "").strip()
                    if not target_label or target_label in nearby_targets:
                        continue
                    nearby_targets.append(target_label)
                    if len(nearby_targets) >= 3:
                        break

                parts: list[str] = [f"{label}."]
                if short_description:
                    parts.append(short_description.rstrip(".") + ".")
                if inspect_summary and inspect_summary != short_description:
                    parts.append(inspect_summary.rstrip(".") + ".")
                if visible_npcs:
                    parts.append(f"Рядом видны: {', '.join(visible_npcs)}.")
                if visible_objects:
                    parts.append(f"В глаза бросается: {', '.join(visible_objects)}.")
                if visible_threats:
                    parts.append(f"Явные угрозы: {', '.join(visible_threats)}.")
                if nearby_targets:
                    parts.append(f"Рядом можно держать путь к: {', '.join(nearby_targets)}.")
                if travel_note:
                    parts.append(f"Ориентир: {travel_note.rstrip('.')}.")
                if available_actions:
                    parts.append(f"Сейчас можно: {', '.join(available_actions)}.")
                if available_services:
                    parts.append(f"Здесь доступны услуги: {', '.join(available_services)}.")
                elif service_hints:
                    parts.append(f"Полезно здесь: {', '.join(service_hints)}.")
                if state_notes:
                    formatted_notes = " ".join(note.rstrip(".") + "." for note in state_notes)
                    parts.append(f"Примечания: {formatted_notes}")

                return True, None, " ".join(parts)
            if action_key == "camp":
                return True, None, f"Группа {actor_group_key} разбила лагерь."
            if action_key == "wait":
                return True, None, f"Группа {actor_group_key} ждёт."
            result = (updated or {}).get("last_context_action_result") if isinstance(updated, dict) else None
            if isinstance(result, dict):
                return True, None, str(result.get("result_summary") or result.get("summary") or f"Группа {actor_group_key} выполняет действие {action_key}.")
            return True, None, f"Группа {actor_group_key} выполняет действие {action_key}."
        if action in {"group_service", "group_service_use"}:
            service_key = str(payload.get("service_id") or payload.get("service_key") or "").strip().lower()
            updated, error = execute_current_group_service(
                sess,
                service_id=service_key,
                player_id=actor_player_id,
                group_id=actor_group_key,
                source=source,
            )
            if error:
                return True, error, None
            label = str(
                (updated or {}).get("last_service_result", {}).get("service_label")
                or (updated or {}).get("last_service_result", {}).get("label")
                or service_key
                or "услуга"
            )
            result = (updated or {}).get("last_service_result") if isinstance(updated, dict) else None
            if isinstance(result, dict):
                return True, None, str(result.get("result_summary") or result.get("summary") or f"Группа {actor_group_key} использует услугу: {label}.")
            return True, None, f"Группа {actor_group_key} использует услугу: {label}."

        target_node = _resolve_group_action_target(
            sess,
            actor_group_id=actor_group_key,
            actor_player_id=actor_player_id,
            payload=payload,
            enter=action == "group_enter",
        )
        if not target_node:
            direct_target = payload.get("target_node") or payload.get("target")
            target_hint = str(payload.get("target_hint") or payload.get("target_label") or "").strip()
            static_match = direct_target if isinstance(direct_target, dict) else resolve_static_map_node(direct_target or target_hint)
            if isinstance(static_match, dict) and static_match.get("node_id"):
                return True, "Группа пока не знает эту точку карты.", None
            return True, "Нужно указать цель движения группы.", None
        route_summary = resolve_group_target_route(
            current_map_position=_get_group_states(sess).get(actor_group_key, {}).get("current_map_position"),
            target_node=target_node,
            action_kind="enter" if action == "group_enter" else "move",
        )
        if route_summary.get("allowed") is not True:
            return True, str(route_summary.get("error") or "Недопустимая цель перемещения группы."), None
        blocked_error = validate_group_route_accessibility(sess, actor_group_key, route_summary)
        if blocked_error:
            return True, blocked_error, None

        movement_mode = str(payload.get("movement_mode") or get_group_movement_mode(sess, actor_group_key) or "normal").strip().lower() or "normal"
        updated = start_group_travel(
            sess,
            actor_group_key,
            route_summary,
            movement_mode=movement_mode,
            source=source,
        )
        if not updated:
            return True, ("Не удалось выполнить вход для группы." if action == "group_enter" else "Не удалось задать движение группы."), None
        updated = evaluate_group_travel_pause(sess, actor_group_key) or updated
        label = str(updated.get("movement_intent", {}).get("target_label") or updated.get("area_label") or "цель")
        if action == "group_enter":
            return True, None, f"Группа {actor_group_key} входит в {label}."
        return True, None, f"Группа {actor_group_key} движется к {label}."

    if action in {"group_wait", "group_camp"}:
        group_id = str(payload.get("group_id") or actor_group_key).strip()
        if not group_id:
            return True, "Группа игрока не найдена.", None
        if actor_group_key != group_id:
            return True, "Можно менять состояние только своей группы.", None
        reason = str(payload.get("reason") or "").strip() or None
        if action == "group_wait":
            updated = set_group_wait(sess, group_id, reason=reason, source=source, requested_by=actor_id)
            if not updated:
                return True, "Не удалось перевести группу в ожидание.", None
            summary = f"Группа {group_id} ждёт."
            if reason:
                summary = f"Группа {group_id} ждёт: {reason}."
            return True, None, summary
        updated = set_group_camp(sess, group_id, reason=reason, source=source, requested_by=actor_id)
        if not updated:
            return True, "Не удалось перевести группу в лагерь.", None
        summary = f"Группа {group_id} разбила лагерь."
        if reason:
            summary = f"Группа {group_id} разбила лагерь: {reason}."
        return True, None, summary

    if action == "group_split":
        source_group_id = str(payload.get("group_id") or actor_group_key).strip()
        if not source_group_id:
            return True, "Группа игрока не найдена.", None
        if actor_group_key != source_group_id:
            return True, "Можно разделить только свою группу.", None
        request = request_group_split(
            source_group_id,
            payload.get("member_player_ids") or [],
            new_group_id=payload.get("new_group_id"),
            source=source,
            requested_by=actor_id,
        )
        if not request:
            return True, "Нужно указать участников для отделения.", None
        created = apply_group_split(sess, request)
        if not created:
            return True, "Не удалось разделить группу.", None
        return True, None, f"Группа {source_group_id} разделена. Новая группа: {created['group_id']}."

    source_group_id = str(payload.get("source_group_id") or "").strip()
    target_group_id = str(payload.get("target_group_id") or actor_group_key).strip()
    if not source_group_id or not target_group_id:
        return True, "Нужно указать группы для объединения.", None
    if actor_group_key not in {source_group_id, target_group_id}:
        return True, "Можно объединять только группы, в одной из которых вы состоите.", None
    request = request_group_merge(
        target_group_id,
        source_group_id,
        source=source,
        requested_by=actor_id,
    )
    if not request:
        return True, "Некорректный запрос на объединение групп.", None
    merged = apply_group_merge(sess, request)
    if not merged:
        return True, "Не удалось объединить группы. Они должны быть в одной точке.", None
    return True, None, f"Группы {source_group_id} и {target_group_id} объединены."


def _verdan_telepathy_status_message(ch: Character) -> tuple[Optional[str], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    telepathy_cfg = _verdan_limited_telepathy_feature(rf)
    if not telepathy_cfg:
        return "Ограниченная телепатия недоступна вашей расе.", None, False
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    target_name = str(runtime.get("verdan_telepathy_last_target") or "").strip()
    if not target_name:
        return None, "[RACE] Ограниченная телепатия готова: 30 фт, простые идеи, цель должна знать язык.", False
    return None, f"[RACE] Ограниченная телепатия: последняя цель — {target_name}.", False


async def _load_feature_gated_character(
    db,
    sess,
    *,
    player: Player,
    feature_getter: Callable[[Any], Any],
    unavailable_message: str,
) -> tuple[bool, Optional[str], Optional[Character], Any]:
    ch = await get_character(db, sess.id, player.id)
    if not ch:
        return True, "Персонаж не найден.", None, None
    feature_cfg = feature_getter(getattr(ch, "race_features", None))
    if not feature_cfg:
        return True, unavailable_message, None, None
    return False, None, ch, feature_cfg


async def _handle_simple_narrative_feature_action(
    db,
    sess,
    *,
    player: Player,
    action_key: str,
    allowed_actions: set[str],
    feature_getter: Callable[[Any], Any],
    unavailable_message: str,
    status_action: str,
    status_message: str,
    message_text: str,
    missing_text_error: str,
    render_message: Callable[[str, str], str],
) -> tuple[bool, Optional[str], Optional[str]]:
    if action_key not in allowed_actions:
        return False, None, None

    handled, error, _ch, _feature_cfg = await _load_feature_gated_character(
        db,
        sess,
        player=player,
        feature_getter=feature_getter,
        unavailable_message=unavailable_message,
    )
    if handled:
        return True, error, None

    if action_key == status_action:
        return True, None, status_message

    text = str(message_text or "").strip()
    if not text:
        return True, missing_text_error, None

    return True, None, render_message(action_key, text)


async def _dispatch_narrow_narrative_utility_action(
    db,
    sess,
    *,
    player: Player,
    session_id: str,
    request_id: Optional[str],
    action: str | None,
    message_text: str,
    handler,
    ws_error_cb,
) -> bool:
    if not action:
        return False

    handled, err, msg = await handler(
        db,
        sess,
        player=player,
        action=action,
        message_text=message_text or "",
    )
    if not handled:
        return False

    if err:
        await ws_error_cb(err, request_id=request_id)
        return True

    if msg:
        actor_name = str(
            getattr((await get_character(db, sess.id, player.id)) or None, "name", "") or player.display_name
        ).strip() or player.display_name
        await add_system_event(db, sess, f"{actor_name}: {msg}")

    await broadcast_state(session_id)
    return True


async def _handle_firbolg_speech_action(
    db,
    sess,
    *,
    player: Player,
    action: str,
    message_text: str = "",
) -> tuple[bool, Optional[str], Optional[str]]:
    action_key = str(action or "").strip().lower()
    return await _handle_simple_narrative_feature_action(
        db,
        sess,
        player=player,
        action_key=action_key,
        allowed_actions={"firbolg_speech_status", "firbolg_speech_beast", "firbolg_speech_plant"},
        feature_getter=_firbolg_speech_feature,
        unavailable_message="Речь зверя и листа недоступна вашей расе.",
        status_action="firbolg_speech_status",
        status_message="[RACE] Речь зверя и листа готова: можно передавать простые идеи зверям и растениям.",
        message_text=message_text,
        missing_text_error="Укажите простую идею после двоеточия.",
        render_message=lambda key, text: (
            f"[RACE] Речь зверя и листа: вы передаёте простую идею "
            f"{'зверю' if key.endswith('beast') else 'растению'}: {text}"
        ),
    )


async def _handle_kenku_mimicry_action(
    db,
    sess,
    *,
    player: Player,
    action: str,
    message_text: str = "",
) -> tuple[bool, Optional[str], Optional[str]]:
    action_key = str(action or "").strip().lower()
    return await _handle_simple_narrative_feature_action(
        db,
        sess,
        player=player,
        action_key=action_key,
        allowed_actions={"kenku_mimicry_status", "kenku_mimicry_voice", "kenku_mimicry_sound"},
        feature_getter=_kenku_mimicry_feature,
        unavailable_message="Подражание недоступно вашей расе.",
        status_action="kenku_mimicry_status",
        status_message="[RACE] Подражание готово: можно имитировать звуки и голоса.",
        message_text=message_text,
        missing_text_error="Укажите звук или фразу после двоеточия.",
        render_message=lambda key, text: (
            f"[RACE] Подражание: вы имитируете {'голос' if key.endswith('voice') else 'звук'}: {text}"
        ),
    )


async def _handle_kenku_expert_forgery_action(
    db,
    sess,
    *,
    player: Player,
    action: str,
    message_text: str = "",
) -> tuple[bool, Optional[str], Optional[str]]:
    action_key = str(action or "").strip().lower()
    return await _handle_simple_narrative_feature_action(
        db,
        sess,
        player=player,
        action_key=action_key,
        allowed_actions={"kenku_forgery_status", "kenku_forgery_copy"},
        feature_getter=_kenku_expert_forgery_feature,
        unavailable_message="Искусный подлог недоступен вашей расе.",
        status_action="kenku_forgery_status",
        status_message="[RACE] Искусный подлог готов: можно тщательно воспроизводить почерк и рисунки по образцу.",
        message_text=message_text,
        missing_text_error="Укажите, что именно вы хотите воспроизвести после двоеточия.",
        render_message=lambda _key, text: f"[RACE] Искусный подлог: вы тщательно воспроизводите {text}.",
    )


async def _handle_loxodon_trunk_action(
    db,
    sess,
    *,
    player: Player,
    action: str,
    message_text: str = "",
) -> tuple[bool, Optional[str], Optional[str]]:
    action_key = str(action or "").strip().lower()
    return await _handle_simple_narrative_feature_action(
        db,
        sess,
        player=player,
        action_key=action_key,
        allowed_actions={"loxodon_trunk_status", "loxodon_trunk_use"},
        feature_getter=_loxodon_trunk_feature,
        unavailable_message="Хобот недоступен вашей расе.",
        status_action="loxodon_trunk_status",
        status_message="[RACE] Хобот готов: можно переносить, толкать, тянуть и выполнять простые бытовые действия; нельзя держать оружие, щит и делать соматические компоненты.",
        message_text=message_text,
        missing_text_error="Опишите простое действие после двоеточия.",
        render_message=lambda _key, text: f"[RACE] Хобот: вы используете хобот, чтобы {text}",
    )


async def _handle_verdan_limited_telepathy_action(
    db,
    sess,
    *,
    player: Player,
    session_id: str,
    action: str,
    target_name: str = "",
    message_text: str = "",
) -> tuple[bool, Optional[str], Optional[str]]:
    action_key = str(action or "").strip().lower()
    if action_key not in {"verdan_telepathy_status", "verdan_telepathy_send"}:
        return False, None, None

    ch = await get_character(db, sess.id, player.id)
    if not ch:
        return True, "Персонаж не найден.", None
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    telepathy_cfg = _verdan_limited_telepathy_feature(rf)
    if not telepathy_cfg:
        return True, "Ограниченная телепатия недоступна вашей расе.", None

    if action_key == "verdan_telepathy_status":
        return True, *_verdan_telepathy_status_message(ch)[:2]

    target_query = str(target_name or "").strip()
    if not target_query:
        return True, "Укажите цель в формате: telepathy send <имя>: <текст>.", None
    text = str(message_text or "").strip()
    if not text:
        return True, "Укажите простую мысль после двоеточия.", None

    uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
    q_norm = target_query.lower()
    best_uid: Optional[int] = None
    best_score = 999
    best_name = ""
    best_player_id = ""
    for uid, (_sp, pl) in uid_map.items():
        if pl.id == player.id:
            continue
        target_ch = chars_by_uid.get(uid)
        name_variants = []
        if target_ch is not None and str(getattr(target_ch, "name", "")).strip():
            name_variants.append(str(target_ch.name).strip())
        if str(getattr(pl, "display_name", "")).strip():
            name_variants.append(str(pl.display_name).strip())
        for variant in name_variants:
            v = variant.lower()
            if v == q_norm:
                score = 0
            elif v.startswith(q_norm):
                score = 1
            elif q_norm in v:
                score = 2
            else:
                continue
            if score < best_score:
                best_score = score
                best_uid = uid
                best_name = variant
                best_player_id = str(pl.id)
            break
    if best_uid is None:
        state = get_combat(session_id)
        if state is not None and state.active:
            for ckey, combatant in (state.combatants or {}).items():
                cname = str(getattr(combatant, "name", "") or "").strip()
                if not cname:
                    continue
                v = cname.lower()
                if v == q_norm or v.startswith(q_norm) or q_norm in v:
                    best_name = cname
                    break
    if not best_name:
        return True, f"Не нашёл цель «{target_query}» в текущей сессии.", None
    if best_player_id and best_player_id == str(player.id):
        return True, "Нельзя направить ограниченную телепатию на себя.", None

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    runtime["verdan_telepathy_last_target"] = best_name
    runtime["verdan_telepathy_last_message"] = text
    runtime["verdan_telepathy_last_used_at"] = utcnow().isoformat()
    rf["runtime"] = runtime
    ch.race_features = rf
    if hasattr(ch, "_sa_instance_state"):
        flag_modified(ch, "race_features")
    await db.commit()
    return True, None, f"[RACE] Ограниченная телепатия → {best_name}: {text}"


def _mind_link_status_message(ch: Character) -> tuple[Optional[str], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    mind_link_cfg = _kalashtar_mind_link_feature(rf)
    if not mind_link_cfg:
        return "Связь разумов недоступна вашей расе.", None, False
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    now_dt = utcnow()
    changed = False
    target_name = str(runtime.get("mind_link_target_name") or runtime.get("mind_link_target_id") or "").strip()
    until_iso = str(runtime.get("mind_link_reply_until") or "").strip()
    until_dt = _parse_iso_datetime(until_iso)
    if target_name and until_iso and (not isinstance(until_dt, datetime) or until_dt < now_dt):
        for key in ("mind_link_target_id", "mind_link_target_name", "mind_link_target_player_id", "mind_link_reply_until"):
            runtime.pop(key, None)
        rf["runtime"] = runtime
        ch.race_features = rf
        changed = True
        target_name = ""
        until_iso = ""
        until_dt = None
    if not target_name:
        return None, "[RACE] Связь разумов: не активна.", changed
    until_hhmm = _mind_link_until_hhmm(until_iso)
    suffix = f" Ответ разрешён до {until_hhmm}." if until_hhmm else ""
    return None, f"[RACE] Связь разумов активна с {target_name}.{suffix}", changed


async def _handle_kalashtar_mind_link_action(
    db,
    sess,
    *,
    player: Player,
    session_id: str,
    combat_action: str,
    raw_text: str,
) -> tuple[bool, Optional[str], Optional[str]]:
    action = str(combat_action or "").strip().lower()
    if action not in {"mind_link_set", "mind_link_clear", "mind_link_say", "mind_link_reply", "mind_link_status"}:
        return False, None, None

    ch = await get_character(db, sess.id, player.id)
    if not ch:
        return True, "Персонаж не найден.", None
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    mind_link_cfg = _kalashtar_mind_link_feature(rf)
    if not mind_link_cfg:
        return True, "Связь разумов недоступна вашей расе.", None

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    now_dt = utcnow()
    def _mark_race_features_modified(entity: Any) -> None:
        if hasattr(entity, "_sa_instance_state"):
            flag_modified(entity, "race_features")

    owner_player_id = str(player.id)
    owner_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name

    # Cleanup expired owner-side link state.
    owner_until_iso = str(runtime.get("mind_link_reply_until") or "").strip()
    owner_until_dt = _parse_iso_datetime(owner_until_iso)
    if owner_until_iso and (not isinstance(owner_until_dt, datetime) or owner_until_dt < now_dt):
        runtime.pop("mind_link_target_id", None)
        runtime.pop("mind_link_target_name", None)
        runtime.pop("mind_link_target_player_id", None)
        runtime.pop("mind_link_reply_until", None)
        rf["runtime"] = runtime
        ch.race_features = rf
        _mark_race_features_modified(ch)
        await db.commit()

    if action == "mind_link_status":
        status_err, status_msg, changed = _mind_link_status_message(ch)
        if changed:
            _mark_race_features_modified(ch)
            await db.commit()
        return True, status_err, status_msg

    if action == "mind_link_clear":
        old_target_player_id = str(runtime.get("mind_link_target_player_id") or "").strip()
        changed = False
        for key in ("mind_link_target_id", "mind_link_target_name", "mind_link_target_player_id", "mind_link_reply_until"):
            if key in runtime:
                runtime.pop(key, None)
                changed = True
        rf["runtime"] = runtime
        ch.race_features = rf
        if changed:
            _mark_race_features_modified(ch)

        uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
        if old_target_player_id:
            for uid, (_sp, _pl) in uid_map.items():
                target_ch = chars_by_uid.get(uid)
                if target_ch is None:
                    continue
                if str(getattr(target_ch, "player_id", "")) != old_target_player_id:
                    continue
                if _clear_kalashtar_reply_grant(target_ch, owner_player_id=owner_player_id):
                    _mark_race_features_modified(target_ch)
                    changed = True
                break
        if changed:
            await db.commit()
            return True, None, "Связь разумов: разорвана."
        return True, None, "Связь разумов уже не активна."

    if action == "mind_link_set":
        target_query = _extract_mind_link_target(raw_text)
        if not target_query:
            return True, "Укажите цель: «связь разумов с <имя>».", None
        q_norm = target_query.lower()

        uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
        best_uid: Optional[int] = None
        best_score = 999
        best_name = ""
        best_player_id = ""
        for uid, (_sp, pl) in uid_map.items():
            if pl.id == player.id:
                continue
            target_ch = chars_by_uid.get(uid)
            name_variants = []
            if target_ch is not None and str(getattr(target_ch, "name", "")).strip():
                name_variants.append(str(target_ch.name).strip())
            if str(getattr(pl, "display_name", "")).strip():
                name_variants.append(str(pl.display_name).strip())
            for variant in name_variants:
                v = variant.lower()
                if v == q_norm:
                    score = 0
                elif v.startswith(q_norm):
                    score = 1
                elif q_norm in v:
                    score = 2
                else:
                    continue
                if score < best_score:
                    best_score = score
                    best_uid = uid
                    best_name = variant
                    best_player_id = str(pl.id)
                break

        target_id = ""
        target_name = ""
        target_player_id = ""
        target_char: Optional[Character] = None
        if best_uid is not None:
            target_id = f"pc_{best_uid}"
            target_name = best_name or target_id
            target_player_id = best_player_id
            target_char = chars_by_uid.get(best_uid)
        else:
            state = get_combat(session_id)
            if state is not None and state.active:
                for ckey, combatant in (state.combatants or {}).items():
                    cname = str(getattr(combatant, "name", "") or "").strip()
                    if not cname:
                        continue
                    v = cname.lower()
                    if v == q_norm or v.startswith(q_norm) or q_norm in v:
                        target_id = str(ckey)
                        target_name = cname
                        break
            if not target_id:
                return True, f"Не нашёл цель «{target_query}» в текущей сессии.", None
        if target_player_id and target_player_id == owner_player_id:
            return True, "Нельзя установить связь разумов с собой.", None

        old_target_player_id = str(runtime.get("mind_link_target_player_id") or "").strip()
        old_target_id = str(runtime.get("mind_link_target_id") or "").strip()
        old_target_name = str(runtime.get("mind_link_target_name") or old_target_id or "").strip()
        changed = False

        if target_char is not None:
            target_rf = getattr(target_char, "race_features", None)
            target_rf_dict = dict(target_rf) if isinstance(target_rf, dict) else {}
            target_runtime_raw = target_rf_dict.get("runtime")
            target_runtime = dict(target_runtime_raw) if isinstance(target_runtime_raw, dict) else {}
            can_reply_until_iso = str(target_runtime.get("mind_link_can_reply_until") or "").strip()
            can_reply_until_dt = _parse_iso_datetime(can_reply_until_iso)
            can_reply_owner = str(target_runtime.get("mind_link_can_reply_to") or "").strip()
            if can_reply_owner and can_reply_owner != owner_player_id and isinstance(can_reply_until_dt, datetime) and can_reply_until_dt >= now_dt:
                return True, f"{target_name}: сейчас отвечает телепатически другому собеседнику.", None

        runtime["mind_link_target_id"] = target_id
        runtime["mind_link_target_name"] = target_name
        runtime["mind_link_target_player_id"] = target_player_id
        runtime["mind_link_reply_until"] = (now_dt + timedelta(hours=1)).isoformat()
        runtime["mind_link_last_set_at"] = now_dt.isoformat()
        rf["runtime"] = runtime
        ch.race_features = rf
        _mark_race_features_modified(ch)
        changed = True

        if old_target_player_id and old_target_player_id != target_player_id:
            for uid, (_sp, _pl) in uid_map.items():
                prev_target_ch = chars_by_uid.get(uid)
                if prev_target_ch is None:
                    continue
                if str(getattr(prev_target_ch, "player_id", "")) != old_target_player_id:
                    continue
                if _clear_kalashtar_reply_grant(prev_target_ch, owner_player_id=owner_player_id):
                    _mark_race_features_modified(prev_target_ch)
                    changed = True
                break
        elif old_target_id and old_target_id != target_id and not target_player_id:
            # Fallback cleanup for stale owner pointer to non-player targets.
            runtime.pop("mind_link_target_player_id", None)

        if target_char is not None:
            target_rf = getattr(target_char, "race_features", None)
            target_rf_dict = dict(target_rf) if isinstance(target_rf, dict) else {}
            target_runtime_raw = target_rf_dict.get("runtime")
            target_runtime = dict(target_runtime_raw) if isinstance(target_runtime_raw, dict) else {}
            target_runtime["mind_link_can_reply_to"] = owner_player_id
            target_runtime["mind_link_can_reply_to_name"] = owner_name
            target_runtime["mind_link_can_reply_until"] = runtime["mind_link_reply_until"]
            target_rf_dict["runtime"] = target_runtime
            target_char.race_features = target_rf_dict
            _mark_race_features_modified(target_char)
            changed = True

        if changed:
            await db.commit()
        until_hhmm = _mind_link_until_hhmm(str(runtime.get("mind_link_reply_until") or ""))
        if old_target_name and old_target_name != target_name:
            return True, None, f"Связь разумов: переключена с {old_target_name} на {target_name}. Ответ разрешён до {until_hhmm or '1 часа'}."
        return True, None, f"Связь разумов: установлена с {target_name}. Ответ разрешён до {until_hhmm or '1 часа'}."

    if action == "mind_link_say":
        text = _extract_mind_link_text(raw_text, reply=False)
        if not text:
            return True, "Используйте формат: «телепатия: <текст>».", None
        target_id = str(runtime.get("mind_link_target_id") or "").strip()
        target_name = str(runtime.get("mind_link_target_name") or "").strip() or target_id
        reply_until_iso = str(runtime.get("mind_link_reply_until") or "").strip()
        reply_until_dt = _parse_iso_datetime(reply_until_iso)
        if not target_id:
            return True, "Сначала установите связь: «связь разумов с <имя>».", None
        if not isinstance(reply_until_dt, datetime) or reply_until_dt < now_dt:
            runtime.pop("mind_link_target_id", None)
            runtime.pop("mind_link_target_name", None)
            runtime.pop("mind_link_target_player_id", None)
            runtime.pop("mind_link_reply_until", None)
            rf["runtime"] = runtime
            ch.race_features = rf
            _mark_race_features_modified(ch)
            await db.commit()
            return True, "Окно ответа по связи разумов истекло. Установите связь заново.", None
        return True, None, f"(Телепатия → {target_name or target_id}): {text}"

    # mind_link_reply
    reply_text = _extract_mind_link_text(raw_text, reply=True)
    if not reply_text:
        return True, "Используйте формат: «ответ мысленно: <текст>».", None
    grant_owner = str(runtime.get("mind_link_can_reply_to") or "").strip()
    grant_owner_name = str(runtime.get("mind_link_can_reply_to_name") or "").strip() or "калаштар"
    grant_until_iso = str(runtime.get("mind_link_can_reply_until") or "").strip()
    grant_until_dt = _parse_iso_datetime(grant_until_iso)
    if not grant_owner:
        return True, "Сейчас вам некому отвечать телепатически.", None
    if not isinstance(grant_until_dt, datetime) or grant_until_dt < now_dt:
        _clear_kalashtar_reply_grant(ch)
        _mark_race_features_modified(ch)
        await db.commit()
        return True, "Окно телепатического ответа истекло.", None
    return True, None, f"(Телепатический ответ → {grant_owner_name}): {reply_text}"
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


def _hexblood_eerie_token_feature(ch: Character) -> dict[str, Any]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    eerie_raw = features.get("eerie_token")
    eerie = dict(eerie_raw) if isinstance(eerie_raw, dict) else {}
    if eerie:
        return eerie
    return {}


def _hexblood_eerie_token_state(ch: Character) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    return rf, runtime, _hexblood_eerie_token_feature(ch)


def _eerie_token_created_label(iso_value: str) -> str:
    dt = _parse_iso_datetime(iso_value)
    if not isinstance(dt, datetime):
        return "—"
    return dt.astimezone().strftime("%d.%m.%Y %H:%M")


def _eerie_token_status_message(ch: Character) -> tuple[Optional[str], Optional[str], bool]:
    _rf, runtime, eerie_cfg = _hexblood_eerie_token_state(ch)
    if not eerie_cfg:
        return "Жуткий сувенир доступен только ведьминой крови.", None, False
    token_id = str(runtime.get("eerie_token_id") or "").strip()
    active = bool(runtime.get("eerie_token_active"))
    consumed = bool(runtime.get("eerie_token_consumed"))
    sense_active = bool(runtime.get("eerie_token_sense_active"))
    created_at = str(runtime.get("eerie_token_created_at") or "").strip()
    uses_max = max(1, as_int(eerie_cfg.get("uses_max"), 1))
    uses_used = max(0, as_int(runtime.get("eerie_token_uses_used"), 0))
    rounds_left = max(0, as_int(runtime.get("eerie_token_remote_view_rounds_left"), 0))
    if sense_active:
        status = "сенсорная связь активна"
    elif active:
        status = "активен"
    elif consumed:
        status = "уничтожен"
    elif token_id:
        status = "сохранён, но не активен"
    else:
        status = "не создан"
    suffix = ""
    if rounds_left > 0:
        suffix = f"; восприятие осталось на {rounds_left} раунд."
    return (
        None,
        (
            "[RACE] Жуткий сувенир. "
            f"Статус: {status}; ID: {token_id or '—'}; "
            f"создан: {_eerie_token_created_label(created_at)}; "
            f"сенсорная связь: {'да' if sense_active else 'нет'}; "
            f"использовано {uses_used}/{uses_max}{suffix}"
        ),
        False,
    )


def _create_eerie_token(ch: Character, *, now: Optional[datetime] = None) -> tuple[Optional[str], Optional[str], bool]:
    rf, runtime, eerie_cfg = _hexblood_eerie_token_state(ch)
    if not eerie_cfg:
        return "Жуткий сувенир доступен только ведьминой крови.", None, False
    uses_max = max(1, as_int(eerie_cfg.get("uses_max"), 1))
    used = max(0, as_int(runtime.get("eerie_token_uses_used"), 0))
    active = bool(runtime.get("eerie_token_active")) and not bool(runtime.get("eerie_token_consumed"))
    current_id = str(runtime.get("eerie_token_id") or "").strip()
    replacing = active and bool(current_id)
    if used >= uses_max and not replacing:
        return "Жуткий сувенир уже использован до долгого отдыха.", None, False
    token_id = f"et_{uuid.uuid4().hex[:8]}"
    now_dt = now if isinstance(now, datetime) else utcnow()
    if not replacing:
        runtime["eerie_token_uses_used"] = used + 1
    runtime["eerie_token_id"] = token_id
    runtime["eerie_token_active"] = True
    runtime["eerie_token_consumed"] = False
    runtime["eerie_token_created_at"] = now_dt.isoformat()
    runtime["eerie_token_last_message"] = ""
    runtime["eerie_token_sense_active"] = False
    runtime["eerie_token_remote_view_rounds_left"] = 0
    runtime["eerie_token_expires_on_next_long_rest"] = True
    rf["runtime"] = runtime
    ch.race_features = rf
    action = "заменён" if replacing else "создан"
    remaining = max(0, uses_max - max(0, as_int(runtime.get("eerie_token_uses_used"), 0)))
    return None, f"[RACE] Жуткий сувенир {action}. ID: {token_id}. Осталось использований: {remaining}/{uses_max}.", True


def _remove_eerie_token(ch: Character) -> tuple[Optional[str], Optional[str], bool]:
    rf, runtime, eerie_cfg = _hexblood_eerie_token_state(ch)
    if not eerie_cfg:
        return "Жуткий сувенир доступен только ведьминой крови.", None, False
    token_id = str(runtime.get("eerie_token_id") or "").strip()
    active = bool(runtime.get("eerie_token_active"))
    consumed = bool(runtime.get("eerie_token_consumed"))
    sense_active = bool(runtime.get("eerie_token_sense_active"))
    if not token_id and not active and not consumed and not sense_active:
        return "Нет активного или сохранённого Жуткого сувенира.", None, False
    for key in (
        "eerie_token_id",
        "eerie_token_active",
        "eerie_token_consumed",
        "eerie_token_created_at",
        "eerie_token_last_message",
        "eerie_token_sense_active",
        "eerie_token_remote_view_rounds_left",
    ):
        if key in runtime:
            runtime.pop(key, None)
    rf["runtime"] = runtime
    ch.race_features = rf
    return None, f"[RACE] Жуткий сувенир удалён. Последний ID: {token_id or '—'}.", True


def _send_eerie_token_message(ch: Character, message: str) -> tuple[Optional[str], Optional[str], bool]:
    rf, runtime, eerie_cfg = _hexblood_eerie_token_state(ch)
    if not eerie_cfg:
        return "Жуткий сувенир доступен только ведьминой крови.", None, False
    if not bool(runtime.get("eerie_token_active")) or bool(runtime.get("eerie_token_consumed")):
        return "Нет активного Жуткого сувенира.", None, False
    text = str(message or "").strip()
    if not text:
        return "Укажите текст сообщения после `eerie token send`.", None, False
    words = [w for w in re.findall(r"\S+", text) if w.strip()]
    max_words = max(1, as_int(eerie_cfg.get("message_words_max"), 25))
    if len(words) > max_words:
        return f"Сообщение слишком длинное: максимум {max_words} слов.", None, False
    runtime["eerie_token_last_message"] = text
    rf["runtime"] = runtime
    ch.race_features = rf
    return None, "[RACE] Сообщение отправлено через Жуткий сувенир.", True


def _activate_eerie_token_sense(
    ch: Character,
    *,
    in_combat: bool = False,
) -> tuple[Optional[str], Optional[str], bool]:
    rf, runtime, eerie_cfg = _hexblood_eerie_token_state(ch)
    if not eerie_cfg:
        return "Жуткий сувенир доступен только ведьминой крови.", None, False
    if not bool(runtime.get("eerie_token_active")) or bool(runtime.get("eerie_token_consumed")):
        return "Нет активного Жуткого сувенира.", None, False
    runtime["eerie_token_active"] = False
    runtime["eerie_token_consumed"] = True
    runtime["eerie_token_sense_active"] = True
    runtime["eerie_token_remote_view_rounds_left"] = 10 if in_combat else 0
    rf["runtime"] = runtime
    ch.race_features = rf
    if in_combat:
        return None, "[RACE] Сенсорная связь через Жуткий сувенир активирована на 1 минуту. Сувенир уничтожен.", True
    return None, "[RACE] Сенсорная связь через Жуткий сувенир активирована. Сувенир уничтожен.", True


def _parse_eerie_token_command(cmdline: str) -> tuple[str | None, str | None]:
    txt = str(cmdline or "").strip()
    if not txt:
        return None, None
    lowered = txt.lower()
    if lowered == "eerie token create":
        return "create", None
    if lowered == "eerie token status":
        return "status", None
    if lowered == "eerie token remove":
        return "remove", None
    if lowered == "eerie token sense":
        return "sense", None
    if lowered.startswith("eerie token send "):
        return "send", txt[len("eerie token send "):].strip()
    return None, None


def _mode_with_poisoned_disadvantage(mode: str, race_features: Any) -> str:
    mode_norm = str(mode or "normal").strip().lower()
    if mode_norm not in {"normal", "advantage", "disadvantage"}:
        mode_norm = "normal"
    if not isinstance(race_features, dict):
        return mode_norm
    runtime_raw = race_features.get("runtime")
    runtime = runtime_raw if isinstance(runtime_raw, dict) else {}
    conditions_raw = runtime.get("conditions")
    conditions = conditions_raw if isinstance(conditions_raw, dict) else {}
    poisoned_raw = conditions.get("poisoned")
    poisoned = poisoned_raw if isinstance(poisoned_raw, dict) else {}
    poisoned_active = bool(poisoned.get("active")) or max(0, as_int(poisoned.get("remaining_rounds"), 0)) > 0
    if not poisoned_active:
        return mode_norm
    if mode_norm == "advantage":
        return "normal"
    return "disadvantage"


def _has_sunlight_sensitivity_feature(race_features: Any) -> bool:
    if not isinstance(race_features, dict):
        return False
    features_raw = race_features.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    sunlight = features.get("sunlight_sensitivity")
    if isinstance(sunlight, list):
        return len(sunlight) > 0
    if isinstance(sunlight, dict):
        return True
    return bool(sunlight)


def _mode_with_sunlight_disadvantage(
    mode: str,
    race_features: Any,
    *,
    sunlight_bright: bool,
    check_name: str = "",
) -> str:
    mode_norm = str(mode or "normal").strip().lower()
    if mode_norm not in {"normal", "advantage", "disadvantage"}:
        mode_norm = "normal"
    if not sunlight_bright:
        return mode_norm
    if not _has_sunlight_sensitivity_feature(race_features):
        return mode_norm
    check_key = str(check_name or "").strip().lower()
    if check_key and check_key not in {"perception", "wisdom (perception)"}:
        return mode_norm
    if mode_norm == "advantage":
        return "normal"
    return "disadvantage"


def _mode_with_keen_smell_advantage(
    mode: str,
    race_features: Any,
    *,
    check_name: str,
    check_tag: str = "",
) -> str:
    mode_norm = str(mode or "normal").strip().lower()
    if mode_norm not in {"normal", "advantage", "disadvantage"}:
        mode_norm = "normal"
    if str(check_tag or "").strip().lower() != "smell":
        return mode_norm
    name_key = str(check_name or "").strip().lower()
    if name_key not in {"perception", "survival", "investigation"}:
        return mode_norm
    if not isinstance(race_features, dict):
        return mode_norm
    features_raw = race_features.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    keen_smell_raw = features.get("keen_smell")
    keen_smell = keen_smell_raw if isinstance(keen_smell_raw, dict) else {}
    checks_raw = keen_smell.get("checks")
    checks = [str(x or "").strip().lower() for x in checks_raw] if isinstance(checks_raw, list) else []
    if f"{name_key}_smell" not in checks:
        return mode_norm
    if mode_norm == "disadvantage":
        return "normal"
    return "advantage"


def _mode_with_shifter_wildhunt_advantage(
    mode: str,
    race_features: Any,
    *,
    check_name: str,
    kind: str,
) -> str:
    mode_norm = str(mode or "normal").strip().lower()
    if mode_norm not in {"normal", "advantage", "disadvantage"}:
        mode_norm = "normal"
    if not isinstance(race_features, dict):
        return mode_norm
    subrace_raw = race_features.get("subrace")
    subrace = subrace_raw if isinstance(subrace_raw, dict) else {}
    choices_raw = race_features.get("choices")
    choices = choices_raw if isinstance(choices_raw, dict) else {}
    subrace_key = str(subrace.get("key") or choices.get("subrace_id") or "").strip().lower()
    if subrace_key != "wildhunt":
        return mode_norm
    features_raw = race_features.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    defense_raw = features.get("shifting_defense")
    defense = defense_raw if isinstance(defense_raw, dict) else {}
    advantage_on = [str(x or "").strip().lower() for x in (defense.get("advantage_on") if isinstance(defense.get("advantage_on"), list) else [])]
    if "wis_checks" not in advantage_on:
        return mode_norm
    runtime_raw = race_features.get("runtime")
    runtime = runtime_raw if isinstance(runtime_raw, dict) else {}
    if not bool(runtime.get("shifted_active")):
        return mode_norm
    check_key = str(check_name or "").strip().lower()
    kind_key = str(kind or "").strip().lower()
    is_wis = check_key == "wis"
    if kind_key == "skill":
        is_wis = str(SKILL_TO_ABILITY.get(check_key) or "").strip().lower() == "wis"
    if not is_wis:
        return mode_norm
    if mode_norm == "disadvantage":
        return "normal"
    return "advantage"


def _set_sunlight_bright_for_session_combatants(session_id: str, *, sunlight_bright: bool) -> bool:
    state = get_combat(session_id)
    if state is None or not state.active:
        return False
    changed = False
    for combatant in state.combatants.values():
        race_features = combatant.race_features if isinstance(getattr(combatant, "race_features", None), dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        current = bool(runtime.get("sunlight_bright"))
        if current == bool(sunlight_bright):
            continue
        runtime["sunlight_bright"] = bool(sunlight_bright)
        race_features["runtime"] = runtime
        combatant.race_features = race_features
        changed = True
    return changed


def _has_hare_trigger_feature(race_features: Any) -> bool:
    if not isinstance(race_features, dict):
        return False
    features_raw = race_features.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    return isinstance(features.get("hare_trigger"), dict)


def _roll_initiative_details(ch: Character | None, *, rng: Any = None) -> tuple[int, int, int, int]:
    dex = 50
    level = 1
    race_features: Any = {}
    if ch is not None:
        level = max(1, as_int(getattr(ch, "level", 1), 1))
        stats = ch.stats
        if isinstance(stats, dict):
            dex_raw = stats.get("dex", 50)
            if isinstance(dex_raw, int):
                dex = int(dex_raw)
        race_features = getattr(ch, "race_features", None)
    dex_mod = ability_mod_from_stat100(dex)
    base = roll_initiative(dex, rng=(rng if rng is not None else random))
    bonus = proficiency_bonus(level) if _has_hare_trigger_feature(race_features) else 0
    return base + bonus, base, dex_mod, bonus


def _roll_initiative_with_racial_bonus(ch: Character | None, *, rng: Any = None) -> tuple[int, int]:
    total, _base, _dex_mod, bonus = _roll_initiative_details(ch, rng=rng)
    return total, bonus


def _format_initiative_roll_line(name: str, *, total: int, base: int, dex_mod: int, hare_bonus: int) -> str:
    d20_roll = base - dex_mod
    parts = [f"d20({d20_roll})", f"ЛОВ {dex_mod:+d}"]
    if hare_bonus > 0:
        parts.append(f"Заячье сердце {hare_bonus:+d}")
    return f"{name}: {' + '.join(parts)} = {total}"


def _harengon_mark_failed_dex_save_context(
    *,
    session_id: str,
    player_uid: int | None,
    ch: Character,
    dc: int,
    total: int,
) -> bool:
    if player_uid is None:
        return False
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    lucky_cfg = features.get("lucky_footwork")
    if not isinstance(lucky_cfg, dict):
        return False
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    runtime["last_failed_dex_save"] = {
        "dc": max(0, int(dc)),
        "total": int(total),
        "at": utcnow().isoformat(),
    }
    rf["runtime"] = runtime
    ch.race_features = rf

    state = get_combat(session_id)
    if state is not None and state.active:
        actor_key = f"pc_{player_uid}"
        actor = state.combatants.get(actor_key)
        if actor is not None:
            actor_rf = actor.race_features if isinstance(actor.race_features, dict) else {}
            actor_runtime_raw = actor_rf.get("runtime")
            actor_runtime = dict(actor_runtime_raw) if isinstance(actor_runtime_raw, dict) else {}
            actor_runtime["last_failed_dex_save"] = {
                "dc": max(0, int(dc)),
                "total": int(total),
                "at": utcnow().isoformat(),
            }
            actor_rf["runtime"] = actor_runtime
            actor.race_features = actor_rf
    return True


def _hobgoblin_allies_within_30ft_for_combatant(session_id: str, actor_key: str) -> int:
    state = get_combat(session_id)
    if state is None or not state.active:
        return 0
    actor = state.combatants.get(actor_key)
    if actor is None:
        return 0
    side = str(getattr(actor, "side", "")).strip().lower()
    if not side:
        return 0
    allies = 0
    for key, combatant in (state.combatants or {}).items():
        if combatant is None or str(key or "") == actor_key:
            continue
        if str(getattr(combatant, "side", "")).strip().lower() != side:
            continue
        if int(getattr(combatant, "hp_current", 0) or 0) <= 0 or bool(getattr(combatant, "is_dead", False)):
            continue
        allies += 1
    return allies


def _hobgoblin_mark_saving_face_pending(
    *,
    session_id: str,
    player_uid: int | None,
    ch: Character,
    kind: str,
    dc: int,
    total: int,
    details: dict[str, Any] | None = None,
) -> int:
    if player_uid is None:
        return 0
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    saving_face_cfg = features.get("saving_face")
    if not isinstance(saving_face_cfg, dict):
        return 0
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    uses_used = max(0, as_int(runtime.get("saving_face_uses_used"), 0))
    uses_max = max(1, as_int(saving_face_cfg.get("uses_max"), 1))
    if uses_used >= uses_max:
        return 0

    actor_key = f"pc_{player_uid}"
    state = get_combat(session_id)
    actor = state.combatants.get(actor_key) if state is not None and state.active else None
    if actor is not None and not bool(getattr(actor, "reaction_available", True)):
        return 0
    if actor is None:
        return 0

    pending = {
        "kind": str(kind or "").strip().lower(),
        "dc": max(0, int(dc)),
        "total": int(total),
        "at": utcnow().isoformat(),
        "details": dict(details) if isinstance(details, dict) else {},
    }
    runtime["saving_face_pending"] = pending
    rf["runtime"] = runtime
    ch.race_features = rf

    actor_rf = actor.race_features if isinstance(actor.race_features, dict) else {}
    actor_runtime_raw = actor_rf.get("runtime")
    actor_runtime = dict(actor_runtime_raw) if isinstance(actor_runtime_raw, dict) else {}
    actor_runtime["saving_face_pending"] = pending
    actor_rf["runtime"] = actor_runtime
    actor.race_features = actor_rf

    allies = _hobgoblin_allies_within_30ft_for_combatant(session_id, actor_key)
    return min(max(0, allies), 5)


def _kender_mark_fearless_pending(
    *,
    session_id: str,
    player_uid: int | None,
    ch: Character,
    dc: int,
    total: int,
    ability: str,
    vs_tag: str,
) -> bool:
    if player_uid is None:
        return False
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    fearless_cfg = features.get("fearless_vs_frightened")
    if not isinstance(fearless_cfg, dict):
        return False
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    uses_used = max(0, as_int(runtime.get("fearless_auto_success_used"), 0))
    uses_max = max(1, as_int(fearless_cfg.get("auto_success_max"), 1))
    if uses_used >= uses_max:
        return False
    actor_key = f"pc_{player_uid}"
    state = get_combat(session_id)
    actor = state.combatants.get(actor_key) if state is not None and state.active else None
    if actor is None:
        return False
    if not bool(getattr(actor, "reaction_available", True)):
        return False
    pending = {
        "kind": "save",
        "dc": max(0, int(dc)),
        "total": int(total),
        "ability": str(ability or "").strip().lower(),
        "vs_tag": str(vs_tag or "").strip().lower(),
        "at": utcnow().isoformat(),
    }
    runtime["fearless_pending_failed_frightened_save"] = pending
    rf["runtime"] = runtime
    ch.race_features = rf

    actor_rf = actor.race_features if isinstance(actor.race_features, dict) else {}
    actor_runtime_raw = actor_rf.get("runtime")
    actor_runtime = dict(actor_runtime_raw) if isinstance(actor_runtime_raw, dict) else {}
    actor_runtime["fearless_pending_failed_frightened_save"] = pending
    actor_rf["runtime"] = actor_runtime
    actor.race_features = actor_rf
    return True


def _sync_character_runtime_to_combat_actor(session_id: str, player_uid: int | None, runtime: dict[str, Any]) -> None:
    if player_uid is None:
        return
    state = get_combat(session_id)
    if state is None or not state.active:
        return
    actor = state.combatants.get(f"pc_{player_uid}")
    if actor is None:
        return
    actor_rf = actor.race_features if isinstance(actor.race_features, dict) else {}
    actor_runtime = dict(actor_rf.get("runtime")) if isinstance(actor_rf.get("runtime"), dict) else {}
    runtime_keys = {
        "knowledge_past_life_uses_used",
        "knowledge_past_life_armed",
        "knowledge_from_a_past_life_pending",
        "knowledge_from_a_past_life_last_result",
        "last_failed_dex_save",
        "last_dex_save_result",
    }
    for key in runtime_keys:
        if key in runtime:
            actor_runtime[key] = runtime[key]
        else:
            actor_runtime.pop(key, None)
    if actor_runtime:
        actor_rf["runtime"] = actor_runtime
    else:
        actor_rf.pop("runtime", None)
    actor.race_features = actor_rf


def _reborn_past_life_feature(ch: Character) -> dict[str, Any]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    feature_raw = features.get("knowledge_from_a_past_life")
    return dict(feature_raw) if isinstance(feature_raw, dict) else {}


def _reborn_past_life_uses_max(ch: Character, feature: dict[str, Any] | None = None) -> int:
    cfg = feature if isinstance(feature, dict) else _reborn_past_life_feature(ch)
    if not cfg:
        return 0
    formula = str(cfg.get("uses_formula") or "").strip().lower()
    if formula == "proficiency_bonus":
        level = max(1, as_int(getattr(ch, "level", 1), 1))
        return max(1, int(proficiency_bonus(level)))
    uses_max = max(0, as_int(cfg.get("uses_max"), 0))
    return uses_max


def _reborn_mark_past_life_pending(
    *,
    session_id: str,
    player_uid: int | None,
    ch: Character,
    dc: int,
    total: int,
    skill_key: str,
) -> bool:
    feature = _reborn_past_life_feature(ch)
    if not feature:
        return False
    uses_max = _reborn_past_life_uses_max(ch, feature)
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime = dict(rf.get("runtime")) if isinstance(rf.get("runtime"), dict) else {}
    used = max(0, as_int(runtime.get("knowledge_past_life_uses_used"), 0))
    if uses_max <= 0 or used >= uses_max:
        return False
    pending = {
        "kind": "skill",
        "dc": max(0, int(dc)),
        "total": int(total),
        "skill": str(skill_key or "").strip().lower(),
        "at": utcnow().isoformat(),
    }
    runtime["knowledge_from_a_past_life_pending"] = pending
    rf["runtime"] = runtime
    ch.race_features = rf
    _sync_character_runtime_to_combat_actor(session_id, player_uid, runtime)
    return True


def _apply_or_arm_reborn_past_life_knowledge(
    *,
    session_id: str,
    player_uid: int | None,
    ch: Character,
) -> tuple[Optional[str], Optional[str], bool]:
    feature = _reborn_past_life_feature(ch)
    if not feature:
        return "Знания из прошлой жизни недоступны вашей расе.", None, False

    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime = dict(rf.get("runtime")) if isinstance(rf.get("runtime"), dict) else {}
    uses_max = _reborn_past_life_uses_max(ch, feature)
    used = max(0, as_int(runtime.get("knowledge_past_life_uses_used"), 0))
    if uses_max <= 0 or used >= uses_max:
        return "Знания из прошлой жизни уже использованы до долгого отдыха.", None, False

    pending = dict(runtime.get("knowledge_from_a_past_life_pending")) if isinstance(runtime.get("knowledge_from_a_past_life_pending"), dict) else {}
    if pending:
        bonus = random.randint(1, 6)
        total_before = int(pending.get("total") or 0)
        dc = max(0, int(pending.get("dc") or 0))
        total_after = total_before + bonus
        runtime["knowledge_past_life_uses_used"] = used + 1
        runtime["knowledge_past_life_armed"] = False
        runtime.pop("knowledge_from_a_past_life_pending", None)
        runtime["knowledge_from_a_past_life_last_result"] = {
            **pending,
            "bonus": bonus,
            "total_after": total_after,
            "success": total_after >= dc if dc > 0 else True,
            "resolved_at": utcnow().isoformat(),
        }
        rf["runtime"] = runtime
        ch.race_features = rf
        _sync_character_runtime_to_combat_actor(session_id, player_uid, runtime)
        outcome = "УСПЕХ" if dc > 0 and total_after >= dc else "FAIL"
        skill_key = str(pending.get("skill") or "").strip().lower()
        return None, f"Знания из прошлой жизни: +1d6 ({bonus}) к {skill_key} => {total_after} (DC {dc}) {outcome}", True

    if bool(runtime.get("knowledge_past_life_armed")):
        return "Знания из прошлой жизни уже готовы: следующая проверка навыка получит +1к6.", None, False

    runtime["knowledge_past_life_armed"] = True
    rf["runtime"] = runtime
    ch.race_features = rf
    _sync_character_runtime_to_combat_actor(session_id, player_uid, runtime)
    return None, "Знания из прошлой жизни: готово. Следующая проверка навыка получит +1к6 (PB/дл. отдых).", True


def _consume_reborn_past_life_for_skill_check(ch: Character, *, kind: str) -> tuple[int, Optional[str], bool]:
    if str(kind or "").strip().lower() != "skill":
        return 0, None, False
    feature = _reborn_past_life_feature(ch)
    if not feature:
        return 0, None, False
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime = dict(rf.get("runtime")) if isinstance(rf.get("runtime"), dict) else {}
    if not bool(runtime.get("knowledge_past_life_armed")):
        return 0, None, False
    uses_max = _reborn_past_life_uses_max(ch, feature)
    used = max(0, as_int(runtime.get("knowledge_past_life_uses_used"), 0))
    if uses_max <= 0 or used >= uses_max:
        runtime["knowledge_past_life_armed"] = False
        rf["runtime"] = runtime
        ch.race_features = rf
        return 0, None, True
    bonus = random.randint(1, 6)
    runtime["knowledge_past_life_uses_used"] = used + 1
    runtime["knowledge_past_life_armed"] = False
    rf["runtime"] = runtime
    ch.race_features = rf
    return bonus, f"1d6 (Знания из прошлой жизни: {bonus})", True


def _consume_reborn_past_life_bonus_for_check(
    ch: Character,
    *,
    requested: bool,
    kind: str,
    rng: Any = None,
) -> tuple[int, str, str, bool, str | None]:
    if not requested:
        return 0, "", "", False, None
    kind_norm = str(kind or "").strip().lower()
    if kind_norm not in {"ability", "skill", "tool"}:
        return 0, "", "", False, "Знания из прошлой жизни можно применять только к проверкам характеристик, навыков и инструментов."

    feature = _reborn_past_life_feature(ch)
    if not feature:
        return 0, "", "", False, "Знания из прошлой жизни недоступны вашей расе."

    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime = dict(rf.get("runtime")) if isinstance(rf.get("runtime"), dict) else {}
    uses_max = _reborn_past_life_uses_max(ch, feature)
    used = max(0, as_int(runtime.get("knowledge_past_life_uses_used"), 0))
    if uses_max <= 0 or used >= uses_max:
        return 0, "", "", False, "Знания из прошлой жизни уже использованы до долгого отдыха."

    roller = rng if rng is not None else random
    bonus = max(1, int(roller.randint(1, 6)))
    runtime["knowledge_past_life_uses_used"] = used + 1
    runtime["knowledge_past_life_armed"] = False
    runtime.pop("knowledge_from_a_past_life_pending", None)
    rf["runtime"] = runtime
    ch.race_features = rf
    remaining = max(0, uses_max - (used + 1))
    return (
        bonus,
        f"Knowledge from a Past Life 1d6({bonus})",
        f"Осталось использований: {remaining}/{uses_max}",
        True,
        None,
    )


def _simic_lvl1_options() -> set[str]:
    return {"manta_glide", "nimble_climber", "underwater_adaptation"}


def _simic_lvl5_options() -> set[str]:
    return {"manta_glide", "nimble_climber", "underwater_adaptation", "grappling_appendages", "carapace", "acid_spit"}


def _normalize_simic_upgrade_option(text: str) -> str:
    raw = str(text or "").strip().lower().replace("-", "_")
    if raw in _simic_lvl5_options():
        return raw
    aliases = {
        "мантия ската": "manta_glide",
        "планирование": "manta_glide",
        "проворный скалолаз": "nimble_climber",
        "скалолаз": "nimble_climber",
        "подводная адаптация": "underwater_adaptation",
        "амфибия": "underwater_adaptation",
        "хватательные придатки": "grappling_appendages",
        "придатки": "grappling_appendages",
        "панцирь": "carapace",
        "кислотный плевок": "acid_spit",
        "acid spit": "acid_spit",
    }
    return aliases.get(raw, "")


def _apply_simic_enhancement_payload(rf: dict[str, Any], enhancement_key: str) -> bool:
    option = str(enhancement_key or "").strip().lower()
    if option not in _simic_lvl5_options():
        return False
    speeds_raw = rf.get("speeds")
    speeds = dict(speeds_raw) if isinstance(speeds_raw, dict) else {}
    walk_ft = max(0, as_int(speeds.get("walk_ft"), 30))
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    natural_weapons_raw = rf.get("natural_weapons")
    natural_weapons = list(natural_weapons_raw) if isinstance(natural_weapons_raw, list) else []
    breath_raw = rf.get("breath")
    breath = dict(breath_raw) if isinstance(breath_raw, dict) else {}

    if option == "manta_glide":
        features["glide"] = {"reduce_fall_ft": 100, "horizontal_per_fall_ft": 2}
    elif option == "nimble_climber":
        speeds["climb_ft"] = walk_ft
    elif option == "underwater_adaptation":
        features["amphibious"] = True
        breath["amphibious"] = True
        speeds["swim_ft"] = walk_ft
    elif option == "grappling_appendages":
        features["grappling_appendages"] = {
            "damage_dice": "1d6",
            "damage_type": "bludgeoning",
            "ability": "str",
            "cannot_wield_weapons": True,
            "cannot_do_fine_work": True,
        }
        if not any(isinstance(item, dict) and str(item.get("key") or "").strip().lower() == "grappling_appendages" for item in natural_weapons):
            natural_weapons.append(
                {
                    "key": "grappling_appendages",
                    "kind": "unarmed",
                    "damage_dice": "1d6",
                    "damage_type": "bludgeoning",
                    "ability": "str",
                }
            )
    elif option == "carapace":
        features["ac_bonus_if_no_heavy_armor"] = {"ac_bonus": 1}
    elif option == "acid_spit":
        features["acid_spit"] = {
            "range_ft": 30,
            "damage": "2d10",
            "damage_type": "acid",
            "dc_formula": "8 + prof + con_mod",
            "uses_formula": "max(con_mod,1)",
            "recharge": "per_long_rest",
        }
    else:
        return False

    rf["speeds"] = speeds
    rf["features"] = features
    rf["natural_weapons"] = natural_weapons
    rf["breath"] = breath
    return True


def _apply_simic_level5_upgrade(ch: Character, option_text: str) -> tuple[Optional[str], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    if str(rf.get("race_key") or "").strip().lower() != "simic_hybrid":
        return "Усиление Simic доступно только гибриду Симиков.", None, False
    level = max(1, as_int(getattr(ch, "level", 1), 1))
    if level < 5:
        return "Второе животное усиление Simic доступно только с 5 уровня.", None, False
    option = _normalize_simic_upgrade_option(option_text)
    if option not in _simic_lvl5_options():
        return "Неизвестное усиление Simic.", None, False

    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    animal_raw = features.get("animal_enhancement")
    animal = dict(animal_raw) if isinstance(animal_raw, dict) else {"pick_1_level": 1, "pick_2_level": 5}
    chosen_lvl1 = str(animal.get("chosen_lvl1") or "").strip().lower()
    chosen_lvl5 = str(animal.get("chosen_lvl5") or "").strip().lower()
    if chosen_lvl5:
        return "Усиление 5 уровня уже выбрано.", None, False
    if option == chosen_lvl1:
        return "Усиление 5 уровня должно отличаться от выбора 1 уровня.", None, False

    if not _apply_simic_enhancement_payload(rf, option):
        return "Не удалось применить усиление Simic.", None, False

    animal["chosen_lvl1"] = chosen_lvl1 or None
    animal["chosen_lvl5"] = option
    features = dict(rf.get("features")) if isinstance(rf.get("features"), dict) else {}
    features["animal_enhancement"] = animal
    rf["features"] = features

    choices_raw = rf.get("choices")
    choices = dict(choices_raw) if isinstance(choices_raw, dict) else {}
    choices["animal_enhancement_lvl5"] = option
    rf["choices"] = choices

    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    runtime["simic_lvl5_enhancement"] = option
    runtime.setdefault("acid_spit_uses_used", 0)
    rf["runtime"] = runtime
    ch.race_features = rf

    names_ru = {
        "manta_glide": "Мантия ската",
        "nimble_climber": "Проворный скалолаз",
        "underwater_adaptation": "Подводная адаптация",
        "grappling_appendages": "Хватательные придатки",
        "carapace": "Панцирь",
        "acid_spit": "Кислотный плевок",
    }
    return None, f"Животное усиление Simic выбрано: {names_ru.get(option, option)}.", True


def _extract_jump_kind(text: str) -> str:
    raw = str(text or "").strip().lower()
    if re.search(r"\bjump\s+long\b|прыга\w*\s+в\s+длин\w*|прыж\w*\s+в\s+длин\w*", raw, flags=re.IGNORECASE):
        return "long_jump"
    if re.search(r"\bjump\s+high\b|прыга\w*\s+в\s+высот\w*|прыж\w*\s+в\s+высот\w*", raw, flags=re.IGNORECASE):
        return "high_jump"
    return ""


def _apply_satyr_mirthful_leaps_jump(
    *,
    session_id: str,
    player_uid: int | None,
    ch: Character,
    jump_kind: str,
) -> tuple[Optional[str], Optional[str], bool]:
    jump_key = str(jump_kind or "").strip().lower()
    if jump_key not in {"long_jump", "high_jump"}:
        return "Не понял тип прыжка. Используйте jump long/jump high.", None, False
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    leaps_raw = features.get("mirthful_leaps")
    leaps = dict(leaps_raw) if isinstance(leaps_raw, dict) else {}
    applies_to = [
        str(item or "").strip().lower()
        for item in (leaps.get("applies_to") if isinstance(leaps.get("applies_to"), list) else [])
        if str(item or "").strip()
    ]
    if not leaps or (applies_to and jump_key not in applies_to):
        return "Зрелищные прыжки недоступны вашей расе.", None, False

    bonus = random.randint(1, 8)
    runtime = dict(rf.get("runtime")) if isinstance(rf.get("runtime"), dict) else {}
    runtime["last_mirthful_leaps_bonus_ft"] = bonus
    runtime["last_mirthful_leaps_kind"] = jump_key
    rf["runtime"] = runtime
    ch.race_features = rf

    jump_ru = "в длину" if jump_key == "long_jump" else "в высоту"
    msg = f"Зрелищные прыжки: прыжок {jump_ru}, +1d8 ({bonus}) фт."

    if player_uid is not None:
        state = get_combat(session_id)
        actor = state.combatants.get(f"pc_{player_uid}") if state is not None and state.active else None
        if actor is not None:
            move_remaining_ft = max(0, int(getattr(actor, "move_remaining_ft", 0) or 0))
            spent_ft = min(move_remaining_ft, bonus)
            actor.move_remaining_ft = max(0, move_remaining_ft - spent_ft)
            actor.move_remaining = actor.move_remaining_ft
            actor.moved_this_turn_ft = max(0, int(getattr(actor, "moved_this_turn_ft", 0) or 0)) + spent_ft
            msg += f" Потрачено движения: {spent_ft} фт (осталось {actor.move_remaining_ft} фт)."

    return None, msg, True


def _reset_harengon_long_rest(ch: Character) -> bool:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    changed = False
    if "rabbit_hop_uses_used" in runtime:
        runtime["rabbit_hop_uses_used"] = 0
        changed = True
    if "last_failed_dex_save" in runtime:
        runtime.pop("last_failed_dex_save", None)
        changed = True
    if "last_dex_save_result" in runtime:
        runtime.pop("last_dex_save_result", None)
        changed = True
    if "saving_face_uses_used" in runtime:
        runtime.pop("saving_face_uses_used", None)
        changed = True
    if "saving_face_pending" in runtime:
        runtime.pop("saving_face_pending", None)
        changed = True
    if "grovel_uses_used" in runtime:
        runtime.pop("grovel_uses_used", None)
        changed = True
    if "grovel_active_until_turn_start_of_actor_id" in runtime:
        runtime.pop("grovel_active_until_turn_start_of_actor_id", None)
        changed = True
    if "hungry_jaws_uses_used" in runtime:
        runtime.pop("hungry_jaws_uses_used", None)
        changed = True
    if "daunting_roar_uses_used" in runtime:
        runtime.pop("daunting_roar_uses_used", None)
        changed = True
    if "goring_rush_available" in runtime:
        runtime.pop("goring_rush_available", None)
        changed = True
    if "hammering_horns_available" in runtime:
        runtime.pop("hammering_horns_available", None)
        changed = True
    if "hammering_horns_target_id" in runtime:
        runtime.pop("hammering_horns_target_id", None)
        changed = True
    if not changed:
        return False
    rf["runtime"] = runtime
    ch.race_features = rf
    return True


def _reset_combatant_harengon_long_rest(session_id: str, actor_key: str) -> bool:
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
    if "rabbit_hop_uses_used" in runtime:
        runtime["rabbit_hop_uses_used"] = 0
        changed = True
    if "last_failed_dex_save" in runtime:
        runtime.pop("last_failed_dex_save", None)
        changed = True
    if "last_dex_save_result" in runtime:
        runtime.pop("last_dex_save_result", None)
        changed = True
    if "saving_face_uses_used" in runtime:
        runtime.pop("saving_face_uses_used", None)
        changed = True
    if "saving_face_pending" in runtime:
        runtime.pop("saving_face_pending", None)
        changed = True
    if "grovel_uses_used" in runtime:
        runtime.pop("grovel_uses_used", None)
        changed = True
    if "grovel_active_until_turn_start_of_actor_id" in runtime:
        runtime.pop("grovel_active_until_turn_start_of_actor_id", None)
        changed = True
    if "hungry_jaws_uses_used" in runtime:
        runtime.pop("hungry_jaws_uses_used", None)
        changed = True
    if "daunting_roar_uses_used" in runtime:
        runtime.pop("daunting_roar_uses_used", None)
        changed = True
    if "goring_rush_available" in runtime:
        runtime.pop("goring_rush_available", None)
        changed = True
    if "hammering_horns_available" in runtime:
        runtime.pop("hammering_horns_available", None)
        changed = True
    if "hammering_horns_target_id" in runtime:
        runtime.pop("hammering_horns_target_id", None)
        changed = True
    if not changed:
        return False
    race_features["runtime"] = runtime
    actor.race_features = race_features
    return True


def _apply_grung_water_immersion(
    ch: Character,
    *,
    now: Optional[datetime] = None,
) -> tuple[Optional[str], Optional[int], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    water_dep_raw = features.get("water_dependency")
    water_dep = dict(water_dep_raw) if isinstance(water_dep_raw, dict) else {}
    if not water_dep:
        return None, None, "Зависимость от воды отсутствует у вашей расы.", False

    now_dt = now if isinstance(now, datetime) else utcnow()
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    runtime["water_last_immersion_at"] = now_dt.isoformat()
    runtime["water_dependency_exhaustion_level"] = 0
    rf["runtime"] = runtime
    ch.race_features = rf
    return now_dt.isoformat(), 0, None, True


def _apply_grung_water_dependency_long_rest(
    ch: Character,
    *,
    now: Optional[datetime] = None,
) -> tuple[int, bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    water_dep_raw = features.get("water_dependency")
    water_dep = dict(water_dep_raw) if isinstance(water_dep_raw, dict) else {}
    if not water_dep:
        return 0, False

    now_dt = now if isinstance(now, datetime) else utcnow()
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    last_immersion = _parse_iso_datetime(runtime.get("water_last_immersion_at"))
    level_before = max(0, as_int(runtime.get("water_dependency_exhaustion_level"), 0))
    hours_since = None
    if isinstance(last_immersion, datetime):
        delta = now_dt - last_immersion
        hours_since = delta.total_seconds() / 3600.0
    if hours_since is None or hours_since > 24.0:
        runtime["water_dependency_exhaustion_level"] = level_before + 1
    else:
        runtime["water_dependency_exhaustion_level"] = level_before
    rf["runtime"] = runtime
    ch.race_features = rf
    return max(0, as_int(runtime.get("water_dependency_exhaustion_level"), 0)), True


def _locathah_limited_amphibious_feature(race_features: Any) -> dict[str, Any]:
    if not isinstance(race_features, dict):
        return {}
    features_raw = race_features.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    limited_raw = features.get("limited_amphibious")
    limited = dict(limited_raw) if isinstance(limited_raw, dict) else {}
    return limited if limited else {}


def _locathah_required_hours(limited_cfg: dict[str, Any]) -> float:
    token = str(limited_cfg.get("must_immerse_every") or "").strip().lower()
    m = re.match(r"^(\d+)\s*_?\s*hours?$", token)
    if m:
        return max(1.0, float(as_int(m.group(1), 4)))
    return 4.0


def _apply_locathah_limited_amphibious_status(
    ch: Character,
    *,
    now: Optional[datetime] = None,
) -> tuple[float, bool, bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    limited_cfg = _locathah_limited_amphibious_feature(rf)
    if not limited_cfg:
        return 0.0, False, False

    now_dt = now if isinstance(now, datetime) else utcnow()
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    last_immersion = _parse_iso_datetime(runtime.get("water_last_immersion_at"))
    required_hours = _locathah_required_hours(limited_cfg)
    if isinstance(last_immersion, datetime):
        delta = now_dt - last_immersion
        hours_since = max(0.0, float(delta.total_seconds() / 3600.0))
    else:
        hours_since = required_hours + 1.0
    suffocating = not isinstance(last_immersion, datetime) or hours_since > required_hours
    prev_hours = float(runtime.get("limited_amphibious_hours_since_immersion") or 0.0)
    prev_suff = bool(runtime.get("suffocating"))
    runtime["limited_amphibious_hours_since_immersion"] = hours_since
    runtime["suffocating"] = suffocating
    rf["runtime"] = runtime
    ch.race_features = rf
    changed = (prev_suff != suffocating) or abs(prev_hours - hours_since) > 1e-6
    return hours_since, suffocating, changed


def _apply_locathah_water_immersion(
    ch: Character,
    *,
    now: Optional[datetime] = None,
) -> tuple[Optional[str], Optional[float], Optional[bool], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    limited_cfg = _locathah_limited_amphibious_feature(rf)
    if not limited_cfg:
        return None, None, None, "Частичная земноводность отсутствует у вашей расы.", False

    now_dt = now if isinstance(now, datetime) else utcnow()
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    runtime["water_last_immersion_at"] = now_dt.isoformat()
    runtime["limited_amphibious_hours_since_immersion"] = 0.0
    runtime["suffocating"] = False
    rf["runtime"] = runtime
    ch.race_features = rf
    return now_dt.isoformat(), 0.0, False, None, True


def _lizardfolk_cunning_artisan_feature(race_features: Any) -> dict[str, Any]:
    if not isinstance(race_features, dict):
        return {}
    features_raw = race_features.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    artisan_raw = features.get("cunning_artisan")
    artisan = artisan_raw if isinstance(artisan_raw, dict) else {}
    return artisan if artisan else {}


def _apply_lizardfolk_cunning_artisan_craft(
    ch: Character,
    option_raw: str,
    *,
    rng: Any = None,
) -> tuple[Optional[str], Optional[str], bool]:
    artisan = _lizardfolk_cunning_artisan_feature(getattr(ch, "race_features", None))
    if not artisan:
        return None, "Умелый ремесленник недоступен вашей расе.", False

    normalized = str(option_raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    alias_map = {
        "щит": "shield",
        "shield": "shield",
        "дубинка": "club",
        "club": "club",
        "копье": "javelin",
        "копьё": "javelin",
        "метательное_копье": "javelin",
        "метательное_копьё": "javelin",
        "javelin": "javelin",
        "дротики": "darts",
        "дротик": "darts",
        "darts": "darts",
        "dart": "darts",
        "иглы": "needles",
        "игла": "needles",
        "needles": "needles",
        "blowgun_needles": "needles",
    }
    option = alias_map.get(normalized, normalized)
    if option not in {"shield", "club", "javelin", "darts", "needles"}:
        return None, "Недопустимый вариант ремесла. Доступно: shield/club/javelin/darts/needles.", False

    stats_raw = getattr(ch, "stats", None)
    stats = dict(stats_raw) if isinstance(stats_raw, dict) else {}
    inv_raw = stats.get("_inv")
    inv = list(inv_raw) if isinstance(inv_raw, list) else []

    if option == "shield":
        craft_name = "Щит"
        craft_def = "shield"
        qty = 1
    elif option == "club":
        craft_name = "Дубинка"
        craft_def = "club"
        qty = 1
    elif option == "javelin":
        craft_name = "Метательное копьё"
        craft_def = "javelin"
        qty = 1
    elif option == "darts":
        craft_name = "Дротик"
        craft_def = "dart"
        roller = rng if rng is not None else random
        qty = max(1, int(roller.randint(1, 4)))
    else:
        craft_name = "Игла для духовой трубки"
        craft_def = "blowgun_needle"
        roller = rng if rng is not None else random
        qty = max(1, int(roller.randint(1, 4)))

    updated = False
    for item in inv:
        if not isinstance(item, dict):
            continue
        item_def = str(item.get("def") or "").strip().lower()
        item_name = str(item.get("name") or "").strip().lower()
        if item_def != craft_def and item_name != craft_name.lower():
            continue
        current_qty = max(1, as_int(item.get("qty"), 1))
        item["qty"] = _clamp(current_qty + qty, 1, 99)
        if not str(item.get("def") or "").strip():
            item["def"] = craft_def
        if not str(item.get("name") or "").strip():
            item["name"] = craft_name
        updated = True
        break
    if not updated:
        inv.append(
            {
                "id": f"craft_{craft_def}_{len(inv)+1}",
                "name": craft_name,
                "qty": _clamp(qty, 1, 99),
                "def": craft_def,
            }
        )

    stats["_inv"] = inv
    ch.stats = stats
    crafted_label = f"{craft_name} x{qty}" if qty > 1 else craft_name
    return f"Умелый ремесленник: создано {crafted_label}.", None, True


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


def _consume_vampiric_bite_bonus_for_d20(ch: Character) -> tuple[int, Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    if not bool(runtime.get("vampiric_bite_bonus_armed")):
        return 0, None, False
    bonus = max(0, as_int(runtime.get("vampiric_bite_bonus_value"), 0))
    runtime["vampiric_bite_bonus_armed"] = False
    runtime["vampiric_bite_bonus_value"] = 0
    if runtime:
        rf["runtime"] = runtime
    else:
        rf.pop("runtime", None)
    ch.race_features = rf
    if bonus <= 0:
        return 0, None, True
    return bonus, f"Укус вампира: +{bonus}", True


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


def _parse_shapechanger_command(cmdline: str) -> tuple[str | None, str | None]:
    txt = str(cmdline or "").strip()
    if not txt:
        return None, None
    lowered = txt.lower()
    if lowered == "shapechange status":
        return "status", None
    if lowered == "shapechange revert":
        return "revert", None
    if lowered == "shapechange assume":
        return "assume", ""
    if lowered.startswith("shapechange assume "):
        return "assume", txt[len("shapechange assume "):].strip()
    return None, None


def _shapechanger_status_message(ch: Character) -> tuple[Optional[str], Optional[str], bool]:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    features_raw = rf.get("features")
    features = dict(features_raw) if isinstance(features_raw, dict) else {}
    shape_cfg_raw = features.get("shapechanger")
    shape_cfg = dict(shape_cfg_raw) if isinstance(shape_cfg_raw, dict) else {}
    if not shape_cfg:
        return "Перевёртыш недоступен вашей расе.", None, False
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    shape_raw = runtime.get("shapechanger")
    shape = dict(shape_raw) if isinstance(shape_raw, dict) else {}
    active = bool(shape.get("active"))
    persona = str(shape.get("persona") or "").strip()
    voice = str(shape.get("voice") or "").strip()
    status = (persona or "неуточнённый образ") if active else "естественный облик"
    notes: list[str] = []
    if active and voice:
        notes.append(f"голос: {voice}")
    if bool(shape_cfg.get("equipment_unchanged")):
        notes.append("одежда и снаряжение не меняются автоматически")
    suffix = f" ({'; '.join(notes)})" if notes else ""
    return None, f"[RACE] Перевёртыш. Текущий облик: {status}.{suffix}", False


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

    if changed:
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


def _break_hidden_step_for_character(ch: Character) -> bool:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    hidden_raw = runtime.get("hidden_step")
    hidden_step = dict(hidden_raw) if isinstance(hidden_raw, dict) else {}
    if not bool(hidden_step.get("active")):
        return False
    hidden_step["active"] = False
    runtime["hidden_step"] = hidden_step
    rf["runtime"] = runtime
    ch.race_features = rf
    return True


def _innate_frequency_maps(race_features: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    spells_raw = race_features.get("innate_spells")
    spells = spells_raw if isinstance(spells_raw, list) else []
    spell_frequency: dict[str, str] = {}
    shared_frequency: dict[str, str] = {}
    for item in spells:
        if not isinstance(item, dict):
            continue
        spell_name = str(item.get("name") or "").strip().lower()
        frequency = str(item.get("frequency") or "").strip().lower()
        if spell_name and frequency:
            spell_frequency[spell_name] = frequency
        shared_group = str(item.get("shared_group") or "").strip().lower()
        if shared_group and frequency:
            prev = shared_frequency.get(shared_group)
            if prev == "shared_1_per_long_rest":
                continue
            shared_frequency[shared_group] = frequency
    return spell_frequency, shared_frequency


def _reset_innate_runtime_for_rest(runtime: dict[str, Any], race_features: dict[str, Any], *, long_rest: bool) -> bool:
    changed = False
    spell_frequency, shared_frequency = _innate_frequency_maps(race_features)

    uses_raw = runtime.get("innate_spell_uses")
    uses = dict(uses_raw) if isinstance(uses_raw, dict) else {}
    if uses:
        keep_uses: dict[str, Any] = {}
        for spell_key, value in uses.items():
            key = str(spell_key or "").strip().lower()
            freq = spell_frequency.get(key, "")
            should_reset = long_rest or freq in {"1_per_short_rest", "1_per_short_or_long_rest"}
            if should_reset:
                changed = True
                continue
            keep_uses[key] = value
        if keep_uses:
            runtime["innate_spell_uses"] = keep_uses
        else:
            if "innate_spell_uses" in runtime:
                runtime.pop("innate_spell_uses", None)
                changed = True

    shared_raw = runtime.get("innate_shared_uses")
    shared_uses = dict(shared_raw) if isinstance(shared_raw, dict) else {}
    if shared_uses:
        keep_shared: dict[str, Any] = {}
        for group_key, value in shared_uses.items():
            key = str(group_key or "").strip().lower()
            freq = shared_frequency.get(key, "")
            should_reset = long_rest or freq in {"shared_1_per_short_rest", "shared_1_per_short_or_long_rest"}
            if should_reset:
                changed = True
                continue
            keep_shared[key] = value
        if keep_shared:
            runtime["innate_shared_uses"] = keep_shared
        else:
            if "innate_shared_uses" in runtime:
                runtime.pop("innate_shared_uses", None)
                changed = True

    return changed


def _runtime_set_if_changed(runtime: dict[str, Any], key: str, value: Any) -> bool:
    if key not in runtime:
        return False
    if runtime.get(key) == value:
        return False
    runtime[key] = value
    return True


def _reset_racial_rest_uses(ch: Character, *, long_rest: bool = True) -> bool:
    race_features = getattr(ch, "race_features", None)
    rf = dict(race_features) if isinstance(race_features, dict) else {}
    runtime_raw = rf.get("runtime")
    runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
    changed = False
    if _reset_innate_runtime_for_rest(runtime, rf, long_rest=long_rest):
        changed = True
    if "hidden_step" in runtime:
        runtime.pop("hidden_step", None)
        changed = True
    if "stone_endurance_used" in runtime:
        runtime.pop("stone_endurance_used", None)
        changed = True
    if long_rest and "healing_hands_used" in runtime:
        runtime.pop("healing_hands_used", None)
        changed = True
    if long_rest and "aasimar_transform_used" in runtime:
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
    if long_rest and "relentless_endurance_used" in runtime:
        runtime.pop("relentless_endurance_used", None)
        changed = True
    if long_rest and _runtime_set_if_changed(runtime, "adrenaline_rush_uses_used", 0):
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
    if "nimble_escape_hide" in runtime:
        runtime.pop("nimble_escape_hide", None)
        changed = True
    if "vampiric_bite_uses_used" in runtime:
        runtime.pop("vampiric_bite_uses_used", None)
        changed = True
    if "vampiric_bite_bonus_armed" in runtime:
        runtime.pop("vampiric_bite_bonus_armed", None)
        changed = True
    if "vampiric_bite_bonus_value" in runtime:
        runtime.pop("vampiric_bite_bonus_value", None)
        changed = True
    if "grung_weapon_poison_armed" in runtime:
        runtime.pop("grung_weapon_poison_armed", None)
        changed = True
    if _runtime_set_if_changed(runtime, "triton_active_water_wall", None):
        changed = True
    if "last_failed_dex_save" in runtime:
        runtime.pop("last_failed_dex_save", None)
        changed = True
    if "last_dex_save_result" in runtime:
        runtime.pop("last_dex_save_result", None)
        changed = True
    if "saving_face_uses_used" in runtime:
        runtime.pop("saving_face_uses_used", None)
        changed = True
    if "saving_face_pending" in runtime:
        runtime.pop("saving_face_pending", None)
        changed = True
    if "grovel_uses_used" in runtime:
        runtime.pop("grovel_uses_used", None)
        changed = True
    if "grovel_active_until_turn_start_of_actor_id" in runtime:
        runtime.pop("grovel_active_until_turn_start_of_actor_id", None)
        changed = True
    if "hungry_jaws_uses_used" in runtime:
        runtime.pop("hungry_jaws_uses_used", None)
        changed = True
    if "daunting_roar_uses_used" in runtime:
        runtime.pop("daunting_roar_uses_used", None)
        changed = True
    if "aggressive_used_turn_id" in runtime:
        runtime.pop("aggressive_used_turn_id", None)
        changed = True
    for key, value in (
        ("shifted_active", False),
        ("shifted_rounds_left", 0),
        ("shifting_temp_hp_granted", 0),
        ("shifting_ac_bonus_active", 0),
        ("shifting_speed_bonus_active_ft", 0),
        ("shifting_longtooth_bite_available", False),
        ("shifting_swiftstride_reaction_available", False),
        ("feline_agility_available", True),
        ("feline_agility_active", False),
        ("feline_agility_used_turn", ""),
        ("moved_this_turn_ft", 0),
        ("shell_defense_active", False),
        ("shell_defense_entered_turn", ""),
    ):
        if _runtime_set_if_changed(runtime, key, value):
            changed = True
    for key in ("ac_bonus", "speed_override_ft"):
        if key in runtime:
            runtime.pop(key, None)
            changed = True
    if "knowledge_past_life_armed" in runtime:
        runtime.pop("knowledge_past_life_armed", None)
        changed = True
    if "knowledge_from_a_past_life_pending" in runtime:
        runtime.pop("knowledge_from_a_past_life_pending", None)
        changed = True
    if "knowledge_from_a_past_life_last_result" in runtime:
        runtime.pop("knowledge_from_a_past_life_last_result", None)
        changed = True
    if "simic_appendages_last_target_id" in runtime:
        runtime.pop("simic_appendages_last_target_id", None)
        changed = True
    if long_rest:
        for key, value in (
            ("shifting_uses_used", 0),
            ("marked_uses_used", 0),
            ("wildhunt_marked_target_id", ""),
            ("wildhunt_marked_until", ""),
            ("knowledge_past_life_uses_used", 0),
            ("acid_spit_uses_used", 0),
            ("triton_gust_of_wind_used", False),
            ("triton_wall_of_water_used", False),
            ("triton_active_water_wall", None),
            ("tiefling_hellish_rebuke_used", False),
            ("tiefling_darkness_used", False),
            ("drow_faerie_fire_used", False),
            ("drow_darkness_used", False),
            ("duergar_enlarge_used", False),
            ("duergar_invisibility_used", False),
            ("githyanki_jump_used", False),
            ("githyanki_misty_step_used", False),
            ("githzerai_shield_used", False),
            ("githzerai_detect_thoughts_used", False),
            ("yuanti_suggestion_used", False),
            ("yuanti_last_innate_spell", None),
        ):
            if _runtime_set_if_changed(runtime, key, value):
                changed = True
        if "fearless_auto_success_used" in runtime:
            runtime.pop("fearless_auto_success_used", None)
            changed = True
        if "fearless_pending_failed_frightened_save" in runtime:
            runtime.pop("fearless_pending_failed_frightened_save", None)
            changed = True
        if "fearless_last_result" in runtime:
            runtime.pop("fearless_last_result", None)
            changed = True
        if "eerie_token_uses_used" in runtime:
            runtime.pop("eerie_token_uses_used", None)
            changed = True
        if "eerie_token_active" in runtime:
            runtime.pop("eerie_token_active", None)
            changed = True
        if "eerie_token_consumed" in runtime:
            runtime.pop("eerie_token_consumed", None)
            changed = True
        if "eerie_token_id" in runtime:
            runtime.pop("eerie_token_id", None)
            changed = True
        if "eerie_token_created_at" in runtime:
            runtime.pop("eerie_token_created_at", None)
            changed = True
        if "eerie_token_last_message" in runtime:
            runtime.pop("eerie_token_last_message", None)
            changed = True
        if "eerie_token_sense_active" in runtime:
            runtime.pop("eerie_token_sense_active", None)
            changed = True
        if "eerie_token_expires_on_next_long_rest" in runtime:
            runtime.pop("eerie_token_expires_on_next_long_rest", None)
            changed = True
        if "eerie_token_remote_view_rounds_left" in runtime:
            runtime.pop("eerie_token_remote_view_rounds_left", None)
            changed = True
    else:
        for key, value in (("shifting_uses_used", 0), ("marked_uses_used", 0)):
            if _runtime_set_if_changed(runtime, key, value):
                changed = True
    if not changed:
        return False
    if runtime:
        rf["runtime"] = runtime
    else:
        rf.pop("runtime", None)
    ch.race_features = rf
    return True


def _reset_combatant_racial_rest_uses(session_id: str, actor_key: str, *, long_rest: bool = True) -> bool:
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
    if _reset_innate_runtime_for_rest(runtime, race_features, long_rest=long_rest):
        changed = True
    if "hidden_step" in runtime:
        runtime.pop("hidden_step", None)
        changed = True
    if "stone_endurance_used" in runtime:
        runtime.pop("stone_endurance_used", None)
        changed = True
    if long_rest and "healing_hands_used" in runtime:
        runtime.pop("healing_hands_used", None)
        changed = True
    if long_rest and "aasimar_transform_used" in runtime:
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
    if long_rest and "relentless_endurance_used" in runtime:
        runtime.pop("relentless_endurance_used", None)
        changed = True
    if long_rest and _runtime_set_if_changed(runtime, "adrenaline_rush_uses_used", 0):
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
    if "nimble_escape_hide" in runtime:
        runtime.pop("nimble_escape_hide", None)
        changed = True
    if "vampiric_bite_uses_used" in runtime:
        runtime.pop("vampiric_bite_uses_used", None)
        changed = True
    if "vampiric_bite_bonus_armed" in runtime:
        runtime.pop("vampiric_bite_bonus_armed", None)
        changed = True
    if "vampiric_bite_bonus_value" in runtime:
        runtime.pop("vampiric_bite_bonus_value", None)
        changed = True
    if "grung_weapon_poison_armed" in runtime:
        runtime.pop("grung_weapon_poison_armed", None)
        changed = True
    if _runtime_set_if_changed(runtime, "triton_active_water_wall", None):
        changed = True
    if "last_failed_dex_save" in runtime:
        runtime.pop("last_failed_dex_save", None)
        changed = True
    if "last_dex_save_result" in runtime:
        runtime.pop("last_dex_save_result", None)
        changed = True
    if "saving_face_uses_used" in runtime:
        runtime.pop("saving_face_uses_used", None)
        changed = True
    if "saving_face_pending" in runtime:
        runtime.pop("saving_face_pending", None)
        changed = True
    if "grovel_uses_used" in runtime:
        runtime.pop("grovel_uses_used", None)
        changed = True
    if "grovel_active_until_turn_start_of_actor_id" in runtime:
        runtime.pop("grovel_active_until_turn_start_of_actor_id", None)
        changed = True
    if "hungry_jaws_uses_used" in runtime:
        runtime.pop("hungry_jaws_uses_used", None)
        changed = True
    if "daunting_roar_uses_used" in runtime:
        runtime.pop("daunting_roar_uses_used", None)
        changed = True
    if "aggressive_used_turn_id" in runtime:
        runtime.pop("aggressive_used_turn_id", None)
        changed = True
    for key, value in (
        ("shifted_active", False),
        ("shifted_rounds_left", 0),
        ("shifting_temp_hp_granted", 0),
        ("shifting_ac_bonus_active", 0),
        ("shifting_speed_bonus_active_ft", 0),
        ("shifting_longtooth_bite_available", False),
        ("shifting_swiftstride_reaction_available", False),
        ("feline_agility_available", True),
        ("feline_agility_active", False),
        ("feline_agility_used_turn", ""),
        ("moved_this_turn_ft", 0),
        ("shell_defense_active", False),
        ("shell_defense_entered_turn", ""),
    ):
        if _runtime_set_if_changed(runtime, key, value):
            changed = True
    for key in ("ac_bonus", "speed_override_ft"):
        if key in runtime:
            runtime.pop(key, None)
            changed = True
    if "knowledge_past_life_armed" in runtime:
        runtime.pop("knowledge_past_life_armed", None)
        changed = True
    if "knowledge_from_a_past_life_pending" in runtime:
        runtime.pop("knowledge_from_a_past_life_pending", None)
        changed = True
    if "knowledge_from_a_past_life_last_result" in runtime:
        runtime.pop("knowledge_from_a_past_life_last_result", None)
        changed = True
    if "simic_appendages_last_target_id" in runtime:
        runtime.pop("simic_appendages_last_target_id", None)
        changed = True
    if long_rest:
        for key, value in (
            ("shifting_uses_used", 0),
            ("marked_uses_used", 0),
            ("wildhunt_marked_target_id", ""),
            ("wildhunt_marked_until", ""),
            ("knowledge_past_life_uses_used", 0),
            ("acid_spit_uses_used", 0),
            ("triton_gust_of_wind_used", False),
            ("triton_wall_of_water_used", False),
            ("triton_active_water_wall", None),
            ("tiefling_hellish_rebuke_used", False),
            ("tiefling_darkness_used", False),
            ("drow_faerie_fire_used", False),
            ("drow_darkness_used", False),
            ("duergar_enlarge_used", False),
            ("duergar_invisibility_used", False),
            ("githyanki_jump_used", False),
            ("githyanki_misty_step_used", False),
            ("githzerai_shield_used", False),
            ("githzerai_detect_thoughts_used", False),
            ("yuanti_suggestion_used", False),
            ("yuanti_last_innate_spell", None),
        ):
            if _runtime_set_if_changed(runtime, key, value):
                changed = True
        if "fearless_auto_success_used" in runtime:
            runtime.pop("fearless_auto_success_used", None)
            changed = True
        if "fearless_pending_failed_frightened_save" in runtime:
            runtime.pop("fearless_pending_failed_frightened_save", None)
            changed = True
        if "fearless_last_result" in runtime:
            runtime.pop("fearless_last_result", None)
            changed = True
        if "eerie_token_uses_used" in runtime:
            runtime.pop("eerie_token_uses_used", None)
            changed = True
        if "eerie_token_active" in runtime:
            runtime.pop("eerie_token_active", None)
            changed = True
        if "eerie_token_consumed" in runtime:
            runtime.pop("eerie_token_consumed", None)
            changed = True
        if "eerie_token_id" in runtime:
            runtime.pop("eerie_token_id", None)
            changed = True
        if "eerie_token_created_at" in runtime:
            runtime.pop("eerie_token_created_at", None)
            changed = True
        if "eerie_token_last_message" in runtime:
            runtime.pop("eerie_token_last_message", None)
            changed = True
        if "eerie_token_sense_active" in runtime:
            runtime.pop("eerie_token_sense_active", None)
            changed = True
        if "eerie_token_expires_on_next_long_rest" in runtime:
            runtime.pop("eerie_token_expires_on_next_long_rest", None)
            changed = True
        if "eerie_token_remote_view_rounds_left" in runtime:
            runtime.pop("eerie_token_remote_view_rounds_left", None)
            changed = True
    else:
        for key, value in (("shifting_uses_used", 0), ("marked_uses_used", 0)):
            if _runtime_set_if_changed(runtime, key, value):
                changed = True
    for combatant in state.combatants.values():
        target_rf = combatant.race_features if isinstance(getattr(combatant, "race_features", None), dict) else {}
        target_runtime_raw = target_rf.get("runtime")
        target_runtime = dict(target_runtime_raw) if isinstance(target_runtime_raw, dict) else {}
        groveled_raw = target_runtime.get("groveled")
        groveled = dict(groveled_raw) if isinstance(groveled_raw, dict) else {}
        if str(groveled.get("source_actor_id") or "").strip() != str(actor_key):
            continue
        target_runtime.pop("groveled", None)
        if target_runtime:
            target_rf["runtime"] = target_runtime
        else:
            target_rf.pop("runtime", None)
        combatant.race_features = target_rf
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
    adrenaline_rush_runtime_by_uid: dict[int, dict[str, Any]] = {}
    built_for_success_runtime_by_uid: dict[int, dict[str, Any]] = {}
    fury_of_small_runtime_by_uid: dict[int, dict[str, Any]] = {}
    vampiric_bite_runtime_by_uid: dict[int, dict[str, Any]] = {}
    hidden_step_runtime_by_uid: dict[int, dict[str, Any]] = {}
    nimble_hide_runtime_by_uid: dict[int, dict[str, Any]] = {}
    grung_poison_runtime_by_uid: dict[int, bool] = {}
    conditions_runtime_by_uid: dict[int, dict[str, Any]] = {}
    rabbit_hop_runtime_by_uid: dict[int, dict[str, Any]] = {}
    lucky_footwork_runtime_by_uid: dict[int, dict[str, Any]] = {}
    saving_face_runtime_by_uid: dict[int, dict[str, Any]] = {}
    grovel_runtime_by_uid: dict[int, dict[str, Any]] = {}
    hungry_jaws_runtime_by_uid: dict[int, dict[str, Any]] = {}
    leonin_roar_runtime_by_uid: dict[int, dict[str, Any]] = {}
    fearless_runtime_by_uid: dict[int, dict[str, Any]] = {}
    minotaur_runtime_by_uid: dict[int, dict[str, Any]] = {}
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
        if "adrenaline_rush_uses_used" in runtime:
            adrenaline_rush_runtime_by_uid[int(uid_raw)] = {
                "adrenaline_rush_uses_used": max(0, as_int(runtime.get("adrenaline_rush_uses_used"), 0))
            }
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
        if (
            "vampiric_bite_uses_used" in runtime
            or "vampiric_bite_bonus_armed" in runtime
            or "vampiric_bite_bonus_value" in runtime
        ):
            vamp_runtime: dict[str, Any] = {}
            if "vampiric_bite_uses_used" in runtime:
                vamp_runtime["vampiric_bite_uses_used"] = max(0, as_int(runtime.get("vampiric_bite_uses_used"), 0))
            if "vampiric_bite_bonus_armed" in runtime:
                vamp_runtime["vampiric_bite_bonus_armed"] = bool(runtime.get("vampiric_bite_bonus_armed"))
            if "vampiric_bite_bonus_value" in runtime:
                vamp_runtime["vampiric_bite_bonus_value"] = max(0, as_int(runtime.get("vampiric_bite_bonus_value"), 0))
            vampiric_bite_runtime_by_uid[int(uid_raw)] = vamp_runtime
        if "hidden_step" in runtime:
            hidden_raw = runtime.get("hidden_step")
            hidden_step = dict(hidden_raw) if isinstance(hidden_raw, dict) else {}
            hidden_step_runtime_by_uid[int(uid_raw)] = hidden_step
        if "nimble_escape_hide" in runtime:
            hide_raw = runtime.get("nimble_escape_hide")
            hide_cfg = dict(hide_raw) if isinstance(hide_raw, dict) else {}
            nimble_hide_runtime_by_uid[int(uid_raw)] = hide_cfg
        if "grung_weapon_poison_armed" in runtime:
            grung_poison_runtime_by_uid[int(uid_raw)] = bool(runtime.get("grung_weapon_poison_armed"))
        if "conditions" in runtime:
            cond_raw = runtime.get("conditions")
            conds = dict(cond_raw) if isinstance(cond_raw, dict) else {}
            if conds:
                conditions_runtime_by_uid[int(uid_raw)] = conds
        if "rabbit_hop_uses_used" in runtime:
            rabbit_hop_runtime_by_uid[int(uid_raw)] = {
                "rabbit_hop_uses_used": max(0, as_int(runtime.get("rabbit_hop_uses_used"), 0))
            }
        if "last_failed_dex_save" in runtime or "last_dex_save_result" in runtime:
            lucky_runtime: dict[str, Any] = {}
            if isinstance(runtime.get("last_failed_dex_save"), dict):
                lucky_runtime["last_failed_dex_save"] = dict(runtime.get("last_failed_dex_save"))
            if isinstance(runtime.get("last_dex_save_result"), dict):
                lucky_runtime["last_dex_save_result"] = dict(runtime.get("last_dex_save_result"))
            if lucky_runtime:
                lucky_footwork_runtime_by_uid[int(uid_raw)] = lucky_runtime
        if "saving_face_uses_used" in runtime or isinstance(runtime.get("saving_face_pending"), dict):
            sf_runtime: dict[str, Any] = {}
            if "saving_face_uses_used" in runtime:
                sf_runtime["saving_face_uses_used"] = max(0, as_int(runtime.get("saving_face_uses_used"), 0))
            if isinstance(runtime.get("saving_face_pending"), dict):
                sf_runtime["saving_face_pending"] = dict(runtime.get("saving_face_pending"))
            if sf_runtime:
                saving_face_runtime_by_uid[int(uid_raw)] = sf_runtime
        if "grovel_uses_used" in runtime or "grovel_active_until_turn_start_of_actor_id" in runtime:
            grovel_runtime: dict[str, Any] = {}
            if "grovel_uses_used" in runtime:
                grovel_runtime["grovel_uses_used"] = max(0, as_int(runtime.get("grovel_uses_used"), 0))
            if "grovel_active_until_turn_start_of_actor_id" in runtime:
                grovel_runtime["grovel_active_until_turn_start_of_actor_id"] = str(
                    runtime.get("grovel_active_until_turn_start_of_actor_id") or ""
                ).strip()
            if grovel_runtime:
                grovel_runtime_by_uid[int(uid_raw)] = grovel_runtime
        if "hungry_jaws_uses_used" in runtime:
            hungry_jaws_runtime_by_uid[int(uid_raw)] = {
                "hungry_jaws_uses_used": max(0, as_int(runtime.get("hungry_jaws_uses_used"), 0))
            }
        if "daunting_roar_uses_used" in runtime:
            leonin_roar_runtime_by_uid[int(uid_raw)] = {
                "daunting_roar_uses_used": max(0, as_int(runtime.get("daunting_roar_uses_used"), 0))
            }
        if "fearless_auto_success_used" in runtime or isinstance(runtime.get("fearless_pending_failed_frightened_save"), dict):
            fearless_runtime: dict[str, Any] = {}
            if "fearless_auto_success_used" in runtime:
                fearless_runtime["fearless_auto_success_used"] = max(0, as_int(runtime.get("fearless_auto_success_used"), 0))
            if isinstance(runtime.get("fearless_pending_failed_frightened_save"), dict):
                fearless_runtime["fearless_pending_failed_frightened_save"] = dict(runtime.get("fearless_pending_failed_frightened_save"))
            if fearless_runtime:
                fearless_runtime_by_uid[int(uid_raw)] = fearless_runtime
        if (
            "goring_rush_available" in runtime
            or "hammering_horns_available" in runtime
            or "hammering_horns_target_id" in runtime
        ):
            minotaur_runtime: dict[str, Any] = {}
            if "goring_rush_available" in runtime:
                minotaur_runtime["goring_rush_available"] = bool(runtime.get("goring_rush_available"))
            if "hammering_horns_available" in runtime:
                minotaur_runtime["hammering_horns_available"] = bool(runtime.get("hammering_horns_available"))
            if "hammering_horns_target_id" in runtime:
                minotaur_runtime["hammering_horns_target_id"] = str(runtime.get("hammering_horns_target_id") or "").strip()
            if minotaur_runtime:
                minotaur_runtime_by_uid[int(uid_raw)] = minotaur_runtime
    if (
        not relentless_used_uids
        and not adrenaline_rush_runtime_by_uid
        and not built_for_success_runtime_by_uid
        and not fury_of_small_runtime_by_uid
        and not vampiric_bite_runtime_by_uid
        and not hidden_step_runtime_by_uid
        and not nimble_hide_runtime_by_uid
        and not grung_poison_runtime_by_uid
        and not conditions_runtime_by_uid
        and not rabbit_hop_runtime_by_uid
        and not lucky_footwork_runtime_by_uid
        and not saving_face_runtime_by_uid
        and not grovel_runtime_by_uid
        and not hungry_jaws_runtime_by_uid
        and not leonin_roar_runtime_by_uid
        and not fearless_runtime_by_uid
        and not minotaur_runtime_by_uid
    ):
        return False

    _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
    changed = False
    for uid, ch in chars_by_uid.items():
        if (
            uid not in relentless_used_uids
            and uid not in adrenaline_rush_runtime_by_uid
            and uid not in built_for_success_runtime_by_uid
            and uid not in fury_of_small_runtime_by_uid
            and uid not in vampiric_bite_runtime_by_uid
            and uid not in hidden_step_runtime_by_uid
            and uid not in nimble_hide_runtime_by_uid
            and uid not in grung_poison_runtime_by_uid
            and uid not in conditions_runtime_by_uid
            and uid not in rabbit_hop_runtime_by_uid
            and uid not in lucky_footwork_runtime_by_uid
            and uid not in saving_face_runtime_by_uid
            and uid not in grovel_runtime_by_uid
            and uid not in hungry_jaws_runtime_by_uid
            and uid not in leonin_roar_runtime_by_uid
            and uid not in fearless_runtime_by_uid
            and uid not in minotaur_runtime_by_uid
        ):
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
        adrenaline_runtime = adrenaline_rush_runtime_by_uid.get(uid)
        if isinstance(adrenaline_runtime, dict):
            value = max(0, as_int(adrenaline_runtime.get("adrenaline_rush_uses_used"), 0))
            if max(0, as_int(runtime.get("adrenaline_rush_uses_used"), 0)) != value:
                runtime["adrenaline_rush_uses_used"] = value
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
        vamp_runtime = vampiric_bite_runtime_by_uid.get(uid)
        if isinstance(vamp_runtime, dict):
            if "vampiric_bite_uses_used" in vamp_runtime:
                value = max(0, as_int(vamp_runtime.get("vampiric_bite_uses_used"), 0))
                if max(0, as_int(runtime.get("vampiric_bite_uses_used"), 0)) != value:
                    runtime["vampiric_bite_uses_used"] = value
                    local_changed = True
            if "vampiric_bite_bonus_armed" in vamp_runtime:
                value = bool(vamp_runtime.get("vampiric_bite_bonus_armed"))
                if bool(runtime.get("vampiric_bite_bonus_armed")) != value:
                    runtime["vampiric_bite_bonus_armed"] = value
                    local_changed = True
            if "vampiric_bite_bonus_value" in vamp_runtime:
                value = max(0, as_int(vamp_runtime.get("vampiric_bite_bonus_value"), 0))
                if max(0, as_int(runtime.get("vampiric_bite_bonus_value"), 0)) != value:
                    runtime["vampiric_bite_bonus_value"] = value
                    local_changed = True
        hidden_runtime = hidden_step_runtime_by_uid.get(uid)
        if isinstance(hidden_runtime, dict):
            current_hidden = dict(runtime.get("hidden_step")) if isinstance(runtime.get("hidden_step"), dict) else {}
            if current_hidden != hidden_runtime:
                runtime["hidden_step"] = dict(hidden_runtime)
                local_changed = True
        nimble_runtime = nimble_hide_runtime_by_uid.get(uid)
        if isinstance(nimble_runtime, dict):
            current_hide = dict(runtime.get("nimble_escape_hide")) if isinstance(runtime.get("nimble_escape_hide"), dict) else {}
            if current_hide != nimble_runtime:
                runtime["nimble_escape_hide"] = dict(nimble_runtime)
                local_changed = True
        if uid in grung_poison_runtime_by_uid:
            poison_armed_value = bool(grung_poison_runtime_by_uid.get(uid))
            if bool(runtime.get("grung_weapon_poison_armed")) != poison_armed_value:
                runtime["grung_weapon_poison_armed"] = poison_armed_value
                local_changed = True
        conditions_runtime = conditions_runtime_by_uid.get(uid)
        if isinstance(conditions_runtime, dict):
            current_conditions = dict(runtime.get("conditions")) if isinstance(runtime.get("conditions"), dict) else {}
            if current_conditions != conditions_runtime:
                runtime["conditions"] = dict(conditions_runtime)
                local_changed = True
        rabbit_runtime = rabbit_hop_runtime_by_uid.get(uid)
        if isinstance(rabbit_runtime, dict):
            value = max(0, as_int(rabbit_runtime.get("rabbit_hop_uses_used"), 0))
            if max(0, as_int(runtime.get("rabbit_hop_uses_used"), 0)) != value:
                runtime["rabbit_hop_uses_used"] = value
                local_changed = True
        lucky_runtime = lucky_footwork_runtime_by_uid.get(uid)
        if isinstance(lucky_runtime, dict):
            current_failed = dict(runtime.get("last_failed_dex_save")) if isinstance(runtime.get("last_failed_dex_save"), dict) else {}
            target_failed = dict(lucky_runtime.get("last_failed_dex_save")) if isinstance(lucky_runtime.get("last_failed_dex_save"), dict) else {}
            if current_failed != target_failed:
                if target_failed:
                    runtime["last_failed_dex_save"] = target_failed
                else:
                    runtime.pop("last_failed_dex_save", None)
                local_changed = True
            current_result = dict(runtime.get("last_dex_save_result")) if isinstance(runtime.get("last_dex_save_result"), dict) else {}
            target_result = dict(lucky_runtime.get("last_dex_save_result")) if isinstance(lucky_runtime.get("last_dex_save_result"), dict) else {}
            if current_result != target_result:
                if target_result:
                    runtime["last_dex_save_result"] = target_result
                else:
                    runtime.pop("last_dex_save_result", None)
                local_changed = True
        sf_runtime = saving_face_runtime_by_uid.get(uid)
        if isinstance(sf_runtime, dict):
            uses_val = max(0, as_int(sf_runtime.get("saving_face_uses_used"), 0))
            if max(0, as_int(runtime.get("saving_face_uses_used"), 0)) != uses_val:
                runtime["saving_face_uses_used"] = uses_val
                local_changed = True
            pending_target = dict(sf_runtime.get("saving_face_pending")) if isinstance(sf_runtime.get("saving_face_pending"), dict) else {}
            pending_current = dict(runtime.get("saving_face_pending")) if isinstance(runtime.get("saving_face_pending"), dict) else {}
            if pending_current != pending_target:
                if pending_target:
                    runtime["saving_face_pending"] = pending_target
                else:
                    runtime.pop("saving_face_pending", None)
                local_changed = True
        grovel_runtime = grovel_runtime_by_uid.get(uid)
        if isinstance(grovel_runtime, dict):
            uses_val = max(0, as_int(grovel_runtime.get("grovel_uses_used"), 0))
            if max(0, as_int(runtime.get("grovel_uses_used"), 0)) != uses_val:
                runtime["grovel_uses_used"] = uses_val
                local_changed = True
            active_until = str(grovel_runtime.get("grovel_active_until_turn_start_of_actor_id") or "").strip()
            current_until = str(runtime.get("grovel_active_until_turn_start_of_actor_id") or "").strip()
            if current_until != active_until:
                if active_until:
                    runtime["grovel_active_until_turn_start_of_actor_id"] = active_until
                else:
                    runtime.pop("grovel_active_until_turn_start_of_actor_id", None)
                local_changed = True
        hungry_jaws_runtime = hungry_jaws_runtime_by_uid.get(uid)
        if isinstance(hungry_jaws_runtime, dict):
            uses_val = max(0, as_int(hungry_jaws_runtime.get("hungry_jaws_uses_used"), 0))
            if max(0, as_int(runtime.get("hungry_jaws_uses_used"), 0)) != uses_val:
                runtime["hungry_jaws_uses_used"] = uses_val
                local_changed = True
        leonin_roar_runtime = leonin_roar_runtime_by_uid.get(uid)
        if isinstance(leonin_roar_runtime, dict):
            uses_val = max(0, as_int(leonin_roar_runtime.get("daunting_roar_uses_used"), 0))
            if max(0, as_int(runtime.get("daunting_roar_uses_used"), 0)) != uses_val:
                runtime["daunting_roar_uses_used"] = uses_val
                local_changed = True
        fearless_runtime = fearless_runtime_by_uid.get(uid)
        if isinstance(fearless_runtime, dict):
            uses_val = max(0, as_int(fearless_runtime.get("fearless_auto_success_used"), 0))
            if max(0, as_int(runtime.get("fearless_auto_success_used"), 0)) != uses_val:
                runtime["fearless_auto_success_used"] = uses_val
                local_changed = True
            pending_target = (
                dict(fearless_runtime.get("fearless_pending_failed_frightened_save"))
                if isinstance(fearless_runtime.get("fearless_pending_failed_frightened_save"), dict)
                else {}
            )
            pending_current = (
                dict(runtime.get("fearless_pending_failed_frightened_save"))
                if isinstance(runtime.get("fearless_pending_failed_frightened_save"), dict)
                else {}
            )
            if pending_current != pending_target:
                if pending_target:
                    runtime["fearless_pending_failed_frightened_save"] = pending_target
                else:
                    runtime.pop("fearless_pending_failed_frightened_save", None)
                local_changed = True
        minotaur_runtime = minotaur_runtime_by_uid.get(uid)
        if isinstance(minotaur_runtime, dict):
            goring_available = bool(minotaur_runtime.get("goring_rush_available"))
            if bool(runtime.get("goring_rush_available")) != goring_available:
                runtime["goring_rush_available"] = goring_available
                local_changed = True
            hammering_available = bool(minotaur_runtime.get("hammering_horns_available"))
            if bool(runtime.get("hammering_horns_available")) != hammering_available:
                runtime["hammering_horns_available"] = hammering_available
                local_changed = True
            hammering_target = str(minotaur_runtime.get("hammering_horns_target_id") or "").strip()
            if str(runtime.get("hammering_horns_target_id") or "").strip() != hammering_target:
                if hammering_target:
                    runtime["hammering_horns_target_id"] = hammering_target
                else:
                    runtime.pop("hammering_horns_target_id", None)
                local_changed = True
        if local_changed:
            race_features["runtime"] = runtime
            ch.race_features = race_features
            flag_modified(ch, "race_features")
            changed = True
    return changed


async def _persist_shifter_runtime_from_combat_state(db, sess, session_id: str) -> bool:
    state = get_combat(session_id)
    if state is None or not state.active:
        return False
    shifter_runtime_by_uid: dict[int, dict[str, Any]] = {}
    for actor_key, actor in (state.combatants or {}).items():
        if not str(actor_key or "").startswith("pc_"):
            continue
        uid_raw = str(actor_key).split("_", 1)[1]
        if not uid_raw.isdigit():
            continue
        race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
        if str(race_features.get("race_key") or "").strip().lower() != "shifter":
            continue
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        tracked: dict[str, Any] = {}
        for key in (
            "shifted_active",
            "shifted_rounds_left",
            "shifting_uses_used",
            "shifting_temp_hp_granted",
            "shifting_ac_bonus_active",
            "shifting_speed_bonus_active_ft",
            "shifting_longtooth_bite_available",
            "shifting_swiftstride_reaction_available",
            "wildhunt_marked_target_id",
            "wildhunt_marked_until",
            "marked_uses_used",
        ):
            if key in runtime:
                tracked[key] = runtime.get(key)
        if tracked:
            shifter_runtime_by_uid[int(uid_raw)] = tracked
    if not shifter_runtime_by_uid:
        return False
    _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
    changed = False
    for uid, tracked in shifter_runtime_by_uid.items():
        ch = chars_by_uid.get(uid)
        if ch is None:
            continue
        race_features_raw = getattr(ch, "race_features", None)
        race_features = dict(race_features_raw) if isinstance(race_features_raw, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        local_changed = False
        for key, value in tracked.items():
            if runtime.get(key) != value:
                runtime[key] = value
                local_changed = True
        if local_changed:
            race_features["runtime"] = runtime
            ch.race_features = race_features
            flag_modified(ch, "race_features")
            changed = True
    return changed


async def _persist_simic_runtime_from_combat_state(db, sess, session_id: str) -> bool:
    state = get_combat(session_id)
    if state is None or not state.active:
        return False
    simic_runtime_by_uid: dict[int, dict[str, Any]] = {}
    for actor_key, actor in (state.combatants or {}).items():
        if not str(actor_key or "").startswith("pc_"):
            continue
        uid_raw = str(actor_key).split("_", 1)[1]
        if not uid_raw.isdigit():
            continue
        race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
        if str(race_features.get("race_key") or "").strip().lower() != "simic_hybrid":
            continue
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        tracked: dict[str, Any] = {}
        for key in ("acid_spit_uses_used", "simic_appendages_last_target_id"):
            if key in runtime:
                tracked[key] = runtime.get(key)
        if tracked:
            simic_runtime_by_uid[int(uid_raw)] = tracked
    if not simic_runtime_by_uid:
        return False
    _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
    changed = False
    for uid, tracked in simic_runtime_by_uid.items():
        ch = chars_by_uid.get(uid)
        if ch is None:
            continue
        race_features_raw = getattr(ch, "race_features", None)
        race_features = dict(race_features_raw) if isinstance(race_features_raw, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        local_changed = False
        for key, value in tracked.items():
            if runtime.get(key) != value:
                runtime[key] = value
                local_changed = True
        if local_changed:
            race_features["runtime"] = runtime
            ch.race_features = race_features
            flag_modified(ch, "race_features")
            changed = True
    return changed


async def _persist_tortle_runtime_from_combat_state(db, sess, session_id: str) -> bool:
    state = get_combat(session_id)
    if state is None or not state.active:
        return False
    tortle_runtime_by_uid: dict[int, dict[str, Any]] = {}
    for actor_key, actor in (state.combatants or {}).items():
        if not str(actor_key or "").startswith("pc_"):
            continue
        uid_raw = str(actor_key).split("_", 1)[1]
        if not uid_raw.isdigit():
            continue
        race_features = actor.race_features if isinstance(getattr(actor, "race_features", None), dict) else {}
        if str(race_features.get("race_key") or "").strip().lower() != "tortle":
            continue
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        tracked: dict[str, Any] = {}
        for key in ("shell_defense_active", "shell_defense_entered_turn", "ac_bonus", "speed_override_ft"):
            if key in runtime:
                tracked[key] = runtime.get(key)
        if tracked:
            tortle_runtime_by_uid[int(uid_raw)] = tracked
    if not tortle_runtime_by_uid:
        return False
    _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
    changed = False
    for uid, tracked in tortle_runtime_by_uid.items():
        ch = chars_by_uid.get(uid)
        if ch is None:
            continue
        race_features_raw = getattr(ch, "race_features", None)
        race_features = dict(race_features_raw) if isinstance(race_features_raw, dict) else {}
        runtime_raw = race_features.get("runtime")
        runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
        local_changed = False
        for key, value in tracked.items():
            if runtime.get(key) != value:
                runtime[key] = value
                local_changed = True
        if not bool(tracked.get("shell_defense_active")):
            for key in ("ac_bonus", "speed_override_ft"):
                if key in runtime:
                    runtime.pop(key, None)
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
        await _auto_recover_lore_pending_on_connect(session_id)
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
                    "combat_vampiric_bite",
                    "combat_end_turn",
                    "combat_dodge",
                    "combat_dash",
                    "combat_move",
                    "combat_disengage",
                    "combat_hide",
                    "combat_takeoff",
                    "combat_land",
                    "combat_mode_walk",
                    "combat_mode_swim",
                    "combat_mode_climb",
                    "combat_escape",
                    "combat_grovel_cower_beg",
                    "combat_grung_poison_weapon",
                    "combat_hungry_jaws",
                    "combat_rabbit_hop",
                    "combat_lucky_footwork",
                    "combat_saving_face",
                    "combat_taunt",
                    "combat_fearless",
                    "combat_daunting_roar",
                    "combat_goring_rush",
                    "combat_hammering_horns",
                    "combat_eerie_token_create",
                    "combat_eerie_token_message",
                    "combat_eerie_token_view",
                    "combat_fury_of_small",
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

                if action in {
                    "group_wait",
                    "group_camp",
                    "group_camp_resolve",
                    "group_rest",
                    "group_scout",
                    "group_split",
                    "group_merge",
                    "group_move",
                    "group_context_action",
                    "group_service",
                    "group_service_use",
                    "group_map_intel",
                    "group_node_entry",
                    "group_destination_event",
                    "group_node_progress",
                    "group_region_progress",
                    "group_exploration_leads",
                    "group_journey_set",
                    "group_journey_advance",
                    "group_journey_status",
                    "group_route_planning",
                    "group_route_plan_to",
                    "group_visit_history",
                    "group_enter",
                    "group_stop",
                    "group_event_resolve",
                    "group_event_ignore",
                    "group_arrive",
                    "group_interrupt",
                    "group_pause",
                    "group_resume",
                    "group_confirm_enter",
                    "group_inspect_target",
                    "group_bypass",
                    "group_resolve_pause",
                    "group_set_mode",
                    "group_set_activity",
                    "group_clear_activity",
                }:
                    handled_group_action, group_err, group_msg = _handle_group_action_request(
                        sess,
                        action=action,
                        actor_player_id=player.id,
                        payload=data if isinstance(data, dict) else {},
                        source="ws_action",
                    )
                    if handled_group_action:
                        if group_err:
                            await ws_error(group_err, request_id=msg_request_id)
                            continue
                        await db.commit()
                        if group_msg:
                            await add_system_event(db, sess, group_msg)
                        await broadcast_state(session_id)
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

                group_action, group_payload = _parse_group_command(cmdline)
                if group_action:
                    handled_group_action, group_err, group_msg = _handle_group_action_request(
                        sess,
                        action=group_action,
                        actor_player_id=player.id,
                        payload=group_payload,
                        source="ws_command",
                    )
                    if group_err:
                        await ws_error(group_err, request_id=msg_request_id)
                        continue
                    if handled_group_action:
                        await db.commit()
                        if group_msg:
                            await add_system_event(db, sess, group_msg)
                        await broadcast_state(session_id)
                        continue

                surface = get_current_group_local_interaction_surface(
                    sess,
                    player_id=player.id,
                )
                group_action, group_payload = _match_simple_text_local_action(cmdline, surface)
                if group_action:
                    handled_group_action, group_err, group_msg = _handle_group_action_request(
                        sess,
                        action=group_action,
                        actor_player_id=player.id,
                        payload=group_payload,
                        source="ws_text_auto_map",
                    )
                    if group_err:
                        await ws_error(group_err, request_id=msg_request_id)
                        continue
                    if handled_group_action:
                        await db.commit()
                        if group_msg:
                            await add_system_event(db, sess, group_msg)
                        await broadcast_state(session_id)
                        continue

                m_simic_upgrade = re.match(
                    r"^(?:simic\s+upgrade|выбираю\s+усиление)\s+(?P<option>[^\n\r]{1,80})$",
                    cmdline,
                    re.IGNORECASE,
                )
                if m_simic_upgrade:
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    simic_err, simic_msg, simic_changed = _apply_simic_level5_upgrade(ch, m_simic_upgrade.group("option"))
                    if simic_err:
                        await ws_error(simic_err, request_id=msg_request_id)
                        continue
                    if simic_changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                        _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                        sync_pcs_from_chars(session_id, chars_by_uid)
                    await add_system_event(db, sess, simic_msg or "Животное усиление выбрано.")
                    await broadcast_state(session_id)
                    continue

                m_tinker_create = re.match(r"^tinker\s+create\s+(?P<kind>[a-z_]{3,40})$", cmdline, re.IGNORECASE)
                if m_tinker_create:
                    combat_state_now = get_combat(session_id)
                    if combat_state_now is not None and combat_state_now.active:
                        await ws_error("Гномий механик недоступен во время боя", request_id=msg_request_id)
                        continue
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    tinker_err, tinker_msg, tinker_changed = _create_tinker_device(ch, m_tinker_create.group("kind"))
                    if tinker_err:
                        await ws_error(tinker_err, request_id=msg_request_id)
                        continue
                    if tinker_changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    if tinker_msg:
                        await add_system_event(db, sess, tinker_msg)
                    await broadcast_state(session_id)
                    continue

                if re.match(r"^tinker\s+list$", cmdline, re.IGNORECASE):
                    combat_state_now = get_combat(session_id)
                    if combat_state_now is not None and combat_state_now.active:
                        await ws_error("Гномий механик недоступен во время боя", request_id=msg_request_id)
                        continue
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    tinker_err, tinker_msg, tinker_changed = _list_tinker_devices(ch)
                    if tinker_err:
                        await ws_error(tinker_err, request_id=msg_request_id)
                        continue
                    if tinker_changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    if tinker_msg:
                        await add_system_event(db, sess, tinker_msg)
                    await broadcast_state(session_id)
                    continue

                m_tinker_remove = re.match(r"^tinker\s+remove\s+(?P<device_id>[a-z0-9_]{3,40})$", cmdline, re.IGNORECASE)
                if m_tinker_remove:
                    combat_state_now = get_combat(session_id)
                    if combat_state_now is not None and combat_state_now.active:
                        await ws_error("Гномий механик недоступен во время боя", request_id=msg_request_id)
                        continue
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    tinker_err, tinker_msg, tinker_changed = _remove_tinker_device(ch, m_tinker_remove.group("device_id"))
                    if tinker_err:
                        await ws_error(tinker_err, request_id=msg_request_id)
                        continue
                    if tinker_changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    if tinker_msg:
                        await add_system_event(db, sess, tinker_msg)
                    await broadcast_state(session_id)
                    continue

                combat_action = _detect_chat_combat_action(text)
                if combat_action == "combat_fury_of_the_small":
                    combat_action = "combat_fury_of_small"
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

                if combat_action == "arm_past_life_knowledge":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    past_life_err, past_life_msg, changed = _apply_or_arm_reborn_past_life_knowledge(
                        session_id=session_id,
                        player_uid=_player_uid(player),
                        ch=ch,
                    )
                    if past_life_err:
                        await ws_error(past_life_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    if past_life_msg:
                        actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                        await add_system_event(db, sess, f"{actor_name}: {past_life_msg}")
                    await broadcast_state(session_id)
                    continue

                if combat_action == "combat_jump":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    if combat_active:
                        state_now = get_combat(session_id)
                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        turn_key = state_now.order[state_now.turn_index] if state_now and state_now.order and 0 <= state_now.turn_index < len(state_now.order) else ""
                        if not turn_key or turn_key != player_key:
                            current_name = current_turn_label(state_now) if state_now else "другой участник"
                            await add_system_event(db, sess, f"Сейчас ходит {current_name}. Дождись своего хода.")
                            await broadcast_state(session_id)
                            continue
                    jump_kind = _extract_jump_kind(cmdline)
                    jump_err, jump_msg, changed = _apply_satyr_mirthful_leaps_jump(
                        session_id=session_id,
                        player_uid=_player_uid(player),
                        ch=ch,
                        jump_kind=jump_kind,
                    )
                    if jump_err:
                        await ws_error(jump_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    if jump_msg:
                        actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                        await add_system_event(db, sess, f"{actor_name}: {jump_msg}")
                    await broadcast_state(session_id)
                    continue

                shapechanger_action, shapechanger_arg = _parse_shapechanger_command(cmdline)
                if shapechanger_action:
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    if shapechanger_action == "status":
                        shape_err, shape_msg, _shape_changed = _shapechanger_status_message(ch)
                        if shape_err:
                            await ws_error(shape_err, request_id=msg_request_id)
                            continue
                        if shape_msg:
                            actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                            await add_system_event(db, sess, f"{actor_name}: {shape_msg}")
                        await broadcast_state(session_id)
                        continue
                    if shapechanger_action == "assume" and not str(shapechanger_arg or "").strip():
                        await ws_error("Укажите описание после `shapechange assume`.", request_id=msg_request_id)
                        continue
                    if combat_active:
                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        combat_patch, shape_err, changed = _apply_shapechanger_in_combat(
                            session_id,
                            player_key,
                            ch,
                            active=shapechanger_action == "assume",
                            persona=shapechanger_arg if shapechanger_action == "assume" else "",
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
                        active=shapechanger_action == "assume",
                        persona=shapechanger_arg if shapechanger_action == "assume" else "",
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

                eerie_token_action, eerie_token_arg = _parse_eerie_token_command(cmdline)
                if eerie_token_action:
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    if combat_active and eerie_token_action in {"create", "send", "sense"}:
                        mapped_action = {
                            "create": "combat_eerie_token_create",
                            "send": "combat_eerie_token_message",
                            "sense": "combat_eerie_token_view",
                        }.get(eerie_token_action, "")
                        combat_patch, combat_err = handle_live_combat_action(
                            mapped_action,
                            session_id,
                            raw_text=text,
                        )
                        if combat_err:
                            await ws_error(combat_err, request_id=msg_request_id)
                            continue
                        if combat_patch:
                            await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_patch)
                        continue

                    eerie_err: Optional[str] = None
                    eerie_msg: Optional[str] = None
                    eerie_changed = False
                    if eerie_token_action == "create":
                        eerie_err, eerie_msg, eerie_changed = _create_eerie_token(ch)
                    elif eerie_token_action == "status":
                        eerie_err, eerie_msg, eerie_changed = _eerie_token_status_message(ch)
                    elif eerie_token_action == "remove":
                        eerie_err, eerie_msg, eerie_changed = _remove_eerie_token(ch)
                    elif eerie_token_action == "send":
                        eerie_err, eerie_msg, eerie_changed = _send_eerie_token_message(ch, eerie_token_arg or "")
                    elif eerie_token_action == "sense":
                        eerie_err, eerie_msg, eerie_changed = _activate_eerie_token_sense(ch, in_combat=False)
                    if eerie_err:
                        await ws_error(eerie_err, request_id=msg_request_id)
                        continue
                    if eerie_changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                        runtime_now = (
                            dict(ch.race_features.get("runtime"))
                            if isinstance(getattr(ch, "race_features", None), dict)
                            and isinstance(ch.race_features.get("runtime"), dict)
                            else {}
                        )
                        _sync_character_runtime_to_combat_actor(session_id, _player_uid(player), runtime_now)
                    if eerie_msg:
                        actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                        await add_system_event(db, sess, f"{actor_name}: {eerie_msg}")
                    await broadcast_state(session_id)
                    continue

                handled_mind_link, mind_link_err, mind_link_msg = await _handle_kalashtar_mind_link_action(
                    db,
                    sess,
                    player=player,
                    session_id=session_id,
                    combat_action=str(combat_action or ""),
                    raw_text=text,
                )
                if handled_mind_link:
                    if mind_link_err:
                        await ws_error(mind_link_err, request_id=msg_request_id)
                        continue
                    if mind_link_msg:
                        await add_system_event(db, sess, mind_link_msg)
                    await broadcast_state(session_id)
                    continue

                verdan_tel_action, verdan_tel_target, verdan_tel_message = _parse_verdan_telepathy_command(cmdline)
                if verdan_tel_action:
                    handled_tel, tel_err, tel_msg = await _handle_verdan_limited_telepathy_action(
                        db,
                        sess,
                        player=player,
                        session_id=session_id,
                        action=verdan_tel_action,
                        target_name=verdan_tel_target or "",
                        message_text=verdan_tel_message or "",
                    )
                    if handled_tel:
                        if tel_err:
                            await ws_error(tel_err, request_id=msg_request_id)
                            continue
                        if tel_msg:
                            actor_name = str(getattr((await get_character(db, sess.id, player.id)) or None, "name", "") or player.display_name).strip() or player.display_name
                            await add_system_event(db, sess, f"{actor_name}: {tel_msg}")
                        await broadcast_state(session_id)
                        continue

                firbolg_speech_action, firbolg_speech_message = _parse_firbolg_speech_command(cmdline)
                if await _dispatch_narrow_narrative_utility_action(
                    db,
                    sess,
                    player=player,
                    session_id=session_id,
                    request_id=msg_request_id,
                    action=firbolg_speech_action,
                    message_text=firbolg_speech_message or "",
                    handler=_handle_firbolg_speech_action,
                    ws_error_cb=ws_error,
                ):
                    continue

                kenku_mimicry_action, kenku_mimicry_message = _parse_kenku_mimicry_command(cmdline)
                if await _dispatch_narrow_narrative_utility_action(
                    db,
                    sess,
                    player=player,
                    session_id=session_id,
                    request_id=msg_request_id,
                    action=kenku_mimicry_action,
                    message_text=kenku_mimicry_message or "",
                    handler=_handle_kenku_mimicry_action,
                    ws_error_cb=ws_error,
                ):
                    continue

                kenku_forgery_action, kenku_forgery_message = _parse_kenku_expert_forgery_command(cmdline)
                if await _dispatch_narrow_narrative_utility_action(
                    db,
                    sess,
                    player=player,
                    session_id=session_id,
                    request_id=msg_request_id,
                    action=kenku_forgery_action,
                    message_text=kenku_forgery_message or "",
                    handler=_handle_kenku_expert_forgery_action,
                    ws_error_cb=ws_error,
                ):
                    continue

                loxodon_trunk_action, loxodon_trunk_message = _parse_loxodon_trunk_command(cmdline)
                if await _dispatch_narrow_narrative_utility_action(
                    db,
                    sess,
                    player=player,
                    session_id=session_id,
                    request_id=msg_request_id,
                    action=loxodon_trunk_action,
                    message_text=loxodon_trunk_message or "",
                    handler=_handle_loxodon_trunk_action,
                    ws_error_cb=ws_error,
                ):
                    continue

                mind_link_action, mind_link_arg = _parse_mind_link_command(cmdline)
                if mind_link_action:
                    synthetic_text = text
                    if mind_link_action == "mind_link_set":
                        synthetic_text = f"mind link {mind_link_arg or ''}".strip()
                    elif mind_link_action == "mind_link_say":
                        synthetic_text = f"mind: {mind_link_arg or ''}".strip()
                    elif mind_link_action == "mind_link_clear":
                        synthetic_text = "mind link off"
                    handled_mind_link, mind_link_err, mind_link_msg = await _handle_kalashtar_mind_link_action(
                        db,
                        sess,
                        player=player,
                        session_id=session_id,
                        combat_action=mind_link_action,
                        raw_text=synthetic_text,
                    )
                    if handled_mind_link:
                        if mind_link_err:
                            await ws_error(mind_link_err, request_id=msg_request_id)
                            continue
                        if mind_link_msg:
                            actor_name = str(getattr((await get_character(db, sess.id, player.id)) or None, "name", "") or player.display_name).strip() or player.display_name
                            await add_system_event(db, sess, f"{actor_name}: {mind_link_msg}")
                        await broadcast_state(session_id)
                        continue

                if combat_action in {"sunlight_on", "sunlight_off"}:
                    if not await is_admin(db, sess, player):
                        await ws_error("Только админ может переключать яркое солнце.", request_id=msg_request_id)
                        continue
                    is_on = combat_action == "sunlight_on"
                    settings_set(sess, "sunlight_bright", bool(is_on))
                    changed_combat_runtime = _set_sunlight_bright_for_session_combatants(
                        session_id,
                        sunlight_bright=bool(is_on),
                    )
                    await db.commit()
                    status = "ВКЛ" if is_on else "ВЫКЛ"
                    await add_system_event(db, sess, f"Яркое солнце: {status}.")
                    if changed_combat_runtime:
                        _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                        sync_pcs_from_chars(session_id, chars_by_uid)
                    await broadcast_state(session_id)
                    continue

                if combat_action in {"combat_fury_of_small", "combat_fury_of_the_small"} and not combat_active:
                    await ws_error("Разъярённая мелкота доступна только в бою.", request_id=msg_request_id)
                    continue
                if combat_action in {"combat_hungry_jaws", "combat_rabbit_hop", "combat_lucky_footwork", "combat_saving_face", "combat_taunt", "combat_fearless", "combat_daunting_roar", "combat_grovel_cower_beg", "combat_goring_rush", "combat_hammering_horns", "combat_adrenaline_rush", "combat_aggressive", "combat_shift", "combat_shift_end", "combat_longtooth_bite", "combat_swiftstride_step", "combat_mark_target", "combat_feline_agility", "combat_cat_claws", "combat_shell_defense", "combat_shell_defense_exit", "combat_tortle_claws", "combat_acid_spit", "combat_grapple_appendages", "combat_appendages_grapple_bonus"} and not combat_active:
                    await ws_error("Эта особенность доступна только в бою.", request_id=msg_request_id)
                    continue
                if combat_action in {"combat_eerie_token_create", "combat_eerie_token_message", "combat_eerie_token_view"} and not combat_active:
                    await ws_error("Жуткий сувенир доступен только в бою.", request_id=msg_request_id)
                    continue
                if combat_action == "combat_grung_poison_weapon" and not combat_active:
                    await ws_error("Яд грунга на оружии доступен только в бою.", request_id=msg_request_id)
                    continue
                if combat_action == "water_immerse":
                    if combat_active:
                        await ws_error("Во время боя погружение в воду недоступно.", request_id=msg_request_id)
                        continue
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    grung_iso, water_level, grung_err, grung_changed = _apply_grung_water_immersion(ch)
                    locathah_iso, loc_hours, loc_suff, loc_err, loc_changed = _apply_locathah_water_immersion(ch)
                    if grung_err and loc_err:
                        await ws_error(grung_err, request_id=msg_request_id)
                        continue
                    changed = bool(grung_changed or loc_changed)
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    immersion_hhmm = ""
                    immersion_dt = _parse_iso_datetime(locathah_iso or grung_iso)
                    if isinstance(immersion_dt, datetime):
                        immersion_hhmm = immersion_dt.astimezone().strftime("%H:%M")
                    if grung_changed:
                        await add_system_event(
                            db,
                            sess,
                            f"{actor_name}: погружение в воду засчитано (1 час/день). "
                            f"Последнее погружение: {immersion_hhmm or 'сейчас'}. Штраф воды: {max(0, as_int(water_level, 0))}.",
                        )
                    if loc_changed:
                        await add_system_event(
                            db,
                            sess,
                            f"{actor_name}: погружение в воду засчитано (локата). "
                            f"Последнее погружение: {immersion_hhmm or 'сейчас'}. "
                            f"Прошло часов: {max(0.0, float(loc_hours or 0.0)):.1f}. Задыхаетесь: {'да' if bool(loc_suff) else 'нет'}.",
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
                    elif combat_action == "arm_past_life_knowledge":
                        pass
                    elif combat_action in {"mind_link_set", "mind_link_clear", "mind_link_say", "mind_link_reply", "mind_link_status"}:
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
                        reaction_actions = {"combat_saving_face", "combat_lucky_footwork", "combat_fearless", "arm_past_life_knowledge", "combat_swiftstride_step"}
                        if combat_action not in reaction_actions:
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
                            hidden_step_broken = _break_hidden_step_for_character(ch)
                            if changed:
                                flag_modified(ch, "race_features")
                            if hidden_step_broken:
                                flag_modified(ch, "race_features")
                            await db.commit()
                            caster_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                            lines = [
                                {"text": f"{caster_name} использует врождённую магию: {spell_display_name}."},
                            ]
                            if hidden_step_broken:
                                lines.append({"text": "Незримая поступь прерывается: невидимость спадает.", "muted": True})
                            combat_state_now = get_combat(session_id)
                            round_no = combat_state_now.round_no if combat_state_now is not None else 1
                            turn_label_now = current_turn_label(combat_state_now) if combat_state_now is not None else "-"
                            patch = {
                                "status": f"⚔ Бой • Раунд {round_no} • Ход: {turn_label_now}",
                                "open": True,
                                "lines": lines,
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
                            bite_empower: Optional[str] = None
                            if combat_action == "combat_move":
                                m_dist = COMBAT_MOVE_DISTANCE_RE.search(cmdline)
                                move_distance_ft = as_int(m_dist.group(1), 0) if m_dist else 0
                            elif combat_action == "combat_vampiric_bite":
                                bite_empower = _detect_vampiric_bite_empower(text)
                            combat_patch, combat_err = handle_live_combat_action(
                                combat_action,
                                session_id,
                                distance_ft=move_distance_ft,
                                empower=bite_empower,
                                raw_text=text,
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
                            shifter_persist_changed = await _persist_shifter_runtime_from_combat_state(db, sess, session_id)
                            simic_persist_changed = await _persist_simic_runtime_from_combat_state(db, sess, session_id)
                            tortle_persist_changed = await _persist_tortle_runtime_from_combat_state(db, sess, session_id)
                            if persist_changed or shifter_persist_changed or simic_persist_changed or tortle_persist_changed:
                                await db.commit()
                                _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                                sync_pcs_from_chars(session_id, chars_by_uid)
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
                            "Combat Lock: в бою доступны только боевые команды (атака/конец хода/уклон/движение/рывок/отход/засада/взлёт/приземление/помощь/побег/пресмыкайся/разъярённая мелкота/яд грунга на оружии/голодная пасть/кроличий прыжок/сильные ноги/сохранить лицо/насмешка/бесстрашие/устрашающий рёв/агрессивный/смена формы/снять форму/укус длиннозуба/шаг быстронога/пометить цель/кошачья ловкость/когти кошки/защита панцирем/вылезти из панциря/когти тортла/хватательные придатки/схватить придатками/кислотный плевок/жуткий сувенир/каменная выносливость/исцеляющие руки/небесное преобразование/незримая поступь/подводное дыхание/оружие дыхания) или OOC/телепатия (mind link) / знания reborn.",
                            request_id=msg_request_id,
                        )
                        continue

                # OOC (any time, no turn)
                if combat_action == "combat_breath_weapon":
                    await ws_error("Оружие дыхания можно применить только в бою.", request_id=msg_request_id)
                    continue
                if combat_action == "combat_hidden_step":
                    await ws_error("Незримую поступь можно применить только в бою.", request_id=msg_request_id)
                    continue
                if combat_action in {"combat_adrenaline_rush", "combat_aggressive"}:
                    await ws_error("Прилив адреналина можно применить только в бою.", request_id=msg_request_id)
                    continue
                if combat_action in {"combat_feline_agility", "combat_cat_claws"}:
                    await ws_error("Особенности табакси доступны только в бою.", request_id=msg_request_id)
                    continue
                if combat_action in {"combat_shell_defense", "combat_shell_defense_exit", "combat_tortle_claws"}:
                    await ws_error("Особенности тортла доступны только в бою.", request_id=msg_request_id)
                    continue
                if combat_action in {"combat_acid_spit", "combat_grapple_appendages", "combat_appendages_grapple_bonus"}:
                    await ws_error("Эта способность Simic доступна только в бою.", request_id=msg_request_id)
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
                    changed = _reset_racial_rest_uses(ch, long_rest=True)
                    water_level, water_changed = _apply_grung_water_dependency_long_rest(ch)
                    loc_hours, loc_suff, loc_changed = _apply_locathah_limited_amphibious_status(ch)
                    if changed:
                        flag_modified(ch, "race_features")
                    if water_changed:
                        flag_modified(ch, "race_features")
                    if loc_changed:
                        flag_modified(ch, "race_features")
                    if _reset_harengon_long_rest(ch):
                        flag_modified(ch, "race_features")
                    player_uid = _player_uid(player)
                    player_key = f"pc_{player_uid}" if player_uid is not None else ""
                    _reset_combatant_racial_rest_uses(session_id, player_key, long_rest=True)
                    _reset_combatant_harengon_long_rest(session_id, player_key)
                    await db.commit()
                    water_suffix = f" Водная зависимость (грунг): уровень штрафа {max(0, int(water_level))}."
                    loc_suffix = (
                        f" Частичная земноводность (локата): прошло {max(0.0, float(loc_hours or 0.0)):.1f} ч, "
                        f"задыхаетесь: {'да' if bool(loc_suff) else 'нет'}."
                    )
                    await add_system_event(
                        db,
                        sess,
                        f"Долгий отдых: врождённые заклинания восстановлены."
                        f"{water_suffix if water_changed else ''}"
                        f"{loc_suffix if loc_changed else ''}",
                    )
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
                        "init / init roll / init set <#> <val> / init start / init clear (админ), "
                        "tinker create <clockwork_toy|fire_starter|music_box>, tinker list, tinker remove <id>, "
                        "speech status|speech beast: <идея>|speech plant: <идея>, "
                        "mimicry status|mimicry voice: <фраза>|mimicry sound: <звук>, "
                        "forgery status|forgery copy: <что копируете>, "
                        "trunk status|trunk use: <простое действие>, "
                        "eerie token create|status|remove|send <message>|sense, "
                        "shapechange assume <description>|status|revert."
                    )
                    await broadcast_state(session_id)
                    continue

                if lower == "char":
                    await add_system_event(
                        db,
                        sess,
                        "de" "ps.Character commands: char create <Name> [Class], me, hp <+N|-N|N>, sta <+N|-N|N>, rest|rest long|rest short|rest hd <N>, "
                        "stat <str|dex|con|int|wis|cha> <0..100>, check|statcheck|skillcheck [adv|dis] [pastlife] <цель> [dc N] (ручной бросок, опционально), "
                        "toolcheck [adv|dis] [pastlife] <tool_key> [dc N], "
                        "save [magic] [adv|dis] [footwork] <str|dex|con|int|wis|cha> [vs <poison|frightened|charmed>] [dc N], "
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
                    if _reset_racial_rest_uses(ch, long_rest=True):
                        flag_modified(ch, "race_features")
                    water_level, water_changed = _apply_grung_water_dependency_long_rest(ch)
                    loc_hours, loc_suff, loc_changed = _apply_locathah_limited_amphibious_status(ch)
                    if water_changed:
                        flag_modified(ch, "race_features")
                    if loc_changed:
                        flag_modified(ch, "race_features")
                    if _reset_harengon_long_rest(ch):
                        flag_modified(ch, "race_features")
                    player_uid = _player_uid(player)
                    player_key = f"pc_{player_uid}" if player_uid is not None else ""
                    _reset_combatant_racial_rest_uses(session_id, player_key, long_rest=True)
                    _reset_combatant_harengon_long_rest(session_id, player_key)
                    await db.commit()
                    await add_system_event(
                        db,
                        sess,
                        f"[REST] long {ch.name}: HP {old_hp}->{int(ch.hp or 0)}/{int(ch.hp_max or 0)}, "
                        f"STA {old_sta}->{int(ch.sta or 0)}/{int(ch.sta_max or 0)}, "
                        f"HD {hd_before}->{hd_after}/{hd_max} (d{max(1, as_int(getattr(ch, 'hit_die', 8), 8))}), "
                        f"water_dep={max(0, int(water_level))}, "
                        f"locathah_hours={max(0.0, float(loc_hours or 0.0)):.1f}, "
                        f"locathah_suffocating={'yes' if bool(loc_suff) else 'no'}",
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
                    if _reset_racial_rest_uses(ch, long_rest=False):
                        flag_modified(ch, "race_features")
                    player_uid = _player_uid(player)
                    player_key = f"pc_{player_uid}" if player_uid is not None else ""
                    _reset_combatant_racial_rest_uses(session_id, player_key, long_rest=False)
                    await db.commit()
                    await add_system_event(
                        db,
                        sess,
                        f"[REST] short {ch.name}: STA {old_sta}->{int(ch.sta or 0)}/{int(ch.sta_max or 0)}",
                    )
                    if _lizardfolk_cunning_artisan_feature(getattr(ch, "race_features", None)):
                        await add_system_event(
                            db,
                            sess,
                            "Умелый ремесленник: на коротком отдыхе можно создать craft shield/club/javelin/darts/needles.",
                        )
                    await broadcast_state(session_id)
                    continue

                m_craft = re.match(r"^(?:craft|создаю|смастерить)\s+(.+)$", cmdline, re.IGNORECASE)
                if m_craft:
                    combat_state_now = get_combat(session_id)
                    if combat_state_now is not None and combat_state_now.active:
                        await ws_error("Ремесло недоступно во время боя", request_id=msg_request_id)
                        continue
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue
                    option = str(m_craft.group(1) or "").strip()
                    craft_msg, craft_err, changed = _apply_lizardfolk_cunning_artisan_craft(ch, option)
                    if craft_err:
                        await ws_error(craft_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "stats")
                        await db.commit()
                    if craft_msg:
                        await add_system_event(db, sess, craft_msg)
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

                if lower.startswith(("check", "statcheck", "skillcheck")):
                    command_kind, mode, use_past_life, key, dc, check_tag, parse_error = _parse_check_command(cmdline)
                    if parse_error:
                        await ws_error(parse_error, request_id=msg_request_id)
                        continue
                    if not command_kind or not mode or not key:
                        await ws_error(
                            "Использование: check|statcheck|skillcheck [adv|dis] [pastlife] <цель> [dc N]",
                            request_id=msg_request_id,
                        )
                        continue
                    if command_kind == "statcheck" and key not in CHAR_STAT_KEYS:
                        await ws_error(
                            "Использование: statcheck [adv|dis] [pastlife] <str|dex|con|int|wis|cha> [dc N]",
                            request_id=msg_request_id,
                        )
                        continue
                    if command_kind == "skillcheck" and (key in CHAR_STAT_KEYS or "|" in key):
                        await ws_error(
                            "Использование: skillcheck [adv|dis] [pastlife] <skill> [dc N]",
                            request_id=msg_request_id,
                        )
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
                        skill_proficient = False
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
                        skill_proficient = bool(sk and int(getattr(sk, "rank", 0) or 0) > 0)
                    if "|" in key:
                        skill_proficient = False
                    elif key in CHAR_STAT_KEYS:
                        skill_proficient = False

                    mapped_mode = {
                        "roll": "normal",
                        "adv": "advantage",
                        "dis": "disadvantage",
                    }.get(mode, "normal")
                    mapped_mode = _mode_with_poisoned_disadvantage(mapped_mode, getattr(ch, "race_features", None))
                    mapped_mode = _mode_with_sunlight_disadvantage(
                        mapped_mode,
                        getattr(ch, "race_features", None),
                        sunlight_bright=bool(settings_get(sess, "sunlight_bright", False)),
                        check_name=key,
                    )
                    mapped_mode = _mode_with_keen_smell_advantage(
                        mapped_mode,
                        getattr(ch, "race_features", None),
                        check_name=key,
                        check_tag=check_tag,
                    )
                    mapped_mode = _mode_with_shifter_wildhunt_advantage(
                        mapped_mode,
                        getattr(ch, "race_features", None),
                        check_name=key,
                        kind="ability" if key in CHAR_STAT_KEYS else "skill",
                    )
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
                    vamp_bonus, vamp_bonus_text, vamp_changed = _consume_vampiric_bite_bonus_for_d20(ch)
                    past_life_bonus, past_life_bonus_text, past_life_uses_text, past_life_changed, past_life_error = (
                        _consume_reborn_past_life_bonus_for_check(
                            ch,
                            requested=use_past_life,
                            kind=str(check_payload["kind"]),
                        )
                    )
                    if past_life_error:
                        await ws_error(past_life_error, request_id=msg_request_id)
                        continue
                    legacy_past_life_bonus = 0
                    legacy_past_life_bonus_text: Optional[str] = None
                    legacy_past_life_changed = False
                    if not use_past_life:
                        legacy_past_life_bonus, legacy_past_life_bonus_text, legacy_past_life_changed = (
                            _consume_reborn_past_life_for_skill_check(
                                ch,
                                kind=str(check_payload["kind"]),
                            )
                        )
                    if bfs_changed:
                        flag_modified(ch, "race_features")
                    if vamp_changed:
                        flag_modified(ch, "race_features")
                    if past_life_changed:
                        flag_modified(ch, "race_features")
                        runtime_now = (
                            dict(ch.race_features.get("runtime"))
                            if isinstance(getattr(ch, "race_features", None), dict)
                            and isinstance(ch.race_features.get("runtime"), dict)
                            else {}
                        )
                        _sync_character_runtime_to_combat_actor(session_id, _player_uid(player), runtime_now)
                    if legacy_past_life_changed:
                        runtime_now = (
                            dict(ch.race_features.get("runtime"))
                            if isinstance(getattr(ch, "race_features", None), dict)
                            and isinstance(ch.race_features.get("runtime"), dict)
                            else {}
                        )
                        _sync_character_runtime_to_combat_actor(session_id, _player_uid(player), runtime_now)
                    if legacy_past_life_changed:
                        flag_modified(ch, "race_features")
                    if bfs_changed or vamp_changed or past_life_changed or legacy_past_life_changed:
                        await db.commit()
                    tp_bonus, tp_bonus_text = _tireless_precision_bonus_for_check(
                        getattr(ch, "race_features", None),
                        kind=str(check_payload["kind"]),
                        key=key,
                        proficient=skill_proficient,
                    )
                    total = (
                        base_total
                        + tp_bonus
                        + bfs_bonus
                        + vamp_bonus
                        + past_life_bonus
                        + legacy_past_life_bonus
                    )
                    msg = _format_check_log(
                        character_name=ch.name,
                        key=key,
                        roll_a=ra,
                        roll_b=rb,
                        roll=roll,
                        mod=mod,
                        tp_bonus_text=tp_bonus_text,
                        extra_bonus_texts=[
                            bfs_bonus_text,
                            vamp_bonus_text,
                            past_life_bonus_text,
                            legacy_past_life_bonus_text,
                        ],
                        past_life_uses_text=past_life_uses_text,
                        total=total,
                        dc=dc,
                    )
                    if dc is not None:
                        ok = total >= dc
                        if not ok:
                            sf_bonus = _hobgoblin_mark_saving_face_pending(
                                session_id=session_id,
                                player_uid=_player_uid(player),
                                ch=ch,
                                kind="check",
                                dc=dc,
                                total=total,
                                details={"name": key},
                            )
                            if sf_bonus > 0:
                                flag_modified(ch, "race_features")
                                await db.commit()
                                msg += f" | Можно реакцией «Сохранить лицо» добавить +{sf_bonus}."
                            if _reborn_mark_past_life_pending(
                                session_id=session_id,
                                player_uid=_player_uid(player),
                                ch=ch,
                                dc=dc,
                                total=total,
                                skill_key=key,
                            ):
                                flag_modified(ch, "race_features")
                                await db.commit()
                                msg += " | Можно применить «Знания из прошлой жизни» и добавить 1к6 после броска."
                    await add_system_event(db, sess, msg)
                    await broadcast_state(session_id)
                    continue

                if lower.startswith("toolcheck"):
                    mapped_mode, tool_key, dc, use_past_life, parse_error = _parse_toolcheck_command(cmdline)
                    if parse_error:
                        await ws_error(parse_error, request_id=msg_request_id)
                        continue
                    if not tool_key or not mapped_mode:
                        await ws_error("Использование: toolcheck [adv|dis] [pastlife] <tool_key> [dc N]", request_id=msg_request_id)
                        continue

                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("No character. Use: char create ...", request_id=msg_request_id)
                        continue

                    toolcheck_error = _toolcheck_access_error(ch, tool_key)
                    if toolcheck_error:
                        await ws_error(toolcheck_error, request_id=msg_request_id)
                        continue

                    mod = 0
                    mapped_mode = _mode_with_poisoned_disadvantage(mapped_mode, getattr(ch, "race_features", None))
                    mapped_mode = _mode_with_sunlight_disadvantage(
                        mapped_mode,
                        getattr(ch, "race_features", None),
                        sunlight_bright=bool(settings_get(sess, "sunlight_bright", False)),
                    )
                    ra, rb, roll = roll_check(
                        mapped_mode,
                        reroll_ones=_lucky_scope_enabled(getattr(ch, "race_features", None), "check"),
                    )
                    check_payload = {
                        "actor_uid": _player_uid(player),
                        "kind": "tool",
                        "name": tool_key,
                        "dc": dc if dc is not None else 0,
                        "mode": mapped_mode,
                    }
                    res = build_check_result(check_payload, mod=mod, roll_a=ra, roll_b=rb, roll=roll)
                    base_total = int(res["total"])
                    vamp_bonus, vamp_bonus_text, vamp_changed = _consume_vampiric_bite_bonus_for_d20(ch)
                    past_life_bonus, past_life_bonus_text, past_life_uses_text, past_life_changed, past_life_error = (
                        _consume_reborn_past_life_bonus_for_check(
                            ch,
                            requested=use_past_life,
                            kind="tool",
                        )
                    )
                    if past_life_error:
                        await ws_error(past_life_error, request_id=msg_request_id)
                        continue
                    if vamp_changed:
                        flag_modified(ch, "race_features")
                    if past_life_changed:
                        flag_modified(ch, "race_features")
                        runtime_now = (
                            dict(ch.race_features.get("runtime"))
                            if isinstance(getattr(ch, "race_features", None), dict)
                            and isinstance(ch.race_features.get("runtime"), dict)
                            else {}
                        )
                        _sync_character_runtime_to_combat_actor(session_id, _player_uid(player), runtime_now)
                    if vamp_changed or past_life_changed:
                        await db.commit()
                    tp_bonus, tp_bonus_text = _tireless_precision_bonus_for_check(
                        getattr(ch, "race_features", None),
                        kind="tool",
                        key=tool_key,
                    )
                    total = base_total + tp_bonus + vamp_bonus + past_life_bonus
                    msg = _format_toolcheck_log(
                        tool_name_ru=_tool_label_ru(tool_key),
                        mode=mapped_mode,
                        roll_a=ra,
                        roll_b=rb,
                        roll=roll,
                        mod=mod,
                        tp_bonus=tp_bonus,
                        tp_bonus_text=tp_bonus_text,
                        extra_bonus_texts=[
                            text
                            for text in (
                                vamp_bonus_text,
                                f"{past_life_bonus_text.replace('Knowledge from a Past Life ', 'Knowledge from a Past Life: +')}"
                                if past_life_bonus_text
                                else "",
                            )
                            if text
                        ],
                        past_life_uses_text=past_life_uses_text,
                        total=total,
                        dc=dc,
                    )
                    if dc is not None:
                        ok = total >= dc
                        if not ok:
                            sf_bonus = _hobgoblin_mark_saving_face_pending(
                                session_id=session_id,
                                player_uid=_player_uid(player),
                                ch=ch,
                                kind="tool",
                                dc=dc,
                                total=total,
                                details={"tool": tool_key},
                            )
                            if sf_bonus > 0:
                                flag_modified(ch, "race_features")
                                await db.commit()
                                msg += f" | Можно реакцией «Сохранить лицо» добавить +{sf_bonus}."
                    await add_system_event(db, sess, msg)
                    await broadcast_state(session_id)
                    continue

                if lower.startswith("save"):
                    is_magic_save, mode, use_footwork, ability, vs_tag, dc, parse_error = _parse_save_command(cmdline)
                    if parse_error:
                        await ws_error(parse_error, request_id=msg_request_id)
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
                    auto_advantage_reason = (
                        _auto_save_advantage_reason(
                            getattr(ch, "race_features", None),
                            ability,
                            vs_magic=is_magic_save,
                            vs_tag=vs_tag,
                        )
                        if requested_mode == "normal" and mapped_mode == "advantage"
                        else ""
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
                    base_total_with_bonus = base_total + bfs_bonus
                    footwork_bonus = 0
                    footwork_bonus_text = ""
                    footwork_note = ""
                    footwork_changed = False
                    footwork_error = None
                    if use_footwork:
                        (
                            footwork_bonus,
                            footwork_bonus_text,
                            footwork_note,
                            footwork_changed,
                            footwork_error,
                        ) = _consume_harengon_lucky_footwork_for_save(
                            ch,
                            session_id=session_id,
                            player_uid=_player_uid(player),
                            requested=True,
                            ability=ability,
                            base_total=base_total_with_bonus,
                            dc=dc,
                        )
                    if footwork_error:
                        await ws_error(footwork_error, request_id=msg_request_id)
                        continue
                    if bfs_changed:
                        pass
                    if footwork_changed:
                        flag_modified(ch, "race_features")
                        runtime_now = (
                            dict(ch.race_features.get("runtime"))
                            if isinstance(getattr(ch, "race_features", None), dict)
                            and isinstance(ch.race_features.get("runtime"), dict)
                            else {}
                        )
                        _sync_character_runtime_to_combat_actor(session_id, _player_uid(player), runtime_now)
                    if bfs_changed or footwork_changed:
                        await db.commit()
                    total = base_total_with_bonus + footwork_bonus
                    save_prefix = "save magic" if is_magic_save else "save"
                    msg = _format_save_log(
                        character_name=ch.name,
                        save_prefix=save_prefix,
                        ability=ability,
                        vs_tag=vs_tag,
                        mode=mapped_mode,
                        roll_a=ra,
                        roll_b=rb,
                        roll=roll,
                        mod=mod,
                        extra_bonus_texts=[bfs_bonus_text] if bfs_bonus > 0 and bfs_bonus_text else [],
                        auto_advantage_reason=auto_advantage_reason,
                        total=base_total_with_bonus if use_footwork else total,
                        dc=dc,
                        footwork_note=footwork_note,
                        footwork_bonus_text=footwork_bonus_text,
                        footwork_new_total=total if use_footwork and footwork_bonus_text else None,
                    )
                    if dc is not None:
                        ok = total >= dc
                        if not ok and not use_footwork:
                            if (
                                ability == "dex"
                                and _harengon_mark_failed_dex_save_context(
                                    session_id=session_id,
                                    player_uid=_player_uid(player),
                                    ch=ch,
                                    dc=dc,
                                    total=total,
                                )
                            ):
                                flag_modified(ch, "race_features")
                                await db.commit()
                                msg += " | Можно реакцией «Сильные ноги» добавить 1d4."
                            sf_bonus = _hobgoblin_mark_saving_face_pending(
                                session_id=session_id,
                                player_uid=_player_uid(player),
                                ch=ch,
                                kind="save",
                                dc=dc,
                                total=total,
                                details={"ability": ability},
                            )
                            if sf_bonus > 0:
                                flag_modified(ch, "race_features")
                                await db.commit()
                                msg += f" | Можно реакцией «Сохранить лицо» добавить +{sf_bonus}."
                            if (
                                _normalize_save_tag(vs_tag) == "frightened"
                                and _kender_mark_fearless_pending(
                                    session_id=session_id,
                                    player_uid=_player_uid(player),
                                    ch=ch,
                                    dc=dc,
                                    total=total,
                                    ability=ability,
                                    vs_tag=vs_tag,
                                )
                            ):
                                flag_modified(ch, "race_features")
                                await db.commit()
                                msg += " | Можно реакцией «Бесстрашие» сделать спасбросок успешным (1/дл. отдых)."
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
                        hare_trigger_rows: list[str] = []
                        init_roll_details: dict[str, tuple[int, int, int, int]] = {}
                        for spx in sps_active:
                            ch = chars_by_pid.get(spx.player_id)
                            val, base, dex_mod, hare_bonus = _roll_initiative_details(ch, rng=random)
                            _set_init_value(sess, spx.player_id, val)
                            init_roll_details[str(spx.player_id)] = (val, base, dex_mod, hare_bonus)
                        await db.commit()
                        init_map = _get_init_map(sess)
                        lines = []
                        for spx in sps_active:
                            nm = names.get(str(spx.player_id), str(spx.player_id))
                            detail = init_roll_details.get(str(spx.player_id))
                            if detail is not None:
                                total, base, dex_mod, hare_bonus = detail
                                total = int(init_map.get(str(spx.player_id), total) or 0)
                                lines.append(f"  #{spx.join_order} {_format_initiative_roll_line(nm, total=total, base=base, dex_mod=dex_mod, hare_bonus=hare_bonus)}")
                                if hare_bonus > 0:
                                    hare_trigger_rows.append(f"  #{spx.join_order} {nm}: +{hare_bonus} (Заячье сердце)")
                            else:
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

                if combat_action == "arm_past_life_knowledge":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    past_life_err, past_life_msg, changed = _apply_or_arm_reborn_past_life_knowledge(
                        session_id=session_id,
                        player_uid=_player_uid(player),
                        ch=ch,
                    )
                    if past_life_err:
                        await ws_error(past_life_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    if past_life_msg:
                        actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                        await add_system_event(db, sess, f"{actor_name}: {past_life_msg}")
                    await broadcast_state(session_id)
                    continue

                if combat_action == "combat_jump":
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    if combat_active:
                        state_now = get_combat(session_id)
                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        turn_key = state_now.order[state_now.turn_index] if state_now and state_now.order and 0 <= state_now.turn_index < len(state_now.order) else ""
                        if not turn_key or turn_key != player_key:
                            current_name = current_turn_label(state_now) if state_now else "другой участник"
                            await add_system_event(db, sess, f"Сейчас ходит {current_name}. Дождись своего хода.")
                            await broadcast_state(session_id)
                            continue
                    jump_kind = _extract_jump_kind(cmdline)
                    jump_err, jump_msg, changed = _apply_satyr_mirthful_leaps_jump(
                        session_id=session_id,
                        player_uid=_player_uid(player),
                        ch=ch,
                        jump_kind=jump_kind,
                    )
                    if jump_err:
                        await ws_error(jump_err, request_id=msg_request_id)
                        continue
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    if jump_msg:
                        actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                        await add_system_event(db, sess, f"{actor_name}: {jump_msg}")
                    await broadcast_state(session_id)
                    continue

                shapechanger_action, shapechanger_arg = _parse_shapechanger_command(cmdline)
                if shapechanger_action:
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    if shapechanger_action == "status":
                        shape_err, shape_msg, _shape_changed = _shapechanger_status_message(ch)
                        if shape_err:
                            await ws_error(shape_err, request_id=msg_request_id)
                            continue
                        if shape_msg:
                            actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                            await add_system_event(db, sess, f"{actor_name}: {shape_msg}")
                        await broadcast_state(session_id)
                        continue
                    if shapechanger_action == "assume" and not str(shapechanger_arg or "").strip():
                        await ws_error("Укажите описание после `shapechange assume`.", request_id=msg_request_id)
                        continue
                    if combat_active:
                        player_uid = _player_uid(player)
                        player_key = f"pc_{player_uid}" if player_uid is not None else ""
                        combat_patch, shape_err, changed = _apply_shapechanger_in_combat(
                            session_id,
                            player_key,
                            ch,
                            active=shapechanger_action == "assume",
                            persona=shapechanger_arg if shapechanger_action == "assume" else "",
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
                        active=shapechanger_action == "assume",
                        persona=shapechanger_arg if shapechanger_action == "assume" else "",
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

                eerie_token_action, eerie_token_arg = _parse_eerie_token_command(cmdline)
                if eerie_token_action:
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    if combat_active and eerie_token_action in {"create", "send", "sense"}:
                        mapped_action = {
                            "create": "combat_eerie_token_create",
                            "send": "combat_eerie_token_message",
                            "sense": "combat_eerie_token_view",
                        }.get(eerie_token_action, "")
                        combat_patch, combat_err = handle_live_combat_action(
                            mapped_action,
                            session_id,
                            raw_text=text,
                        )
                        if combat_err:
                            await ws_error(combat_err, request_id=msg_request_id)
                            continue
                        if combat_patch:
                            await _broadcast_state_unlocked(session_id, combat_log_ui_patch=combat_patch)
                        continue

                    eerie_err: Optional[str] = None
                    eerie_msg: Optional[str] = None
                    eerie_changed = False
                    if eerie_token_action == "create":
                        eerie_err, eerie_msg, eerie_changed = _create_eerie_token(ch)
                    elif eerie_token_action == "status":
                        eerie_err, eerie_msg, eerie_changed = _eerie_token_status_message(ch)
                    elif eerie_token_action == "remove":
                        eerie_err, eerie_msg, eerie_changed = _remove_eerie_token(ch)
                    elif eerie_token_action == "send":
                        eerie_err, eerie_msg, eerie_changed = _send_eerie_token_message(ch, eerie_token_arg or "")
                    elif eerie_token_action == "sense":
                        eerie_err, eerie_msg, eerie_changed = _activate_eerie_token_sense(ch, in_combat=False)
                    if eerie_err:
                        await ws_error(eerie_err, request_id=msg_request_id)
                        continue
                    if eerie_changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                        runtime_now = (
                            dict(ch.race_features.get("runtime"))
                            if isinstance(getattr(ch, "race_features", None), dict)
                            and isinstance(ch.race_features.get("runtime"), dict)
                            else {}
                        )
                        _sync_character_runtime_to_combat_actor(session_id, _player_uid(player), runtime_now)
                    if eerie_msg:
                        actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                        await add_system_event(db, sess, f"{actor_name}: {eerie_msg}")
                    await broadcast_state(session_id)
                    continue

                handled_mind_link, mind_link_err, mind_link_msg = await _handle_kalashtar_mind_link_action(
                    db,
                    sess,
                    player=player,
                    session_id=session_id,
                    combat_action=str(combat_action or ""),
                    raw_text=text,
                )
                if handled_mind_link:
                    if mind_link_err:
                        await ws_error(mind_link_err, request_id=msg_request_id)
                        continue
                    if mind_link_msg:
                        await add_system_event(db, sess, mind_link_msg)
                    await broadcast_state(session_id)
                    continue

                verdan_tel_action, verdan_tel_target, verdan_tel_message = _parse_verdan_telepathy_command(cmdline)
                if verdan_tel_action:
                    handled_tel, tel_err, tel_msg = await _handle_verdan_limited_telepathy_action(
                        db,
                        sess,
                        player=player,
                        session_id=session_id,
                        action=verdan_tel_action,
                        target_name=verdan_tel_target or "",
                        message_text=verdan_tel_message or "",
                    )
                    if handled_tel:
                        if tel_err:
                            await ws_error(tel_err, request_id=msg_request_id)
                            continue
                        if tel_msg:
                            actor_name = str(getattr((await get_character(db, sess.id, player.id)) or None, "name", "") or player.display_name).strip() or player.display_name
                            await add_system_event(db, sess, f"{actor_name}: {tel_msg}")
                        await broadcast_state(session_id)
                        continue

                firbolg_speech_action, firbolg_speech_message = _parse_firbolg_speech_command(cmdline)
                if await _dispatch_narrow_narrative_utility_action(
                    db,
                    sess,
                    player=player,
                    session_id=session_id,
                    request_id=msg_request_id,
                    action=firbolg_speech_action,
                    message_text=firbolg_speech_message or "",
                    handler=_handle_firbolg_speech_action,
                    ws_error_cb=ws_error,
                ):
                    continue

                kenku_mimicry_action, kenku_mimicry_message = _parse_kenku_mimicry_command(cmdline)
                if await _dispatch_narrow_narrative_utility_action(
                    db,
                    sess,
                    player=player,
                    session_id=session_id,
                    request_id=msg_request_id,
                    action=kenku_mimicry_action,
                    message_text=kenku_mimicry_message or "",
                    handler=_handle_kenku_mimicry_action,
                    ws_error_cb=ws_error,
                ):
                    continue

                kenku_forgery_action, kenku_forgery_message = _parse_kenku_expert_forgery_command(cmdline)
                if await _dispatch_narrow_narrative_utility_action(
                    db,
                    sess,
                    player=player,
                    session_id=session_id,
                    request_id=msg_request_id,
                    action=kenku_forgery_action,
                    message_text=kenku_forgery_message or "",
                    handler=_handle_kenku_expert_forgery_action,
                    ws_error_cb=ws_error,
                ):
                    continue

                loxodon_trunk_action, loxodon_trunk_message = _parse_loxodon_trunk_command(cmdline)
                if await _dispatch_narrow_narrative_utility_action(
                    db,
                    sess,
                    player=player,
                    session_id=session_id,
                    request_id=msg_request_id,
                    action=loxodon_trunk_action,
                    message_text=loxodon_trunk_message or "",
                    handler=_handle_loxodon_trunk_action,
                    ws_error_cb=ws_error,
                ):
                    continue

                mind_link_action, mind_link_arg = _parse_mind_link_command(cmdline)
                if mind_link_action:
                    synthetic_text = text
                    if mind_link_action == "mind_link_set":
                        synthetic_text = f"mind link {mind_link_arg or ''}".strip()
                    elif mind_link_action == "mind_link_say":
                        synthetic_text = f"mind: {mind_link_arg or ''}".strip()
                    elif mind_link_action == "mind_link_clear":
                        synthetic_text = "mind link off"
                    handled_mind_link, mind_link_err, mind_link_msg = await _handle_kalashtar_mind_link_action(
                        db,
                        sess,
                        player=player,
                        session_id=session_id,
                        combat_action=mind_link_action,
                        raw_text=synthetic_text,
                    )
                    if handled_mind_link:
                        if mind_link_err:
                            await ws_error(mind_link_err, request_id=msg_request_id)
                            continue
                        if mind_link_msg:
                            actor_name = str(getattr((await get_character(db, sess.id, player.id)) or None, "name", "") or player.display_name).strip() or player.display_name
                            await add_system_event(db, sess, f"{actor_name}: {mind_link_msg}")
                        await broadcast_state(session_id)
                        continue

                if combat_action in {"sunlight_on", "sunlight_off"}:
                    if not await is_admin(db, sess, player):
                        await ws_error("Только админ может переключать яркое солнце.", request_id=msg_request_id)
                        continue
                    is_on = combat_action == "sunlight_on"
                    settings_set(sess, "sunlight_bright", bool(is_on))
                    changed_combat_runtime = _set_sunlight_bright_for_session_combatants(
                        session_id,
                        sunlight_bright=bool(is_on),
                    )
                    await db.commit()
                    status = "ВКЛ" if is_on else "ВЫКЛ"
                    await add_system_event(db, sess, f"Яркое солнце: {status}.")
                    if changed_combat_runtime:
                        _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                        sync_pcs_from_chars(session_id, chars_by_uid)
                    await broadcast_state(session_id)
                    continue

                if combat_action in {"combat_fury_of_small", "combat_fury_of_the_small"} and not combat_active:
                    await ws_error("Разъярённая мелкота доступна только в бою.", request_id=msg_request_id)
                    continue
                if combat_action in {"combat_hungry_jaws", "combat_rabbit_hop", "combat_lucky_footwork", "combat_saving_face", "combat_taunt", "combat_fearless", "combat_daunting_roar", "combat_grovel_cower_beg", "combat_goring_rush", "combat_hammering_horns", "combat_adrenaline_rush", "combat_aggressive", "combat_shift", "combat_shift_end", "combat_longtooth_bite", "combat_swiftstride_step", "combat_mark_target", "combat_feline_agility", "combat_cat_claws", "combat_shell_defense", "combat_shell_defense_exit", "combat_tortle_claws", "combat_acid_spit", "combat_grapple_appendages", "combat_appendages_grapple_bonus"} and not combat_active:
                    await ws_error("Эта особенность доступна только в бою.", request_id=msg_request_id)
                    continue
                if combat_action in {"combat_eerie_token_create", "combat_eerie_token_message", "combat_eerie_token_view"} and not combat_active:
                    await ws_error("Жуткий сувенир доступен только в бою.", request_id=msg_request_id)
                    continue
                if combat_action == "combat_grung_poison_weapon" and not combat_active:
                    await ws_error("Яд грунга на оружии доступен только в бою.", request_id=msg_request_id)
                    continue
                if combat_action == "water_immerse":
                    if combat_active:
                        await ws_error("Во время боя погружение в воду недоступно.", request_id=msg_request_id)
                        continue
                    ch = await get_character(db, sess.id, player.id)
                    if not ch:
                        await ws_error("Персонаж не найден.", request_id=msg_request_id)
                        continue
                    grung_iso, water_level, grung_err, grung_changed = _apply_grung_water_immersion(ch)
                    locathah_iso, loc_hours, loc_suff, loc_err, loc_changed = _apply_locathah_water_immersion(ch)
                    if grung_err and loc_err:
                        await ws_error(grung_err, request_id=msg_request_id)
                        continue
                    changed = bool(grung_changed or loc_changed)
                    if changed:
                        flag_modified(ch, "race_features")
                        await db.commit()
                    actor_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                    immersion_hhmm = ""
                    immersion_dt = _parse_iso_datetime(locathah_iso or grung_iso)
                    if isinstance(immersion_dt, datetime):
                        immersion_hhmm = immersion_dt.astimezone().strftime("%H:%M")
                    if grung_changed:
                        await add_system_event(
                            db,
                            sess,
                            f"{actor_name}: погружение в воду засчитано (1 час/день). "
                            f"Последнее погружение: {immersion_hhmm or 'сейчас'}. Штраф воды: {max(0, as_int(water_level, 0))}.",
                        )
                    if loc_changed:
                        await add_system_event(
                            db,
                            sess,
                            f"{actor_name}: погружение в воду засчитано (локата). "
                            f"Последнее погружение: {immersion_hhmm or 'сейчас'}. "
                            f"Прошло часов: {max(0.0, float(loc_hours or 0.0)):.1f}. Задыхаетесь: {'да' if bool(loc_suff) else 'нет'}.",
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
                    if combat_action == "arm_past_life_knowledge":
                        pass
                    innate_spell_key = _detect_innate_spell_key(text) if combat_action == "combat_innate_spell" else None
                    actor_label = await _event_actor_label(db, sess, player)
                    pid = str(player.id)
                    current_position = _get_player_position_context(sess, pid)
                    current_zone = str(current_position.get("zone_label") or "стартовая локация")
                    new_zone_preview = current_zone
                    position_payload = _build_player_action_position_payload(
                        sess,
                        player.id,
                        zone_after=new_zone_preview,
                        map_position_after=_get_player_map_position(sess, player.id),
                    )
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
                        "turn_index": int(sess.turn_index or 0),
                        "combat_chat_action": combat_action,
                        "spell_key": innate_spell_key,
                    }
                    payload.update(position_payload)
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
                        reaction_actions = {"combat_saving_face", "combat_lucky_footwork", "combat_fearless", "arm_past_life_knowledge", "combat_swiftstride_step"}
                        if combat_action not in reaction_actions:
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
                            hidden_step_broken = _break_hidden_step_for_character(ch)
                            if changed:
                                flag_modified(ch, "race_features")
                            if hidden_step_broken:
                                flag_modified(ch, "race_features")
                            await db.commit()
                            caster_name = str(getattr(ch, "name", "") or player.display_name).strip() or player.display_name
                            lines = [
                                {"text": f"{caster_name} использует врождённую магию: {spell_display_name}."},
                            ]
                            if hidden_step_broken:
                                lines.append({"text": "Незримая поступь прерывается: невидимость спадает.", "muted": True})
                            combat_state_now = get_combat(session_id)
                            round_no = combat_state_now.round_no if combat_state_now is not None else 1
                            turn_label_now = current_turn_label(combat_state_now) if combat_state_now is not None else "-"
                            patch = {
                                "status": f"⚔ Бой • Раунд {round_no} • Ход: {turn_label_now}",
                                "open": True,
                                "lines": lines,
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
                        bite_empower: Optional[str] = None
                        if combat_action == "combat_move":
                            m_dist = COMBAT_MOVE_DISTANCE_RE.search(cmdline)
                            move_distance_ft = as_int(m_dist.group(1), 0) if m_dist else 0
                        elif combat_action == "combat_vampiric_bite":
                            bite_empower = _detect_vampiric_bite_empower(text)
                        combat_patch, combat_err = handle_live_combat_action(
                            combat_action,
                            session_id,
                            distance_ft=move_distance_ft,
                            empower=bite_empower,
                            raw_text=text,
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
                        shifter_persist_changed = await _persist_shifter_runtime_from_combat_state(db, sess, session_id)
                        simic_persist_changed = await _persist_simic_runtime_from_combat_state(db, sess, session_id)
                        tortle_persist_changed = await _persist_tortle_runtime_from_combat_state(db, sess, session_id)
                        if persist_changed or shifter_persist_changed or simic_persist_changed or tortle_persist_changed:
                            await db.commit()
                            _uid_map, chars_by_uid, _ = await _load_actor_context(db, sess)
                            sync_pcs_from_chars(session_id, chars_by_uid)
                        await broadcast_state(session_id, combat_log_ui_patch=merged_patch)
                        state_for_prompt = state_after_actions
                        ch = await get_character(db, sess.id, player.id)
                        narration_inputs = _build_combat_narration_inputs(
                            sess=sess,
                            combat_state=state_for_prompt,
                            combat_patch=merged_patch,
                            combat_action=combat_action,
                            character=ch,
                            actor_label=actor_label,
                        )
                        gm_text = await _generate_combat_narration(
                            campaign_title=narration_inputs["campaign_title"],
                            outcome_summary=narration_inputs["outcome_summary"],
                            player_action=narration_inputs["player_action"],
                            current_turn=narration_inputs["current_turn"],
                            participants_block=narration_inputs["participants_block"],
                            actor_name=narration_inputs["actor_name"],
                            actor_gender=narration_inputs["actor_gender"],
                            actor_pronouns=narration_inputs["actor_pronouns"],
                        )
                        await add_system_event(
                            db,
                            sess,
                            f"🧙 GM: {gm_text}",
                            result_json={
                                "type": "combat_chat_gm_reply",
                                "combat_action": combat_action,
                                "combat_summary": narration_inputs["outcome_summary"],
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
                if combat_action == "combat_hidden_step":
                    await ws_error("Незримую поступь можно применить только в бою.")
                    continue
                if combat_action in {"combat_adrenaline_rush", "combat_aggressive"}:
                    await ws_error("Прилив адреналина можно применить только в бою.")
                    continue
                if combat_action in {"combat_feline_agility", "combat_cat_claws"}:
                    await ws_error("Особенности табакси доступны только в бою.")
                    continue
                if combat_action in {"combat_shell_defense", "combat_shell_defense_exit", "combat_tortle_claws"}:
                    await ws_error("Особенности тортла доступны только в бою.")
                    continue
                if combat_action in {"combat_acid_spit", "combat_grapple_appendages", "combat_appendages_grapple_bonus"}:
                    await ws_error("Эта способность Simic доступна только в бою.")
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
                    position_payload = _apply_player_action_position_update(sess, player.id, text)
                    actor_label = await _event_actor_label(db, sess, player)
                    payload = {
                        "type": "player_action",
                        "actor_uid": _player_uid(player),
                        "actor_player_id": str(player.id),
                        "join_order": int(sp.join_order or 0),
                        "raw_text": gm_action_text,
                        "mode": "free_turns",
                        "phase": phase,
                        "turn_index": int(sess.turn_index or 0),
                        "combat_chat_action": combat_action,
                    }
                    payload.update(position_payload)
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
                position_payload = _apply_player_action_position_update(sess, player.id, text)
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
                    "turn_index": int(sess.turn_index or 0),
                    "combat_chat_action": combat_action,
                }
                payload.update(position_payload)
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
