from enum import Enum


class MessagePlatformType(str, Enum):
    DISCORD = "discord"


class LogSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ModeratorDeploymentEventType(str, Enum):
    DEPLOYMENT_START = "start"
    DEPLOYMENT_ALIVE = "alive"
    DEPLOYMENT_STOP = "stop"
    DEPLOYMENT_DEAD = "dead"
    DEPLOYMENT_FAILED = "failed"
    DEPLOYMENT_HEARTBEAT = "heartbeat"
    ACTION_PERFORMED = "action"
    EVALUATION_CREATED = "evaluation"
    ERROR = "error"
    WARNING = "warning"


class ModeratorDeploymentStatus(str, Enum):
    OFFLINE = "offline"
    PENDING = "pending"
    ONLINE = "online"


class ActionStatus(str, Enum):
    FAILED = "failed"
    PENDING = "pending"
    SUCCESS = "success"
    DECLINED = "declined"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"


class PricingTierType(int, Enum):
    FREE = 0
    PRO = 1
    ENTERPRISE = 2


class CoreEventType(str, Enum):
    MODERATOR_DEPLOYMENT = "moderator_deployment"
