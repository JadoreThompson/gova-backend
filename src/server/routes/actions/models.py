from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from core.enums import ActionStatus
from core.models import CustomBaseModel


class ActionUpdate(CustomBaseModel):
    status: Literal[ActionStatus.APPROVED, ActionStatus.DECLINED]


class ActionResponse(CustomBaseModel):
    log_id: UUID
    deployment_id: UUID
    action_type: str
    action_params: dict[str, Any]
    status: ActionStatus
    created_at: datetime
