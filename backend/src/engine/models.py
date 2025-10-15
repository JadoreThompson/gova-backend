from pydantic import BaseModel

from core.enums import MessagePlatformType
from core.models import CustomBaseModel
from engine.discord.actions import DiscordAction


class MessageContext(CustomBaseModel):
    platform: MessagePlatformType
    content: str


class MessageBreach(BaseModel):
    breach_type: str
    breach_score: float


class MessageEvaluation(CustomBaseModel):
    evaluation_score: float
    breaches: list[MessageBreach]
    action: DiscordAction | None
