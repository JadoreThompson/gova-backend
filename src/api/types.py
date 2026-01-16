from typing import NamedTuple
from uuid import UUID

from enums import PricingTier
from models import CustomBaseModel


class JWTPayload(CustomBaseModel):
    sub: UUID
    em: str
    exp: int
    pricing_tier: PricingTier
    is_verified: bool


class Identity(NamedTuple):
    username: str | None
    avatar: str | None
    success: bool
