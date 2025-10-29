from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from core.enums import PricingTierType


@dataclass
class JWTPayload:
    sub: UUID
    em: str
    exp: datetime
    pricing_tier: PricingTierType
    authenticated: bool


class Identity(NamedTuple):
    username: str | None
    avatar: str | None
    success: bool


# TODO: Convert to base model and move to shared
class Guild(NamedTuple):
    id: int
    name: str
    icon: str | None


class GuildChannel(NamedTuple):
    id: int
    name: str
