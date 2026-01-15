from enum import Enum


class MessagePlatform(str, Enum):
    DISCORD = "discord"


class ActionStatus(str, Enum):
    COMPLETED = "completed"
    AWAITING_APPROVAL = "awaiting_approval"
    FAILED = "failed"
