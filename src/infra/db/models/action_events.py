import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from enums import ActionStatus
from utils import get_datetime
from .base import Base
from .utils import uuid_pk, datetime_tz

if TYPE_CHECKING:
    from .moderators import Moderators
    from .evaluation_events import EvaluationEvents


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
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_events.event_id"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action_params: Mapped[dict] = mapped_column(JSONB, nullable=True)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[ActionStatus] = mapped_column(String, nullable=False)
    error_msg: Mapped[str] = mapped_column(String, nullable=True)
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

    moderator: Mapped["Moderators"] = relationship(
        back_populates="actions", passive_deletes=True
    )
    event: Mapped["EvaluationEvents"] = relationship(
        back_populates="actions", passive_deletes=True
    )