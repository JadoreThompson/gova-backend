from pydantic import BaseModel, Field

from engine.actions.discord import BaseDiscordAction


class DiscordModeratorConfig(BaseModel):
    guild_id: int
    channel_ids: list[int]
    guild_summary: str = Field(..., min_length=1)
    guidelines: str = Field(..., min_length=10)
    instructions: str | None = None
    actions: list[BaseDiscordAction]
