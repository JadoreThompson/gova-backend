from typing import Literal
from uuid import UUID

from core.models import CustomBaseModel
from core.enums import MessagePlatformType
from engine.discord.config import DiscordConfig


DeploymentEventType = Literal["start", "stop", "stopped"]


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