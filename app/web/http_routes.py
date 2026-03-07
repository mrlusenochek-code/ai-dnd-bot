import random

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.ai.gm import generate_lore
from app.db.connection import AsyncSessionLocal
from app.db.models import Session, SessionPlayer
from app.rules.character_catalog import CLASS_CATALOG, RACE_CATALOG, resolve_class, resolve_race
from app.rules.feats_catalog import FEATS_CATALOG
from app.web.db_helpers import get_or_create_player_web, get_player_by_uid, get_session
from app.web.gameplay_helpers import (
    CLASS_PRESETS,
    DEFAULT_TIMEZONE,
    GM_OLLAMA_TIMEOUT_SECONDS,
    _char_to_payload,
    _get_kicked,
    _looks_like_refusal,
    _normalize_story_config,
    _put_character_meta_into_stats,
    _resolve_character_stats,
    _stats_points_used,
    _story_is_configured,
    _upsert_starter_skills,
    add_system_event,
    create_character,
    get_character,
    is_admin,
    logger,
)
from app.web.session_state import _set_ready, _touch_last_seen, settings_get, settings_set
from app.web.state_builder import broadcast_state
from app.web.utils import as_int


router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
TIRELESS_PRECISION_TOOL_WHITELIST = {
    "thieves_tools",
    "smith_tools",
    "mason_tools",
    "brewer_supplies",
    "tinkers_tools",
    "herbalism_kit",
    "disguise_kit",
    "forgery_kit",
    "navigator_tools",
    "alchemists_supplies",
    "calligraphers_supplies",
    "carpenters_tools",
    "cartographers_tools",
    "cobblers_tools",
    "cooks_utensils",
    "glassblowers_tools",
    "jewelers_tools",
    "leatherworkers_tools",
    "painters_supplies",
    "potters_tools",
    "weavers_tools",
    "woodcarvers_tools",
}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/c/{session_id}", response_class=HTMLResponse)
async def character_create_page(request: Request, session_id: str):
    return templates.TemplateResponse("character_create.html", {"request": request, "session_id": session_id})


@router.get("/story/{session_id}", response_class=HTMLResponse)
async def story_setup_page(request: Request, session_id: str, uid: Optional[int] = None):
    if not uid or uid <= 0:
        return RedirectResponse(url=f"/s/{session_id}", status_code=303)

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_player_by_uid(db, uid)
        if not player:
            return RedirectResponse(url=f"/s/{session_id}", status_code=303)

        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp or not sp.is_admin:
            return RedirectResponse(url=f"/s/{session_id}", status_code=303)

    return templates.TemplateResponse(
        "story_setup.html",
        {"request": request, "session_id": session_id, "uid": uid},
    )


@router.post("/api/new")
async def api_new(payload: dict):
    title = (payload.get("title") or "Campaign").strip()
    uid = int(payload.get("uid"))
    name = (payload.get("name") or "Игрок").strip()

    async with AsyncSessionLocal() as db:
        player = await get_or_create_player_web(db, uid, name)

        room_id = random.randint(10_000_000_000, 99_999_999_999)
        sess = Session(
            telegram_chat_id=room_id,
            title=title,
            settings={"channel": "web"},
            world_seed=random.randint(1, 2_000_000_000),
            timezone=DEFAULT_TIMEZONE,
            is_active=False,
            is_paused=False,
            turn_index=0,
            current_player_id=None,
            turn_started_at=None,
        )
        db.add(sess)
        await db.commit()
        await db.refresh(sess)

        sp = SessionPlayer(
            session_id=sess.id,
            player_id=player.id,
            is_admin=True,
            join_order=1,
            is_active=True,
        )
        db.add(sp)
        await db.commit()

        # ready defaults
        _set_ready(sess, player.id, False)
        await db.commit()

        await add_system_event(db, sess, f"Создана игра «{title}». Админ: {player.display_name}.")

    return JSONResponse({"session_id": str(sess.id)})


@router.get("/s/{session_id}", response_class=HTMLResponse)
async def session_page(request: Request, session_id: str):
    resp = templates.TemplateResponse("session.html", {"request": request, "session_id": session_id})
    # чтобы не ловили старый session.html (кеш ломает cid/x-client-id)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@router.post("/api/join")
