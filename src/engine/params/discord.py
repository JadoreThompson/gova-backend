from pydantic import BaseModel


class DiscordPerformedActionParamsReply(BaseModel):
    content: str


class DiscordDefaultParamsTimeout(BaseModel):
    duration: int


class DiscordPerformedActionParamsTimeout(BaseModel):
    duration: int
    user_id: int


class DiscordPerformedActionParamsKick(BaseModel):
    user_id: int
