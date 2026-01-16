import uuid
from enum import Enum
from typing import Any

from pydantic import Field

from models import CustomBaseModel
from utils import get_datetime


class BaseEvent(CustomBaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    type: Enum
    timestamp: int = Field(default_factory=lambda: int(get_datetime().timestamp()))
    details: dict[str, Any] | None = None