async def api_join(payload: dict):
    session_id = payload.get("session_id")
    uid = int(payload.get("uid"))
    name = (payload.get("name") or "Игрок").strip()

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_or_create_player_web(db, uid, name)

        kicked = _get_kicked(sess)
        if str(player.id) in kicked:
            raise HTTPException(status_code=403, detail="You were kicked from this session")

        q = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q.scalar_one_or_none()
        if sp:
            # reactivate if they had left
            if sp.is_active is False:
                sp.is_active = True
                _set_ready(sess, player.id, False)
                _touch_last_seen(sess, player.id)
                await db.commit()
                await add_system_event(db, sess, f"Игрок вернулся: {player.display_name} (#{sp.join_order}).")
                await broadcast_state(session_id)
                return JSONResponse({"ok": True})
            _touch_last_seen(sess, player.id)
            await db.commit()
            return JSONResponse({"ok": True})

        q2 = await db.execute(select(SessionPlayer.join_order).where(SessionPlayer.session_id == sess.id))
        orders = [r[0] for r in q2.all()] or [0]
        join_order = max(orders) + 1

        sp = SessionPlayer(
            session_id=sess.id,
            player_id=player.id,
            is_admin=False,
            join_order=join_order,
            is_active=True,
        )
        db.add(sp)
        _set_ready(sess, player.id, False)
        _touch_last_seen(sess, player.id)
        await db.commit()

        await add_system_event(db, sess, f"Игрок присоединился: {player.display_name} (#{join_order}).")

    await broadcast_state(session_id)
    return JSONResponse({"ok": True})


@router.get("/api/classes")
async def api_classes():
    items = []
    for class_item in CLASS_CATALOG:
        class_id = str(class_item.get("key") or "").strip().lower()
        if not class_id:
            continue
        preset = CLASS_PRESETS.get(class_id) or {}
        stats = _resolve_character_stats(class_id if preset else None, None)
        items.append(
            {
                "id": class_id,
                "name": class_item.get("name") or preset.get("display_name") or class_item.get("name_ru") or class_id,
                "source": class_item.get("source") or "custom",
                "hit_die": max(1, as_int(class_item.get("hit_die"), 8)),
                "speed_ft": max(0, as_int(class_item.get("speed_ft"), 30)),
                "subclasses": list(class_item.get("subclasses") or []),
                "level_progression": dict(class_item.get("features_by_level") or class_item.get("level_progression") or {}),
                "spell_lists": class_item.get("spell_lists") if isinstance(class_item.get("spell_lists"), dict) else list(class_item.get("spell_lists") or []),
                "hp_max": max(1, as_int(preset.get("hp_max"), 20)),
                "sta_max": max(1, as_int(preset.get("sta_max"), 10)),
                "stats": stats,
                "details": {
                    "name_ru": class_item.get("name_ru") or class_id,
                    "description_ru": class_item.get("description_ru") or "",
                    "primary_abilities": list(class_item.get("primary_abilities") or []),
                    "saving_throws": list(class_item.get("saving_throws") or []),
                    "proficiencies": dict(class_item.get("proficiencies") or {}),
                    "skill_choices": dict(class_item.get("skill_choices") or {}),
                    "starting_equipment": list(class_item.get("starting_equipment") or []),
                    "features_by_level": dict(class_item.get("features_by_level") or {}),
                    "spellcasting": dict(class_item.get("spellcasting") or {}),
                    "tags": list(class_item.get("tags") or []),
                },
            }
        )
    return JSONResponse({"classes": items})


@router.get("/api/races")
async def api_races():
    items = []
    for race_item in RACE_CATALOG:
        race_id = str(race_item.get("key") or "").strip().lower()
        if not race_id:
            continue
        items.append(
            {
                "id": race_id,
                "name": race_item.get("name_ru") or race_item.get("name") or race_id,
                "source": race_item.get("source") or "custom",
                "speed_ft": max(0, as_int(race_item.get("speed_ft"), 30)),
                "hit_die": max(1, as_int(race_item.get("hit_die"), 8)),
                "subraces": list(race_item.get("subraces") or []),
                "details": {
                    "name_ru": race_item.get("name_ru") or race_id,
                    "name_en": race_item.get("name") or race_id,
                    "description_ru": race_item.get("description_ru") or "",
                    "notes_ru": race_item.get("notes_ru") or "",
                    "asi": list(race_item.get("asi") or []),
                    "age": dict(race_item.get("age") or {}),
                    "alignment": race_item.get("alignment") or "",
                    "size": race_item.get("size") or "medium",
                    "speed_notes_ru": race_item.get("speed_notes_ru") or "",
                    "languages": list(race_item.get("languages") or []),
                    "traits": list(race_item.get("traits") or []),
                    "tags": list(race_item.get("tags") or []),
                },
            }
        )
    return JSONResponse({"races": items})


@router.get("/api/feats")
async def api_feats():
    items = []
    for feat_item in FEATS_CATALOG:
        key = str(feat_item.get("key") or "").strip().lower()
        if not key:
            continue
        items.append(
            {
                "key": key,
                "name_ru": str(feat_item.get("name_ru") or key).strip(),
                "summary_ru": str(feat_item.get("summary_ru") or "").strip(),
            }
        )
    return JSONResponse({"feats": items})


