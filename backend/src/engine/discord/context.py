from pydantic import BaseModel

from engine.models import MessageContext
from core.enums import ChatPlatformType


class DiscordServer(BaseModel):
    name: str
    id: int


class DiscordChatContext(MessageContext):
    platform: ChatPlatformType = ChatPlatformType.DISCORD
    server: DiscordServer  # The server the message ws sent in
    channel: str  # The channel the message was sent in
    user_id: int  # The user who sent the message
