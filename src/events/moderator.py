import uuid
from enum import Enum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

from events.base import BaseEvent

C = TypeVar("C", bound=BaseModel)


class ModeratorEventType(str, Enum):
    START = "start"
    STOP = "stop"
    ALIVE = "alive"
    DEAD = "dead"
    UPDATE_CONFIG = "update_config"
    CONFIG_UPDATED = "config_updated"


class StartModeratorEvent(BaseEvent):
    type: Literal[ModeratorEventType.START] = ModeratorEventType.START
    moderator_id: uuid.UUID


class StopModeratorEvent(BaseEvent):
    type: Literal[ModeratorEventType.STOP] = ModeratorEventType.STOP
    moderator_id: uuid.UUID
    reason: str


class AliveModeratorEvent(BaseEvent):
    type: Literal[ModeratorEventType.ALIVE] = ModeratorEventType.ALIVE
    moderator_id: uuid.UUID


class DeadModeratorEvent(BaseEvent):
    type: Literal[ModeratorEventType.DEAD] = ModeratorEventType.DEAD
    moderator_id: uuid.UUID
    reason: str | None = None


class UpdateModeratorConfigEvent(BaseEvent, Generic[C]):
    type: Literal[ModeratorEventType.UPDATE_CONFIG] = ModeratorEventType.UPDATE_CONFIG
    moderator_id: uuid.UUID
    config: C


class ConfigUpdatedModeratorEvent(BaseEvent, Generic[C]):
    type: Literal[ModeratorEventType.CONFIG_UPDATED] = ModeratorEventType.CONFIG_UPDATED
    moderator_id: uuid.UUID
    config: C
