from enum import Enum
from typing import Literal

from engineV2.actions.base import BaseAction, BasePerformedAction
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


class BaseDiscordPerformedAction(BasePerformedAction):
    type: DiscordActionType
    platform: Literal[MessagePlatform.DISCORD] = MessagePlatform.DISCORD


class DiscordActionReply(BaseDiscordAction[DiscordDefaultParamsReply]):
    type: Literal[DiscordActionType.REPLY] = DiscordActionType.REPLY


class DiscordPerformedActionReply(
    BaseDiscordPerformedAction[DiscordDefaultParamsReply]
):
    type: Literal[DiscordActionType.REPLY] = DiscordActionType.REPLY


class DiscordActionTimeout(BaseDiscordAction[DiscordDefaultParamsTimeout]):
    type: Literal[DiscordActionType.TIMEOUT] = DiscordActionType.TIMEOUT


class DiscordPerformedActionTimeout(BasePerformedAction[DiscordDefaultParamsTimeout]):
    type: Literal[DiscordActionType.TIMEOUT] = DiscordActionType.TIMEOUT


class DiscordActionKick(BaseDiscordAction):
    type: Literal[DiscordActionType.TIMEOUT] = DiscordActionType.TIMEOUT


class DiscordPerformedActionKick(BasePerformedAction):
    type: Literal[DiscordActionType.KICK] = DiscordActionType.KICK
