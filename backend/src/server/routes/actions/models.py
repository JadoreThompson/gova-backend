from typing import Literal

from core.enums import ActionStatus
from core.models import CustomBaseModel


class ActionUpdate(CustomBaseModel):
    status: Literal[ActionStatus.APPROVED, ActionStatus.DECLINED]