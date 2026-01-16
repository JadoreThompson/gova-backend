from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from enums import ActionStatus, MessagePlatform, ModeratorStatus
from models import CustomBaseModel


class ModeratorCreate(BaseModel):
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


class ActionResponse(CustomBaseModel):
    """Response model for action data."""

    action_id: UUID
    event_id: UUID
    moderator_id: UUID
    platform_user_id: str | None
    action_type: str
    action_params: dict[str, Any] | None
    context: dict[str, Any]
    status: ActionStatus
    reason: str | None
    created_at: datetime
    updated_at: datetime
    executed_at: datetime | None


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
