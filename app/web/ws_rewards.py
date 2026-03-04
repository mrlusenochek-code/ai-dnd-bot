import random
import zlib
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session
from app.rules.defeat_outcomes import pick_defeat_outcome
from app.rules.item_catalog import ITEMS
from app.rules.loot_tables import roll_loot
from app.web.constants import COMBAT_STATE_KEY
from app.web.gameplay_helpers import add_system_event
from app.web.inventory_helpers import _character_inventory_from_stats, _inv_add_on_character, _inv_remove_on_character
from app.web.session_state import _set_pc_zone, settings_get, settings_set
from app.web.utils import as_int
from app.web.ws_access import _load_actor_context
from app.web.ws_progression import _level_from_xp_total


def _is_victory_patch(patch: dict[str, Any]) -> bool:
    if not isinstance(patch, dict):
        return False
    if patch.get("status") != "Бой завершён":
        return False
    lines = patch.get("lines")
    if not isinstance(lines, list):
        return False
    for raw_line in lines:
        text: Optional[str] = None
        if isinstance(raw_line, str):
            text = raw_line
        elif isinstance(raw_line, dict):
            candidate = raw_line.get("text")
            if isinstance(candidate, str):
                text = candidate
        if isinstance(text, str) and text.startswith("Победа:"):
            return True
    return False


def _is_defeat_patch(patch: dict[str, Any]) -> bool:
    if not isinstance(patch, dict):
        return False
    if patch.get("status") != "Бой завершён":
        return False
    lines = patch.get("lines")
    if not isinstance(lines, list):
        return False
    for raw_line in lines:
        text: Optional[str] = None
        if isinstance(raw_line, str):
            text = raw_line
        elif isinstance(raw_line, dict):
            candidate = raw_line.get("text")
            if isinstance(candidate, str):
                text = candidate
        if isinstance(text, str) and text.startswith("Поражение:"):
            return True
    return False


def _combat_started_at_from_settings(sess: Session) -> str | None:
    payload = settings_get(sess, COMBAT_STATE_KEY, None)
    if not isinstance(payload, dict):
        return None
    raw = payload.get("started_at_iso")
    return raw if isinstance(raw, str) else None


