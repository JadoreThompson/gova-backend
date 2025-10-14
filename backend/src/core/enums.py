from enum import Enum


class ChatPlatformType(Enum):
    DISCORD = "discord"


class ModeratorState(Enum):
    OFFLINE = "offline"
    PENDING = "pending"
    ONLINE = "online"
