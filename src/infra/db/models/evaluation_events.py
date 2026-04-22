import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, Float, String, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base
from .utils import datetime_tz

if TYPE_CHECKING:
    from .moderators import Moderators
    from .action_events import ActionEvents


class EvaluationEvents(Base):
    __tablename__ = "evaluation_events"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, primary_key=True
    )
    moderator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("moderators.moderator_id", ondelete="CASCADE"),
        nullable=False,
    )
    platform_user_id: Mapped[str] = mapped_column(String, nullable=False)
    severity_score: Mapped[float] = mapped_column(Float, nullable=False)
    behaviour_score: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("0.00")
    )
    context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = datetime_tz()

    moderator: Mapped["Moderators"] = relationship(
        back_populates="evaluations", passive_deletes=True
    )
    actions: Mapped[list["ActionEvents"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )