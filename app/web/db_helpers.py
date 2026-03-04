import uuid

from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session, Player, SessionPlayer


async def get_or_create_player_web(db: AsyncSession, uid: int, display_name: str) -> Player:
    """
    uid — это наш "web user id". Храним в Player.web_user_id.
    """
    q = await db.execute(select(Player).where(Player.web_user_id == uid))
    player = q.scalar_one_or_none()
    if player:
        if display_name and display_name.strip() and player.display_name != display_name.strip():
            player.display_name = display_name.strip()
            await db.commit()
        return player

    name = (display_name or "").strip() or f"Player {uid}"
    player = Player(
        web_user_id=uid,
        username=None,
        display_name=name,
    )
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return player


async def get_player_by_uid(db: AsyncSession, uid: int) -> Optional[Player]:
    q = await db.execute(select(Player).where(Player.web_user_id == uid))
    return q.scalar_one_or_none()


async def get_session(db: AsyncSession, session_id: str) -> Optional[Session]:
    try:
        sid = uuid.UUID(session_id)
    except Exception:
        return None
    q = await db.execute(select(Session).where(Session.id == sid))
    return q.scalar_one_or_none()


async def list_session_players(db: AsyncSession, sess: Session, active_only: bool = True) -> list[SessionPlayer]:
    conds = [SessionPlayer.session_id == sess.id]
    if active_only:
        # is_active could be NULL for legacy records -> treat as active
        conds.append(or_(SessionPlayer.is_active == True, SessionPlayer.is_active.is_(None)))
    q = await db.execute(
        select(SessionPlayer)
        .where(*conds)
        .order_by(SessionPlayer.join_order.asc())
    )
    return q.scalars().all()
