from __future__ import annotations
from typing import Literal

from enums import MessagePlatform
from models import CustomBaseModel


class DiscordMessageContext(CustomBaseModel):
    platform: Literal[MessagePlatform.DISCORD] = MessagePlatform.DISCORD
    guild_id: int
    channel_id: int
    channel_name: str
    user_id: int
    content: str
    reply_to: DiscordMessageContext | None = None
