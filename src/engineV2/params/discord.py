from pydantic import BaseModel


class DiscordPerformedActionParamsReply(BaseModel):
    content: str


class DiscordDefaultParamsTimeout(BaseModel):
    duration: int | None = None


class DiscordPerformedActionParamsTimeout(BaseModel):
    duration: int
    user_id: int
    reason: str | None = None


class DiscordPerformedActionParamsKick(BaseModel):
    user_id: int
    reason: str | None = None
