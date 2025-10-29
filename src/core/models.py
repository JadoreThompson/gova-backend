from datetime import datetime
from enum import Enum
from json import loads
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CustomBaseModel(BaseModel):
    model_config = {
        "json_encoders": {
            UUID: str,
            datetime: lambda dt: dt.isoformat(),
            Enum: lambda e: e.value,
        }
    }

    def to_serialisable_dict(self) -> dict:
        return loads(self.model_dump_json())


class PaymentInfo(CustomBaseModel):
    customer_id: str | None = None
    subscription_id: str | None = None
    last: dict[str, Any] | None = None