@router.get("/api/story/get")
async def api_story_get(session_id: str, uid: int):
    if uid <= 0:
        raise HTTPException(status_code=400, detail="Bad uid")

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_player_by_uid(db, uid)
        if not player:
            raise HTTPException(status_code=403, detail="Admin access required")

        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp or not sp.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        raw_story = settings_get(sess, "story", {}) or {}
        config = _normalize_story_config(sess, raw_story)
        configured = bool(isinstance(raw_story, dict) and raw_story.get("story_configured"))
        if configured:
            config["story_configured"] = True
            config["configured_at"] = str(raw_story.get("configured_at") or "")
        lore_text = str(settings_get(sess, "lore_text", "") or "")
        lore_generated = bool(settings_get(sess, "lore_generated", False))

    return JSONResponse({"ok": True, "config": config, "lore_text": lore_text, "lore_generated": lore_generated})


@router.post("/api/story/save")
async def api_story_save(payload: dict):
    session_id = str(payload.get("session_id") or "").strip()
    uid = as_int(payload.get("uid"), 0)
    config_raw = payload.get("config")

    if uid <= 0:
        raise HTTPException(status_code=400, detail="Bad uid")
    if not isinstance(config_raw, dict):
        raise HTTPException(status_code=400, detail="Bad config payload")

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_player_by_uid(db, uid)
        if not player:
            raise HTTPException(status_code=403, detail="Admin access required")

        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp or not sp.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        config = _normalize_story_config(sess, config_raw)
        config["story_configured"] = True
        config["configured_at"] = datetime.now(timezone.utc).isoformat()
        settings_set(sess, "story", config)
        if "lore_text" in config_raw:
            lore_text = str(config_raw.get("lore_text") or "").strip()
            if lore_text and not _looks_like_refusal(lore_text):
                settings_set(sess, "lore_text", lore_text)
                settings_set(sess, "lore_generated", True)
                settings_set(sess, "lore_posted", False)
            else:
                # очистка (или защита от сохранения отказа)
                settings_set(sess, "lore_text", "")
                settings_set(sess, "lore_generated", False)
                settings_set(sess, "lore_posted", False)
        await db.commit()

    return JSONResponse({"ok": True})


@router.post("/api/story/lore/generate")
async def api_story_lore_generate(payload: dict):
    session_id = str(payload.get("session_id") or "").strip()
    uid = as_int(payload.get("uid"), 0)
    force = bool(payload.get("force", False))

    if uid <= 0:
        raise HTTPException(status_code=400, detail="Bad uid")

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_player_by_uid(db, uid)
        if not player:
            raise HTTPException(status_code=403, detail="Admin access required")

        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp or not sp.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        existing_lore = str(settings_get(sess, "lore_text", "") or "").strip()
        if existing_lore and not force:
            return JSONResponse({"ok": True, "lore_text": existing_lore})

        story = settings_get(sess, "story", {}) or {}
        if not isinstance(story, dict):
            story = {}
        story_setting = str(story.get("story_setting") or "").strip()
        story_title = str(story.get("story_title") or "").strip() or str(sess.title or "Campaign").strip() or "Campaign"
        lore_resp = await generate_lore(
            session_title=story_title,
            setting_text=story_setting,
            timeout_seconds=GM_OLLAMA_TIMEOUT_SECONDS,
        )
        logger.info(
            "lore generation call",
            extra={
                "action": {
                    "llm_finish_reason": lore_resp.get("finish_reason"),
                    "llm_usage": lore_resp.get("usage"),
                }
            },
        )
        lore_text = str(lore_resp.get("text") or "")
        lore_text = lore_text.strip()
        if not lore_text:
            raise HTTPException(status_code=400, detail="Lore generation refused...")
        if _looks_like_refusal(lore_text):
            raise HTTPException(status_code=400, detail="Lore generation refused...")

        settings_set(sess, "lore_text", lore_text)
        settings_set(sess, "lore_generated", True)
        settings_set(sess, "lore_generated_at", datetime.now(timezone.utc).isoformat())
        settings_set(sess, "lore_posted", False)
        await db.commit()

    return JSONResponse({"ok": True, "lore_text": lore_text})


