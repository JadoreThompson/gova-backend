from discord import Message as DiscordMessage
from pydantic import BaseModel

from engine.models import MessageContext
from core.enums import MessagePlatformType


class DiscordServer(BaseModel):
    name: str
    id: int


class DiscordMessageContext(MessageContext):
    model_config = {"arbitrary_types_allowed": True}
    
    platform: MessagePlatformType = MessagePlatformType.DISCORD
    msg: DiscordMessage

    def to_serialisable_dict(self):
        self.msg = None
        d = super().to_serialisable_dict()
        d.pop("msg")
        print(d)
        return d

