from typing import Literal

from enums import ActionStatus
from models import CustomBaseModel


class ActionUpdate(CustomBaseModel):
    status: Literal[ActionStatus.APPROVED, ActionStatus.DECLINED]
