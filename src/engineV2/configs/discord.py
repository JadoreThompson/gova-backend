from pydantic import BaseModel
from engineV2.actions.discord import BaseDiscordAction


# TODO: Put this in api router's models.py
class _DiscordModeratorConfig(BaseModel):
    guild_id: int
    channels: list[int]
    actions: list[BaseDiscordAction]


class DiscordModeratorConfig(BaseModel):
    guild_id: int
    channel_ids: list[int]
    guild_summary: str
    guidelines: str
    actions: list[BaseDiscordAction]
