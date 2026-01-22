from enum import Enum
from typing import Generic, Literal, TypeVar

from engine.actions.base import BaseAction, BasePerformedAction
from engine.params.discord import (
    DiscordDefaultParamsTimeout,
    DiscordPerformedActionParamsKick,
    DiscordPerformedActionParamsReply,
    DiscordPerformedActionParamsTimeout,
)
from enums import MessagePlatform
from pydantic import BaseModel


DP = TypeVar("DP", bound=BaseModel)
P = TypeVar("P", bound=BaseModel)


class DiscordActionType(str, Enum):
    REPLY = "reply"
    KICK = "kick"
    TIMEOUT = "timeout"


class BaseDiscordAction(BaseAction[DP], Generic[DP]):
    type: DiscordActionType
    platform: Literal[MessagePlatform.DISCORD] = MessagePlatform.DISCORD


class BaseDiscordPerformedAction(BasePerformedAction[P], Generic[P]):
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


class DiscordActionKick(BaseDiscordAction[None]):
    type: Literal[DiscordActionType.KICK] = DiscordActionType.KICK


class DiscordPerformedActionKick(
    BaseDiscordPerformedAction[DiscordPerformedActionParamsKick]
):
    type: Literal[DiscordActionType.KICK] = DiscordActionType.KICK
