import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Session(Base):
    turn_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    title: Mapped[str] = mapped_column(String(120), default="Campaign")
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    world_seed: Mapped[int] = mapped_column(BigInteger)

    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Warsaw")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    turn_index: Mapped[int] = mapped_column(Integer, default=0)
    current_player_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    players = relationship("SessionPlayer", back_populates="session", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="session", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    web_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True, nullable=True)

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions = relationship("SessionPlayer", back_populates="player", cascade="all, delete-orphan")


class SessionPlayer(Base):
    __tablename__ = "session_players"
    __table_args__ = (
        UniqueConstraint("session_id", "player_id", name="uq_session_player"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"))

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    join_order: Mapped[int] = mapped_column(Integer, default=0)

    session = relationship("Session", back_populates="players")
    player = relationship("Player", back_populates="sessions")


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"))

    name: Mapped[str] = mapped_column(String(80))
    class_kit: Mapped[str] = mapped_column(String(40))      # механика: Fighter/Guardian/...
    class_skin: Mapped[str] = mapped_column(String(60))     # лор-название под сеттинг

    level: Mapped[int] = mapped_column(Integer, default=1)
    xp_total: Mapped[int] = mapped_column(Integer, default=0)

    hp_max: Mapped[int] = mapped_column(Integer, default=20)
    hp: Mapped[int] = mapped_column(Integer, default=20)

    sta_max: Mapped[int] = mapped_column(Integer, default=10)
    sta: Mapped[int] = mapped_column(Integer, default=10)

    luck_tokens: Mapped[int] = mapped_column(Integer, default=0)  # 0..50
    karma: Mapped[int] = mapped_column(Integer, default=0)        # -100..100

    stress: Mapped[int] = mapped_column(Integer, default=0)       # 0..10
    fear: Mapped[int] = mapped_column(Integer, default=0)         # 0..10

    # Статы 0..100
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)

    is_alive: Mapped[bool] = mapped_column(Boolean, default=True)


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("character_id", "skill_key", name="uq_character_skill"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"))
    skill_key: Mapped[str] = mapped_column(String(40))  # "stealth", "persuasion" etc.

    rank: Mapped[int] = mapped_column(Integer, default=0)     # 0..10
    xp: Mapped[int] = mapped_column(Integer, default=0)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"))

    turn_index: Mapped[int] = mapped_column(Integer)
    actor_player_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_character_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    message_text: Mapped[str] = mapped_column(Text)
    parsed_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="events")
