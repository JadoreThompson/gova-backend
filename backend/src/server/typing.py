from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class JWTPayload:
    sub: UUID
    exp: datetime
