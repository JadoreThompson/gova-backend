from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, field_validator

from core.enums import MessagePlatformType, ModeratorStatus
from core.models import CustomBaseModel
from engine.discord.config import DiscordConfig
from server.exc import CustomValidationError


class ModeratorBase(CustomBaseModel):
    name: str
    guideline_id: UUID


class ModeratorCreate(ModeratorBase):
    platform: MessagePlatformType
    platform_server_id: str
    conf: DiscordConfig


class ModeratorResponse(ModeratorBase):
    platform: MessagePlatformType
    platform_server_id: str
    conf: DiscordConfig
    status: ModeratorStatus
    created_at: datetime


class MessageChartData(CustomBaseModel):
    date: date
    counts: dict[MessagePlatformType, int]


class ModeratorStats(BaseModel):
    total_messages: int
    total_actions: int
    message_chart: list[MessageChartData]


class DiscordConfigResponse(DiscordConfig):
    guild_id: str

    @field_validator("guild_id", mode="before")
    def validate_guild_id(cls, v):
        if isinstance(v, str):
            return v
        if isinstance(v, int):
            return str(v)
        raise CustomValidationError(400, f"Invalid type '{type(v)}' for guild_id")
