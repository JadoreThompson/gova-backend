from enum import Enum
from .base import BaseEvent

from engineV2.actions.base import BasePerformedAction


class ActionEventType(str, Enum):
    ACTION_PERFORMED = "action_performed"


class ActionPerformedEvent(BaseEvent):
    type: ActionEventType.ACTION_PERFORMED
    action: BasePerformedAction
    reason: str  # Reason the action was taken
