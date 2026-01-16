from enum import Enum


class PricingTier(int, Enum):
    FREE = 0
    PRO = 1


class MessagePlatform(str, Enum):
    DISCORD = "discord"


class ModeratorStatus(str, Enum):
    OFFLINE = "offline"
    PENDING = "pending"
    ONLINE = "online"


class ActionStatus(str, Enum):
    COMPLETED = "completed"
    AWAITING_APPROVAL = "awaiting_approval"
    FAILED = "failed"
    REJECTED = "rejected"


class CoreEventType(str, Enum):
    MODERATOR_EVENT = "moderator_event"


class LogSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
