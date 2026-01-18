from enum import Enum
from typing import Literal

from engine.actions.base import BaseAction, BasePerformedAction
from engine.params.discord import (
    DiscordDefaultParamsTimeout,
    DiscordPerformedActionParamsKick,
    DiscordPerformedActionParamsReply,
    DiscordPerformedActionParamsTimeout,
)
from enums import MessagePlatform


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


class DiscordActionReply(BaseDiscordAction[None]):
    type: Literal[DiscordActionType.REPLY] = DiscordActionType.REPLY


class DiscordPerformedActionReply(
    BaseDiscordPerformedAction[DiscordPerformedActionParamsReply]
):
    type: Literal[DiscordActionType.REPLY] = DiscordActionType.REPLY


class DiscordActionTimeout(BaseDiscordAction[DiscordDefaultParamsTimeout]):
    type: Literal[DiscordActionType.TIMEOUT] = DiscordActionType.TIMEOUT


class DiscordPerformedActionTimeout(
    BaseDiscordPerformedAction[DiscordPerformedActionParamsTimeout]
):
    type: Literal[DiscordActionType.TIMEOUT] = DiscordActionType.TIMEOUT


class DiscordActionKick(BaseDiscordAction):
    type: Literal[DiscordActionType.TIMEOUT] = DiscordActionType.TIMEOUT


class DiscordPerformedActionKick(
    BaseDiscordPerformedAction[DiscordPerformedActionParamsKick]
):
    type: Literal[DiscordActionType.TIMEOUT] = DiscordActionType.TIMEOUT
