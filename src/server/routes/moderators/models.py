from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from core.enums import MessagePlatformType
from core.models import CustomBaseModel
from server.shared.models import MessageChartData


class ModeratorBase(CustomBaseModel):
    name: str
    guideline_id: UUID


class ModeratorCreate(ModeratorBase):
    pass


class ModeratorUpdate(ModeratorBase):
    name: str | None = None
    guideline_id: UUID | None = None


class ModeratorResponse(ModeratorBase):
    moderator_id: UUID
    created_at: datetime
    deployment_platforms: list[MessagePlatformType]


class ModeratorStats(BaseModel):
    total_messages: int
    total_actions: int
    message_chart: list[MessageChartData]


class DeploymentCreate(CustomBaseModel):
    platform: MessagePlatformType
    name: str | None
    conf: dict[str, Any]
