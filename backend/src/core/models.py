from pydantic import BaseModel, Field
from core.enums import ActionType


class Action(BaseModel):
    type: ActionType
    reason: str


class BanAction(Action):
    type: ActionType = ActionType.BAN


class MuteAction(Action):
    type: ActionType = ActionType.MUTE
    duration: int = Field(
        ..., ge=0, description="Duration in milliseconds to mute the user."
    )
