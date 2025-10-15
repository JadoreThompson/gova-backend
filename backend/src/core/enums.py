from enum import Enum


class MessagePlatformType(Enum):
    DISCORD = "discord"


class ModeratorDeploymentState(Enum):
    OFFLINE = "offline"
    PENDING = "pending"
    ONLINE = "online"
