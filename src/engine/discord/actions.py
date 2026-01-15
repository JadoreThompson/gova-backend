from enum import Enum
from typing import Literal, Union

from pydantic import Field

from engine.base.base_action import BaseAction, BaseActionDefinition


class DiscordAction(str, Enum):
    BAN = "ban"
    MUTE = "mute"
    KICK = "kick"


class DiscordAction(BaseAction):
    type: DiscordAction


class BanAction(DiscordAction):
    type: DiscordAction = DiscordAction.BAN
    user_id: int


class BanActionDefinition(BaseActionDefinition):
    type: Literal[DiscordAction.BAN] = DiscordAction.BAN


class MuteAction(DiscordAction):
    type: DiscordAction = DiscordAction.MUTE
    user_id: int
    duration: int = Field(
        ..., ge=0, description="Duration in milliseconds to mute the user."
    )


class MuteActionDefinition(BaseActionDefinition):
    type: Literal[DiscordAction.MUTE] = DiscordAction.MUTE
    duration: int | None = Field(
        None, ge=0, description="Duration in milliseconds to mute the user."
    )


class KickAction(DiscordAction):
    type: DiscordAction = DiscordAction.KICK
    user_id: int


class KickActionDefinition(BaseActionDefinition):
    type: Literal[DiscordAction.KICK] = DiscordAction.KICK


DiscActionUnion = Union[BanAction, MuteAction, KickAction]
DiscActionDefinitionUnion = Union[
    MuteActionDefinition, BanActionDefinition, KickActionDefinition
]
