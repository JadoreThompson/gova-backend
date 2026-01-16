from pydantic import BaseModel


class Identity(BaseModel):
    username: str | None
    avatar: str | None
    success: bool


class Guild(BaseModel):
    id: str
    name: str
    icon: str | None


class GuildChannel(BaseModel):
    id: str
    name: str
