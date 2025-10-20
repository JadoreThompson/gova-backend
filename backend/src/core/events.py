from typing import Literal
from uuid import UUID

from engine.discord.config import DiscordConfig
from core.models import CustomBaseModel
from core.enums import MessagePlatformType


DeploymentEventType = Literal["start", "stop"]


class DeploymentEvent(CustomBaseModel):
    type: DeploymentEventType
    deployment_id: UUID


class CreateDeploymentEvent(DeploymentEvent):
    type: DeploymentEventType = "start"
    moderator_id: UUID
    platform: MessagePlatformType
    conf: DiscordConfig


class StopDeploymentEvent(DeploymentEvent):
    type: DeploymentEventType = "stop"
