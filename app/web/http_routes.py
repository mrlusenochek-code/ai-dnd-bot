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
    "bagpipes",
    "drum",
    "dulcimer",
    "flute",
    "horn",
    "lute",
    "lyre",
    "pan_flute",
    "shawm",
    "viol",
}
WIZARD_CANTRIP_WHITELIST = {
    "fire_bolt",
    "ray_of_frost",
    "shocking_grasp",
    "mage_hand",
    "minor_illusion",
    "prestidigitation",
    "light",
    "dancing_lights",
}
AUTOGNOME_TOOL_WHITELIST = set(TIRELESS_PRECISION_TOOL_WHITELIST)
MARTIAL_WEAPON_WHITELIST = {
    "battleaxe",
    "flail",
    "glaive",
    "greataxe",
    "greatsword",
    "halberd",
    "lance",
    "longsword",
    "maul",
    "morningstar",
    "pike",
    "rapier",
    "scimitar",
    "shortsword",
    "trident",
    "war_pick",
    "warhammer",
    "whip",
    "blowgun",
    "hand_crossbow",
    "heavy_crossbow",
    "longbow",
    "net",
}
LANGUAGE_WHITELIST = {
    "common",
    "dwarvish",
    "elvish",
    "halfling",
    "gnomish",
    "orc",
    "draconic",
    "goblin",
    "infernal",
    "celestial",
    "giant",
    "primordial",
    "auran",
    "aquan",
    "terran",
    "ignan",
    "abyssal",
    "sylvan",
    "undercommon",
    "deep_speech",
    "thieves_cant",
    "gith",
    "quori",
    "leonin",
    "tabaxi",
    "vedalken",
    "aarakocra",
    "loxodon",
    "minotaur",
    "grung",
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

    def _uniq_lower_str_list(v):
        out: list[str] = []
        for item in _as_list(v):
            value = str(item or "").strip().lower()
            if value and value not in out:
                out.append(value)
        return out

    def _append_innate_spell(*, ability: str, spell_obj: dict[str, Any]) -> None:
        spell_name = str(spell_obj.get("name") or spell_obj.get("spell_ref") or "").strip().lower()
        if not spell_name:
            return
        level = as_int(spell_obj.get("level"), -1)
        if level < 0:
            level = as_int(spell_obj.get("spell_level"), -1)
        if level < 0:
            level = 0 if str(spell_obj.get("kind") or "").strip().lower() == "cantrip" else 1
            if spell_name == "faerie_fire":
                level = 1
            elif spell_name == "darkness":
                level = 2
        frequency = str(spell_obj.get("frequency") or "").strip().lower()
        if not frequency:
            if str(spell_obj.get("kind") or "").strip().lower() == "cantrip":
                frequency = "at_will"
            elif as_int(spell_obj.get("uses_per_day"), 0) > 0:
                frequency = "1_per_long_rest"
        entry: dict[str, Any] = {
            "ability": str(ability or "").strip().lower(),
            "level": max(0, level),
            "name": spell_name,
            "frequency": frequency,
        }
        spell_level = as_int(spell_obj.get("spell_level"), -1)
        if spell_level >= 0:
            entry["spell_level"] = max(0, spell_level)
        if spell_obj.get("min_level") is not None:
            entry["min_level"] = as_int(spell_obj.get("min_level"), 0)
        note = str(spell_obj.get("note") or "").strip().lower()
        if note:
            entry["note"] = note
        if spell_obj.get("no_material_components") is not None:
            entry["no_material_components"] = bool(spell_obj.get("no_material_components"))
        innate_spells.append(entry)

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
    weapon_profs: list[str] = []
    armor_profs: list[str] = []
    out_nat: dict[str, Any] | None = None
    out_nat_weapons: list[dict[str, Any]] = []
    breath: dict[str, Any] = {}
    movement: dict[str, Any] = {}
    innate_spells: list[dict[str, Any]] = []
    carry: dict[str, Any] = {}
    features: dict[str, Any] = {}
    saves: dict[str, Any] = {}
    needs: dict[str, Any] = {}
    save_advantage_conditions: list[str] = []
    save_advantage_vs_magic: list[str] = []
    allowed_save_abilities = {"str", "dex", "con", "int", "wis", "cha"}
    race_key = str(selected_race.get("key") or "").strip().lower()
    creature_type = ""
    speed_notes_ru = str(selected_race.get("speed_notes_ru") or details.get("speed_notes_ru") or "").strip().lower()

    for t in traits:
        if not isinstance(t, dict):
            continue
        mech = t.get("mechanics")
        if not isinstance(mech, dict):
            mech = {}
        mtype = str(mech.get("type") or "").strip().lower()
        mname = str(mech.get("name") or "").strip().lower()
        tkey = str(t.get("key") or "").strip().lower()

        if mtype == "darkvision" or (mtype == "sense" and mname == "darkvision"):
            senses["darkvision_ft"] = max(as_int(mech.get("range_ft"), 60), 0)

        if mtype == "feline_agility":
            features["feline_agility"] = {
                "type": "feline_agility",
                "double_speed": True,
                "reset_if_zero_movement_turn": True,
            }

        if mtype in ("swim_speed", "fly_speed", "climb_speed"):
            speed_equals_walk = bool(mech.get("speed_equals_walk"))
            sp = max(as_int(mech.get("speed_ft"), 0), 0)
            if speed_equals_walk:
                sp = max(0, walk)
            if mtype == "swim_speed":
                speeds["swim_ft"] = sp
            elif mtype == "climb_speed":
                speeds["climb_ft"] = sp
            elif mtype == "fly_speed":
                speeds["fly_ft"] = sp
                if speed_equals_walk:
                    speeds["fly_speed_equals_walk"] = True
                # ограничения по броне сохраним как есть
                if isinstance(mech.get("restriction"), dict):
                    speeds["fly_restriction"] = mech.get("restriction")

        if mtype == "damage_resistance":
            resist.extend([str(x) for x in _as_list(mech.get("damage")) if str(x)])
            damage_type = str(mech.get("damage_type") or "").strip().lower()
            if damage_type:
                resist.append(damage_type)

        if mtype == "glide":
            features["glide"] = {
                "reduce_fall_ft": max(0, as_int(mech.get("reduce_fall_ft"), 0)),
                "horizontal_per_fall_ft": max(0, as_int(mech.get("horizontal_per_fall_ft"), 0)),
            }

        if mtype == "resistance":
            damage_type = str(mech.get("damage_type") or "").strip().lower()
            if damage_type:
                resist.append(damage_type)

        if mtype == "damage_and_condition_immunity":
            damage_items = [str(x) for x in _as_list(mech.get("damage")) if str(x)]
            condition_items = [str(x) for x in _as_list(mech.get("conditions")) if str(x)]
            immune_damage.extend(damage_items)
            immune_cond.extend(condition_items)
            if tkey:
                features[tkey] = {
                    "type": "damage_and_condition_immunity",
                    "damage": _uniq_lower_str_list(damage_items),
                    "conditions": _uniq_lower_str_list(condition_items),
                }

        if mtype == "skill_proficiency":
            sk = str(mech.get("skill") or "").strip().lower()
            if sk:
                skill_profs.append(sk)

        if mtype == "telepathy":
            telepathy: dict[str, Any] = {}
            range_ft = as_int(mech.get("range_ft"), 0)
            if range_ft > 0:
                telepathy["range_ft"] = range_ft
            range_formula = str(mech.get("range_formula") or "").strip().lower()
            if range_formula:
                telepathy["range_formula"] = range_formula
            allow_reply_duration = str(mech.get("allow_reply_duration") or "").strip().lower()
            if allow_reply_duration:
                telepathy["allow_reply_duration"] = allow_reply_duration
            if mech.get("one_target_reply") is not None:
                telepathy["one_target_reply"] = bool(mech.get("one_target_reply"))
            if mech.get("requires_target_language") is not None:
                telepathy["requires_target_language"] = bool(mech.get("requires_target_language"))
            bandwidth = str(mech.get("bandwidth") or "").strip().lower()
            if bandwidth:
                telepathy["bandwidth"] = bandwidth
            if telepathy:
                senses["telepathy"] = telepathy
                if tkey == "mind_link":
                    features["mind_link"] = dict(telepathy)

        if mtype == "tool_proficiency_choice":
            tool_profs.append("choose_any_tools")
            choose = max(as_int(mech.get("choose"), as_int(mech.get("count"), 0)), 0)
            from_raw = mech.get("from")
            from_list = from_raw if isinstance(from_raw, list) else [from_raw]
            from_items = _uniq_lower_str_list(from_list)
            if choose > 0 and from_items:
                features["tool_choice"] = {"choose": choose, "from": from_items}

        if mtype == "proficiency":
            skill_profs.extend(_uniq_lower_str_list(mech.get("skills")))
            weapon_profs.extend(_uniq_lower_str_list(mech.get("weapons")))
            armor_profs.extend(_uniq_lower_str_list(mech.get("armor")))
            tool_profs.extend(_uniq_lower_str_list(mech.get("tools")))

        if mtype == "proficiency_bundle":
            skill_profs.extend(_uniq_lower_str_list(mech.get("skills")))
            weapon_profs.extend(_uniq_lower_str_list(mech.get("weapons")))
            armor_profs.extend(_uniq_lower_str_list(mech.get("armor")))
            tool_profs.extend(_uniq_lower_str_list(mech.get("tools")))
            choose_musical = max(as_int(mech.get("choose_musical_instrument"), 0), 0)
            if choose_musical > 0:
                features["tool_choice"] = {
                    "choose": choose_musical,
                    "from": sorted(
                        {
                            "bagpipes",
                            "drum",
                            "dulcimer",
                            "flute",
                            "horn",
                            "lute",
                            "lyre",
                            "pan_flute",
                            "shawm",
                            "viol",
                        }
                    ),
                }
                features["reveler"] = {
                    "skills": _uniq_lower_str_list(mech.get("skills")),
                    "choose_musical_instrument": choose_musical,
                }

        if mtype in {"skill_proficiency", "skill_proficiencies"}:
            skill_profs.extend(_uniq_lower_str_list(mech.get("skills")))

        if _uniq_lower_str_list(mech.get("resistances")):
            resist.extend(_uniq_lower_str_list(mech.get("resistances")))
        if _uniq_lower_str_list(mech.get("saves_advantage")):
            save_advantage_conditions.extend(_uniq_lower_str_list(mech.get("saves_advantage")))
        if _uniq_lower_str_list(mech.get("immunities")):
            immune_cond.extend(_uniq_lower_str_list(mech.get("immunities")))

        if tkey == "tool_proficiency":
            choose = max(as_int(mech.get("choose"), 0), 0)
            from_items = _uniq_lower_str_list(mech.get("from"))
            if choose > 0 and from_items:
                features["tool_choice"] = {"choose": choose, "from": from_items}

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
            if mech.get("requires_unarmored") is not None:
                nat_obj["requires_unarmored"] = bool(mech.get("requires_unarmored"))
            else:
                nat_obj["requires_unarmored"] = True
            if mech.get("allow_when_armored_if_better") is not None:
                nat_obj["allow_when_armored_if_better"] = bool(mech.get("allow_when_armored_if_better"))
            # only set if we actually found something useful
            if nat_obj:
                out_nat = nat_obj

        if mtype == "trunk":
            features["trunk"] = dict(mech)

        if mtype == "advantage_on_checks" and tkey == "keen_smell":
            features["keen_smell"] = dict(mech)

        if mtype == "natural_weapon":
            weapon_key = str(t.get("key") or mech.get("key") or "").strip().lower()
            name_ru = str(t.get("name_ru") or mech.get("name_ru") or "").strip()
            damage_dice = str(mech.get("damage_dice") or "").strip().lower()
            damage_type = str(mech.get("damage_type") or "").strip().lower()
            kind = str(mech.get("kind") or "").strip().lower()
            if not kind:
                kind = "unarmed"
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
                if weapon_key:
                    features[weapon_key] = {
                        "type": "natural_weapon",
                        "name": weapon_key,
                        "name_ru": name_ru,
                        "damage_dice": damage_dice,
                        "damage_type": damage_type,
                        "ability": ability,
                        "kind": kind,
                    }

        if mtype == "hold_breath":
            duration = str(mech.get("duration") or "").strip()
            if duration:
                breath["hold"] = duration
            features["hold_breath"] = dict(mech)

        if mtype == "shell_defense":
            features["shell_defense"] = {
                "type": "shell_defense",
                "ac_bonus": 4,
                "adv_saves": ["str", "con"],
                "disadv_saves": ["dex"],
                "speed_override_ft": 0,
            }

        if mtype == "cunning_artisan":
            features["cunning_artisan"] = dict(mech)

        if mtype == "hungry_jaws":
            features["hungry_jaws"] = dict(mech)

        if mtype == "amphibious":
            breath["amphibious"] = True
            features["amphibious"] = True

        if mtype == "constructed_resilience":
            adv_conditions = _uniq_lower_str_list(mech.get("advantage_on_saves"))
            resistances = _uniq_lower_str_list(mech.get("damage_resistance"))
            immunity_conditions = _uniq_lower_str_list(mech.get("condition_immunity"))
            no_need_items = _uniq_lower_str_list(mech.get("no_need"))
            save_advantage_conditions.extend(adv_conditions)
            resist.extend(resistances)
            immune_cond.extend(immunity_conditions)
            if no_need_items:
                existing_no_need = _uniq_lower_str_list(needs.get("no_need"))
                merged_no_need: list[str] = []
                for item in [*existing_no_need, *no_need_items]:
                    if item and item not in merged_no_need:
                        merged_no_need.append(item)
                needs["no_need"] = merged_no_need
            if bool(mech.get("cannot_be_magically_slept")) and "magic_sleep" not in immune_cond:
                immune_cond.append("magic_sleep")
            features["constructed_resilience"] = {
                "type": "constructed_resilience",
                "advantage_on_saves": adv_conditions,
                "damage_resistance": resistances,
                "condition_immunity": immunity_conditions,
                "no_need": no_need_items,
                "cannot_be_magically_slept": bool(mech.get("cannot_be_magically_slept")),
            }

        if mtype == "guardians_of_the_depths":
            if "cold" not in resist:
                resist.append("cold")
            features["guardians_of_the_depths"] = {
                "type": "guardians_of_the_depths",
                "cold_resistance": True,
                "deep_pressure_adapted": True,
            }

        if mtype == "speak_with_beasts":
            features["emissary_of_the_sea"] = {
                "type": "speak_with_beasts",
                "scope": str(mech.get("scope") or "").strip().lower() or "sea_beasts",
            }

        if mtype == "poisonous_skin":
            features["poisonous_skin"] = dict(mech)

        if mtype == "standing_leap":
            features["standing_leap"] = dict(mech)

        if mtype == "jump_bonus":
            features["mirthful_leaps"] = {
                "bonus_dice": str(mech.get("bonus_dice") or "1d8").strip().lower() or "1d8",
                "applies_to": _uniq_lower_str_list(mech.get("applies_to")),
            }

        if mtype == "shifting":
            features["shifting"] = {
                "duration": str(mech.get("duration") or "1_minute").strip().lower() or "1_minute",
                "temp_hp_formula": str(mech.get("temp_hp_formula") or "level + con_mod (min 1)").strip() or "level + con_mod (min 1)",
                "end_conditions": _uniq_lower_str_list(mech.get("end_conditions")),
                "uses": str(mech.get("uses") or "per_short_or_long_rest").strip().lower() or "per_short_or_long_rest",
                "uses_max": max(0, as_int(mech.get("uses_max"), 0)),
            }

        if mtype == "shifting_bonus":
            features["shifting_bonus"] = {
                "temp_hp_extra": str(mech.get("temp_hp_extra") or "").strip().lower(),
                "ac_bonus": max(0, as_int(mech.get("ac_bonus"), 0)),
            }

        if mtype == "shifting_bonus_action_attack":
            features["shifting_bonus_action_attack"] = {
                "damage_dice": str(mech.get("damage_dice") or "1d6").strip().lower() or "1d6",
                "damage_type": str(mech.get("damage_type") or "piercing").strip().lower() or "piercing",
                "ability": str(mech.get("ability") or "str").strip().lower() or "str",
            }

        if mtype == "shifting_mobility":
            features["shifting_mobility"] = {
                "walk_speed_bonus_ft": max(0, as_int(mech.get("walk_speed_bonus_ft"), 0)),
                "reaction_move_ft": max(0, as_int(mech.get("reaction_move_ft"), 0)),
                "trigger": str(mech.get("trigger") or "").strip().lower(),
                "no_opportunity_attacks": bool(mech.get("no_opportunity_attacks") or mech.get("no_oa")),
            }

        if mtype == "marked_target":
            features["marked_target"] = {
                "mark_range_ft": max(0, as_int(mech.get("mark_range_ft"), 0)),
                "track_bonus": str(mech.get("track_bonus") or "").strip().lower(),
                "locate_range_ft": max(0, as_int(mech.get("locate_range_ft"), 0)),
                "duration": str(mech.get("duration") or "").strip().lower(),
                "uses": str(mech.get("uses") or "per_short_or_long_rest").strip().lower() or "per_short_or_long_rest",
                "uses_max": max(0, as_int(mech.get("uses_max"), 0)),
            }

        if mtype == "shifting_defense":
            features["shifting_defense"] = {
                "advantage_on": _uniq_lower_str_list(mech.get("advantage_on")),
                "deny_enemy_advantage_range_ft": max(0, as_int(mech.get("deny_enemy_advantage_range_ft"), 0)),
                "while_conscious": bool(mech.get("while_conscious")),
            }

        if mtype == "water_dependency":
            features["water_dependency"] = dict(mech)

        if mtype == "limited_amphibious":
            features["limited_amphibious"] = dict(mech)

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
            features["powerful_build"] = dict(mech)

        if mtype == "stone_endurance":
            features["stone_endurance"] = dict(mech)

        if mtype == "relentless_endurance":
            features["relentless_endurance"] = dict(mech)

        if mtype == "savage_attacks":
            features["savage_attacks"] = dict(mech)

        if mtype == "reach_bonus":
            features["reach_bonus"] = dict(mech)

        if mtype == "surprise_attack":
            features["surprise_attack"] = dict(mech)

        if mtype == "initiative_bonus" and tkey == "hare_trigger":
            features["hare_trigger"] = dict(mech)

        if mtype == "lucky_footwork":
            features["lucky_footwork"] = dict(mech)

        if mtype == "rabbit_hop":
            features["rabbit_hop"] = dict(mech)

        if mtype == "saving_face":
            features["saving_face"] = dict(mech)

        if mtype == "fearless_vs_frightened":
            features["fearless_vs_frightened"] = dict(mech)
            if bool(mech.get("advantage")) and "frightened" not in save_advantage_conditions:
                save_advantage_conditions.append("frightened")

        if mtype == "taunt":
            features["taunt"] = dict(mech)

        if mtype == "aoe_frighten" and tkey == "daunting_roar":
            features["daunting_roar"] = dict(mech)

        if mtype == "goring_rush":
            features["goring_rush"] = dict(mech)

        if mtype == "hammering_horns":
            features["hammering_horns"] = dict(mech)

        if mtype == "bonus_action_move_toward_enemy" and tkey == "aggressive":
            features["aggressive"] = dict(mech)

        if mtype == "expert_forgery":
            features["expert_forgery"] = dict(mech)

        if mtype == "mimicry":
            features["mimicry"] = dict(mech)

        if mtype == "charge_bonus_attack":
            features["charge"] = dict(mech)

        if mtype == "equine_build":
            carry["powerful_build"] = True
            movement["climb_extra_cost_ft_per_ft"] = max(0, as_int(mech.get("climb_extra_cost_ft_per_ft"), 4))
            movement["climb_requires_hands_and_feet"] = bool(mech.get("climb_requires_hands_and_feet", True))

        if mtype == "bonus_damage" and tkey == "fury_of_the_small":
            features["fury_of_the_small"] = dict(mech)

        if mtype == "bonus_action_options" and tkey == "nimble_escape":
            features["nimble_escape"] = True

        if mtype == "pack_tactics":
            features["pack_tactics"] = dict(mech) if mech else {"enabled": True}

        if mtype == "action_debuff" and tkey == "grovel_cower_beg":
            features["grovel_cower_beg"] = dict(mech)

        if mtype == "skill_bonus":
            features["stonecunning"] = dict(mech)

        if mtype == "stealth_bonus":
            features["mask_of_the_wild"] = dict(mech)
            features["stealth_bonus"] = dict(mech)

        if mtype == "rest_override":
            features["trance"] = dict(mech)

        if mtype == "climb_and_natural_weapon":
            climb_ft = max(0, as_int(mech.get("climb_speed_ft"), 0))
            if climb_ft > 0:
                speeds["climb_ft"] = climb_ft
            weapon_raw = mech.get("weapon")
            weapon = dict(weapon_raw) if isinstance(weapon_raw, dict) else {}
            out_nat_weapons.append(
                {
                    "key": "cat_claws",
                    "kind": "unarmed",
                    "damage_dice": str(weapon.get("damage_dice") or "1d4").strip().lower() or "1d4",
                    "damage_type": str(weapon.get("damage_type") or "slashing").strip().lower() or "slashing",
                    "ability": "str",
                }
            )
            features["cat_claws"] = {
                "type": "natural_weapon",
                "name": "cat_claws",
                "damage_dice": str(weapon.get("damage_dice") or "1d4").strip().lower() or "1d4",
                "damage_type": str(weapon.get("damage_type") or "slashing").strip().lower() or "slashing",
                "ability": "str",
                "is_unarmed_replacement": True,
            }

        if mtype == "animal_enhancement":
            features["animal_enhancement"] = {
                "pick_1_level": max(0, as_int(mech.get("pick_1_level"), 1)),
                "pick_2_level": max(0, as_int(mech.get("pick_2_level"), 5)),
                "chosen_lvl1": None,
                "chosen_lvl5": None,
            }

        if mtype == "healing_hands":
            features["healing_hands"] = dict(mech)

        if mtype == "aasimar_transformation":
            features["aasimar_transformation"] = dict(mech)

        if mtype == "hit_dice_reroll":
            features["hit_dice_reroll"] = dict(mech)

        if mtype == "size_change":
            features["size_change"] = dict(mech)

        if mtype == "shapechanger":
            features["shapechanger"] = dict(mech)

        if mtype == "innate_spellcasting":
            ability = str(mech.get("ability") or "").strip().lower()
            no_material_components = bool(mech.get("no_material_components"))
            spells = _as_list(mech.get("spells"))
            normalized_spells: list[dict[str, Any]] = []
            for spell in spells:
                if not isinstance(spell, dict):
                    continue
                spell_obj = dict(spell)
                if no_material_components:
                    spell_obj["no_material_components"] = True
                normalized_spell = dict(spell_obj)
                if not normalized_spell.get("name") and normalized_spell.get("spell_ref"):
                    normalized_spell["name"] = normalized_spell.get("spell_ref")
                if not normalized_spell.get("min_level"):
                    normalized_spell["min_level"] = 1
                normalized_spells.append(normalized_spell)
                _append_innate_spell(ability=ability, spell_obj=spell_obj)
            if normalized_spells:
                features["innate_spellcasting"] = {
                    "type": "innate_spellcasting",
                    "ability": ability,
                    "spells": normalized_spells,
                }
                if tkey == "duergar_magic":
                    features["duergar_magic"] = {
                        "type": "innate_spellcasting",
                        "ability": ability,
                        "spells": normalized_spells,
                    }
                if tkey == "light_cantrip":
                    light_spell = next(
                        (
                            item
                            for item in normalized_spells
                            if str((item or {}).get("name") or (item or {}).get("spell_ref") or "").strip().lower() == "light"
                        ),
                        None,
                    )
                    if isinstance(light_spell, dict):
                        features["light_bearer"] = {
                            "type": "innate_spellcasting",
                            "ability": ability,
                            "spell": {
                                "name": "light",
                                "frequency": str(light_spell.get("frequency") or "at_will").strip().lower() or "at_will",
                                "min_level": max(1, as_int(light_spell.get("min_level"), 1)),
                                "ability": ability,
                            },
                        }

        if mtype == "innate_spellcasting_shared_cooldown":
            ability = str(mech.get("ability") or "").strip().lower()
            shared_group = str(mech.get("shared_group") or tkey or "innate_shared").strip().lower()
            shared_recharge = str(mech.get("shared_recharge") or "").strip().lower()
            frequency = "shared_1_per_short_or_long_rest"
            if shared_recharge == "per_long_rest":
                frequency = "shared_1_per_long_rest"
            spells = _as_list(mech.get("spells"))
            normalized_spells: list[str] = []
            normalized_entries: list[dict[str, Any]] = []
            for spell_item in spells:
                if isinstance(spell_item, dict):
                    spell_name = str(spell_item.get("name") or spell_item.get("spell_ref") or "").strip().lower()
                else:
                    spell_name = str(spell_item or "").strip().lower()
                if not spell_name:
                    continue
                normalized_spells.append(spell_name)
                normalized_entries.append(
                    {
                        "name": spell_name,
                        "frequency": frequency,
                        "min_level": 1,
                    }
                )
                innate_spells.append(
                    {
                        "ability": ability,
                        "level": 1,
                        "name": spell_name,
                        "frequency": frequency,
                        "shared_group": shared_group,
                        "shared_recharge": shared_recharge,
                    }
                )
            shared_magic_cfg = {
                "ability": ability,
                "spells": normalized_spells,
                "shared_group": shared_group,
                "shared_recharge": shared_recharge,
                "special": dict(mech.get("special")) if isinstance(mech.get("special"), dict) else {},
                "allow_spell_slots": bool(mech.get("allow_spell_slots")),
            }
            if tkey:
                features[tkey] = shared_magic_cfg
            # Keep backward-compatible key used by existing Firbolg UI/tests.
            if tkey == "firbolg_magic":
                features["firbolg_magic"] = shared_magic_cfg
            if normalized_entries:
                features["innate_spellcasting"] = {
                    "type": "innate_spellcasting",
                    "ability": ability,
                    "spells": normalized_entries,
                }

        if mtype == "invisibility_burst":
            features["hidden_step"] = dict(mech)

        if mtype == "limited_beast_plant_speech":
            features["speech_of_beast_and_leaf"] = dict(mech)

        if mtype == "creature_type":
            creature_type = str(mech.get("value") or "").strip().lower()

        if mtype == "mechanical_nature":
            resist.extend(_uniq_lower_str_list(mech.get("damage_resistance")))
            immune_cond.extend(_uniq_lower_str_list(mech.get("condition_immunity")))
            save_advantage_conditions.extend(_uniq_lower_str_list(mech.get("condition_advantage")))
            no_need_items = _uniq_lower_str_list(mech.get("no_need"))
            if no_need_items:
                needs["no_need"] = no_need_items

        if mtype == "no_need":
            no_need_items = _uniq_lower_str_list(mech.get("no_need"))
            if no_need_items:
                existing_no_need = _uniq_lower_str_list(needs.get("no_need"))
                merged_no_need: list[str] = []
                for item in [*existing_no_need, *no_need_items]:
                    if item and item not in merged_no_need:
                        merged_no_need.append(item)
                needs["no_need"] = merged_no_need

        if mtype == "spider_climb":
            climb_equals_walk = bool(mech.get("climb_speed_equals_walk"))
            at_level = max(0, as_int(mech.get("at_level"), 0))
            ceiling_hands_free = bool(mech.get("can_climb_ceiling_hands_free"))
            if climb_equals_walk:
                speeds["climb_ft"] = max(0, as_int(speeds.get("walk_ft"), 0))
            features["spider_climb"] = {
                "at_level": at_level,
                "can_climb_ceiling_hands_free": ceiling_hands_free,
                "climb_speed_equals_walk": climb_equals_walk,
            }

        if mtype == "ancestral_legacy":
            features["ancestral_legacy"] = dict(mech)

        if mtype == "eerie_token":
            features["eerie_token"] = dict(mech)

        if mtype == "vampiric_bite":
            bite_cfg = dict(mech)
            weapon_raw = bite_cfg.get("weapon")
            weapon = weapon_raw if isinstance(weapon_raw, dict) else {}
            weapon_norm = {
                "damage_dice": str(weapon.get("damage_dice") or "1d4").strip().lower(),
                "damage_type": str(weapon.get("damage_type") or "piercing").strip().lower(),
                "ability": str(weapon.get("ability") or "con").strip().lower(),
            }
            bite_cfg["weapon"] = weapon_norm
            bite_cfg["advantage_when_hp_below_half"] = bool(bite_cfg.get("advantage_when_hp_below_half"))
            bite_cfg["uses"] = str(bite_cfg.get("uses") or "per_long_rest").strip().lower()
            bite_cfg["uses_formula"] = str(bite_cfg.get("uses_formula") or "proficiency_bonus").strip().lower()
            empower_raw = bite_cfg.get("empower_options")
            empower_list = empower_raw if isinstance(empower_raw, list) else []
            bite_cfg["empower_options"] = _uniq_lower_str_list(empower_list)
            features["vampiric_bite"] = bite_cfg

        if mtype == "sentry_rest":
            features["sentry_rest"] = dict(mech)

        if mtype == "integrated_protection":
            features["integrated_protection"] = {
                "type": "integrated_protection",
                "ac_bonus": max(0, as_int(mech.get("ac_bonus"), 0)),
                "armor_integrate_hours": max(0, as_int(mech.get("armor_integrate_hours"), 0)),
                "cannot_be_removed_by_force": bool(mech.get("cannot_be_removed_by_force")),
            }

        if mtype == "specialized_design":
            choose_skill = max(0, as_int(mech.get("choose_skill"), 0))
            choose_tool = max(0, as_int(mech.get("choose_tool"), 0))
            features["specialized_design"] = {
                "type": "specialized_design",
                "choose_skill": choose_skill,
                "choose_tool": choose_tool,
            }
            if choose_tool > 0:
                features["tool_choice"] = {"choose": choose_tool, "from": ["any"]}

        if mtype == "built_for_success":
            features["built_for_success"] = dict(mech)

        if mtype == "mending_heal":
            features["mending_heal"] = dict(mech)

        if mtype == "healing_spells_affect_construct":
            features["healing_spells_affect_construct"] = True

        if mtype == "spell_grants":
            ability = str(mech.get("casting_ability") or "").strip().lower()
            grants = _as_list(mech.get("grants"))
            normalized_spells: list[dict[str, Any]] = []
            for grant in grants:
                if not isinstance(grant, dict):
                    continue
                spell_key = str(grant.get("spell") or "").strip().lower()
                if not spell_key:
                    continue
                kind = str(grant.get("kind") or "").strip().lower()
                uses = str(grant.get("uses") or "").strip().lower()
                frequency = ""
                if kind == "cantrip":
                    frequency = "at_will"
                elif uses == "per_long_rest":
                    frequency = "1_per_long_rest"
                spell_obj: dict[str, Any] = {
                    "spell_ref": spell_key,
                    "kind": kind,
                    "frequency": frequency,
                }
                if grant.get("min_level") is not None:
                    spell_obj["min_level"] = as_int(grant.get("min_level"), 0)
                spell_level = as_int(grant.get("spell_level"), -1)
                if spell_level >= 0:
                    spell_obj["spell_level"] = spell_level
                    spell_obj["level"] = spell_level
                normalized_spells.append(
                    {
                        "name": spell_key,
                        "frequency": frequency,
                        "min_level": max(1, as_int(grant.get("min_level"), 1)),
                    }
                )
                _append_innate_spell(ability=ability, spell_obj=spell_obj)
            if normalized_spells:
                features["infernal_legacy"] = {
                    "type": "innate_spellcasting",
                    "ability": ability,
                    "spells": normalized_spells,
                }
                features["innate_spellcasting"] = {
                    "type": "innate_spellcasting",
                    "ability": ability,
                    "spells": normalized_spells,
                }

        if tkey == "drow_magic":
            ability = str(mech.get("ability") or "").strip().lower()
            spells = _as_list(mech.get("spells"))
            normalized_spells: list[dict[str, Any]] = []
            for spell in spells:
                if isinstance(spell, dict):
                    spell_ref = str(spell.get("spell_ref") or spell.get("name") or "").strip().lower()
                    frequency = "at_will" if str(spell.get("kind") or "").strip().lower() == "cantrip" else ""
                    if as_int(spell.get("uses_per_day"), 0) > 0:
                        frequency = "1_per_long_rest"
                    spell_entry: dict[str, Any] = {
                        "name": spell_ref,
                        "frequency": frequency,
                        "min_level": max(1, as_int(spell.get("min_level"), 1)),
                    }
                    normalized_spells.append(spell_entry)
                    _append_innate_spell(ability=ability, spell_obj=spell)
            if normalized_spells:
                features["drow_magic"] = {
                    "type": "innate_spellcasting",
                    "ability": ability,
                    "spells": normalized_spells,
                }
                features["innate_spellcasting"] = {
                    "type": "innate_spellcasting",
                    "ability": ability,
                    "spells": normalized_spells,
                }

        if tkey == "sunlight_sensitivity":
            disadvantage = _uniq_lower_str_list(mech.get("disadvantage"))
            if not disadvantage:
                disadvantage = ["attack_rolls", "perception_checks_relying_on_sight"]
            if disadvantage:
                features["sunlight_sensitivity"] = disadvantage

        if tkey == "wizard_cantrip" and mtype == "choice":
            choose = max(as_int(mech.get("choose"), 0), 0)
            from_list = str(mech.get("from_list") or "").strip().lower()
            ability = str(mech.get("ability") or "").strip().lower()
            if choose > 0 and from_list == "wizard_cantrips":
                features["wizard_cantrip_choice"] = {
                    "choose": choose,
                    "from_list": from_list,
                    "ability": ability,
                }

        if mtype == "saving_throw_advantage":
            abilities = []
            for item in _as_list(mech.get("abilities")):
                ability = str(item or "").strip().lower()
                if ability in allowed_save_abilities and ability not in abilities:
                    abilities.append(ability)
            if abilities:
                saves["advantage"] = abilities
            if tkey == "vedalken_dispassion":
                features["vedalken_dispassion"] = {
                    "type": "save_advantage",
                    "abilities": list(abilities),
                }

        if mtype == "save_advantage":
            vs_key = str(mech.get("vs") or "").strip().lower()
            if vs_key == "frightened":
                save_advantage_conditions.append("frightened")
            abilities = []
            save_items = _as_list(mech.get("saves"))
            if not save_items:
                save_items = _as_list(mech.get("stats"))
            for item in save_items:
                ability = str(item or "").strip().lower()
                if ability in allowed_save_abilities and ability not in abilities:
                    abilities.append(ability)
            is_magic_only = str(mech.get("vs") or "").strip().lower() == "magic"
            if abilities and is_magic_only:
                for ability in abilities:
                    if ability not in save_advantage_vs_magic:
                        save_advantage_vs_magic.append(ability)
                if tkey == "gnome_cunning":
                    features["gnome_cunning"] = {
                        "type": "save_advantage_vs_magic",
                        "abilities": list(abilities),
                    }
            elif abilities:
                saves["advantage"] = abilities
            if tkey == "dual_mind" and abilities:
                features["dual_mind"] = {
                    "type": "save_advantage",
                    "abilities": list(abilities),
                }
            if tkey == "vedalken_dispassion" and abilities:
                features["vedalken_dispassion"] = {
                    "type": "save_advantage",
                    "abilities": list(abilities),
                }

        if mtype == "save_advantage_conditions":
            save_advantage_conditions.extend(_uniq_lower_str_list(mech.get("conditions")))

        if mtype == "deathless_nature":
            save_advantage_conditions.extend(_uniq_lower_str_list(mech.get("advantage_on_saves")))
            resist.extend(_uniq_lower_str_list(mech.get("damage_resistance")))
            no_need_items = _uniq_lower_str_list(mech.get("no_need"))
            if no_need_items:
                needs["no_need"] = no_need_items
            if bool(mech.get("cannot_be_magically_slept")) and "magic_sleep" not in immune_cond:
                immune_cond.append("magic_sleep")
            features["deathless_nature"] = {
                "advantage_on_saves": _uniq_lower_str_list(mech.get("advantage_on_saves")),
                "damage_resistance": _uniq_lower_str_list(mech.get("damage_resistance")),
                "no_need": no_need_items,
                "cannot_be_magically_slept": bool(mech.get("cannot_be_magically_slept")),
                "long_rest_hours": max(0, as_int(mech.get("long_rest_hours"), 0)),
                "remain_conscious": bool(mech.get("remain_conscious")),
            }

        if mtype == "add_d6_to_skill_check" and tkey == "knowledge_from_a_past_life":
            features["knowledge_from_a_past_life"] = {
                "dice": str(mech.get("dice") or "1d6").strip().lower() or "1d6",
                "timing": str(mech.get("timing") or "after_seeing_d20").strip().lower() or "after_seeing_d20",
                "uses": str(mech.get("uses") or "per_long_rest").strip().lower() or "per_long_rest",
                "uses_formula": str(mech.get("uses_formula") or "proficiency_bonus").strip().lower() or "proficiency_bonus",
            }

        if mtype == "dream_immunity":
            features["dream_immunity"] = {"not_sleep_immunity": bool(mech.get("not_sleep_immunity"))}

        if mtype == "reroll_ones":
            scope = _uniq_lower_str_list(mech.get("scope"))
            features["reroll_ones"] = {"scope": scope}

        if mtype == "move_through_larger_creatures":
            features["move_through_larger_creatures"] = True

        if mtype == "hide_with_larger_cover":
            features["hide_with_larger_cover"] = True

        if mtype == "poison_resilience":
            if bool(mech.get("save_advantage")):
                save_advantage_conditions.append("poison")
            if bool(mech.get("damage_resistance")):
                resist.append("poison")

        if mtype == "fey_ancestry":
            save_advantage_conditions.append("charmed")
            immune_cond.append("magic_sleep")
            features["fey_ancestry"] = {
                "type": "fey_ancestry",
                "advantage_on_saves_vs": ["charmed"],
                "immune_to_magical_sleep": True,
            }

        if mtype == "magic_resistance":
            for ability in allowed_save_abilities:
                if ability not in save_advantage_vs_magic:
                    save_advantage_vs_magic.append(ability)
            features["magic_resistance"] = {"applies_to": "all_magic_saves"}

        if mtype == "ac_bonus_if_no_heavy_armor":
            features["ac_bonus_if_no_heavy_armor"] = {"ac_bonus": max(0, as_int(mech.get("ac_bonus"), 0))}

        if mtype == "grappling_appendages":
            features["grappling_appendages"] = {
                "damage_dice": str(mech.get("damage_dice") or "1d6").strip().lower() or "1d6",
                "damage_type": str(mech.get("damage_type") or "bludgeoning").strip().lower() or "bludgeoning",
                "ability": str(mech.get("ability") or "str").strip().lower() or "str",
                "cannot_wield_weapons": True,
                "cannot_do_fine_work": True,
            }

        if mtype == "acid_spit":
            features["acid_spit"] = {
                "range_ft": max(0, as_int(mech.get("range_ft"), 30)),
                "damage": str(mech.get("damage") or "2d10").strip().lower() or "2d10",
                "damage_type": str(mech.get("damage_type") or "acid").strip().lower() or "acid",
                "dc_formula": str(mech.get("dc_formula") or "8 + prof + con_mod").strip().lower() or "8 + prof + con_mod",
                "uses_formula": str(mech.get("uses_formula") or "max(con_mod,1)").strip().lower() or "max(con_mod,1)",
                "recharge": str(mech.get("recharge") or "per_long_rest").strip().lower() or "per_long_rest",
            }

        if mtype == "learn_cantrip":
            spell_key = str(mech.get("spell_key") or "").strip().lower()
            ability = str(mech.get("ability") or "").strip().lower()
            if spell_key:
                _append_innate_spell(
                    ability=ability,
                    spell_obj={
                        "spell_ref": spell_key,
                        "kind": "cantrip",
                        "frequency": "at_will",
                        "level": 0,
                    },
                )
                features["innate_spellcasting"] = {
                    "type": "innate_spellcasting",
                    "ability": ability,
                    "spells": [
                        {
                            "name": spell_key,
                            "frequency": "at_will",
                            "min_level": 1,
                        }
                    ],
                }
                if tkey == "natural_illusionist" and spell_key == "minor_illusion":
                    features["forest_gnome_cantrip"] = {
                        "type": "innate_spellcasting",
                        "ability": ability,
                        "spell": {
                            "name": spell_key,
                            "frequency": "at_will",
                            "min_level": 1,
                            "ability": ability,
                        },
                    }

        if mtype == "talk_with_small_beasts":
            scope = "small_or_smaller_beasts"
            features["speak_with_small_beasts"] = {
                "type": "speak_with_beasts",
                "scope": scope,
            }
            features["talk_with_small_beasts"] = {
                "type": "speak_with_beasts",
                "scope": scope,
            }

        if mtype == "expertise":
            features["expertise"] = dict(mech)

        if mtype == "tinker":
            features["tinker"] = dict(mech)
            tool_prof = str(mech.get("tool_proficiency") or "").strip().lower()
            if tool_prof:
                tool_profs.append(tool_prof)

        if mtype in {"choose_feat", "feat_choice"}:
            choose = max(as_int(mech.get("choose"), as_int(mech.get("count"), 0)), 0)
            if choose > 0:
                features["feat_choice"] = {"choose": choose, "required": True}

        if tkey == "variable_trait_choice" and mtype == "choice":
            choose = max(as_int(mech.get("choose"), as_int(mech.get("count"), 0)), 0)
            options = _uniq_lower_str_list(mech.get("options"))
            if choose > 0 and options:
                features["variable_trait_choice"] = {
                    "choose": choose,
                    "options": options,
                    "required": True,
                }

    if save_advantage_conditions:
        saves["advantage_conditions"] = sorted(set(save_advantage_conditions))
    if save_advantage_vs_magic:
        saves["advantage_vs_magic"] = sorted(set(save_advantage_vs_magic))
    if race_key == "dwarf" or ("тяж" in speed_notes_ru and "не сниж" in speed_notes_ru and "скорост" in speed_notes_ru):
        movement["ignore_heavy_armor_speed_penalty"] = True

    out: dict[str, Any] = {
        "race_key": str(selected_race.get("key") or "").strip(),
        "size": size,
        "creature_type": creature_type,
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
            "weapons": sorted(set(weapon_profs)),
            "armor": sorted(set(armor_profs)),
        },
        "breath": breath,
        "movement": movement,
        "innate_spells": innate_spells,
        "carry": carry,
        "features": features,
        "saves": saves,
        "needs": needs,
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
        if bonus == 0:
            continue
        current = as_int(stats.get(stat_key), 50)
        stats[stat_key] = max(0, min(100, current + (bonus * 5)))


def _simic_enhancement_keys() -> tuple[set[str], set[str]]:
    lvl1 = {"manta_glide", "nimble_climber", "underwater_adaptation"}
    lvl5 = {"manta_glide", "nimble_climber", "underwater_adaptation", "grappling_appendages", "carapace", "acid_spit"}
    return lvl1, lvl5


def _apply_simic_enhancement_to_race_features(race_features: dict[str, Any], enhancement_key: str) -> None:
    if not isinstance(race_features, dict):
        return
    enhancement = str(enhancement_key or "").strip().lower()
    if not enhancement:
        return

    speeds = race_features.get("speeds")
    speeds_dict: dict[str, Any] = speeds if isinstance(speeds, dict) else {}
    features = race_features.get("features")
    features_dict: dict[str, Any] = features if isinstance(features, dict) else {}
    natural_weapons = race_features.get("natural_weapons")
    natural_weapons_list = list(natural_weapons) if isinstance(natural_weapons, list) else []
    breath = race_features.get("breath")
    breath_dict: dict[str, Any] = breath if isinstance(breath, dict) else {}
    walk_ft = max(0, as_int(speeds_dict.get("walk_ft"), 30))

    if enhancement == "manta_glide":
        features_dict["glide"] = {"reduce_fall_ft": 100, "horizontal_per_fall_ft": 2}
    elif enhancement == "nimble_climber":
        speeds_dict["climb_ft"] = walk_ft
    elif enhancement == "underwater_adaptation":
        features_dict["amphibious"] = True
        breath_dict["amphibious"] = True
        speeds_dict["swim_ft"] = walk_ft
    elif enhancement == "grappling_appendages":
        features_dict["grappling_appendages"] = {
            "damage_dice": "1d6",
            "damage_type": "bludgeoning",
            "ability": "str",
            "cannot_wield_weapons": True,
            "cannot_do_fine_work": True,
        }
        has_weapon = any(
            isinstance(item, dict) and str(item.get("key") or "").strip().lower() == "grappling_appendages"
            for item in natural_weapons_list
        )
        if not has_weapon:
            natural_weapons_list.append(
                {
                    "key": "grappling_appendages",
                    "kind": "unarmed",
                    "damage_dice": "1d6",
                    "damage_type": "bludgeoning",
                    "ability": "str",
                }
            )
    elif enhancement == "carapace":
        features_dict["ac_bonus_if_no_heavy_armor"] = {"ac_bonus": 1}
    elif enhancement == "acid_spit":
        features_dict["acid_spit"] = {
            "range_ft": 30,
            "damage": "2d10",
            "damage_type": "acid",
            "dc_formula": "8 + prof + con_mod",
            "uses_formula": "max(con_mod,1)",
            "recharge": "per_long_rest",
        }

    race_features["speeds"] = speeds_dict
    race_features["features"] = features_dict
    race_features["breath"] = breath_dict
    race_features["natural_weapons"] = natural_weapons_list


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
    race_choice_tools: list[str] = []
    race_choice_cantrips: list[str] = []
    race_choice_martial_weapons: list[str] = []
    race_choice_flex_asi_variant = ""
    race_choice_flex_asi_stats: list[str] = []
    race_choice_tp_skill = ""
    race_choice_tp_tool = ""
    race_choice_draconic_ancestry = ""
    race_choice_size = ""
    race_choice_variable_trait = ""
    race_choice_animal_enhancement_lvl1 = ""
    race_choice_decadent_language = ""
    race_choice_decadent_skill = ""
    race_choice_decadent_tool = ""
    race_choice_innate_ability = str(payload.get("race_choice_innate_ability") or "").strip().lower()
    if isinstance(race_choices_payload, dict):
        raw_langs = race_choices_payload.get("languages")
        raw_langs_list = raw_langs if isinstance(raw_langs, list) else []
        seen_language_keys: set[str] = set()
        for item in raw_langs_list:
            lang = str(item or "").strip().lower()
            if lang in seen_language_keys:
                raise HTTPException(status_code=400, detail="Language choices must be distinct")
            seen_language_keys.add(lang)
            if lang and lang not in LANGUAGE_WHITELIST:
                raise HTTPException(status_code=400, detail=f"Invalid language choice: {lang}")
            if lang and lang not in race_choice_languages:
                race_choice_languages.append(lang)
        raw_extra_language = str(race_choices_payload.get("extra_language") or "").strip().lower()
        if raw_extra_language:
            if raw_extra_language not in LANGUAGE_WHITELIST:
                raise HTTPException(status_code=400, detail=f"Invalid language choice: {raw_extra_language}")
            if raw_extra_language in seen_language_keys:
                raise HTTPException(status_code=400, detail="Language choices must be distinct")
            seen_language_keys.add(raw_extra_language)
            race_choice_languages.append(raw_extra_language)
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
            bonus = as_int(item.get("bonus"), as_int(item.get("delta"), 0))
            if bonus <= 0:
                continue
            if stat in seen_asi_stats:
                raise HTTPException(status_code=400, detail="ASI stats must be distinct")
            seen_asi_stats.add(stat)
            race_choice_asi.append({"stat": stat, "bonus": bonus})
        raw_asi_plus1_stat = str(race_choices_payload.get("asi_plus1_stat") or "").strip().lower()
        if raw_asi_plus1_stat:
            if raw_asi_plus1_stat not in allowed_asi_stats:
                raise HTTPException(status_code=400, detail=f"Invalid ASI stat choice: {raw_asi_plus1_stat}")
            if raw_asi_plus1_stat in seen_asi_stats:
                raise HTTPException(status_code=400, detail="ASI stats must be distinct")
            seen_asi_stats.add(raw_asi_plus1_stat)
            race_choice_asi.append({"stat": raw_asi_plus1_stat, "bonus": 1})
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
                raise HTTPException(status_code=400, detail="Skill choices must be distinct")
            seen_skill_keys.add(skill)
            race_choice_skills.append(skill)
        raw_specialized_skill = str(race_choices_payload.get("specialized_design_skill") or "").strip().lower()
        if raw_specialized_skill:
            if raw_specialized_skill not in allowed_skill_keys:
                raise HTTPException(status_code=400, detail=f"Invalid skill choice: {raw_specialized_skill}")
            if raw_specialized_skill in seen_skill_keys:
                raise HTTPException(status_code=400, detail="Skill choices must be distinct")
            seen_skill_keys.add(raw_specialized_skill)
            race_choice_skills.append(raw_specialized_skill)
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
        raw_tools = race_choices_payload.get("tools")
        raw_tools_list = raw_tools if isinstance(raw_tools, list) else []
        for item in raw_tools_list:
            tool = str(item or "").strip().lower()
            if tool and tool not in race_choice_tools:
                race_choice_tools.append(tool)
        raw_specialized_tool = str(race_choices_payload.get("specialized_design_tool") or "").strip().lower()
        if raw_specialized_tool and raw_specialized_tool not in race_choice_tools:
            race_choice_tools.append(raw_specialized_tool)
        raw_cantrips = race_choices_payload.get("cantrips")
        raw_cantrips_list = raw_cantrips if isinstance(raw_cantrips, list) else []
        for item in raw_cantrips_list:
            cantrip = str(item or "").strip().lower()
            if not cantrip:
                continue
            if cantrip not in WIZARD_CANTRIP_WHITELIST:
                raise HTTPException(status_code=400, detail=f"Invalid cantrip choice: {cantrip}")
            if cantrip not in race_choice_cantrips:
                race_choice_cantrips.append(cantrip)
        raw_martial_weapons = race_choices_payload.get("martial_weapons")
        raw_martial_weapons_list = raw_martial_weapons if isinstance(raw_martial_weapons, list) else []
        seen_martial_weapon_keys: set[str] = set()
        for item in raw_martial_weapons_list:
            weapon_key = str(item or "").strip().lower()
            if not weapon_key:
                continue
            if weapon_key not in MARTIAL_WEAPON_WHITELIST:
                raise HTTPException(status_code=400, detail=f"Invalid martial weapon choice: {weapon_key}")
            if weapon_key in seen_martial_weapon_keys:
                raise HTTPException(status_code=400, detail="Martial weapon choices must be distinct")
            seen_martial_weapon_keys.add(weapon_key)
            race_choice_martial_weapons.append(weapon_key)
        raw_flex_asi = race_choices_payload.get("flex_asi")
        if isinstance(raw_flex_asi, dict):
            race_choice_flex_asi_variant = str(raw_flex_asi.get("variant") or "").strip().lower()
            raw_flex_stats = raw_flex_asi.get("stats")
            raw_flex_stats_list = raw_flex_stats if isinstance(raw_flex_stats, list) else []
            allowed_asi_stats = {"str", "dex", "con", "int", "wis", "cha"}
            seen_flex_asi_stats: set[str] = set()
            for item in raw_flex_stats_list:
                stat_key = str(item or "").strip().lower()
                if not stat_key:
                    continue
                if stat_key not in allowed_asi_stats:
                    raise HTTPException(status_code=400, detail=f"Invalid flex ASI stat choice: {stat_key}")
                if stat_key in seen_flex_asi_stats:
                    raise HTTPException(status_code=400, detail="Flex ASI stats must be distinct")
                seen_flex_asi_stats.add(stat_key)
                race_choice_flex_asi_stats.append(stat_key)
        raw_tp = race_choices_payload.get("tireless_precision")
        if isinstance(raw_tp, dict):
            race_choice_tp_skill = str(raw_tp.get("skill") or "").strip().lower()
            race_choice_tp_tool = str(raw_tp.get("tool") or "").strip().lower()
        race_choice_draconic_ancestry = str(race_choices_payload.get("draconic_ancestry") or "").strip().lower()
        race_choice_size = str(race_choices_payload.get("size") or "").strip().lower()
        race_choice_variable_trait = str(race_choices_payload.get("variable_trait") or "").strip().lower()
        race_choice_animal_enhancement_lvl1 = str(race_choices_payload.get("animal_enhancement_lvl1") or "").strip().lower()
        raw_decadent_mastery = race_choices_payload.get("decadent_mastery")
        if isinstance(raw_decadent_mastery, dict):
            race_choice_decadent_language = str(raw_decadent_mastery.get("language") or "").strip().lower()
            race_choice_decadent_skill = str(raw_decadent_mastery.get("skill") or "").strip().lower()
            race_choice_decadent_tool = str(raw_decadent_mastery.get("tool") or "").strip().lower()

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
        selected_race_key = str((selected_race or {}).get("key") or "").strip().lower()
        selected_subrace: dict[str, Any] | None = None
        effective_race: dict[str, Any] | None = selected_race

        if selected_race_key == "gith" and not subrace_id:
            raise HTTPException(status_code=400, detail="Gith subrace choice is required")
        if selected_race_key == "shifter" and not subrace_id:
            raise HTTPException(status_code=400, detail="Shifter subrace choice is required")

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
            if selected_race_key in {"gith", "shifter"} and selected_subrace is None:
                raise HTTPException(status_code=400, detail=f"Invalid subrace choice: {subrace_id}")

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
        draconic_ancestry_options: list[dict[str, Any]] = []
        breath_weapon_mechanics: dict[str, Any] = {}
        wizard_cantrip_choice_cfg: dict[str, Any] = {}
        required_race_asi_count = 0
        required_race_asi_bonus = 0
        required_race_asi_exclude: set[str] = set()
        required_race_asi_from: set[str] = set()
        required_race_skill_count = 0
        required_race_skill_options: list[str] = []
        required_race_feat_count = 0
        required_race_martial_weapon_count = 0
        required_race_language_count = 0
        race_language_choice_available = False
        race_flex_asi_available = False
        effective_race_key = ""
        custom_lineage_variable_trait_options: list[str] = []
        base_race_language_keys: set[str] = set()
        if isinstance(effective_race, dict):
            effective_traits = effective_race.get("traits")
            effective_traits_list = effective_traits if isinstance(effective_traits, list) else []
            effective_asi = effective_race.get("asi")
            effective_asi_list = effective_asi if isinstance(effective_asi, list) else []
            effective_languages = effective_race.get("languages")
            effective_languages_list = effective_languages if isinstance(effective_languages, list) else []
            for item in effective_languages_list:
                lang_key = str(item or "").strip().lower()
                if lang_key:
                    base_race_language_keys.add(lang_key)
            effective_race_key = str(effective_race.get("key") or "").strip().lower()
            if effective_race_key == "changeling":
                for asi_item in effective_asi_list:
                    if not isinstance(asi_item, dict):
                        continue
                    choose = max(as_int(asi_item.get("choose"), as_int(asi_item.get("count"), 0)), 0)
                    bonus = max(as_int(asi_item.get("bonus"), as_int(asi_item.get("delta"), 0)), 0)
                    from_raw = asi_item.get("from")
                    from_list = from_raw if isinstance(from_raw, list) else [from_raw]
                    from_items = [str(x or "").strip().lower() for x in from_list if str(x or "").strip()]
                    if choose == 1 and bonus == 1 and from_items:
                        required_race_asi_count = max(required_race_asi_count, 1)
                        required_race_asi_bonus = max(required_race_asi_bonus, 1)
                        required_race_asi_from.update(from_items)
                        required_race_asi_exclude.add("cha")
            for asi_item in effective_asi_list:
                if not isinstance(asi_item, dict):
                    continue
                choose = max(as_int(asi_item.get("choose"), as_int(asi_item.get("count"), 0)), 0)
                bonus = max(as_int(asi_item.get("bonus"), as_int(asi_item.get("delta"), 0)), 0)
                if choose <= 0 or bonus <= 0:
                    continue
                required_race_asi_count = max(required_race_asi_count, choose)
                required_race_asi_bonus = max(required_race_asi_bonus, bonus)
                from_raw = asi_item.get("from")
                from_list = from_raw if isinstance(from_raw, list) else [from_raw]
                for item in from_list:
                    stat_key = str(item or "").strip().lower()
                    if stat_key:
                        required_race_asi_from.add(stat_key)
            for asi_item in effective_asi_list:
                if not isinstance(asi_item, dict):
                    continue
                if str(asi_item.get("note") or "").strip().lower() == "flexible_asi":
                    race_flex_asi_available = True
                    break
            for trait in effective_traits_list:
                if not isinstance(trait, dict):
                    continue
                mech = trait.get("mechanics")
                if not isinstance(mech, dict):
                    continue
                mtype = str(mech.get("type") or "").strip().lower()
                if mtype != "tireless_precision":
                    if mtype == "choose_draconic_ancestry":
                        options = mech.get("options")
                        options_list = options if isinstance(options, list) else []
                        for option in options_list:
                            if not isinstance(option, dict):
                                continue
                            ancestry_key = str(option.get("key") or "").strip().lower()
                            damage_type = str(option.get("damage_type") or "").strip().lower()
                            breath = option.get("breath")
                            breath_obj = dict(breath) if isinstance(breath, dict) else {}
                            if ancestry_key:
                                draconic_ancestry_options.append(
                                    {
                                        "key": ancestry_key,
                                        "damage_type": damage_type,
                                        "breath": breath_obj,
                                    }
                                )
                    elif mtype == "breath_weapon":
                        breath_weapon_mechanics = dict(mech)
                    elif mtype == "choice" and str(mech.get("from_list") or "").strip().lower() == "wizard_cantrips":
                        wizard_cantrip_choice_cfg = {
                            "choose": max(as_int(mech.get("choose"), 0), 0),
                            "from_list": "wizard_cantrips",
                            "ability": str(mech.get("ability") or "").strip().lower(),
                        }
                    elif mtype == "choose_asi":
                        count = max(as_int(mech.get("count"), as_int(mech.get("choices"), 0)), 0)
                        bonus = max(as_int(mech.get("delta"), as_int(mech.get("bonus"), 0)), 0)
                        if count > 0 and bonus > 0:
                            required_race_asi_count = max(required_race_asi_count, count)
                            required_race_asi_bonus = max(required_race_asi_bonus, bonus)
                            for item in (mech.get("exclude") if isinstance(mech.get("exclude"), list) else []):
                                key = str(item or "").strip().lower()
                                if key:
                                    required_race_asi_exclude.add(key)
                    elif mtype in {"choose_skill_proficiency", "choose_skill_proficiencies"}:
                        count = max(as_int(mech.get("count"), as_int(mech.get("choose"), 0)), 0)
                        if count > 0:
                            required_race_skill_count = max(required_race_skill_count, count)
                            from_items: list[str] = []
                            from_raw = mech.get("from")
                            from_list = from_raw if isinstance(from_raw, list) else [from_raw]
                            for item in from_list:
                                skill_key = str(item or "").strip().lower()
                                if skill_key and skill_key not in from_items:
                                    from_items.append(skill_key)
                            if from_items and not required_race_skill_options:
                                required_race_skill_options = from_items
                    elif mtype == "specialized_design":
                        choose_skill = max(as_int(mech.get("choose_skill"), 0), 0)
                        if choose_skill > 0:
                            required_race_skill_count = max(required_race_skill_count, choose_skill)
                    elif mtype == "ancestral_legacy":
                        fallback_count = max(as_int(mech.get("fallback_choose_skills"), 0), 0)
                        if fallback_count > 0:
                            required_race_skill_count = max(required_race_skill_count, fallback_count)
                    elif mtype in {"choose_feat", "feat_choice"}:
                        count = max(as_int(mech.get("count"), as_int(mech.get("choose"), 0)), 0)
                        if count > 0:
                            required_race_feat_count = max(required_race_feat_count, count)
                    elif mtype == "proficiency_bundle":
                        choose_martial = max(as_int(mech.get("choose_martial_weapons"), 0), 0)
                        if choose_martial > 0:
                            required_race_martial_weapon_count = max(required_race_martial_weapon_count, choose_martial)
                    elif mtype in {"choose_language", "language_choice"}:
                        count = max(as_int(mech.get("count"), as_int(mech.get("choose"), 0)), 0)
                        if count > 0:
                            race_language_choice_available = True
                            required_race_language_count = max(required_race_language_count, count)
                    elif mtype == "choice":
                        from_raw = mech.get("from")
                        from_values = from_raw if isinstance(from_raw, list) else [from_raw]
                        normalized_from = [str(item or "").strip().lower() for item in from_values if str(item or "").strip()]
                        if normalized_from and ("any" in normalized_from or "any_language" in normalized_from):
                            count = max(as_int(mech.get("count"), as_int(mech.get("choose"), 0)), 0)
                            if count > 0:
                                race_language_choice_available = True
                                required_race_language_count = max(required_race_language_count, count)
                        options = mech.get("options")
                        options_list = options if isinstance(options, list) else []
                        if str(trait.get("key") or "").strip().lower() == "variable_trait_choice":
                            for item in options_list:
                                option_key = str(item or "").strip().lower()
                                if option_key and option_key not in custom_lineage_variable_trait_options:
                                    custom_lineage_variable_trait_options.append(option_key)
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

        ancestry_by_key = {
            str(item.get("key") or "").strip().lower(): item for item in draconic_ancestry_options if isinstance(item, dict)
        }
        ancestry_required = bool(ancestry_by_key)
        if ancestry_required and not race_choice_draconic_ancestry:
            raise HTTPException(status_code=400, detail="Draconic ancestry choice is required")
        if race_choice_draconic_ancestry and race_choice_draconic_ancestry not in ancestry_by_key:
            raise HTTPException(status_code=400, detail=f"Invalid draconic ancestry choice: {race_choice_draconic_ancestry}")
        if not ancestry_required and race_choice_draconic_ancestry:
            raise HTTPException(status_code=400, detail="Draconic ancestry is not available for selected race")
        wizard_cantrip_required = max(as_int(wizard_cantrip_choice_cfg.get("choose"), 0), 0)
        if wizard_cantrip_required > 0:
            if len(race_choice_cantrips) != wizard_cantrip_required:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exactly {wizard_cantrip_required} wizard cantrip choice(s) required",
                )
        elif race_choice_cantrips:
            raise HTTPException(status_code=400, detail="Wizard cantrip choice is not available for selected race")

        if required_race_asi_count > 0:
            if len(race_choice_asi) != required_race_asi_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exactly {required_race_asi_count} race ASI choice(s) required",
                )
            if required_race_asi_bonus > 0:
                for item in race_choice_asi:
                    if as_int(item.get("bonus"), 0) != required_race_asi_bonus:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Race ASI bonus must be +{required_race_asi_bonus}",
                        )
            for item in race_choice_asi:
                stat_key = str(item.get("stat") or "").strip().lower()
                if stat_key in required_race_asi_exclude:
                    raise HTTPException(status_code=400, detail=f"Invalid ASI stat choice: {stat_key}")
                if required_race_asi_from and stat_key not in required_race_asi_from:
                    raise HTTPException(status_code=400, detail=f"Invalid ASI stat choice: {stat_key}")
        elif race_choice_asi:
            raise HTTPException(status_code=400, detail="Race ASI choice is not available for selected race")

        if required_race_skill_count > 0:
            if len(race_choice_skills) != required_race_skill_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exactly {required_race_skill_count} race skill choice(s) required",
                )
            if required_race_skill_options:
                for skill in race_choice_skills:
                    if skill not in required_race_skill_options:
                        raise HTTPException(status_code=400, detail=f"Invalid race skill choice: {skill}")
        elif race_choice_skills and not (
            effective_race_key == "custom_lineage" and race_choice_variable_trait == "skill_proficiency_choice_1"
        ):
            raise HTTPException(status_code=400, detail="Race skill choice is not available for selected race")

        if required_race_language_count > 0:
            if len(race_choice_languages) != required_race_language_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exactly {required_race_language_count} race language choice(s) required",
                )
        elif race_choice_languages and not race_language_choice_available:
            raise HTTPException(status_code=400, detail="Race language choice is not available for selected race")

        if race_flex_asi_available:
            if race_choice_flex_asi_variant not in {"2_1", "1_1_1"}:
                raise HTTPException(status_code=400, detail="Flex ASI variant is required")
            expected_count = 2 if race_choice_flex_asi_variant == "2_1" else 3
            if len(race_choice_flex_asi_stats) != expected_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Flex ASI requires exactly {expected_count} distinct stat choice(s)",
                )
        elif race_choice_flex_asi_variant or race_choice_flex_asi_stats:
            raise HTTPException(status_code=400, detail="Flex ASI is not available for selected race")
        if required_race_feat_count > 0:
            if len(race_choice_feats) != required_race_feat_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exactly {required_race_feat_count} race feat choice(s) required",
                )
        elif race_choice_feats:
            raise HTTPException(status_code=400, detail="Race feat choice is not available for selected race")
        if required_race_martial_weapon_count > 0:
            if len(race_choice_martial_weapons) != required_race_martial_weapon_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exactly {required_race_martial_weapon_count} martial weapon choice(s) required",
                )
        elif race_choice_martial_weapons:
            raise HTTPException(status_code=400, detail="Martial weapon choice is not available for selected race")

        if race_choice_size and effective_race_key not in {"custom_lineage", "dhampir", "harengon", "hexblood", "owlin", "reborn"}:
            raise HTTPException(status_code=400, detail="Race size choice is not available for selected race")
        if race_choice_variable_trait and effective_race_key != "custom_lineage":
            raise HTTPException(status_code=400, detail="Variable trait choice is not available for selected race")
        if effective_race_key == "custom_lineage":
            if race_choice_size not in {"small", "medium"}:
                raise HTTPException(status_code=400, detail="Custom Lineage size choice is required")
            if len(race_choice_asi) != 1 or as_int((race_choice_asi[0] or {}).get("bonus"), 0) != 2:
                raise HTTPException(status_code=400, detail="Custom Lineage requires exactly one +2 ASI choice")
            if len(race_choice_feats) != 1:
                raise HTTPException(status_code=400, detail="Custom Lineage feat choice is required")
            variable_options = (
                custom_lineage_variable_trait_options
                if custom_lineage_variable_trait_options
                else ["darkvision_60", "skill_proficiency_choice_1"]
            )
            if race_choice_variable_trait not in variable_options:
                raise HTTPException(status_code=400, detail="Custom Lineage variable trait choice is required")
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Custom Lineage extra language choice is required")
            if race_choice_languages[0] == "common":
                raise HTTPException(status_code=400, detail="Custom Lineage extra language must not duplicate Common")
            if race_choice_variable_trait == "skill_proficiency_choice_1":
                if len(race_choice_skills) != 1:
                    raise HTTPException(status_code=400, detail="Custom Lineage skill choice is required")
            elif race_choice_skills:
                raise HTTPException(
                    status_code=400,
                    detail="Custom Lineage skill choice is only available with skill_proficiency_choice_1",
                )
        if effective_race_key == "dhampir":
            if race_choice_size not in {"small", "medium"}:
                raise HTTPException(status_code=400, detail="Dhampir size choice is required")
            if race_choice_flex_asi_variant not in {"2_1", "1_1_1"}:
                raise HTTPException(status_code=400, detail="Dhampir flexible ASI choice is required")
            if len(race_choice_skills) != 2:
                raise HTTPException(status_code=400, detail="Dhampir ancestral legacy requires exactly 2 skill choices")
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Dhampir extra language choice is required")
            dhampir_lang = race_choice_languages[0]
            if dhampir_lang == "common":
                raise HTTPException(status_code=400, detail="Dhampir extra language must not duplicate Common")
            if dhampir_lang in base_race_language_keys:
                raise HTTPException(status_code=400, detail="Dhampir extra language must be distinct from base languages")
        if effective_race_key == "harengon":
            if race_choice_size not in {"small", "medium"}:
                raise HTTPException(status_code=400, detail="Harengon size choice is required")
            if race_choice_flex_asi_variant not in {"2_1", "1_1_1"}:
                raise HTTPException(status_code=400, detail="Harengon flexible ASI choice is required")
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Harengon extra language choice is required")
            harengon_lang = race_choice_languages[0]
            if harengon_lang == "common":
                raise HTTPException(status_code=400, detail="Harengon extra language must not duplicate Common")
            if harengon_lang in base_race_language_keys:
                raise HTTPException(
                    status_code=400,
                    detail="Harengon extra language must not duplicate base race languages",
                )
        if effective_race_key == "hexblood":
            if race_choice_size not in {"small", "medium"}:
                raise HTTPException(status_code=400, detail="Hexblood size choice is required")
            if race_choice_flex_asi_variant not in {"2_1", "1_1_1"}:
                raise HTTPException(status_code=400, detail="Hexblood flexible ASI choice is required")
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Hexblood extra language choice is required")
            hexblood_lang = race_choice_languages[0]
            if hexblood_lang == "common":
                raise HTTPException(status_code=400, detail="Hexblood extra language must not duplicate Common")
            if hexblood_lang in base_race_language_keys:
                raise HTTPException(status_code=400, detail="Hexblood extra language must be distinct from base languages")
            if race_choice_innate_ability not in {"int", "wis", "cha"}:
                raise HTTPException(
                    status_code=400,
                    detail="Hexblood innate spellcasting ability choice required (int/wis/cha)",
                )
            if len(race_choice_skills) != 2:
                raise HTTPException(status_code=400, detail="Hexblood ancestral legacy requires exactly 2 skill choices")
        if effective_race_key == "owlin":
            if race_choice_size not in {"small", "medium"}:
                raise HTTPException(status_code=400, detail="Owlin size choice is required")
            if race_choice_flex_asi_variant not in {"2_1", "1_1_1"}:
                raise HTTPException(status_code=400, detail="Owlin flexible ASI choice is required")
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Owlin extra language choice is required")
            owlin_lang = race_choice_languages[0]
            if owlin_lang == "common":
                raise HTTPException(status_code=400, detail="Owlin extra language must not duplicate Common")
            if owlin_lang in base_race_language_keys:
                raise HTTPException(status_code=400, detail="Owlin extra language must be distinct from base race languages")
        if effective_race_key == "reborn":
            if race_choice_size not in {"small", "medium"}:
                raise HTTPException(status_code=400, detail="Reborn size choice is required")
            if race_choice_flex_asi_variant not in {"2_1", "1_1_1"}:
                raise HTTPException(status_code=400, detail="Reborn flexible ASI choice is required")
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Reborn extra language choice is required")
            reborn_lang = race_choice_languages[0]
            if reborn_lang == "common":
                raise HTTPException(status_code=400, detail="Reborn extra language must not duplicate Common")
            if reborn_lang in base_race_language_keys:
                raise HTTPException(status_code=400, detail="Reborn extra language must be distinct from base race languages")
            if len(race_choice_skills) != 2:
                raise HTTPException(status_code=400, detail="Reborn ancestral legacy requires exactly 2 skill choices")
        if effective_race_key == "fairy":
            if race_choice_innate_ability not in {"int", "wis", "cha"}:
                raise HTTPException(
                    status_code=400,
                    detail="Race innate spellcasting ability choice required (int/wis/cha)",
                )
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Fairy extra language choice is required")
            fairy_lang = race_choice_languages[0]
            if fairy_lang == "common":
                raise HTTPException(status_code=400, detail="Fairy extra language cannot be Common")
            if fairy_lang in base_race_language_keys:
                raise HTTPException(status_code=400, detail="Fairy extra language must be distinct from base languages")
            if race_choice_flex_asi_variant not in {"2_1", "1_1_1"}:
                raise HTTPException(status_code=400, detail="Fairy flexible ASI choice is required")
        if effective_race_key == "kalashtar":
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Kalashtar extra language choice is required")
            kalashtar_lang = race_choice_languages[0]
            if kalashtar_lang in base_race_language_keys:
                raise HTTPException(
                    status_code=400,
                    detail="Kalashtar extra language must be distinct from Common and Quori",
                )
        if effective_race_key == "kender":
            if race_choice_flex_asi_variant not in {"2_1", "1_1_1"}:
                raise HTTPException(status_code=400, detail="Kender flexible ASI choice is required")
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Kender extra language choice is required")
            kender_lang = race_choice_languages[0]
            if kender_lang in base_race_language_keys:
                raise HTTPException(
                    status_code=400,
                    detail="Kender extra language must not duplicate Common/base languages",
                )
            allowed_kender_skills = {"insight", "investigation", "sleight_of_hand", "stealth", "survival"}
            if len(race_choice_skills) != 1:
                raise HTTPException(status_code=400, detail="Kender aptitude requires exactly 1 skill choice")
            if race_choice_skills[0] not in allowed_kender_skills:
                raise HTTPException(status_code=400, detail="Invalid Kender aptitude skill choice")
            if race_choice_innate_ability not in {"int", "wis", "cha"}:
                raise HTTPException(status_code=400, detail="Kender taunt ability choice required (int/wis/cha)")
        if effective_race_key == "simic_hybrid":
            simic_lvl1_options, _simic_lvl5_options = _simic_enhancement_keys()
            if len(race_choice_asi) != 1 or as_int((race_choice_asi[0] or {}).get("bonus"), 0) != 1:
                raise HTTPException(status_code=400, detail="Simic Hybrid requires exactly one +1 ASI choice")
            simic_asi_stat = str((race_choice_asi[0] or {}).get("stat") or "").strip().lower()
            if simic_asi_stat not in {"str", "dex", "int", "wis", "cha"}:
                raise HTTPException(status_code=400, detail="Simic Hybrid ASI +1 must be str/dex/int/wis/cha")
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Simic Hybrid language choice is required")
            simic_lang = race_choice_languages[0]
            if simic_lang not in {"elvish", "vedalken"}:
                raise HTTPException(status_code=400, detail="Simic Hybrid language must be Elvish or Vedalken")
            if race_choice_animal_enhancement_lvl1 not in simic_lvl1_options:
                raise HTTPException(status_code=400, detail="Simic Hybrid level 1 animal enhancement choice is required")
        if effective_race_key == "warforged":
            if len(race_choice_asi) != 1 or as_int((race_choice_asi[0] or {}).get("bonus"), 0) != 1:
                raise HTTPException(status_code=400, detail="Warforged requires exactly one +1 ASI choice")
            warforged_asi_stat = str((race_choice_asi[0] or {}).get("stat") or "").strip().lower()
            if warforged_asi_stat not in {"str", "dex", "int", "wis", "cha"}:
                raise HTTPException(status_code=400, detail="Warforged ASI +1 must be str/dex/int/wis/cha")
            if warforged_asi_stat == "con":
                raise HTTPException(status_code=400, detail="Warforged ASI +1 cannot be con")
            if len(race_choice_skills) != 1:
                raise HTTPException(status_code=400, detail="Warforged specialized design requires exactly 1 skill choice")
            if len(race_choice_tools) != 1:
                raise HTTPException(status_code=400, detail="Warforged specialized design requires exactly 1 tool choice")
            if race_choice_tools[0] not in TIRELESS_PRECISION_TOOL_WHITELIST:
                raise HTTPException(status_code=400, detail=f"Invalid race tool choice: {race_choice_tools[0]}")
            if len(race_choice_languages) != 1:
                raise HTTPException(status_code=400, detail="Warforged extra language choice is required")
            warforged_lang = race_choice_languages[0]
            if warforged_lang == "common":
                raise HTTPException(status_code=400, detail="Warforged extra language must not duplicate Common")
            if warforged_lang in base_race_language_keys:
                raise HTTPException(status_code=400, detail="Warforged extra language must be distinct from base languages")
        if race_choice_animal_enhancement_lvl1 and effective_race_key != "simic_hybrid":
            raise HTTPException(status_code=400, detail="Animal enhancement choice is not available for selected race")
        elif race_choice_innate_ability and effective_race_key not in {"hexblood", "kender"}:
            raise HTTPException(
                status_code=400,
                detail="Race innate spellcasting ability choice is not available for selected race",
            )

        selected_subrace_key = str((selected_subrace or {}).get("key") or "").strip().lower()
        is_githyanki = effective_race_key == "gith" and selected_subrace_key == "githyanki"
        if is_githyanki:
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
            if not race_choice_decadent_language:
                raise HTTPException(status_code=400, detail="Githyanki Decadent Mastery language choice is required")
            if race_choice_decadent_language in {"common", "gith"}:
                raise HTTPException(
                    status_code=400,
                    detail="Githyanki Decadent Mastery language must not duplicate Common or Gith",
                )
            if race_choice_decadent_language in base_race_language_keys:
                raise HTTPException(
                    status_code=400,
                    detail="Githyanki Decadent Mastery language must be distinct from base languages",
                )
            has_decadent_skill = bool(race_choice_decadent_skill)
            has_decadent_tool = bool(race_choice_decadent_tool)
            if has_decadent_skill and has_decadent_tool:
                raise HTTPException(
                    status_code=400,
                    detail="Githyanki Decadent Mastery requires exactly one choice: skill or tool",
                )
            if not has_decadent_skill and not has_decadent_tool:
                raise HTTPException(
                    status_code=400,
                    detail="Githyanki Decadent Mastery requires one choice: skill or tool",
                )
            if has_decadent_skill and race_choice_decadent_skill not in allowed_skill_keys:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Githyanki Decadent Mastery skill: {race_choice_decadent_skill}",
                )
            if has_decadent_tool and race_choice_decadent_tool not in TIRELESS_PRECISION_TOOL_WHITELIST:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Githyanki Decadent Mastery tool: {race_choice_decadent_tool}",
                )
        elif race_choice_decadent_language or race_choice_decadent_skill or race_choice_decadent_tool:
            raise HTTPException(
                status_code=400,
                detail="Githyanki Decadent Mastery choices are not available for selected race",
            )

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
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "grung":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("grung_weapon_poison_armed", False)
            runtime.setdefault("water_last_immersion_at", "")
            runtime.setdefault("water_dependency_exhaustion_level", 0)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "hexblood":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("innate_shared_uses", {})
            runtime.setdefault("eerie_token_uses_used", 0)
            runtime.setdefault("eerie_token_active", False)
            runtime.setdefault("eerie_token_consumed", False)
            runtime.setdefault("eerie_token_created_at", "")
            runtime.setdefault("eerie_token_expires_on_next_long_rest", True)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "hobgoblin":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("saving_face_uses_used", 0)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "kalashtar":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("mind_link_target_id", "")
            runtime.setdefault("mind_link_reply_until", "")
            runtime.setdefault("mind_link_last_set_at", "")
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "lizardfolk":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("hungry_jaws_uses_used", 0)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "kender":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("fearless_auto_success_used", 0)
            runtime.setdefault("fearless_pending_failed_frightened_save", {})
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "locathah":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("water_last_immersion_at", "")
            runtime.setdefault("limited_amphibious_hours_since_immersion", 0.0)
            runtime.setdefault("suffocating", True)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "minotaur":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("goring_rush_available", False)
            runtime.setdefault("hammering_horns_available", False)
            runtime.setdefault("hammering_horns_target_id", "")
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "reborn":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("knowledge_past_life_uses_used", 0)
            runtime.setdefault("knowledge_past_life_armed", False)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "shifter":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("shifted_active", False)
            runtime.setdefault("shifted_rounds_left", 0)
            runtime.setdefault("shifting_uses_used", 0)
            runtime.setdefault("shifting_temp_hp_granted", 0)
            runtime.setdefault("shifting_ac_bonus_active", 0)
            runtime.setdefault("shifting_speed_bonus_active_ft", 0)
            runtime.setdefault("shifting_longtooth_bite_available", False)
            runtime.setdefault("shifting_swiftstride_reaction_available", False)
            runtime.setdefault("wildhunt_marked_target_id", "")
            runtime.setdefault("wildhunt_marked_until", "")
            runtime.setdefault("marked_uses_used", 0)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "simic_hybrid":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("simic_lvl1_enhancement", "")
            runtime.setdefault("simic_lvl5_enhancement", "")
            runtime.setdefault("acid_spit_uses_used", 0)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "tabaxi":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("feline_agility_available", True)
            runtime.setdefault("feline_agility_active", False)
            runtime.setdefault("feline_agility_used_turn", "")
            runtime.setdefault("moved_this_turn_ft", 0)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "tortle":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("shell_defense_active", False)
            runtime.setdefault("shell_defense_entered_turn", "")
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "triton":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("triton_gust_of_wind_used", False)
            runtime.setdefault("triton_wall_of_water_used", False)
            runtime.setdefault("triton_active_water_wall", None)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "tiefling":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("tiefling_hellish_rebuke_used", False)
            runtime.setdefault("tiefling_darkness_used", False)
            race_features["runtime"] = runtime
        if (
            isinstance(race_features, dict)
            and str(race_features.get("race_key") or "").strip().lower() == "elf"
            and selected_subrace is not None
            and str(selected_subrace.get("key") or "").strip().lower() == "drow"
        ):
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("drow_faerie_fire_used", False)
            runtime.setdefault("drow_darkness_used", False)
            race_features["runtime"] = runtime
        if (
            isinstance(race_features, dict)
            and str(race_features.get("race_key") or "").strip().lower() == "dwarf"
            and selected_subrace is not None
            and str(selected_subrace.get("key") or "").strip().lower() == "duergar"
        ):
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("duergar_enlarge_used", False)
            runtime.setdefault("duergar_invisibility_used", False)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "firbolg":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            hidden_raw = runtime.get("hidden_step")
            hidden = dict(hidden_raw) if isinstance(hidden_raw, dict) else {}
            hidden.setdefault("used", 0)
            hidden.setdefault("active", False)
            hidden.setdefault("source", "hidden_step")
            hidden.setdefault("expires_on_owner_turn_start", True)
            runtime["hidden_step"] = hidden
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "yuan_ti_pureblood":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("yuanti_suggestion_used", False)
            runtime.setdefault("yuanti_last_innate_spell", None)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "warforged":
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("warforged_sentry_rest_active", False)
            runtime.setdefault("warforged_integrated_armor_state", None)
            race_features["runtime"] = runtime
        if (
            isinstance(race_features, dict)
            and selected_subrace is not None
            and str(selected_race.get("key") or "").strip().lower() == "gnome"
            and str(selected_subrace.get("key") or "").strip().lower() == "rock_gnome"
        ):
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime.setdefault("tinker_devices", [])
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and selected_subrace is not None:
            race_features["subrace"] = {
                "key": str(selected_subrace.get("key") or "").strip(),
                "name_ru": str(selected_subrace.get("name_ru") or selected_subrace.get("name") or "").strip(),
            }
        tool_choice_cfg: dict[str, Any] = {}
        if isinstance(race_features, dict):
            rf_features = race_features.get("features")
            if isinstance(rf_features, dict):
                maybe_tool_choice = rf_features.get("tool_choice")
                if isinstance(maybe_tool_choice, dict):
                    tool_choice_cfg = maybe_tool_choice
        allowed_tool_choices: list[str] = []
        for item in (tool_choice_cfg.get("from") if isinstance(tool_choice_cfg.get("from"), list) else []):
            tool = str(item or "").strip().lower()
            if tool and tool not in allowed_tool_choices:
                allowed_tool_choices.append(tool)
        required_tool_choices = max(as_int(tool_choice_cfg.get("choose"), 0), 0)
        if "any" in allowed_tool_choices:
            allowed_tool_choices = sorted(AUTOGNOME_TOOL_WHITELIST)
        if required_tool_choices > 0:
            if len(race_choice_tools) != required_tool_choices:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exactly {required_tool_choices} race tool choice(s) required",
                )
            for tool in race_choice_tools:
                if tool not in allowed_tool_choices:
                    raise HTTPException(status_code=400, detail=f"Invalid race tool choice: {tool}")
        elif race_choice_tools:
            raise HTTPException(status_code=400, detail="Race tool choice is not available for selected race")
        choices = race_features.get("choices") if isinstance(race_features, dict) else None
        choices_dict: dict[str, Any] = choices if isinstance(choices, dict) else {}
        if isinstance(race_features, dict) and selected_subrace is not None:
            choices_dict["subrace_id"] = str(selected_subrace.get("key") or "").strip().lower()
        if isinstance(race_features, dict) and is_githyanki:
            base_langs = race_features.get("languages")
            base_langs_list = base_langs if isinstance(base_langs, list) else []
            merged_langs: list[str] = []
            for item in [*base_langs_list, race_choice_decadent_language]:
                lang = str(item or "").strip().lower()
                if lang and lang not in merged_langs:
                    merged_langs.append(lang)
            race_features["languages"] = merged_langs

            prof_raw = race_features.get("proficiencies")
            prof_dict: dict[str, Any] = prof_raw if isinstance(prof_raw, dict) else {}
            skills_raw = prof_dict.get("skills")
            tools_raw = prof_dict.get("tools")
            skills = [str(item or "").strip().lower() for item in (skills_raw if isinstance(skills_raw, list) else []) if str(item or "").strip()]
            tools = [str(item or "").strip().lower() for item in (tools_raw if isinstance(tools_raw, list) else []) if str(item or "").strip()]
            if race_choice_decadent_skill and race_choice_decadent_skill not in skills:
                skills.append(race_choice_decadent_skill)
            if race_choice_decadent_tool and race_choice_decadent_tool not in tools:
                tools.append(race_choice_decadent_tool)
            prof_dict["skills"] = skills
            prof_dict["tools"] = tools
            race_features["proficiencies"] = prof_dict

            choices_dict["decadent_mastery"] = {
                "language": race_choice_decadent_language,
                "skill": race_choice_decadent_skill or None,
                "tool": race_choice_decadent_tool or None,
            }
        if (
            isinstance(race_features, dict)
            and str(selected_race.get("key") or "").strip().lower() == "gith"
            and selected_subrace is not None
        ):
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            selected_subrace_key = str(selected_subrace.get("key") or "").strip().lower()
            if selected_subrace_key == "githyanki":
                runtime.setdefault("githyanki_jump_used", False)
                runtime.setdefault("githyanki_misty_step_used", False)
            if selected_subrace_key == "githzerai":
                runtime.setdefault("githzerai_shield_used", False)
                runtime.setdefault("githzerai_detect_thoughts_used", False)
            race_features["runtime"] = runtime
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
        if isinstance(race_features, dict) and race_choice_size:
            race_features["size"] = race_choice_size
            choices_dict["size"] = race_choice_size
        if isinstance(race_features, dict) and race_choice_asi:
            choices_dict["asi"] = list(race_choice_asi)
            race_key_norm = str(race_features.get("race_key") or "").strip().lower()
            if race_key_norm in {"simic_hybrid", "warforged"} and len(race_choice_asi) == 1:
                choices_dict["asi_plus1_stat"] = str((race_choice_asi[0] or {}).get("stat") or "").strip().lower()
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
        if isinstance(race_features, dict) and race_choice_tools:
            prof = race_features.get("proficiencies")
            prof_dict = prof if isinstance(prof, dict) else {}
            prof_tools = prof_dict.get("tools")
            prof_tools_list = prof_tools if isinstance(prof_tools, list) else []
            merged_tools: list[str] = []
            for item in [*prof_tools_list, *race_choice_tools]:
                tool = str(item or "").strip().lower()
                if tool and tool not in merged_tools:
                    merged_tools.append(tool)
            prof_dict["tools"] = merged_tools
            race_features["proficiencies"] = prof_dict
            choices_dict["tools"] = list(race_choice_tools)
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "warforged":
            features_raw = race_features.get("features")
            features_dict = dict(features_raw) if isinstance(features_raw, dict) else {}
            specialized_raw = features_dict.get("specialized_design")
            specialized = dict(specialized_raw) if isinstance(specialized_raw, dict) else {"type": "specialized_design"}
            if race_choice_skills:
                specialized["chosen_skill"] = race_choice_skills[0]
                choices_dict["specialized_design_skill"] = race_choice_skills[0]
            if race_choice_tools:
                specialized["chosen_tool"] = race_choice_tools[0]
                choices_dict["specialized_design_tool"] = race_choice_tools[0]
            features_dict["specialized_design"] = specialized
            extra_lang_raw = features_dict.get("extra_language_choice")
            extra_lang = dict(extra_lang_raw) if isinstance(extra_lang_raw, dict) else {"type": "language_choice"}
            if race_choice_languages:
                extra_lang["chosen"] = race_choice_languages[0]
                choices_dict["extra_language"] = race_choice_languages[0]
            features_dict["extra_language_choice"] = extra_lang
            race_features["features"] = features_dict
        if isinstance(race_features, dict) and race_choice_cantrips:
            choices_dict["cantrips"] = list(race_choice_cantrips)
            race_key_norm = str(race_features.get("race_key") or "").strip().lower()
            subrace_raw = race_features.get("subrace")
            subrace = subrace_raw if isinstance(subrace_raw, dict) else {}
            subrace_key = str(subrace.get("key") or "").strip().lower()
            if race_key_norm == "elf" and subrace_key == "high_elf":
                selected_cantrip = race_choice_cantrips[0]
                innate_raw = race_features.get("innate_spells")
                innate_spells = list(innate_raw) if isinstance(innate_raw, list) else []
                innate_spells = [
                    item
                    for item in innate_spells
                    if not (
                        isinstance(item, dict)
                        and str(item.get("source") or "").strip().lower() == "high_elf_cantrip"
                    )
                ]
                innate_spells.append(
                    {
                        "name": selected_cantrip,
                        "frequency": "at_will",
                        "min_level": 1,
                        "ability": "int",
                        "source": "high_elf_cantrip",
                    }
                )
                race_features["innate_spells"] = innate_spells

                features_raw = race_features.get("features")
                features_dict: dict[str, Any] = features_raw if isinstance(features_raw, dict) else {}
                high_elf_spell = {
                    "name": selected_cantrip,
                    "frequency": "at_will",
                    "min_level": 1,
                    "ability": "int",
                }
                features_dict["high_elf_cantrip"] = {
                    "type": "innate_spellcasting",
                    "ability": "int",
                    "spell": dict(high_elf_spell),
                }
                features_dict["innate_spellcasting"] = {
                    "type": "innate_spellcasting",
                    "ability": "int",
                    "spells": [dict(high_elf_spell)],
                }
                race_features["features"] = features_dict
        if isinstance(race_features, dict) and race_choice_martial_weapons:
            prof = race_features.get("proficiencies")
            prof_dict: dict[str, Any] = prof if isinstance(prof, dict) else {}
            current_weapons_raw = prof_dict.get("weapons")
            current_weapons = [
                str(item or "").strip().lower()
                for item in (current_weapons_raw if isinstance(current_weapons_raw, list) else [])
                if str(item or "").strip()
            ]
            merged_weapons: list[str] = []
            for item in [*current_weapons, *race_choice_martial_weapons]:
                weapon_key = str(item or "").strip().lower()
                if weapon_key and weapon_key not in merged_weapons:
                    merged_weapons.append(weapon_key)
            prof_dict["weapons"] = merged_weapons
            race_features["proficiencies"] = prof_dict
            choices_dict["martial_weapons"] = list(race_choice_martial_weapons)
        if isinstance(race_features, dict) and race_choice_flex_asi_variant and race_choice_flex_asi_stats:
            choices_dict["flex_asi"] = {
                "variant": race_choice_flex_asi_variant,
                "stats": list(race_choice_flex_asi_stats),
            }
        if isinstance(race_features, dict) and str(race_features.get("race_key") or "").strip().lower() == "simic_hybrid":
            simic_features = race_features.get("features")
            simic_features_dict: dict[str, Any] = simic_features if isinstance(simic_features, dict) else {}
            animal_cfg = simic_features_dict.get("animal_enhancement")
            animal_cfg_dict: dict[str, Any] = dict(animal_cfg) if isinstance(animal_cfg, dict) else {"pick_1_level": 1, "pick_2_level": 5}
            animal_cfg_dict["chosen_lvl1"] = race_choice_animal_enhancement_lvl1 or None
            animal_cfg_dict["chosen_lvl5"] = None
            simic_features_dict["animal_enhancement"] = animal_cfg_dict
            race_features["features"] = simic_features_dict
            if race_choice_languages:
                choices_dict["language"] = race_choice_languages[0]
            if race_choice_animal_enhancement_lvl1:
                choices_dict["animal_enhancement_lvl1"] = race_choice_animal_enhancement_lvl1
                _apply_simic_enhancement_to_race_features(race_features, race_choice_animal_enhancement_lvl1)
            runtime_raw = race_features.get("runtime")
            runtime = dict(runtime_raw) if isinstance(runtime_raw, dict) else {}
            runtime["simic_lvl1_enhancement"] = race_choice_animal_enhancement_lvl1 or ""
            runtime.setdefault("simic_lvl5_enhancement", "")
            runtime.setdefault("acid_spit_uses_used", 0)
            race_features["runtime"] = runtime
        if isinstance(race_features, dict) and race_choice_feats:
            choices_dict["feats"] = list(race_choice_feats)
        if isinstance(race_features, dict) and race_choice_variable_trait:
            choices_dict["variable_trait"] = race_choice_variable_trait
            if race_choice_variable_trait == "darkvision_60":
                senses = race_features.get("senses")
                senses_dict: dict[str, Any] = senses if isinstance(senses, dict) else {}
                senses_dict["darkvision_ft"] = 60
                race_features["senses"] = senses_dict
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
        if isinstance(race_features, dict) and race_choice_draconic_ancestry:
            ancestry = ancestry_by_key.get(race_choice_draconic_ancestry) or {}
            damage_type = str(ancestry.get("damage_type") or "").strip().lower()
            breath = ancestry.get("breath")
            breath_obj: dict[str, Any] = dict(breath) if isinstance(breath, dict) else {}

            choice_payload = {
                "key": race_choice_draconic_ancestry,
                "damage_type": damage_type,
                "breath": breath_obj,
            }
            choices_dict["draconic_ancestry"] = choice_payload

            resistances = race_features.get("resistances")
            resistances_list = resistances if isinstance(resistances, list) else []
            merged_resistances: list[str] = []
            for item in [*resistances_list, damage_type]:
                dt = str(item or "").strip().lower()
                if dt and dt not in merged_resistances:
                    merged_resistances.append(dt)
            race_features["resistances"] = merged_resistances

            area: dict[str, Any] = {}
            shape = str(breath_obj.get("shape") or "").strip().lower()
            if shape:
                area["shape"] = shape
            if breath_obj.get("cone_ft") is not None:
                area["cone_ft"] = max(0, as_int(breath_obj.get("cone_ft"), 0))
            if breath_obj.get("line_ft") is not None:
                area["line_ft"] = max(0, as_int(breath_obj.get("line_ft"), 0))
            if breath_obj.get("line_width_ft") is not None:
                area["line_width_ft"] = max(0, as_int(breath_obj.get("line_width_ft"), 0))

            breath_weapon = {
                "dc_formula": str(breath_weapon_mechanics.get("dc_formula") or "").strip(),
                "damage_progression": list(breath_weapon_mechanics.get("damage_progression") or []),
                "recharge": str(breath_weapon_mechanics.get("recharge") or "").strip().lower(),
                "damage_type": damage_type,
                "area": area,
                "save_ability": str(breath_obj.get("save") or "").strip().lower(),
            }
            features_raw = race_features.get("features")
            features_dict: dict[str, Any] = features_raw if isinstance(features_raw, dict) else {}
            features_dict["breath_weapon"] = breath_weapon
            race_features["features"] = features_dict
        if isinstance(race_features, dict) and race_choice_innate_ability:
            choices_dict["innate_spellcasting_ability"] = race_choice_innate_ability
            if str(race_features.get("race_key") or "").strip().lower() == "kender":
                choices_dict["taunt_ability"] = race_choice_innate_ability
                rf_features = race_features.get("features")
                features_dict: dict[str, Any] = rf_features if isinstance(rf_features, dict) else {}
                taunt_raw = features_dict.get("taunt")
                taunt_cfg = dict(taunt_raw) if isinstance(taunt_raw, dict) else {}
                if taunt_cfg:
                    taunt_cfg["chosen_ability"] = race_choice_innate_ability
                    features_dict["taunt"] = taunt_cfg
                    race_features["features"] = features_dict
            innate_raw = race_features.get("innate_spells")
            innate_spells = innate_raw if isinstance(innate_raw, list) else []
            for spell_item in innate_spells:
                if not isinstance(spell_item, dict):
                    continue
                ability_key = str(spell_item.get("ability") or "").strip().lower()
                if ability_key == "choose_int_wis_cha":
                    spell_item["ability"] = race_choice_innate_ability
            race_features["innate_spells"] = innate_spells
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
        if race_choice_flex_asi_variant and race_choice_flex_asi_stats:
            flex_asi_items: list[dict[str, Any]] = []
            if race_choice_flex_asi_variant == "2_1" and len(race_choice_flex_asi_stats) == 2:
                flex_asi_items = [
                    {"stat": race_choice_flex_asi_stats[0], "bonus": 2},
                    {"stat": race_choice_flex_asi_stats[1], "bonus": 1},
                ]
            elif race_choice_flex_asi_variant == "1_1_1" and len(race_choice_flex_asi_stats) == 3:
                flex_asi_items = [{"stat": stat_key, "bonus": 1} for stat_key in race_choice_flex_asi_stats]
            _apply_asi_bonuses(stats, flex_asi_items)

        hp_max = max(1, as_int((selected_preset or {}).get("hp_max"), 20))
        sta_max = max(1, as_int((selected_preset or {}).get("sta_max"), 10))
        if str((selected_subrace or {}).get("key") or "").strip().lower() == "hill_dwarf":
            hp_max += 1
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
