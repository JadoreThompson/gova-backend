import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from enums import MessagePlatform, ModeratorStatus
from .base import Base
from .utils import get_uuid, datetime_tz

if TYPE_CHECKING:
    from .users import Users
    from .evaluation_events import EvaluationEvents
    from .action_events import ActionEvents


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
    description: Mapped[str] = mapped_column(String(200), nullable=True)
    platform: Mapped[MessagePlatform] = mapped_column(String, nullable=False)
    platform_server_id: Mapped[str] = mapped_column(String, nullable=False)
    conf: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String, default=ModeratorStatus.OFFLINE.value, nullable=False
    )
    created_at: Mapped[datetime] = datetime_tz()

    user: Mapped["Users"] = relationship(
        back_populates="moderators", passive_deletes=True
    )
    evaluations: Mapped[list["EvaluationEvents"]] = relationship(
        back_populates="moderator", cascade="all, delete-orphan"
    )
    actions: Mapped[list["ActionEvents"]] = relationship(
        back_populates="moderator", cascade="all, delete-orphan"
    )