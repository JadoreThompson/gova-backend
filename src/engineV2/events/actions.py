from .base import BaseEvent
from .enums import EventType

from engineV2.actions.base import BasePerformedAction


class ActionPerformedEvent(BaseEvent):
    type: EventType.ACTION_PERFORMED
    action: BasePerformedAction
    reason: str  # Reason the action was taken
