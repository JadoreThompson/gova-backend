import uuid
from enum import Enum
from typing import Literal

from engineV2.actions.base import BasePerformedAction
from .base import BaseEvent



class ActionEventType(str, Enum):
    ACTION_PERFORMED = "action_performed"


class ActionPerformedEvent(BaseEvent):
    type: Literal[ActionEventType.ACTION_PERFORMED] = ActionEventType.ACTION_PERFORMED
    moderator_id: uuid.UUID
    action: BasePerformedAction
