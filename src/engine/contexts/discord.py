from __future__ import annotations

import uuid

from typing import Literal

from enums import MessagePlatform
from models import CustomBaseModel


class DiscordMessageContext(CustomBaseModel):
    message_id: uuid.UUID = uuid.uuid4()
    platform: Literal[MessagePlatform.DISCORD] = MessagePlatform.DISCORD
    guild_id: int
    channel_id: int
    channel_name: str
    user_id: int
    username: str
    content: str
    roles: list[str]
    reply_to: DiscordMessageContext | None = None
