from enum import Enum
from typing import Literal

from engineV2.actions.base import BaseAction
from engineV2.actions.registry import PerformedActionRegistry
from engineV2.enums import MessagePlatform
from engineV2.params.discord import (
    DiscordDefaultParamsTimeout,
    DiscordDefaultParamsReply,
)


class DiscordActionType(str, Enum):
    REPLY = "reply"
    KICK = "kick"
    TIMEOUT = "timeout"


class BaseDiscordAction(BaseAction):
    type: DiscordActionType
    platform: Literal[MessagePlatform.DISCORD] = MessagePlatform.DISCORD


class BaseDiscordPerformedAction(BaseDiscordAction):
    pass


class DiscordActionReply(BaseDiscordAction[DiscordDefaultParamsReply]):
    type: Literal[DiscordActionType.REPLY] = DiscordActionType.REPLY


class DiscordPerformedActionReply(DiscordActionReply):
    pass


class DiscordActionTimeout(BaseDiscordAction[DiscordDefaultParamsTimeout]):
    type: Literal[DiscordActionType.TIMEOUT] = DiscordActionType.TIMEOUT


class DiscordPerformedActionTimeout(DiscordActionTimeout):
    pass


class DiscordActionKick(BaseDiscordAction):
    type: Literal[DiscordActionType.TIMEOUT] = DiscordActionType.TIMEOUT


class DiscordPerformedActionKick(DiscordActionKick):
    pass
