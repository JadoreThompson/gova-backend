from enum import Enum


class MessagePlatformType(str, Enum):
    DISCORD = "discord"


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
