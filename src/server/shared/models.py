from datetime import datetime, date
from uuid import UUID

from pydantic import ValidationError, field_validator

from core.enums import ActionStatus, MessagePlatformType, ModeratorDeploymentStatus
from core.models import CustomBaseModel
from engine.discord.config import DiscordConfig


class MessageChartData(CustomBaseModel):
    date: date
    counts: dict[MessagePlatformType, int]


class DiscordConfigResponse(DiscordConfig):
    guild_id: str

    @field_validator("guild_id", mode="before")
    def validate_guild_id(cls, v):
        if isinstance(v, str):
            return v
        if isinstance(v, int):
            return str(v)
        raise ValidationError(f"Invalid type '{type(v)}' for guild_id")


class DeploymentResponse(CustomBaseModel):
    deployment_id: UUID
    moderator_id: UUID
    platform: MessagePlatformType
    name: str
    conf: DiscordConfigResponse
    status: ModeratorDeploymentStatus
    created_at: datetime


class DeploymentAction(CustomBaseModel):
    log_id: UUID
    deployment_id: UUID
    action_type: str
    action_params: dict
    status: ActionStatus
    created_at: datetime


class PlatformConnection(CustomBaseModel):
    username: str
    avatar: str
