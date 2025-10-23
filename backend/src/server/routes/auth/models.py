from pydantic import BaseModel

from core.enums import ConnectionType
from core.models import CustomBaseModel
from server.shared.models import PlatformConnection


class UserCreate(CustomBaseModel):
    username: str
    password: str


class UserLogin(CustomBaseModel):
    username: str
    password: str


class UserMe(CustomBaseModel):
    username: str
    connections: dict[ConnectionType, PlatformConnection] | None = None


class UpdateUsername(BaseModel):
    username: str


class UpdatePassword(BaseModel):
    password: str
