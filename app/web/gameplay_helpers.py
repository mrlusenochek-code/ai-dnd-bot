import logging
import os
import re
import uuid

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Character, Event, Player, Session, SessionPlayer, Skill
from app.web.session_state import settings_get
from app.web.utils import _clamp, as_int


logger = logging.getLogger("app.web.server")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Warsaw")
GM_OLLAMA_TIMEOUT_SECONDS = max(1.0, float(os.getenv("GM_OLLAMA_TIMEOUT_SECONDS", "30")))
CHAR_STAT_KEYS = ("str", "dex", "con", "int", "wis", "cha")
CHAR_DEFAULT_STATS = {k: 50 for k in CHAR_STAT_KEYS}
CLASS_PRESETS: dict[str, dict[str, Any]] = {
    "fighter": {
        "display_name": "Fighter",
        "hp_max": 24,
        "sta_max": 12,
        "stats_shift": {"str": 15, "con": 10, "dex": 5, "int": -5, "wis": -5, "cha": 0},
        "starter_skills": {"athletics": 2, "endurance": 1},
    },
    "rogue": {
        "display_name": "Rogue",
        "hp_max": 18,
        "sta_max": 14,
        "stats_shift": {"str": 0, "con": 0, "dex": 15, "int": 5, "wis": 0, "cha": 5},
        "starter_skills": {"stealth": 2, "trickery": 1},
    },
    "ranger": {
        "display_name": "Ranger",
        "hp_max": 20,
        "sta_max": 13,
        "stats_shift": {"str": 5, "con": 5, "dex": 10, "int": 0, "wis": 10, "cha": -5},
        "starter_skills": {"survival": 2, "tracking": 1},
    },
    "mage": {
        "display_name": "Mage",
        "hp_max": 16,
        "sta_max": 12,
        "stats_shift": {"str": -10, "con": -5, "dex": 0, "int": 20, "wis": 10, "cha": 0},
        "starter_skills": {"arcana": 2, "focus": 1},
    },
    "cleric": {
        "display_name": "Cleric",
        "hp_max": 20,
        "sta_max": 11,
        "stats_shift": {"str": 0, "con": 5, "dex": 0, "int": 5, "wis": 15, "cha": 5},
        "starter_skills": {"faith": 2, "medicine": 1},
    },
    "bard": {
        "display_name": "Bard",
        "hp_max": 18,
        "sta_max": 13,
        "stats_shift": {"str": -5, "con": 0, "dex": 5, "int": 5, "wis": 0, "cha": 20},
        "starter_skills": {"performance": 2, "persuasion": 1},
    },
}

STORY_DIFFICULTY_VALUES = {"easy", "medium", "hard"}
STORY_HEALTH_SYSTEM_VALUES = {"none", "normal"}
STORY_DMG_SCALE_VALUES = {"reduced", "standard", "increased"}
STORY_AI_VERBOSITY_VALUES = {"auto", "restrained", "very_restrained"}


def _looks_like_refusal(text: str) -> bool:
    t = str(text or "").strip().lower()
    if not t:
        return False

    # базовые маркеры "не могу"
    cannot = ("не могу" in t) or ("can't" in t) or ("cannot" in t) or ("can’t" in t)
    if not cannot:
        return False

    # жёсткие шаблоны отказов (почти всегда это именно отказ ассистента)
    hard = [
        "я не могу продолжить эту тему",
        "я не могу продолжать эту тему",
        "я не могу помочь с этим",
        "не могу помочь с этим",
        "я не могу предоставить",
        "не могу предоставить",
        "i can't help",
        "i cannot help",
        "i can't continue",
        "i cannot continue",
        "i can't comply",
        "i cannot comply",
    ]
    if any(x in t for x in hard):
        return True

    # мягкие маркеры отказа: извинения / предложение помочь "с другим" / ссылки на правила
    starts_apology = t.startswith(("извини", "простите", "прошу прощения", "sorry", "i'm sorry", "i am sorry"))
    offers_other = any(
        x in t
        for x in (
            "я могу помочь с другим",
            "могу помочь с другим",
            "могу помочь с чем-то другим",
            "i can help with something else",
            "something else",
        )
    )
    mentions_policy = any(
        x in t
        for x in (
            "политик",
            "правил",
            "policy",
            "guideline",
            "как модель",
            "как ии",
            "as an ai",
        )
    )

    if starts_apology or offers_other or mentions_policy:
        return True

    return False
    t = str(text or "").lower()
    if "я не могу" not in t and "i can't" not in t:
        return False
    return any(k in t for k in ["сексу", "насил", "эксплуатац", "sexual", "violence"])