def _build_race_features(selected_race: dict | None) -> dict[str, Any]:
    if not isinstance(selected_race, dict):
        return {}

    # В каталогах race details лежат внутри race["details"]
    details = selected_race.get("details")
    if not isinstance(details, dict):
        details = {}
    if not isinstance(details, dict):
        details = {}

    def _as_list(v):
        return list(v) if isinstance(v, (list, tuple)) else []

    # speeds
    walk = as_int(selected_race.get("speed_ft"), 30)
    speeds: dict[str, Any] = {"walk_ft": max(0, walk)}

    # traits (используем mechanics.type, если есть)
    # In create flow race catalog keeps these on top-level; details is fallback.
    traits = _as_list(selected_race.get("traits") or details.get("traits"))
    subraces = _as_list(selected_race.get("subraces") or details.get("subraces"))
    languages = _as_list(selected_race.get("languages") or details.get("languages"))
    size = str(selected_race.get("size") or details.get("size") or "").strip()
    senses: dict[str, Any] = {}
    resist: list[str] = []
    immune_damage: list[str] = []
    immune_cond: list[str] = []
    skill_profs: list[str] = []
    tool_profs: list[str] = []
    out_nat: dict[str, Any] | None = None
    out_nat_weapons: list[dict[str, Any]] = []
    breath: dict[str, Any] = {}
    movement: dict[str, Any] = {}
    innate_spells: list[dict[str, Any]] = []
    carry: dict[str, Any] = {}
    features: dict[str, Any] = {}
    saves: dict[str, Any] = {}
    allowed_save_abilities = {"str", "dex", "con", "int", "wis", "cha"}

    for t in traits:
        if not isinstance(t, dict):
            continue
        mech = t.get("mechanics")
        if not isinstance(mech, dict):
            mech = {}
        mtype = str(mech.get("type") or "").strip().lower()

        if mtype == "darkvision":
            senses["darkvision_ft"] = max(as_int(mech.get("range_ft"), 60), 0)

        if mtype in ("swim_speed", "fly_speed", "climb_speed"):
            sp = max(as_int(mech.get("speed_ft"), 0), 0)
            if mtype == "swim_speed":
                speeds["swim_ft"] = sp
            elif mtype == "climb_speed":
                speeds["climb_ft"] = sp
            elif mtype == "fly_speed":
                speeds["fly_ft"] = sp
                # ограничения по броне сохраним как есть
                if isinstance(mech.get("restriction"), dict):
                    speeds["fly_restriction"] = mech.get("restriction")

        if mtype == "damage_resistance":
            resist.extend([str(x) for x in _as_list(mech.get("damage")) if str(x)])

        if mtype == "resistance":
            damage_type = str(mech.get("damage_type") or "").strip().lower()
            if damage_type:
                resist.append(damage_type)

        if mtype == "damage_and_condition_immunity":
            immune_damage.extend([str(x) for x in _as_list(mech.get("damage")) if str(x)])
            immune_cond.extend([str(x) for x in _as_list(mech.get("conditions")) if str(x)])

        if mtype == "skill_proficiency":
            sk = str(mech.get("skill") or "").strip().lower()
            if sk:
                skill_profs.append(sk)

        if mtype == "tool_proficiency_choice":
            tool_profs.append("choose_any_tools")

        if mtype == "natural_armor":
            # Supports either fixed AC or formula in mechanics
            nat_obj: dict[str, Any] = {}
            ac_fixed = mech.get("ac")
            if ac_fixed is not None:
                nat_obj["ac"] = max(0, as_int(ac_fixed, 0))
            ac_formula = str(mech.get("ac_formula") or "").strip()
            if ac_formula:
                nat_obj["ac_formula"] = ac_formula
            if mech.get("no_armor_stack") is not None:
                nat_obj["no_armor_stack"] = bool(mech.get("no_armor_stack"))
            if mech.get("shield_applies") is not None:
                nat_obj["shield_applies"] = bool(mech.get("shield_applies"))
            # only set if we actually found something useful
            if nat_obj:
                out_nat = nat_obj

        if mtype == "natural_weapon":
            weapon_key = str(t.get("key") or mech.get("key") or "").strip().lower()
            name_ru = str(t.get("name_ru") or mech.get("name_ru") or "").strip()
            damage_dice = str(mech.get("damage_dice") or "").strip().lower()
            damage_type = str(mech.get("damage_type") or "").strip().lower()
            kind = str(mech.get("kind") or "").strip().lower()
            ability = str(mech.get("ability") or "").strip().lower()
            if kind == "unarmed" and not ability:
                ability = "str"
            if damage_dice and damage_type:
                out_nat_weapons.append(
                    {
                        "key": weapon_key,
                        "name_ru": name_ru,
                        "damage_dice": damage_dice,
                        "damage_type": damage_type,
                        "kind": kind,
                        "ability": ability,
                    }
                )

        if mtype == "hold_breath":
            duration = str(mech.get("duration") or "").strip()
            if duration:
                breath["hold"] = duration

        if mtype == "amphibious":
            breath["amphibious"] = True

        if mtype == "breathe_underwater":
            underwater: dict[str, Any] = {}
            duration_seconds = as_int(mech.get("duration_seconds"), 0)
            if duration_seconds > 0:
                underwater["duration_seconds"] = duration_seconds
            uses = str(mech.get("uses") or "").strip().lower()
            if uses:
                underwater["uses"] = uses
            if underwater:
                breath["underwater"] = underwater

        if mtype == "ignore_difficult_terrain":
            terrain = [str(x).strip() for x in _as_list(mech.get("terrain")) if str(x).strip()]
            if terrain:
                movement["ignore_difficult_terrain"] = terrain

        if mtype == "powerful_build":
            carry["powerful_build"] = True
            carry["effective_size_delta"] = as_int(mech.get("effective_size_delta"), 1)
            applies = [str(x).strip() for x in _as_list(mech.get("applies_to")) if str(x).strip()]
            if applies:
                carry["applies_to"] = applies

        if mtype == "stone_endurance":
            features["stone_endurance"] = dict(mech)

        if mtype == "healing_hands":
            features["healing_hands"] = dict(mech)

        if mtype == "aasimar_transformation":
            features["aasimar_transformation"] = dict(mech)

        if mtype == "innate_spellcasting":
            ability = str(mech.get("ability") or "").strip().lower()
            spells = _as_list(mech.get("spells"))
            for spell in spells:
                if not isinstance(spell, dict):
                    continue
                name = str(spell.get("name") or "").strip()
                frequency = str(spell.get("frequency") or "").strip()
                if not name:
                    continue
                spell_obj: dict[str, Any] = {
                    "ability": ability,
                    "level": as_int(spell.get("level"), 0),
                    "name": name,
                    "frequency": frequency,
                }
                if spell.get("min_level") is not None:
                    spell_obj["min_level"] = as_int(spell.get("min_level"), 0)
                innate_spells.append(spell_obj)

        if mtype == "saving_throw_advantage":
            abilities = []
            for item in _as_list(mech.get("abilities")):
                ability = str(item or "").strip().lower()
                if ability in allowed_save_abilities and ability not in abilities:
                    abilities.append(ability)
            if abilities:
                saves["advantage"] = abilities

    out: dict[str, Any] = {
        "race_key": str(selected_race.get("key") or "").strip(),
        "size": size,
        "languages": [str(x) for x in languages if str(x)],
        "speeds": speeds,
        "senses": senses,
        "natural_armor": out_nat or {},
        "natural_weapons": out_nat_weapons,
        "resistances": sorted(set(resist)),
        "immunities": {
            "damage": sorted(set(immune_damage)),
            "conditions": sorted(set(immune_cond)),
        },
        "proficiencies": {
            "skills": sorted(set(skill_profs)),
            "tools": sorted(set(tool_profs)),
        },
        "breath": breath,
        "movement": movement,
        "innate_spells": innate_spells,
        "carry": carry,
        "features": features,
        "saves": saves,
    }
    return out


