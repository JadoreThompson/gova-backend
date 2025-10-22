from pydantic import BaseModel


class Guild(BaseModel):
    id: int
    name: str
    icon: str | None