from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel

from enums import ActionStatus, MessagePlatform
from models import CustomBaseModel


DP = TypeVar("DP", bound=BaseModel)
P = TypeVar("P", bound=BaseModel)


class BaseAction(CustomBaseModel, Generic[DP]):
    type: Enum
    platform: MessagePlatform
    requires_approval: bool
    default_params: DP | None = None


class BasePerformedAction(CustomBaseModel, Generic[P]):
    type: Enum
    platform: MessagePlatform
    requires_approval: bool
    params: P
    reason: str
    status: ActionStatus
    error_msg: str | None = None
