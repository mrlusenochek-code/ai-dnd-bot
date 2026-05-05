import logging
import re
import uuid
from typing import Any, Optional

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import current_turn_label, get_combat
from app.gm import combat_narration as gm_combat_narration
from app.rules.derived_stats import compute_ac
from app.web.combat_helpers import _combat_participant_line, _de_numberize_text, _hit_force_label, _hp_state_label
from app.web.gameplay_helpers import (
    CHAR_DEFAULT_STATS,
    GM_FINAL_NUM_PREDICT,
    GM_OLLAMA_TIMEOUT_SECONDS,
    _character_meta_from_stats,
    _normalized_stats,
    _player_uid,
)
from app.web.inventory_helpers import _character_equip_from_stats, _character_inventory_from_stats
from app.web.session_state import settings_get
from app.web.utils import _clamp, as_int
from app.web.ws_combat_prompting import _gender_to_pronouns


logger = logging.getLogger("app.web.server")


def _combat_outcome_summary_from_patch(
    action: str,
    combat_patch: Optional[dict[str, Any]],
) -> list[str]:
    combat_line_re = re.compile(
        r"(?:^Атака:|^Результат:|^Урон:|:\s*HP\s*\d+/\d+|Ход автоматически передан|повержен|промах|попадание|крит)",
        flags=re.IGNORECASE,
    )
    patch = combat_patch if isinstance(combat_patch, dict) else {}
    lines: list[str] = []
    for item in patch.get("lines", []):
        if isinstance(item, dict):
            txt = str(item.get("text") or "").strip()
            if txt and combat_line_re.search(txt):
                lines.append(txt)
    if not lines:
        return ["Схватка продолжается в напряжённом темпе."]

    if action == "combat_attack":
        actor = "боец"
        target = "цель"
        for line in lines:
            m_attack = re.search(r"^Атака:\s*(.+?)\s*[→-]\s*(.+)$", line)
            if m_attack:
                actor = m_attack.group(1).strip() or actor
                target = m_attack.group(2).strip() or target
                break

        outcome = "промах"
        for line in lines:
            low = line.lower()
            if "крит" in low:
                outcome = "крит"
                break
            if "попадание" in low:
                outcome = "попадание"
                break
            if "промах" in low:
                outcome = "промах"

        hp_state = "цел"
        for line in lines:
            m_hp = re.search(r":\s*HP\s*(\d+)\s*/\s*(\d+)", line, flags=re.IGNORECASE)
            if m_hp:
                hp_state = _hp_state_label(int(m_hp.group(1)), int(m_hp.group(2)))
                break
            if "повержен" in line.lower():
                hp_state = "повержен"
                break

        hit_force = "легко"
        for line in lines:
            m_dmg = re.search(r"Урон:\s*.+?=\s*(\d+)", line, flags=re.IGNORECASE)
            if m_dmg:
                hit_force = _hit_force_label(int(m_dmg.group(1)))
                break

        summary = f"{actor} атакует {target}: {outcome}; цель {hp_state}; удар {hit_force}."
        return [_de_numberize_text(summary)]

    action_summaries = {
        "combat_dodge": "ушёл в оборону и сбил темп противника.",
        "combat_help": "помог союзнику и открыл окно для атаки.",
        "combat_dash": "рванул вперёд и резко сменил позицию.",
        "combat_hooves_attack": "воспользовался разбегом и ударил копытами.",
        "combat_shapechanger_shift": "сменил облик, скрыв истинное лицо.",
        "combat_shapechanger_revert": "сбросил маску и вернулся к истинной форме.",
        "combat_mode_walk": "перешёл на ходьбу и стабилизировал движение.",
        "combat_mode_swim": "перешёл на плавание и продолжил манёвр.",
        "combat_mode_climb": "перешёл на лазание и полез вверх.",
        "combat_disengage": "отступил без раскрытия и разорвал дистанцию.",
        "combat_escape": "попытался вырваться из схватки и уйти из боя.",
        "combat_use_object": "использовал объект в гуще схватки.",
        "combat_end_turn": "передал ход следующему бойцу.",
    }
    base = action_summaries.get(action, "действует в бою.")
    for line in lines:
        if line.startswith("Атака:"):
            continue
        if "повержен" in line.lower():
            base = f"{base.rstrip('.')} Один из противников повержен."
            break
    return [_de_numberize_text(base)]


