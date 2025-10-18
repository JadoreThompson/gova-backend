from enum import Enum

from pydantic import Field

from engine.base_action import BaseAction, BaseActionDefinition


class DiscordActionType(str, Enum):
    BAN = "ban"
    MUTE = "mute"


class DiscordAction(BaseAction):
    pass


class BanAction(DiscordAction):
    type: DiscordActionType = DiscordActionType.BAN
    user_id: int


class BanActionDefinition(BaseActionDefinition):
    type: DiscordActionType = DiscordActionType.BAN


class MuteAction(DiscordAction):
    type: DiscordActionType = DiscordActionType.MUTE
    user_id: int
    duration: int = Field(
        ..., ge=0, description="Duration in milliseconds to mute the user."
    )


class MuteActionDefinition(BaseActionDefinition):
    type: DiscordActionType = DiscordActionType.MUTE
    duration: int | None = Field(
        None, ge=0, description="Duration in milliseconds to mute the user."
    )
