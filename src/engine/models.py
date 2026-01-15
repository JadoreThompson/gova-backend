from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from enums import MessagePlatform
from models import CustomBaseModel


T = TypeVar("T")


class BaseMessageContext(CustomBaseModel):
    platform: MessagePlatform
    platform_author_id: str
    platform_message_id: str
    content: str
    metadata: Any


class TopicEvaluation(BaseModel):
    topic: str
    topic_score: float


class MessageEvaluation(CustomBaseModel, Generic[T]):
    evaluation_score: float
    topic_evaluations: list[TopicEvaluation]
    action: T | None
