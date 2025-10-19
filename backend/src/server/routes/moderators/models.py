from datetime import datetime
from typing import Any
from uuid import UUID

from engine.discord.config import DiscordConfig
from core.enums import MessagePlatformType, ModeratorDeploymentStatus
from core.models import CustomBaseModel


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


class ModeratorDeploymentCreate(CustomBaseModel):
    platform: MessagePlatformType
    name: str | None
    conf: dict[str, Any]


class ModeratorDeploymentResponse(CustomBaseModel):
    deployment_id: UUID
    moderator_id: UUID
    platform: MessagePlatformType
    conf: DiscordConfig
    status: ModeratorDeploymentStatus
    created_at: datetime
