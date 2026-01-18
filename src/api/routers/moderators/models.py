from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from enums import MessagePlatform, ModeratorStatus
from models import CustomBaseModel


class ModeratorCreate(CustomBaseModel):
    """Request model for creating a new moderator."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=200)
    platform: MessagePlatform
    platform_server_id: str
    conf: dict[str, Any]


class ModeratorResponse(CustomBaseModel):
    """Response model for moderator data."""

    moderator_id: UUID
    name: str
    description: str | None
    platform: MessagePlatform
    platform_server_id: str
    conf: dict[str, Any]
    status: ModeratorStatus
    created_at: datetime


class ModeratorUpdate(BaseModel):
    """Request model for updating a moderator."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=200)
    conf: dict[str, Any] | None = None


class BarChartData(BaseModel):
    """Bar chart data point for stats."""

    date: date
    evaluations_count: int
    actions_count: int


class ModeratorStats(BaseModel):
    """Stats response for a moderator."""

    evaluations_count: int
    actions_count: int
    bar_chart: list[BarChartData]


class BehaviorScoreResponse(CustomBaseModel):
    """Response model for user behavior score."""

    user_id: str
    username: str
    behaviour_score: float
