from datetime import datetime
from typing import Any
from uuid import UUID

from enums import ActionStatus
from models import CustomBaseModel


class ActionResponse(CustomBaseModel):
    log_id: UUID
    action_type: str
    action_params: dict[str, Any]
    status: ActionStatus
    created_at: datetime
