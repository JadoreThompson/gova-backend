from typing import Any

from pydantic import BaseModel

from core.enums import MessagePlatformType
from core.models import CustomBaseModel
from server.shared.models import MessageChartData


class DeploymentBase(CustomBaseModel):
    platform: MessagePlatformType
    name: str
    conf: dict[str, Any]


class DeploymentUpdate(CustomBaseModel):
    name: str | None = None
    conf: dict[str, Any] | None = None


class DeploymentStats(BaseModel):
    total_messages: int
    total_actions: int
    message_chart: list[MessageChartData]
