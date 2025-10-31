from typing import Any
from uuid import UUID

from core.enums import (
    ActionStatus,
    CoreEventType,
    MessagePlatformType,
    ModeratorDeploymentEventType,
)
from core.models import CustomBaseModel
from engine.base.base_action import BaseAction
from engine.discord.config import DiscordConfig
from engine.models import BaseMessageContext, MessageEvaluation


class CoreEvent(CustomBaseModel):
    """Generic system event."""

    type: CoreEventType
    data: Any


class ModeratorDeploymentEvent(CustomBaseModel):
    """Base deployment event."""

    type: ModeratorDeploymentEventType
    deployment_id: UUID


class StartModeratorDeploymentEvent(ModeratorDeploymentEvent):
    """Deployment start request."""

    type: ModeratorDeploymentEventType = ModeratorDeploymentEventType.DEPLOYMENT_START
    moderator_id: UUID
    platform: MessagePlatformType
    moderator_conf: DiscordConfig


class StartedModeratorDeploymentEvent(ModeratorDeploymentEvent):
    """Deployment started and alive."""

    type: ModeratorDeploymentEventType = ModeratorDeploymentEventType.DEPLOYMENT_ALIVE
    server_id: str


class StopModeratorDeploymentEvent(ModeratorDeploymentEvent):
    """Deployment stop request."""

    type: ModeratorDeploymentEventType = ModeratorDeploymentEventType.DEPLOYMENT_STOP
    reason: str | None = None


class StoppedModeratorDeploymentEvent(StopModeratorDeploymentEvent):
    """Deployment stopped."""

    type: ModeratorDeploymentEventType = ModeratorDeploymentEventType.DEPLOYMENT_DEAD


class ErrorModeratorDeploymentEvent(ModeratorDeploymentEvent):
    """Deployment error."""

    type: ModeratorDeploymentEventType = ModeratorDeploymentEventType.ERROR
    stack_trace: str | None = None


class ActionModeratorDeploymentEvent(ModeratorDeploymentEvent):
    """Deployment action event."""

    action_type: Any # Enum
    params: BaseAction
    status: ActionStatus


class EvaluationModeratorDeploymentEvent(ModeratorDeploymentEvent):
    """Message evaluation result."""

    type: ModeratorDeploymentEventType = ModeratorDeploymentEventType.EVALUATION_CREATED
    evaluation: MessageEvaluation
    context: BaseMessageContext
