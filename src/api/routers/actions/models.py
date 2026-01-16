from datetime import datetime
from typing import Any
from uuid import UUID

from enums import ActionStatus
from models import CustomBaseModel


class ActionResponse(CustomBaseModel):
    """Response model for action data."""

    action_id: UUID
    moderator_id: UUID
    platform_user_id: str | None
    action_type: str
    action_params: dict[str, Any] | None
    context: dict[str, Any]
    status: ActionStatus
    reason: str | None
    created_at: datetime
    updated_at: datetime
    executed_at: datetime | None
