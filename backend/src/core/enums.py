from enum import Enum


class ChatPlatformType(Enum):
    DISCORD = "discord"


class ModeratorDeploymentState(Enum):
    OFFLINE = "offline"
    PENDING = "pending"
    ONLINE = "online"