def _story_is_configured(sess: Session) -> bool:
    raw = settings_get(sess, "story", {}) or {}
    return bool(isinstance(raw, dict) and raw.get("story_configured"))


def _split_red_flags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        parts = [str(x).strip() for x in raw]
    else:
        txt = str(raw or "")
        parts = [x.strip() for x in re.split(r"[\n,]+", txt)]
    out: list[str] = []
    for item in parts:
        if item:
            out.append(item[:200])
    return out


def _normalize_story_config(sess: Session, raw: Any) -> dict[str, Any]:
    cfg = raw if isinstance(raw, dict) else {}
    difficulty = str(cfg.get("difficulty") or "medium").strip().lower()
    if difficulty not in STORY_DIFFICULTY_VALUES:
        difficulty = "medium"
    health_system = str(cfg.get("health_system") or "normal").strip().lower()
    if health_system not in STORY_HEALTH_SYSTEM_VALUES:
        health_system = "normal"
    dmg_scale = str(cfg.get("dmg_scale") or "standard").strip().lower()
    if dmg_scale not in STORY_DMG_SCALE_VALUES:
        dmg_scale = "standard"
    ai_verbosity = str(cfg.get("ai_verbosity") or "auto").strip().lower()
    if ai_verbosity not in STORY_AI_VERBOSITY_VALUES:
        ai_verbosity = "auto"

    story_title = str(cfg.get("story_title") or "").strip()
    if not story_title:
        story_title = str(sess.title or "Campaign").strip() or "Campaign"

    return {
        "story_title": story_title[:200],
        "story_setting": str(cfg.get("story_setting") or "").strip()[:2000],
        "free_turns": bool(cfg.get("free_turns")),
        "difficulty": difficulty,
        "health_system": health_system,
        "dmg_scale": dmg_scale,
        "journal_hint": str(cfg.get("journal_hint") or "").strip()[:1000],
        "red_flags": _split_red_flags(cfg.get("red_flags")),
        "ai_verbosity": ai_verbosity,
        "gm_notes": str(cfg.get("gm_notes") or "").strip()[:1000],
    }


def _normalized_stats(stats_raw: Any) -> dict[str, int]:
    out = dict(CHAR_DEFAULT_STATS)
    if isinstance(stats_raw, dict):
        for key in CHAR_STAT_KEYS:
            if key in stats_raw:
                out[key] = _clamp(as_int(stats_raw.get(key), 50), 0, 100)
    return out


def _character_meta_from_stats(stats_raw: Any) -> dict[str, str]:
    if not isinstance(stats_raw, dict):
        return {"gender": "", "race": "", "description": ""}
    raw_meta = stats_raw.get("_meta")
    if not isinstance(raw_meta, dict):
        return {"gender": "", "race": "", "description": ""}
    return {
        "gender": str(raw_meta.get("gender") or "").strip()[:40],
        "race": str(raw_meta.get("race") or "").strip()[:60],
        "description": str(raw_meta.get("description") or "").strip()[:1000],
    }


def _put_character_meta_into_stats(stats_raw: Any, *, gender: str, race: str, description: str) -> dict[str, Any]:
    stats = dict(stats_raw) if isinstance(stats_raw, dict) else {}
    stats["_meta"] = {
        "gender": str(gender or "").strip()[:40],
        "race": str(race or "").strip()[:60],
        "description": str(description or "").strip()[:1000],
    }
    return stats


def _stats_points_used(stats: dict[str, int]) -> int:
    points = 0
    for key in CHAR_STAT_KEYS:
        v = _clamp(as_int(stats.get(key), 50), 0, 100)
        points += int((v - 50) / 5)
    return points


def _resolve_character_stats(class_id: Optional[str], incoming_stats: Any) -> dict[str, int]:
    stats = dict(CHAR_DEFAULT_STATS)
    preset = CLASS_PRESETS.get((class_id or "").lower())
    if preset:
        shifts = preset.get("stats_shift") or {}
        for key in CHAR_STAT_KEYS:
            stats[key] = _clamp(50 + as_int(shifts.get(key), 0), 0, 100)
    if isinstance(incoming_stats, dict):
        for key in CHAR_STAT_KEYS:
            if key in incoming_stats:
                stats[key] = _clamp(as_int(incoming_stats.get(key), 50), 0, 100)
    return stats


