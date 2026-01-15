from typing import Any, Generic, Literal, TypeVar
from uuid import UUID, uuid4

from pydantic import Field

from enums import (
    ActionStatus,
    CoreEventType,
    MessagePlatform,
    ModeratorEventType,
)
from models import CustomBaseModel
from engine.base.base_action import BaseAction
from engine.discord.config import DiscordConfig
from engine.models import BaseMessageContext, MessageEvaluation


C = TypeVar("C", bound=BaseMessageContext)
A = TypeVar("A", bound=BaseAction)


class CoreEvent(CustomBaseModel):
    """Generic system event."""

    type: CoreEventType
    data: Any
    id: UUID = Field(default_factory=uuid4)


# Moderator Events


class ModeratorEvent(CustomBaseModel):
    """Base deployment event."""

    type: ModeratorEventType
    moderator_id: UUID


class StartModeratorEvent(ModeratorEvent):
    """Deployment start request."""

    type: ModeratorEventType = ModeratorEventType.START
    moderator_id: UUID
    platform: MessagePlatform
    conf: DiscordConfig


class KillModeratorEvent(ModeratorEvent):
    """Deployment stop request."""

    type: ModeratorEventType = ModeratorEventType.KILL
    reason: str | None = None


class DeadModeratorEvent(ModeratorEvent):
    """Deployment stopped."""

    type: ModeratorEventType = ModeratorEventType.DEAD
    reason: str | None = None


class HeartbeatModeratorEvent(ModeratorEvent):
    type: ModeratorEventType = ModeratorEventType.HEARTBEAT
    role: Literal["moderator", "server"]
    timestamp: int


class ActionPerformedModeratorEvent(ModeratorEvent, Generic[A, C]):
    """Deployment action event."""

    type: ModeratorEventType = ModeratorEventType.ACTION_PERFORMED
    action_type: Any  # Enum
    params: A
    status: ActionStatus
    context: C


class EvaluationCreatedModeratorEvent(ModeratorEvent, Generic[A, C]):
    """Message evaluation result."""

    type: ModeratorEventType = ModeratorEventType.EVALUATION_CREATED
    message_id: UUID
    evaluation: MessageEvaluation[A]
    context: C


class ErrorModeratorEvent(ModeratorEvent):
    type: ModeratorEventType = ModeratorEventType.ERROR
    stack_trace: str | None = None