def _merge_combat_patches(patches: list[dict[str, Any]]) -> dict[str, Any]:
    if not patches:
        return {"open": True, "lines": []}
    last = patches[-1]
    merged_lines: list[dict[str, Any]] = []
    for patch in patches:
        for item in patch.get("lines", []):
            if isinstance(item, dict):
                merged_lines.append(item)
    out = dict(last)
    out["lines"] = merged_lines
    return out


def _append_combat_patch_lines(
    combat_patch: Optional[dict[str, Any]],
    lines_to_add: list[dict[str, Any]],
    *,
    prepend: bool = False,
) -> dict[str, Any]:
    patch = combat_patch if isinstance(combat_patch, dict) else {}
    lines = patch.get("lines")
    if not isinstance(lines, list):
        lines = []
        patch["lines"] = lines
    prepared_lines: list[dict[str, Any]] = []
    for line in lines_to_add:
        text = str(line.get("text") or "").strip() if isinstance(line, dict) else ""
        if not text:
            continue
        prepared_lines.append(line)
    if prepend:
        patch["lines"] = prepared_lines + lines
    else:
        lines.extend(prepared_lines)
    return patch


def _build_combat_start_preamble_lines(
    *,
    player: Optional[Any],
    chars_by_uid: dict[int, Any],
    combat_state: Any,
) -> list[dict[str, Any]]:
    if combat_state is None or not getattr(combat_state, "active", False):
        return []

    player_uid = _player_uid(player)
    player_name = str(getattr(player, "display_name", "") or "").strip() or "Игрок"
    level = 1
    class_kit = "Adventurer"
    stats = dict(CHAR_DEFAULT_STATS)
    hp_cur = 0
    hp_max = 1
    ac = 10

    if player_uid is not None:
        character = chars_by_uid.get(player_uid)
        if character is not None:
            char_name = str(character.name or "").strip()
            if char_name:
                player_name = char_name
            level = max(1, as_int(character.level, 1))
            class_kit = str(character.class_kit or "").strip() or "Adventurer"
            stats = _normalized_stats(character.stats)
            equip_map = _character_equip_from_stats(character.stats)
            inv = _character_inventory_from_stats(character.stats)
            ac = compute_ac(
                stats=character.stats,
                inventory=inv,
                equip_map=equip_map,
                race_features=getattr(character, "race_features", None),
                class_features=getattr(character, "class_features", None),
            )
            hp_max = max(1, as_int(character.hp_max, hp_max))
            hp_cur = _clamp(as_int(character.hp, hp_cur), 0, hp_max)

        combatants = getattr(combat_state, "combatants", {})
        if isinstance(combatants, dict):
            pc_key = f"pc_{player_uid}"
            player_combatant = combatants.get(pc_key)
            if player_combatant is not None:
                hp_max = max(1, as_int(getattr(player_combatant, "hp_max", hp_max), hp_max))
                hp_cur = _clamp(as_int(getattr(player_combatant, "hp_current", hp_cur), hp_cur), 0, hp_max)
                ac = max(0, as_int(getattr(player_combatant, "ac", ac), ac))

    enemy_name = "противником"
    combatants = getattr(combat_state, "combatants", {})
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


