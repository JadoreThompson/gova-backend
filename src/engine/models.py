from pydantic import BaseModel

from core.enums import MessagePlatformType
from core.models import CustomBaseModel
from engine.discord.actions import DiscordAction


class BaseMessageContext(CustomBaseModel):
    platform: MessagePlatformType
    content: str


class TopicEvaluation(BaseModel):
    topic: str
    topic_score: float


class MessageEvaluation(CustomBaseModel):
    evaluation_score: float
    topic_evaluations: list[TopicEvaluation]
    action: DiscordAction | None
