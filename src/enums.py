from enum import Enum


class PricingTierType(int, Enum):
    FREE = 0
    PRO = 1
    ENTERPRISE = 2


class MessagePlatform(str, Enum):
    DISCORD = "discord"


class ModeratorStatus(str, Enum):
    OFFLINE = "offline"
    PENDING = "pending"
    ONLINE = "online"


class ActionStatus(str, Enum):
    FAILED = "failed"
    SUCCESS = "success"
    DECLINED = "declined"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"


class CoreEventType(str, Enum):
    MODERATOR_EVENT = "moderator_event"


class ModeratorEventType(str, Enum):
    START = "start"
    ALIVE = "alive"
    KILL = "stop"
    DEAD = "dead"
    FAILED = "failed"
    HEARTBEAT = "heartbeat"
    ACTION_PERFORMED = "action"
    EVALUATION_CREATED = "evaluation"
    ERROR = "error"
    WARNING = "warning"


class LogSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
