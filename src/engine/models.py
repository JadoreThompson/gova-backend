from pydantic import BaseModel

from core.enums import MessagePlatformType
from core.models import CustomBaseModel
from engine.base.base_action import BaseAction


class BaseMessageContext(CustomBaseModel):
    platform: MessagePlatformType
    content: str


class TopicEvaluation(BaseModel):
    topic: str
    topic_score: float


class MessageEvaluation(CustomBaseModel):
    evaluation_score: float
    topic_evaluations: list[TopicEvaluation]
    action: BaseAction | None