def _maybe_apply_opening_combat_action(
    *,
    session_id: str,
    combat_action: Optional[str],
    player_uid: Optional[int],
    player_id: uuid.UUID,
    combat_patch: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    _ = player_id
    if combat_action is None:
        return combat_patch

    state = get_combat(session_id)
    if state is None or not state.active:
        return combat_patch

    player_key = f"pc_{player_uid}" if player_uid is not None else ""
    if player_key and player_key in state.order:
        state.turn_index = state.order.index(player_key)
        state.round_no = max(1, int(state.round_no or 0))

    return _collect_and_merge_combat_patches(
        session_id=session_id,
        combat_action=combat_action,
        combat_patch=combat_patch,
        round_no=state.round_no,
        turn_label=current_turn_label(state),
    )


def _collect_and_merge_combat_patches(
    *,
    session_id: str,
    combat_action: str,
    combat_patch: Optional[dict[str, Any]],
    round_no: int,
    turn_label: str,
) -> Optional[dict[str, Any]]:
    merge_items: list[dict[str, Any]] = []
    if isinstance(combat_patch, dict):
        merge_items.append(combat_patch)
    merge_items.append(
        {
            "open": True,
            "lines": [
                {
                    "text": f"⚔ Бой • Раунд {round_no} • Ход: {turn_label}",
                    "muted": True,
                    "kind": "status",
                }
            ],
        }
    )

    opening_patch, _opening_err = handle_live_combat_action(combat_action, session_id)
    if isinstance(opening_patch, dict):
        merge_items.append(opening_patch)

        max_enemy_steps = 3
        enemy_steps = 0
        while enemy_steps < max_enemy_steps:
            state_now = get_combat(session_id)
            if state_now is None or not state_now.active or not state_now.order:
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
            if isinstance(enemy_patch, dict):
                merge_items.append(enemy_patch)
            enemy_steps += 1

    return _merge_combat_patches(merge_items) if merge_items else combat_patch


def _combat_participants_block(state: Any) -> str:
    combatants = getattr(state, "combatants", {}) if state is not None else {}
    if not isinstance(combatants, dict) or not combatants:
        return "- PC: (нет)\n- ENEMY: (нет)"

    pcs: list[str] = []
    enemies: list[str] = []
    for key in getattr(state, "order", []) or []:
        actor = combatants.get(key)
        if actor is None:
            continue
        label = _combat_participant_line(actor)
        side = str(getattr(actor, "side", "")).lower()
        if side == "pc":
            pcs.append(label)
        elif side == "enemy":
            enemies.append(label)

    if not pcs or not enemies:
        for key, actor in combatants.items():
            label = _combat_participant_line(actor)
            side = str(getattr(actor, "side", "")).lower()
            if side == "pc" and label not in pcs:
                pcs.append(label)
            elif side == "enemy" and label not in enemies:
                enemies.append(label)

    pcs_text = ", ".join(pcs) if pcs else "(нет)"
    enemies_text = ", ".join(enemies) if enemies else "(нет)"
    return f"- PC: {pcs_text}\n- ENEMY: {enemies_text}"


async def _generate_combat_narration(
    campaign_title: str,
    outcome_summary: list[str],
    player_action: str,
    current_turn: str,
    participants_block: str,
    actor_name: str,
    actor_gender: str,
    actor_pronouns: str,
) -> str:
    return await gm_combat_narration.generate_combat_narration(
        campaign_title=campaign_title,
        outcome_summary=outcome_summary,
        player_action=player_action,
        current_turn=current_turn,
        participants_block=participants_block,
        actor_name=actor_name,
        actor_gender=actor_gender,
        actor_pronouns=actor_pronouns,
        timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
        num_predict=max(240, GM_FINAL_NUM_PREDICT // 3),
    )


def _build_combat_narration_inputs(
    *,
    sess: Any,
    combat_state: Any,
    combat_patch: Optional[dict[str, Any]],
    combat_action: str,
    character: Any,
    actor_label: str,
) -> dict[str, Any]:
    story = settings_get(sess, "story", {}) or {}
    if not isinstance(story, dict):
        story = {}
    campaign_title = str(story.get("story_title") or "").strip() or str(getattr(sess, "title", "") or "Campaign").strip() or "Campaign"
    outcome_summary = _combat_outcome_summary_from_patch(combat_action, combat_patch)
    current_turn = current_turn_label(combat_state) if combat_state else "-"
    participants_block = _combat_participants_block(combat_state)
    meta = _character_meta_from_stats(character.stats) if character else {"gender": "", "race": "", "description": ""}
    actor_gender = meta["gender"]
    actor_pronouns = _gender_to_pronouns(actor_gender) or "unknown"
    actor_name = str(getattr(character, "name", "") or "").strip() if character else ""
    if not actor_name:
        actor_name = actor_label
    return {
        "campaign_title": campaign_title,
        "outcome_summary": outcome_summary,
        "player_action": combat_action,
        "current_turn": current_turn,
        "participants_block": participants_block,
        "actor_name": actor_name,
        "actor_gender": actor_gender,
        "actor_pronouns": actor_pronouns,
    }
