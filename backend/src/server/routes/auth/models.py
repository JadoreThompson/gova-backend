from core.enums import ConnectionType
from core.models import CustomBaseModel


class UserCreate(CustomBaseModel):
    username: str
    password: str


class UserLogin(CustomBaseModel):
    username: str
    password: str


class PlatformConnection(CustomBaseModel):
    username: str
    avatar: str


class UserMe(CustomBaseModel):
    username: str
    connections: dict[ConnectionType, PlatformConnection] | None = None
