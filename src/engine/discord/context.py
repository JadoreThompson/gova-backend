from pydantic import BaseModel

from enums import MessagePlatform
from engine.models import BaseMessageContext


class DiscordServer(BaseModel):
    name: str
    id: int


class DiscordContext(BaseModel):
    """A replacement for discord.Message"""

    channel_id: int
    guild_id: int


class DiscordMessageContext(BaseMessageContext):
    platform: MessagePlatform = MessagePlatform.DISCORD
    metadata: DiscordContext
