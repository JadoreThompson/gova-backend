from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from engineV2.enums import MessagePlatform
from models import CustomBaseModel


DP = TypeVar("DP", bound=BaseModel)


class BaseAction(CustomBaseModel, Generic[DP]):
    type: Enum
    platform: MessagePlatform
    requires_approval: bool
    default_params: DP | None = None


class BasePerformedAction(BaseAction[DP]):
    params: dict[str, Any]  # Extends dict version of DP
    reason: str
