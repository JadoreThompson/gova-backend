from pydantic import BaseModel


class DiscordDefaultParamsReply(BaseModel):
    prefix: str | None = None
    suffix: str | None = None


class DiscordPerformedActionParamsReply(BaseModel):
    content: str


class DiscordDefaultParamsTimeout(BaseModel):
    secs: int | None = None


class DiscordPerformedActionParamsTimeout(BaseModel):
    duration: int
    user_id: int


class DiscordPerformedActionParamsKick(BaseModel):
    user_id: int