def _apply_asi_bonuses(stats: dict[str, Any], asi_items: Any) -> None:
    allowed_asi_stats = {"str", "dex", "con", "int", "wis", "cha"}
    items = asi_items if isinstance(asi_items, list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        stat_key = str(item.get("stat") or "").strip().lower()
        if stat_key not in allowed_asi_stats:
            continue
        bonus = as_int(item.get("bonus"), 0)
        if bonus <= 0:
            continue
        current = as_int(stats.get(stat_key), 50)
        stats[stat_key] = max(0, min(100, current + (bonus * 5)))


@router.post("/api/character/create")
async def api_character_create(payload: dict):
    session_id = str(payload.get("session_id") or "").strip()
    uid = as_int(payload.get("uid"), 0)
    char_name = str(payload.get("name") or "").strip()
    class_id = str(payload.get("class_id") or "").strip().lower()
    custom_class = str(payload.get("custom_class") or "").strip()
    race_id = str(payload.get("race_id") or "").strip().lower()
    subrace_id = str(payload.get("subrace_id") or "").strip().lower()
    custom_race = str(payload.get("custom_race") or "").strip()
    race_choices_payload = payload.get("race_choices")
    stats_in = payload.get("stats")
    meta_gender = str(payload.get("gender") or "").strip()[:40]
    meta_race = str(payload.get("race") or "").strip()[:60]
    meta_description = str(payload.get("description") or "").strip()[:1000]
    race_choice_languages: list[str] = []
    race_choice_asi: list[dict[str, Any]] = []
    race_choice_skills: list[str] = []
    race_choice_feats: list[str] = []
    race_choice_tp_skill = ""
    race_choice_tp_tool = ""
    if isinstance(race_choices_payload, dict):
        raw_langs = race_choices_payload.get("languages")
        raw_langs_list = raw_langs if isinstance(raw_langs, list) else []
        for item in raw_langs_list:
            lang = str(item or "").strip().lower()
            if lang and lang not in race_choice_languages:
                race_choice_languages.append(lang)
        raw_asi = race_choices_payload.get("asi")
        raw_asi_list = raw_asi if isinstance(raw_asi, list) else []
        seen_asi_stats: set[str] = set()
        allowed_asi_stats = {"str", "dex", "con", "int", "wis", "cha"}
        for item in raw_asi_list:
            if not isinstance(item, dict):
                continue
            stat = str(item.get("stat") or "").strip().lower()
            if stat not in allowed_asi_stats:
                continue
            bonus = as_int(item.get("bonus"), 0)
            if bonus <= 0:
                continue
            if stat in seen_asi_stats:
                raise HTTPException(status_code=400, detail="ASI stats must be distinct")
            seen_asi_stats.add(stat)
            race_choice_asi.append({"stat": stat, "bonus": bonus})
        raw_skills = race_choices_payload.get("skills")
        raw_skills_list = raw_skills if isinstance(raw_skills, list) else []
        seen_skill_keys: set[str] = set()
        allowed_skill_keys = {
            "acrobatics",
            "animal_handling",
            "arcana",
            "athletics",
            "deception",
            "history",
            "insight",
            "intimidation",
            "investigation",
            "medicine",
            "nature",
            "perception",
            "performance",
            "persuasion",
            "religion",
            "sleight_of_hand",
            "stealth",
            "survival",
        }
        for item in raw_skills_list:
            skill = str(item or "").strip().lower()
            if not skill:
                continue
            if skill not in allowed_skill_keys:
                raise HTTPException(status_code=400, detail=f"Invalid skill choice: {skill}")
            if skill in seen_skill_keys:
                continue
            seen_skill_keys.add(skill)
            race_choice_skills.append(skill)
        raw_feats = race_choices_payload.get("feats")
        raw_feats_list = raw_feats if isinstance(raw_feats, list) else []
        allowed_feat_keys = {
            str(item.get("key") or "").strip().lower()
            for item in FEATS_CATALOG
            if isinstance(item, dict) and str(item.get("key") or "").strip()
        }
        seen_feat_keys: set[str] = set()
        for item in raw_feats_list:
            feat = str(item or "").strip().lower()
            if not feat:
                continue
            if feat not in allowed_feat_keys:
                raise HTTPException(status_code=400, detail=f"Invalid feat choice: {feat}")
            if feat in seen_feat_keys:
                continue
            seen_feat_keys.add(feat)
            race_choice_feats.append(feat)
        if len(race_choice_feats) > 1:
            raise HTTPException(status_code=400, detail="Only one feat choice is allowed")
        raw_tp = race_choices_payload.get("tireless_precision")
        if isinstance(raw_tp, dict):
            race_choice_tp_skill = str(raw_tp.get("skill") or "").strip().lower()
            race_choice_tp_tool = str(raw_tp.get("tool") or "").strip().lower()

    if uid <= 0:
        raise HTTPException(status_code=400, detail="Bad uid")
    if not char_name:
        raise HTTPException(status_code=400, detail="Character name is required")

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_or_create_player_web(db, uid, "")
        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp:
            raise HTTPException(status_code=403, detail="Join session first")
        if sp.is_active is False:
            raise HTTPException(status_code=403, detail="You are offline in this session")

        existing = await get_character(db, sess.id, player.id)
        if existing:
            return JSONResponse({"detail": "Character already exists"}, status_code=409)

        selected_class = resolve_class(class_id) if class_id else None
        selected_class_key = str((selected_class or {}).get("key") or "").strip().lower()
        selected_preset = (
            CLASS_PRESETS.get(class_id)
            or CLASS_PRESETS.get(selected_class_key)
            if class_id
            else None
        )
        class_name = custom_class or (selected_class.get("name") if selected_class else "Adventurer")
        class_kit = (
            custom_class[:40]
            if custom_class
            else str((selected_class or {}).get("key") or class_name).strip()[:40]
        )
        class_skin = class_name[:60]

        selected_race = resolve_race(race_id) if race_id else None
        selected_subrace: dict[str, Any] | None = None
        effective_race: dict[str, Any] | None = selected_race

        if isinstance(selected_race, dict) and subrace_id:
            subs = selected_race.get("subraces")
            subs_list = subs if isinstance(subs, list) else []
            for sr in subs_list:
                if not isinstance(sr, dict):
                    continue
                k = str(sr.get("key") or "").strip().lower()
                if k and k == subrace_id:
                    selected_subrace = sr
                    break

            if selected_subrace is not None:
                eff = dict(selected_race)
                base_traits = eff.get("traits")
                base_traits_list = base_traits if isinstance(base_traits, list) else []
                sub_traits = selected_subrace.get("traits")
                sub_traits_list = sub_traits if isinstance(sub_traits, list) else []
                race_key = str(selected_race.get("key") or "").strip().lower()
                subrace_key = str(selected_subrace.get("key") or "").strip().lower()
                if race_key == "human" and subrace_key == "variant_human":
                    eff["traits"] = sub_traits_list
                else:
                    eff["traits"] = [*base_traits_list, *sub_traits_list]

                base_asi = eff.get("asi")
                base_asi_list = base_asi if isinstance(base_asi, list) else []
                sub_asi = selected_subrace.get("asi")
                sub_asi_list = sub_asi if isinstance(sub_asi, list) else []
                if race_key == "human" and subrace_key == "variant_human":
                    eff["asi"] = sub_asi_list
                else:
                    eff["asi"] = [*base_asi_list, *sub_asi_list]

                base_lang = eff.get("languages")
                base_lang_list = base_lang if isinstance(base_lang, list) else []
                sub_lang = selected_subrace.get("languages")
                sub_lang_list = sub_lang if isinstance(sub_lang, list) else []
                merged: list[str] = []
                for x in [*base_lang_list, *sub_lang_list]:
                    xs = str(x).strip()
                    if xs and xs not in merged:
                        merged.append(xs)
                eff["languages"] = merged

                # allow simple overrides
                if selected_subrace.get("speed_ft") is not None:
                    eff["speed_ft"] = selected_subrace.get("speed_ft")
                if selected_subrace.get("size") is not None:
                    eff["size"] = selected_subrace.get("size")

                effective_race = eff

        tireless_precision_skills: list[str] = []
        if isinstance(effective_race, dict):
            effective_traits = effective_race.get("traits")
            effective_traits_list = effective_traits if isinstance(effective_traits, list) else []
            for trait in effective_traits_list:
                if not isinstance(trait, dict):
                    continue
                mech = trait.get("mechanics")
                if not isinstance(mech, dict):
                    continue
                mtype = str(mech.get("type") or "").strip().lower()
                if mtype != "tireless_precision":
                    continue
                for item in (mech.get("choose_skill_from") if isinstance(mech.get("choose_skill_from"), list) else []):
                    skill_key = str(item or "").strip().lower()
                    if skill_key and skill_key not in tireless_precision_skills:
                        tireless_precision_skills.append(skill_key)

        tireless_precision_required = bool(tireless_precision_skills)
        if tireless_precision_required and (not race_choice_tp_skill or not race_choice_tp_tool):
            raise HTTPException(status_code=400, detail="Tireless Precision choices are required")
        if race_choice_tp_skill and race_choice_tp_skill not in tireless_precision_skills:
            raise HTTPException(status_code=400, detail=f"Invalid Tireless Precision skill: {race_choice_tp_skill}")
        if race_choice_tp_tool and race_choice_tp_tool not in TIRELESS_PRECISION_TOOL_WHITELIST:
            raise HTTPException(status_code=400, detail=f"Invalid Tireless Precision tool: {race_choice_tp_tool}")
        if not tireless_precision_required and (race_choice_tp_skill or race_choice_tp_tool):
            raise HTTPException(status_code=400, detail="Tireless Precision is not available for selected race")

        if selected_race is not None:
            # When a preset race is selected, keep mechanics by base race id.
            race_kit = str(selected_race.get("key") or "human").strip()[:40]
            if custom_race:
                race_skin = custom_race.strip()[:60]
            elif selected_subrace is not None:
                race_skin = str(
                    selected_subrace.get("name_ru")
                    or selected_subrace.get("name")
                    or selected_subrace.get("key")
                    or (selected_race.get("name_ru") or selected_race.get("name") or "Human")
                ).strip()[:60]
            else:
                race_skin = str(selected_race.get("name_ru") or selected_race.get("name") or "Human").strip()[:60]
        else:
            race_skin = (custom_race or "Human").strip()[:60]
            race_kit = (custom_race.strip().lower().replace(" ", "_") if custom_race else "human")[:40]

        race_features = _build_race_features(effective_race)
        if isinstance(race_features, dict) and selected_subrace is not None:
            race_features["subrace"] = {
                "key": str(selected_subrace.get("key") or "").strip(),
                "name_ru": str(selected_subrace.get("name_ru") or selected_subrace.get("name") or "").strip(),
            }
        choices = race_features.get("choices") if isinstance(race_features, dict) else None
        choices_dict: dict[str, Any] = choices if isinstance(choices, dict) else {}
        if isinstance(race_features, dict) and race_choice_languages:
            base_langs = race_features.get("languages")
            base_langs_list = base_langs if isinstance(base_langs, list) else []
            merged_langs: list[str] = []
            for item in [*base_langs_list, *race_choice_languages]:
                lang = str(item or "").strip().lower()
                if lang and lang not in merged_langs:
                    merged_langs.append(lang)
            race_features["languages"] = merged_langs
            choices_dict["languages"] = list(race_choice_languages)
        if isinstance(race_features, dict) and race_choice_asi:
            choices_dict["asi"] = list(race_choice_asi)
        if isinstance(race_features, dict) and race_choice_skills:
            prof = race_features.get("proficiencies")
            prof_dict: dict[str, Any] = prof if isinstance(prof, dict) else {}
            prof_skills = prof_dict.get("skills")
            prof_skills_list = prof_skills if isinstance(prof_skills, list) else []
            merged_skills: list[str] = []
            for item in [*prof_skills_list, *race_choice_skills]:
                skill = str(item or "").strip().lower()
                if skill and skill not in merged_skills:
                    merged_skills.append(skill)
            prof_dict["skills"] = merged_skills
            race_features["proficiencies"] = prof_dict
            choices_dict["skills"] = list(race_choice_skills)
        if isinstance(race_features, dict) and race_choice_feats:
            choices_dict["feats"] = list(race_choice_feats)
        if isinstance(race_features, dict) and race_choice_tp_skill and race_choice_tp_tool:
            choices_dict["tireless_precision"] = {
                "skill": race_choice_tp_skill,
                "tool": race_choice_tp_tool,
            }
            bonuses = race_features.get("bonuses")
            bonuses_dict: dict[str, Any] = bonuses if isinstance(bonuses, dict) else {}
            bonuses_dict["tireless_precision"] = {
                "die": "1d4",
                "skills": [race_choice_tp_skill],
                "tools": [race_choice_tp_tool],
            }
            race_features["bonuses"] = bonuses_dict
        if isinstance(race_features, dict) and choices_dict:
            race_features["choices"] = choices_dict
        walk_speed = as_int(((race_features.get("speeds") or {}) if isinstance(race_features, dict) else {}).get("walk_ft"), 30)
        if not meta_race:
            meta_race = race_skin
        stats_preset_key = class_id if CLASS_PRESETS.get(class_id) else selected_class_key
        stats = _resolve_character_stats(stats_preset_key if selected_preset else None, stats_in)
        stats = _put_character_meta_into_stats(
            stats,
            gender=meta_gender,
            race=meta_race,
            description=meta_description,
        )
        if _stats_points_used(stats) > 20:
            raise HTTPException(status_code=400, detail="Points budget exceeded (max 20)")
        if isinstance(effective_race, dict):
            _apply_asi_bonuses(stats, effective_race.get("asi"))
        if race_choice_asi:
            _apply_asi_bonuses(stats, race_choice_asi)

        hp_max = max(1, as_int((selected_preset or {}).get("hp_max"), 20))
        sta_max = max(1, as_int((selected_preset or {}).get("sta_max"), 10))
        ch = await create_character(
            db,
            sess.id,
            player.id,
            name=char_name[:80],
            class_kit=class_kit,
            class_skin=class_skin,
            race_kit=race_kit,
            race_skin=race_skin,
            hp_max=hp_max,
            sta_max=sta_max,
            stats=stats,
            race_features=race_features,
            speed_ft=walk_speed,
        )
        await _upsert_starter_skills(db, ch, (selected_preset or {}).get("starter_skills") or {})
        await add_system_event(db, sess, f"Character ready: {ch.name} for player #{sp.join_order}.")
        next_url = f"/s/{session_id}"
        if sp.is_admin and not _story_is_configured(sess):
            next_url = f"/story/{session_id}?uid={uid}"
        return JSONResponse({"ok": True, "character": _char_to_payload(ch), "next_url": next_url})


@router.post("/api/character/update_stats")
async def api_character_update_stats(payload: dict):
    session_id = str(payload.get("session_id") or "").strip()
    uid = as_int(payload.get("uid"), 0)
    stats_in = payload.get("stats")

    if uid <= 0:
        raise HTTPException(status_code=400, detail="Bad uid")
    if not isinstance(stats_in, dict):
        raise HTTPException(status_code=400, detail="Bad stats payload")

    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        player = await get_or_create_player_web(db, uid, "")
        q_sp = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q_sp.scalar_one_or_none()
        if not sp:
            raise HTTPException(status_code=403, detail="Join session first")
        if sp.is_active is False:
            raise HTTPException(status_code=403, detail="You are offline in this session")

        admin = await is_admin(db, sess, player)
        if sess.is_active and not admin:
            raise HTTPException(status_code=403, detail="Only admin can change stats after start")

        ch = await get_character(db, sess.id, player.id)
        if not ch:
            raise HTTPException(status_code=404, detail="No character. Use: char create ...")

        stats = _resolve_character_stats(None, stats_in)
        if _stats_points_used(stats) > 20:
            raise HTTPException(status_code=400, detail="Points budget exceeded (max 20)")

        ch.stats = stats
        await db.commit()
        await add_system_event(db, sess, f"[STAT] player #{sp.join_order} updated character stats.")
        return JSONResponse({"ok": True, "character": _char_to_payload(ch)})


@router.get("/api/character/me")
async def api_character_me(session_id: str, uid: int):
    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        player = await get_or_create_player_web(db, as_int(uid, 0), "")
        ch = await get_character(db, sess.id, player.id)
        return JSONResponse({"ok": True, "has_character": ch is not None, "character": _char_to_payload(ch)})
