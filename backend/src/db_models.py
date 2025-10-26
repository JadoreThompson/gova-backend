from datetime import datetime
from uuid import uuid4, UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import UUID as SaUUID, Float, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import JSONB

from core.enums import ModeratorDeploymentStatus, PricingTierType
from utils.db import get_datetime


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
    connections: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_datetime,
        onupdate=get_datetime,
    )
    pricing_tier: Mapped[str] = mapped_column(
        Integer, nullable=False, default=PricingTierType.FREE.value
    )
    payment_info: Mapped[dict] = mapped_column(JSONB, nullable=True)
    payment_link: Mapped[str] = mapped_column(String, nullable=True)
    authenticated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True
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
    guideline_id: Mapped[str] = mapped_column(
        SaUUID(as_uuid=True), ForeignKey("guidelines.guideline_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )

    # Relationships
    user: Mapped["Users"] = relationship(back_populates="moderators")
    deployments: Mapped[list["ModeratorDeployments"]] = relationship(
        back_populates="moderator", cascade="all, delete-orphan"
    )
    logs: Mapped[list["ModeratorDeploymentLogs"]] = relationship(
        back_populates="moderator", cascade="all, delete-orphan"
    )
    guideline: Mapped["Guidelines"] = relationship(back_populates="moderators")


class ModeratorDeployments(Base):
    __tablename__ = "moderator_deployments"

    deployment_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, nullable=False, default=get_uuid
    )
    moderator_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), ForeignKey("moderators.moderator_id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    conf: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=ModeratorDeploymentStatus.OFFLINE.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )

    # Relationships
    moderator: Mapped["Moderators"] = relationship(back_populates="deployments")
    logs: Mapped[list["ModeratorDeploymentLogs"]] = relationship(
        back_populates="deployment", cascade="all, delete-orphan"
    )


class ModeratorDeploymentLogs(Base):
    __tablename__ = "moderator_logs"

    log_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, nullable=False, default=get_uuid
    )
    moderator_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), ForeignKey("moderators.moderator_id"), nullable=False
    )
    deployment_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True),
        ForeignKey("moderator_deployments.deployment_id"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    action_params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )

    # Relationships
    moderator: Mapped["Moderators"] = relationship(back_populates="logs")
    deployment: Mapped["ModeratorDeployments"] = relationship(back_populates="logs")


class Messages(Base):
    __tablename__ = "messages"

    message_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    moderator_id: Mapped[UUID] = mapped_column(SaUUID(as_uuid=True), nullable=False)
    deployment_id: Mapped[UUID] = mapped_column(SaUUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )


class MessagesEvaluations(Base):
    __tablename__ = "message_evaluations"
    # NOTE: No foreign keys in this table as we want to retain all data
    # regardless is a parent is deleted.

    evaluation_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    message_id: Mapped[UUID] = mapped_column(SaUUID(as_uuid=True), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024))
    topic: Mapped[str] = mapped_column(String, nullable=False)
    topic_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )

    # Relationships
