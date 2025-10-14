from pydantic import BaseModel

from core.enums import ChatPlatformType
from core.models import CustomBaseModel
from engine.enums import MaliciousState
from .discord.actions import DiscordAction


class PromptValidation(BaseModel):
    malicious: MaliciousState


class MessageContext(CustomBaseModel):
    platform: ChatPlatformType
    message: str


class MessageEvaluation(CustomBaseModel):
    evaluation_score: float
    action: DiscordAction | None
