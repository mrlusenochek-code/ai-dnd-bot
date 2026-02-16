import os
import asyncio
import random
from datetime import datetime, timedelta
from aiogram.client.session.aiohttp import AiohttpSession

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import Command

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import AsyncSessionLocal
from app.db.models import Session, Player, SessionPlayer, Event

load_dotenv()
BOT_TOKEN = os.environ["BOT_TOKEN"]
TURN_TIMEOUT_SECONDS = int(os.getenv("TURN_TIMEOUT_SECONDS", "300"))
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Warsaw")

router = Router()


async def ensure_player(db: AsyncSession, tg_user) -> Player:
    q = await db.execute(select(Player).where(Player.telegram_user_id == tg_user.id))
    player = q.scalar_one_or_none()
    if player:
        return player

    player = Player(
        telegram_user_id=tg_user.id,
        username=tg_user.username,
        display_name=(tg_user.full_name or tg_user.username or str(tg_user.id)),
    )
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return player


async def get_session_by_chat(db: AsyncSession, chat_id: int) -> Session | None:
    q = await db.execute(select(Session).where(Session.telegram_chat_id == chat_id))
    return q.scalar_one_or_none()


@router.message(Command("newgame"))
async def newgame(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Создавай игру в групповом чате.")
        return

    async with AsyncSessionLocal() as db:
        existing = await get_session_by_chat(db, message.chat.id)
        if existing:
            await message.answer("Игра в этом чате уже создана. Используй /join и /begin.")
            return

        player = await ensure_player(db, message.from_user)

        title = message.text.replace("/newgame", "").strip() or "Campaign"
        seed = random.randint(1, 2_000_000_000)

        sess = Session(
            telegram_chat_id=message.chat.id,
            title=title,
            settings={},
            world_seed=seed,
            timezone=DEFAULT_TIMEZONE,
            is_active=True,
            turn_index=0,
            current_player_id=None,
        )
        db.add(sess)
        await db.commit()
        await db.refresh(sess)

        sp = SessionPlayer(session_id=sess.id, player_id=player.id, is_admin=True, join_order=1)
        db.add(sp)
        await db.commit()

        await message.answer(
            f"✅ Игра создана: {title}\n"
            f"Seed: {seed}\n\n"
            f"Теперь игроки пишут /join\n"
            f"Админ запускает очередь: /begin"
        )


@router.message(Command("join"))
async def join_game(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Вступать нужно в групповом чате игры.")
        return

    async with AsyncSessionLocal() as db:
        sess = await get_session_by_chat(db, message.chat.id)
        if not sess:
            await message.answer("Сначала создай игру: /newgame")
            return

        player = await ensure_player(db, message.from_user)

        q = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q.scalar_one_or_none()
        if sp:
            await message.answer("Ты уже в игре.")
            return

        # join_order = max + 1
        q2 = await db.execute(select(SessionPlayer.join_order).where(SessionPlayer.session_id == sess.id))
        orders = [r[0] for r in q2.all()] or [0]
        join_order = max(orders) + 1

        sp = SessionPlayer(session_id=sess.id, player_id=player.id, is_admin=False, join_order=join_order)
        db.add(sp)
        await db.commit()

        await message.answer(f"✅ {message.from_user.full_name} вступил(а) в игру. Порядок: {join_order}")


@router.message(Command("begin"))
async def begin_turns(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return

    async with AsyncSessionLocal() as db:
        sess = await get_session_by_chat(db, message.chat.id)
        if not sess:
            await message.answer("Нет игры. Создай: /newgame")
            return

        # проверим админа
        player = await ensure_player(db, message.from_user)
        q = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == sess.id,
                SessionPlayer.player_id == player.id,
            )
        )
        sp = q.scalar_one_or_none()
        if not sp or not sp.is_admin:
            await message.answer("Запустить очередь может только создатель/админ.")
            return

        # выберем первого игрока по join_order
        q2 = await db.execute(
            select(SessionPlayer).where(SessionPlayer.session_id == sess.id, SessionPlayer.is_active == True)
            .order_by(SessionPlayer.join_order.asc())
        )
        players = q2.scalars().all()
        if len(players) < 1:
            await message.answer("Нет игроков. Пусть напишут /join")
            return

        sess.current_player_id = players[0].player_id
        sess.turn_index = 1
        await db.commit()

        await message.answer(
            f"🎲 Очередь началась.\n"
            f"Ход игрока #{players[0].join_order}. Пиши любое действие обычным текстом."
        )


async def next_player(db: AsyncSession, sess: Session) -> SessionPlayer | None:
    q = await db.execute(
        select(SessionPlayer).where(SessionPlayer.session_id == sess.id, SessionPlayer.is_active == True)
        .order_by(SessionPlayer.join_order.asc())
    )
    sps = q.scalars().all()
    if not sps:
        return None

    # найти текущего
    idx = 0
    for i, sp in enumerate(sps):
        if sp.player_id == sess.current_player_id:
            idx = i
            break
    nxt = sps[(idx + 1) % len(sps)]
    sess.current_player_id = nxt.player_id
    sess.turn_index += 1
    await db.commit()
    return nxt


@router.message(F.text)
async def handle_free_text(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return

    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return

    async with AsyncSessionLocal() as db:
        sess = await get_session_by_chat(db, message.chat.id)

        # ✅ вместо молчания — всегда объясняем, что не так
        if not sess:
            await message.answer("В этом чате нет игры. Создай: /newgame")
            return

        if not sess.is_active:
            await message.answer("Игра не активна.")
            return

        if sess.is_paused:
            await message.answer("⏸ Игра на паузе. /resume")
            return

        if not sess.current_player_id:
            await message.answer("Очередь не запущена. Админ: /begin")
            return

        player = await ensure_player(db, message.from_user)

        if player.id != sess.current_player_id:
            await message.answer("⏳ Сейчас ход другого игрока.")
            return

        ev = Event(
            session_id=sess.id,
            turn_index=sess.turn_index,
            actor_player_id=player.id,
            actor_character_id=None,
            message_text=text,
            parsed_json=None,
            result_json=None,
        )
        db.add(ev)
        await db.commit()

        nxt = await next_player(db, sess)
        if not nxt:
            await message.answer("Нет активных игроков.")
            return

        await message.answer(
            f"✅ Ход принят: «{text}»\n"
            f"➡️ Следующий игрок (порядок #{nxt.join_order}) ходит."
        )


async def main():
    session = AiohttpSession(timeout=90)  # timeout в секундах (int)
    bot = Bot(token=BOT_TOKEN, session=session)

    dp = Dispatcher()
    dp.include_router(router)

    me = await bot.get_me()
    print(f"[OK] Bot started: @{me.username} (id={me.id})")

    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())
