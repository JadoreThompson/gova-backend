from datetime import datetime
from uuid import uuid4, UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    UUID as SaUUID,
    Float,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import JSONB

from enums import ModeratorStatus, PricingTier
from utils import get_datetime


def get_uuid():
    return uuid4()


class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    jwt: Mapped[str] = mapped_column(String, nullable=True)
    discord_oauth: Mapped[str] = mapped_column(String, nullable=True)
    pricing_tier: Mapped[str] = mapped_column(
        Integer, nullable=False, default=PricingTier.FREE.value
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_datetime,
        onupdate=get_datetime,
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship
    moderators: Mapped[list["Moderators"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Guidelines(Base):
    __tablename__ = "guidelines"

    guideline_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, nullable=False, default=get_uuid
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[UUID] = mapped_column(SaUUID(as_uuid=True), nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    topics: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )

    # Relationships
    moderators: Mapped[list["Moderators"]] = relationship(back_populates="guideline")


class Moderators(Base):
    __tablename__ = "moderators"

    moderator_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    user_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    # Telegram group, Discord server
    platform_server_id: Mapped[str] = mapped_column(String, nullable=False)
    conf: Mapped[dict] = mapped_column(JSONB, nullable=False)
    guideline_id: Mapped[str] = mapped_column(
        SaUUID(as_uuid=True), ForeignKey("guidelines.guideline_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, default=ModeratorStatus.OFFLINE.value, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )

    # Relationships
    user: Mapped["Users"] = relationship(back_populates="moderators")
    event_logs: Mapped[list["ModeratorEventLogs"]] = relationship(
        back_populates="moderator", cascade="all, delete-orphan"
    )
    guideline: Mapped["Guidelines"] = relationship(back_populates="moderators")


class ModeratorEventLogs(Base):
    __tablename__ = "moderator_event_logs"

    log_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, nullable=False, default=get_uuid
    )
    moderator_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), ForeignKey("moderators.moderator_id"), nullable=False
    )
    # Event log
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String, nullable=False)

    # Event details
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Action tracking (for moderation actions)
    action_type: Mapped[str | None] = mapped_column(String, nullable=True)
    action_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    action_status: Mapped[str | None] = mapped_column(String, nullable=True)

    # Context and metadata
    context: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # Context object used at that time

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    # User/message references
    message_id: Mapped[UUID | None] = mapped_column(
        SaUUID(as_uuid=True), nullable=True
    )  # Link to Messages table

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime, index=True
    )

    # Relationships
    moderator: Mapped["Moderators"] = relationship(back_populates="event_logs")


class Messages(Base):
    __tablename__ = "messages"

    message_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    moderator_id: Mapped[UUID] = mapped_column(SaUUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    platform_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    platform_author_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )


class MessagesEvaluations(Base):
    __tablename__ = "message_evaluations"

    evaluation_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    moderator_id: Mapped[UUID] = mapped_column(SaUUID(as_uuid=True), nullable=False)
    message_id: Mapped[UUID] = mapped_column(SaUUID(as_uuid=True), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024))
    topic: Mapped[str] = mapped_column(String, nullable=False)
    topic_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )
