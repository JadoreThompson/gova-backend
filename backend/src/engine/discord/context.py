from pydantic import BaseModel

from core.enums import MessagePlatformType
from engine.models import MessageContext


class DiscordServer(BaseModel):
    name: str
    id: int


class DiscordContext(BaseModel):
    """A replacement for discord.Message"""

    user_id: int
    channel_id: int
    guild_id: int


class DiscordMessageContext(MessageContext):
    platform: MessagePlatformType = MessagePlatformType.DISCORD
    discord: DiscordContext
