from datetime import datetime
from uuid import uuid4, UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import UUID as SaUUID, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import JSONB

from core.enums import ModeratorDeploymentState
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
    password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
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
    breach_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )


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
    messages: Mapped[list["MessagesEvaluations"]] = relationship(
        back_populates="moderator", cascade="all, delete-orphan"
    )
    deployments: Mapped[list["ModeratorDeployments"]] = relationship(
        back_populates="moderator", cascade="all, delete-orphan"
    )
    user: Mapped["Users"] = relationship(back_populates="moderators")


class ModeratorDeployments(Base):
    __tablename__ = "moderator_deployments"

    deployment_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, nullable=False, default=get_uuid
    )
    moderator_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), ForeignKey("moderators.moderator_id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(
        String, nullable=False, default=ModeratorDeploymentState.OFFLINE.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )

    # Relationships
    moderator: Mapped[list["Moderators"]] = relationship(back_populates="deployments")


class MessagesEvaluations(Base):
    __tablename__ = "messages"

    message_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    moderator_id: Mapped[UUID] = mapped_column(SaUUID(as_uuid=True), nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    breach_type: Mapped[str] = mapped_column(String, nullable=False)
    breach_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )

    # Relationships