def _enemy_ids_from_combat_state_payload(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    combatants = payload.get("combatants")
    if not isinstance(combatants, dict):
        return []
    out: list[str] = []
    for key, raw in combatants.items():
        if not isinstance(key, str) or not isinstance(raw, dict):
            continue
        if raw.get("side") == "enemy":
            out.append(key)
    return out


def _compute_rewards_from_combat_state_payload(payload: Any) -> tuple[list[int], int | None, int, dict[str, int]]:
    if not isinstance(payload, dict):
        return [], None, 0, {}

    combatants = payload.get("combatants")
    if not isinstance(combatants, dict):
        return [], None, 0, {}

    pc_uids: list[int] = []
    seen_pc_uids: set[int] = set()
    enemies: list[tuple[str, int]] = []

    for key, raw in combatants.items():
        if not isinstance(key, str):
            continue
        if key.startswith("pc_"):
            uid_raw = key[3:]
            if uid_raw.isdigit():
                uid = int(uid_raw)
                if uid not in seen_pc_uids:
                    seen_pc_uids.add(uid)
                    pc_uids.append(uid)
        if isinstance(raw, dict) and raw.get("side") == "enemy":
            enemies.append((key, max(10, as_int(raw.get("hp_max"), 0))))

    leader_uid: int | None = None
    order_raw = payload.get("order")
    order = order_raw if isinstance(order_raw, list) else []
    for key in order:
        if not isinstance(key, str) or not key.startswith("pc_"):
            continue
        uid_raw = key[3:]
        if uid_raw.isdigit():
            uid = int(uid_raw)
            if uid in seen_pc_uids:
                leader_uid = uid
                break
    if leader_uid is None and pc_uids:
        leader_uid = pc_uids[0]

    xp_total_enemy_sum = sum(max(10, hp_max * 5) for _enemy_id, hp_max in enemies)
    xp_each = xp_total_enemy_sum // max(1, len(pc_uids))

    started_at = payload.get("started_at_iso")
    started_at_str = started_at if isinstance(started_at, str) else ""
    loot_dict: dict[str, int] = {}
    for enemy_id, _hp_max in enemies:
        rng = random.Random(zlib.adler32((started_at_str + ":" + enemy_id).encode("utf-8")))
        drops = roll_loot(enemy_id, rng=rng)
        for drop in drops:
            if not isinstance(drop, dict):
                continue
            def_key = drop.get("def")
            if not isinstance(def_key, str) or not def_key:
                continue
            qty = max(0, as_int(drop.get("qty"), 0))
            if qty <= 0:
                continue
            loot_dict[def_key] = loot_dict.get(def_key, 0) + qty

    return pc_uids, leader_uid, xp_each, loot_dict


def _apply_defeat_outcome_to_settings(sess: Session, started_at: str) -> dict[str, Any]:
    outcome = pick_defeat_outcome(started_at_iso=started_at, rng=None)
    payload = {
        "started_at_iso": started_at,
        "key": outcome.key,
        "title_ru": outcome.title_ru,
        "description_ru": outcome.description_ru,
        "tags": list(outcome.tags),
    }
    settings_set(sess, "combat_defeat_outcome_for", started_at)
    settings_set(sess, "combat_defeat_outcome", payload)
    return payload


def _revive_characters_to_1hp(chars: list[Any]) -> bool:
    changed = False
    for ch in chars:
        hp = as_int(getattr(ch, "hp", 0), 0)
        if hp <= 0:
            setattr(ch, "hp", 1)
            if hasattr(ch, "is_alive"):
                setattr(ch, "is_alive", True)
            changed = True
    return changed


def _apply_left_for_dead_character_state(chars_by_uid: dict[int, Any]) -> int | None:
    if not chars_by_uid:
        return None
    leader_uid = min(chars_by_uid.keys())
    for uid, ch in chars_by_uid.items():
        hp = as_int(getattr(ch, "hp", 0), 0)
        if uid == leader_uid:
            if hp <= 0:
                setattr(ch, "hp", 1)
        elif hp <= 0:
            setattr(ch, "hp", 0)
        if hasattr(ch, "is_alive"):
            setattr(ch, "is_alive", True)
    return leader_uid


def _compute_robbed_removals(inv: list[dict[str, Any]], max_take: int = 2) -> list[str]:
    if not isinstance(inv, list):
        return []
    candidates: list[tuple[str, str]] = []
    for entry in inv:
        if not isinstance(entry, dict):
            continue
        def_key = str(entry.get("def") or "").strip()
        item_def = ITEMS.get(def_key) if def_key else None
        if item_def is not None and item_def.kind == "quest":
            continue
        entry_id = str(entry.get("id") or "").strip().lower()
        entry_name = str(entry.get("name") or "").strip()
        if not entry_id and not entry_name:
            continue
        sort_key = entry_id or entry_name.lower()
        remove_name = entry_id or entry_name
        candidates.append((sort_key, remove_name))
    candidates.sort(key=lambda x: x[0])
    take = max(0, as_int(max_take, 2))
    return [remove_name for _sort_key, remove_name in candidates[:take]]


async def _apply_defeat_effects_once(
    db: AsyncSession,
    sess: Session,
) -> bool:
    outcome_payload = settings_get(sess, "combat_defeat_outcome", None)
    if not isinstance(outcome_payload, dict):
        return False

    started_at = str(outcome_payload.get("started_at_iso") or "").strip()
    key = str(outcome_payload.get("key") or "").strip()
    if not started_at or not key:
        return False

    if settings_get(sess, "combat_defeat_effects_applied_for", "") == started_at:
        return False

    uid_map, chars_by_uid, _skill_mods_by_char = await _load_actor_context(db, sess)
    all_chars = list(chars_by_uid.values())

    if key == "enemies_withdraw":
        _revive_characters_to_1hp(all_chars)
        settings_set(sess, "combat_defeat_effects_applied_for", started_at)
        await add_system_event(db, sess, "☠ Поражение: враги отступили. Вы приходите в себя (1 HP).")
        return True

    if key == "robbed":
        _revive_characters_to_1hp(all_chars)
        if not chars_by_uid:
            return False
        victim_uid = sorted(chars_by_uid.keys())[0]
        victim = chars_by_uid.get(victim_uid)
        if victim is None:
            return False

        inv = _character_inventory_from_stats(victim.stats)
        to_remove = _compute_robbed_removals(inv, max_take=2)
        removed_names: list[str] = []
        for remove_name in to_remove:
            changed, _qty, removed_item = _inv_remove_on_character(victim, name=remove_name, qty=1)
            if not changed:
                continue
            removed_name = str((removed_item or {}).get("name") or remove_name).strip() or remove_name
            removed_names.append(removed_name)

        settings_set(sess, "combat_defeat_effects_applied_for", started_at)
        removed_text = ", ".join(removed_names) if removed_names else "ничего"
        await add_system_event(db, sess, f"☠ Поражение: вас ограбили. Потеряно: {removed_text}.")
        return True

    if key == "captured":
        _revive_characters_to_1hp(all_chars)
        for uid in sorted(uid_map.keys()):
            sp, _pl = uid_map[uid]
            _set_pc_zone(sess, sp.player_id, "prison_cell")
        settings_set(sess, "combat_defeat_effects_applied_for", started_at)
        await add_system_event(db, sess, "☠ Поражение: вас взяли в плен. Вы очнулись в камере (prison_cell).")
        return True

    if key == "rescued":
        _revive_characters_to_1hp(all_chars)
        for uid in sorted(uid_map.keys()):
            sp, _pl = uid_map[uid]
            _set_pc_zone(sess, sp.player_id, "safehouse")
        for uid in sorted(chars_by_uid.keys()):
            ch = chars_by_uid[uid]
            _inv_add_on_character(
                ch,
                name=ITEMS["healing_potion"].name_ru,
                qty=1,
                item_def="healing_potion",
                tags=["rescue"],
                notes="defeat:rescued",
            )
        settings_set(sess, "combat_defeat_effects_applied_for", started_at)
        await add_system_event(
            db,
            sess,
            "☠ Поражение: вас спасли и доставили в убежище (safehouse). Получено: Зелье лечения x1 каждому.",
        )
        return True

    if key == "left_for_dead":
        _apply_left_for_dead_character_state(chars_by_uid)
        for uid in sorted(uid_map.keys()):
            sp, _pl = uid_map[uid]
            _set_pc_zone(sess, sp.player_id, "wilderness_edge")
        settings_set(sess, "combat_defeat_effects_applied_for", started_at)
        await add_system_event(
            db,
            sess,
            "☠ Поражение: вас бросили умирать. Вы приходите в себя на обочине (wilderness_edge).",
        )
        return True

    return False


async def _grant_defeat_outcome_once(
    db: AsyncSession,
    sess: Session,
    patch: dict[str, Any],
) -> bool:
    if not _is_defeat_patch(patch):
        return False

    started_at = _combat_started_at_from_settings(sess)
    if not started_at:
        return False

    if settings_get(sess, "combat_defeat_outcome_for", "") == started_at:
        return False

    outcome_payload = _apply_defeat_outcome_to_settings(sess, started_at)
    await add_system_event(
        db,
        sess,
        f"☠ Поражение. Исход: {outcome_payload['title_ru']}. {outcome_payload['description_ru']}",
    )
    return True


async def _grant_combat_rewards_once(
    db: AsyncSession,
    sess: Session,
    patch: dict[str, Any],
) -> bool:
    if not _is_victory_patch(patch):
        return False

    started_at = _combat_started_at_from_settings(sess)
    if not started_at:
        return False

    if settings_get(sess, "combat_rewards_granted_for", "") == started_at:
        return False

    payload = settings_get(sess, COMBAT_STATE_KEY, None)
    if not isinstance(payload, dict):
        return False

    pc_uids, leader_uid, xp_each, loot_dict = _compute_rewards_from_combat_state_payload(payload)
    _uid_map, chars_by_uid, _skill_mods_by_char = await _load_actor_context(db, sess)

    for uid in pc_uids:
        ch = chars_by_uid.get(uid)
        if ch is None:
            continue
        ch.xp_total = max(0, as_int(ch.xp_total, 0)) + max(0, xp_each)
        ch.level = _level_from_xp_total(ch.xp_total, as_int(ch.level, 1))

    if leader_uid is not None:
        leader_ch = chars_by_uid.get(leader_uid)
        if leader_ch is not None:
            for enemy_id in _enemy_ids_from_combat_state_payload(payload):
                rng = random.Random(zlib.adler32((started_at + ":" + enemy_id).encode("utf-8")))
                drops = roll_loot(enemy_id, rng=rng)
                enemy_loot: dict[str, int] = {}
                for drop in drops:
                    if not isinstance(drop, dict):
                        continue
                    def_key = drop.get("def")
                    if not isinstance(def_key, str) or not def_key:
                        continue
                    qty = max(0, as_int(drop.get("qty"), 0))
                    if qty <= 0:
                        continue
                    enemy_loot[def_key] = enemy_loot.get(def_key, 0) + qty
                for def_key, qty in enemy_loot.items():
                    item = ITEMS[def_key]
                    _inv_add_on_character(
                        leader_ch,
                        name=item.name_ru,
                        qty=qty,
                        item_def=def_key,
                        tags=["loot"],
                        notes=f"combat:{enemy_id}",
                    )

    settings_set(sess, "combat_rewards_granted_for", started_at)

    loot_chunks: list[str] = []
    for def_key, qty in sorted(loot_dict.items()):
        item = ITEMS.get(def_key)
        item_name = item.name_ru if item is not None else def_key
        loot_chunks.append(f"{item_name} x{qty}")
    loot_text = ", ".join(loot_chunks) if loot_chunks else "нет"
    await add_system_event(db, sess, f"🏆 Победа! XP: +{xp_each} каждому. Лут: {loot_text} (лидеру)")
    return True
