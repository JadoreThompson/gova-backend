from datetime import datetime
from uuid import uuid4, UUID

from sqlalchemy import UUID as SaUUID, String, DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from core.enums import ModeratorState
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


class Projects(Base):
    __tablename__ = "projects"

    project_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    guidelines: Mapped[str] = mapped_column(String, nullable=True)
    topics: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )


class Moderators(Base):
    __tablename__ = "moderators"

    moderator_id: Mapped[UUID] = mapped_column(
        SaUUID(as_uuid=True), primary_key=True, default=get_uuid
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(
        String, nullable=False, default=ModeratorState.OFFLINE.value
    )
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_datetime
    )
