from typing import Generic, TypeVar
from pydantic import Field

from engine.actions.discord import BaseDiscordAction
from models import CustomBaseModel

A = TypeVar("A", bound=BaseDiscordAction)


class DiscordModeratorConfig(CustomBaseModel, Generic[A]):
    guild_id: int
    channel_ids: list[int]
    guild_summary: str = Field(..., min_length=1)
    guidelines: str = Field(..., min_length=10)
    instructions: str | None = None
    actions: list[A]
