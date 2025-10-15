from datetime import datetime
from uuid import UUID

from core.models import CustomBaseModel


class ModeratorBase(CustomBaseModel):
    name: str
    guideline_id: UUID


class ModeratorCreate(ModeratorBase):
    pass


class ModeratorUpdate(ModeratorBase):
    name: str | None = None
    guideline_id: UUID | None = None


class ModeratorResponse(ModeratorBase):
    moderator_id: UUID
    created_at: datetime