def _char_to_payload(ch: Optional[Character]) -> Optional[dict]:
    if not ch:
        return None
    meta = _character_meta_from_stats(ch.stats)
    return {
        "name": ch.name,
        "class_kit": ch.class_kit,
        "class_skin": ch.class_skin,
        "level": int(ch.level or 1),
        "xp_total": int(ch.xp_total or 0),
        "hp": int(ch.hp or 0),
        "hp_max": int(ch.hp_max or 0),
        "sta": int(ch.sta or 0),
        "sta_max": int(ch.sta_max or 0),
        "stats": _normalized_stats(ch.stats),
        "gender": meta["gender"],
        "race": meta["race"],
        "description": meta["description"],
    }


async def get_character(db: AsyncSession, session_id: uuid.UUID, player_id: uuid.UUID) -> Optional[Character]:
    q = await db.execute(
        select(Character)
        .where(
            Character.session_id == session_id,
            Character.player_id == player_id,
        )
        .limit(1)
    )
    return q.scalars().first()


async def create_character(
    db: AsyncSession,
    session_id: uuid.UUID,
    player_id: uuid.UUID,
    name: str,
    class_kit: str = "Adventurer",
    class_skin: str = "Adventurer",
    hp_max: int = 20,
    sta_max: int = 10,
    stats: Optional[dict[str, int]] = None,
) -> Character:
    hp_max = max(1, hp_max)
    sta_max = max(1, sta_max)
    ch = Character(
        session_id=session_id,
        player_id=player_id,
        name=name,
        class_kit=class_kit,
        class_skin=class_skin,
        level=1,
        hp_max=hp_max,
        hp=hp_max,
        sta_max=sta_max,
        sta=sta_max,
        stats=(dict(stats) if isinstance(stats, dict) else dict(CHAR_DEFAULT_STATS)),
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    return ch


async def _upsert_starter_skills(db: AsyncSession, ch: Character, starter: dict[str, Any]) -> None:
    changed = False
    for raw_key, raw_rank in (starter or {}).items():
        key = (str(raw_key or "").strip().lower())[:40]
        if not key:
            continue
        rank = _clamp(as_int(raw_rank, 0), 0, 10)
        q = await db.execute(
            select(Skill).where(
                Skill.character_id == ch.id,
                Skill.skill_key == key,
            )
        )
        sk = q.scalar_one_or_none()
        if sk:
            if int(sk.rank or 0) != rank:
                sk.rank = rank
                changed = True
            continue
        db.add(Skill(character_id=ch.id, skill_key=key, rank=rank, xp=0))
        changed = True
    if changed:
        await db.commit()


async def is_admin(db: AsyncSession, sess: Session, player: Player) -> bool:
    q = await db.execute(
        select(SessionPlayer).where(
            SessionPlayer.session_id == sess.id,
            SessionPlayer.player_id == player.id,
        )
    )
    sp = q.scalar_one_or_none()
    return bool(sp and sp.is_admin)


def _safe_event_text(text: Any) -> str:
    s = str(text or "")
    s = s.replace("\x00", "")
    s = s.encode("utf-8", "replace").decode("utf-8")
    return s[:8000]


async def add_event(
    db: AsyncSession,
    sess: Session,
    text: Any,
    actor_player_id: Optional[uuid.UUID] = None,
    actor_character_id: Optional[uuid.UUID] = None,
    parsed_json: Optional[dict] = None,
    result_json: Optional[dict] = None,
) -> None:
    text = _safe_event_text(text)
    ev = Event(
        session_id=sess.id,
        turn_index=sess.turn_index or 0,
        actor_player_id=actor_player_id,
        actor_character_id=actor_character_id,
        message_text=text,
        parsed_json=parsed_json,
        result_json=result_json,
    )
    db.add(ev)
    await db.commit()


async def add_system_event(
    db: AsyncSession,
    sess: Session,
    text: str,
    *,
    result_json: Optional[dict] = None,
    parsed_json: Optional[dict] = None,
) -> None:
    await add_event(db, sess, f"[SYSTEM] {text}", actor_player_id=None, parsed_json=parsed_json, result_json=result_json)


def _get_kicked(sess: Session) -> set[str]:
    raw = settings_get(sess, "kicked", []) or []
    out: set[str] = set()
    for x in raw:
        if x is None:
            continue
        out.add(str(x))
    return out
