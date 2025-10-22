from pydantic import BaseModel


class Guild(BaseModel):
    id: str
    name: str
    icon: str | None


class GuildChannel(BaseModel):
    id: str
    name: str
