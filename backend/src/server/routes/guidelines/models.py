from datetime import datetime
from uuid import UUID

from core.models import CustomBaseModel


class GuidelineBase(CustomBaseModel):
    name: str
    text: str


class GuidelineCreate(GuidelineBase):
    pass


class GuidelineUpdate(GuidelineBase):
    name: str | None = None
    text: str | None = None


class GuidelineResponse(GuidelineBase):
    created_at: datetime
    breach_types: list[str]
