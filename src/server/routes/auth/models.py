from pydantic import BaseModel
from typing import Literal

from core.enums import MessagePlatformType, PricingTierType
from core.models import CustomBaseModel


class UserCreate(CustomBaseModel):
    username: str
    email: str
    password: str


class UserLogin(CustomBaseModel):
    username: str | None = None
    email: str | None = None
    password: str


class UserConnection(BaseModel):
    username: str
    avatar: str


class UserMe(CustomBaseModel):
    username: str
    pricing_tier: PricingTierType
    connections: dict[MessagePlatformType, UserConnection]


class UpdateUsername(BaseModel):
    username: str


class UpdatePassword(BaseModel):
    password: str


class VerifyCode(BaseModel):
    code: str


class VerifyAction(VerifyCode):
    action: Literal["change_username", "change_password"]
