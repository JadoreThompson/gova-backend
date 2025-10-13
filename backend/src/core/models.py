from datetime import datetime
from enum import Enum
from json import loads
from uuid import UUID

from pydantic import BaseModel, Field
from core.enums import ActionType


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


class Action(CustomBaseModel):
    type: ActionType
    reason: str


class BanAction(Action):
    type: ActionType = ActionType.BAN


class MuteAction(Action):
    type: ActionType = ActionType.MUTE
    duration: int = Field(
        ..., ge=0, description="Duration in milliseconds to mute the user."
    )
