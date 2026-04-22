from typing import TYPE_CHECKING
import uuid
from datetime import datetime

from sqlalchemy import UUID, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enums import PricingTier
from utils import get_datetime
from .base import Base
from .utils import get_uuid, datetime_tz

if TYPE_CHECKING:
    from .moderators import Moderators


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
        String, nullable=False, default=PricingTier.FREE.value
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

    moderators: Mapped[list["Moderators"]] = relationship(
        "Moderators", cascade="all, delete-orphan"
    )
