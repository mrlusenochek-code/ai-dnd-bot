import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Character, Event, Player, Session, SessionPlayer, Skill
from app.web.db_helpers import list_session_players
from app.web.gameplay_helpers import get_character
from app.web.ws_checks import _skill_bonus_from_rank_and_level


COMBAT_CLARIFY_TEXT = "🧙 GM: Сейчас бой. Уточни: атака/уклон/помощь/рывок/отход/побег/предмет/конец хода.\nЧто делаете дальше?"


def _player_uid(player: Optional[Player]) -> Optional[int]:
    if not player:
        return None
    raw = player.web_user_id if player.web_user_id is not None else player.telegram_user_id
    return int(raw) if raw is not None else None


async def _event_actor_label(db: AsyncSession, sess: Session, player: Player) -> str:
    ch = await get_character(db, sess.id, player.id)
    if ch and str(ch.name or "").strip():
        return str(ch.name).strip()
    return str(player.display_name or "").strip() or "Персонаж"


async def _combat_clarify_already_sent(
    db: AsyncSession,
    sess: Session,
    request_id: Optional[str],
) -> bool:
    rid = str(request_id or "").strip()
    if not rid:
        return False
    q_events = await db.execute(
        select(Event)
        .where(Event.session_id == sess.id)
        .order_by(Event.created_at.desc())
        .limit(25)
    )
    for ev in q_events.scalars().all():
        payload = ev.result_json if isinstance(ev.result_json, dict) else {}
        if str(payload.get("type") or "") != "combat_chat_gm_reply":
            continue
        if payload.get("combat_action") is not None:
            continue
        if str(payload.get("request_id") or "").strip() != rid:
            continue
        if COMBAT_CLARIFY_TEXT in str(ev.message_text or ""):
            return True
    return False


async def _load_actor_context(
    db: AsyncSession,
    sess: Session,
) -> tuple[dict[int, tuple[SessionPlayer, Player]], dict[int, Character], dict[uuid.UUID, dict[str, int]]]:
    sps = await list_session_players(db, sess, active_only=True)
    if not sps:
        return {}, {}, {}
    player_ids = [sp.player_id for sp in sps]
    q_players = await db.execute(select(Player).where(Player.id.in_(player_ids)))
    players = q_players.scalars().all()
    players_by_id = {p.id: p for p in players}
    uid_map: dict[int, tuple[SessionPlayer, Player]] = {}
    for sp in sps:
        pl = players_by_id.get(sp.player_id)
        uid = _player_uid(pl)
        if pl and uid is not None and uid > 0:
            uid_map[uid] = (sp, pl)

    q_chars = await db.execute(
        select(Character).where(
            Character.session_id == sess.id,
            Character.player_id.in_(player_ids),
        )
    )
    chars = q_chars.scalars().all()
    chars_by_player = {ch.player_id: ch for ch in chars}
    chars_by_uid: dict[int, Character] = {}
    for uid, (sp, _pl) in uid_map.items():
        ch = chars_by_player.get(sp.player_id)
        if ch:
            chars_by_uid[uid] = ch

    skill_mods_by_char: dict[uuid.UUID, dict[str, int]] = {}
    levels_by_char_id = {ch.id: ch.level for ch in chars}
    char_ids = [ch.id for ch in chars]
    if char_ids:
        q_skills = await db.execute(select(Skill).where(Skill.character_id.in_(char_ids)))
        for sk in q_skills.scalars().all():
            skill_mods_by_char.setdefault(sk.character_id, {})[str(sk.skill_key or "").strip().lower()] = _skill_bonus_from_rank_and_level(
                sk.rank,
                levels_by_char_id.get(sk.character_id),
            )
    return uid_map, chars_by_uid, skill_mods_by_char
