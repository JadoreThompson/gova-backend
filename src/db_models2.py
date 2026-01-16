import uuid
from datetime import datetime

from sqlalchemy import UUID, Float, Integer, String, DateTime, ForeignKey, text
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import JSONB

from enums import ActionStatus, MessagePlatform, ModeratorStatus, PricingTierType
from utils import get_datetime


def get_uuid():
    return uuid.uuid4()


def uuid_pk(**kw):
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )


def datetime_tz():
    return mapped_column(DateTime(timezone=True), nullable=False, default=get_datetime)


class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    jwt: Mapped[str] = mapped_column(String, nullable=True)
    discord_oauth_payload: Mapped[str] = mapped_column(String, nullable=True)
    pricing_tier: Mapped[str] = mapped_column(
        Integer, nullable=False, default=PricingTierType.FREE.value
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True
    )
    created_at: Mapped[datetime] = datetime_tz()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_datetime,
        onupdate=get_datetime,
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    moderators: list["Moderators"] = relationship(
        "Moderators", cascade="all, delete-orphan"
    )


class Moderators(Base):
    __tablename__ = "moderators"

    moderator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[MessagePlatform] = mapped_column(String, nullable=False)
    platform_server_id: Mapped[str] = mapped_column(String, nullable=False)
    conf: Mapped[dict] = mapped_column(JSONB, nullable=False)
    guideline_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guidelines.guideline_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, default=ModeratorStatus.OFFLINE.value, nullable=False
    )
    created_at: Mapped[datetime] = datetime_tz()

    # Relationships
    user: Mapped["Users"] = relationship(
        back_populates="moderators", passive_deletes=True
    )
    evaluations: Mapped[list["EvaluationEvents"]] = relationship(
        back_populates="moderator", cascade="all, delete-orphan"
    )
    # event_logs: Mapped[list["ModeratorEventLogs"]] = relationship(
    #     back_populates="moderator", cascade="all, delete-orphan"
    # )


# class ModeratorEventLogs(Base):
#     __tablename__ = "moderator_event_logs"

#     log_id: Mapped[uuid.UUID] = mapped_column(
#         UUID(as_uuid=True), primary_key=True, nullable=False, default=get_uuid
#     )
#     moderator_id: Mapped[uuid.UUID] = mapped_column(
#         UUID(as_uuid=True), ForeignKey("moderators.moderator_id"), nullable=False
#     )
#     # Event log
#     event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
#     severity: Mapped[str] = mapped_column(String, nullable=False)

#     # Event details
#     message: Mapped[str] = mapped_column(Text, nullable=False)
#     details: Mapped[dict] = mapped_column(JSONB, nullable=True)

#     # Action tracking (for moderation actions)
#     action_type: Mapped[str | None] = mapped_column(String, nullable=True)
#     action_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
#     action_status: Mapped[str | None] = mapped_column(String, nullable=True)

#     # Context and metadata
#     context: Mapped[dict | None] = mapped_column(
#         JSONB, nullable=True
#     )  # Context object used at that time

#     # Error tracking
#     error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
#     stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

#     # User/message references
#     message_id: Mapped[UUID | None] = mapped_column(
#         UUID(as_uuid=True), nullable=True
#     )  # Link to Messages table

#     created_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True), nullable=False, default=get_datetime, index=True
#     )

#     # Relationships
#     moderator: Mapped["Moderators"] = relationship(back_populates="event_logs")


# class Messages(Base):
#     __tablename__ = "messages"

#     message_id: Mapped[uuid.UUID] = mapped_column(
#         UUID(as_uuid=True), primary_key=True, default=get_uuid
#     )
#     moderator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
#     content: Mapped[str] = mapped_column(String, nullable=False)
#     platform: Mapped[str] = mapped_column(String, nullable=False)
#     platform_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
#     platform_author_id: Mapped[str | None] = mapped_column(String, nullable=True)
#     created_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True), nullable=False, default=get_datetime
#     )


# class MessagesEvaluations(Base):
#     __tablename__ = "message_evaluations"

#     evaluation_id: Mapped[uuid.UUID] = mapped_column(
#         UUID(as_uuid=True), primary_key=True, default=get_uuid
#     )
#     moderator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
#     message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
#     embedding: Mapped[list[float]] = mapped_column(Vector(1024))
#     topic: Mapped[str] = mapped_column(String, nullable=False)
#     topic_score: Mapped[float] = mapped_column(Float, nullable=False)
#     created_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True), nullable=False, default=get_datetime
#     )


class EvaluationEvents(Base):
    __tablename__ = "evaluation_events"

    event_id: Mapped[uuid.UUID] = uuid_pk()
    moderator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("moderators.moderator_id", ondelete="CASCADE"),
        nullable=False,
    )
    platform_user_id: Mapped[str] = mapped_column(String, nullable=False)
    severity_score: Mapped[float] = mapped_column(
        Float(precision=1, scale=2), nullable=False
    )
    behaviour_score: Mapped[float] = mapped_column(
        Float(precision=1, scale=2), nullable=False, server_default=text("0.00")
    )
    context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = datetime_tz()

    # Relationships
    moderator = relationship(
        "Moderators", back_populates="evaluations", passive_deletes=True
    )


class ActionEvents(Base):
    __tablename__ = "action_events"

    action_id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    moderator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("moderators.moderator_id", ondelete="CASCADE"),
        nullable=False,
    )
    platform_user_id: Mapped[str] = mapped_column(String, nullable=True)
    action_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action_params: Mapped[dict] = mapped_column(JSONB, nullable=True)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[ActionStatus] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = datetime_tz()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_datetime,
        onupdate=get_datetime,
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    moderator: Mapped["Moderators"] = relationship("Moderators", passive_deletes=True)
