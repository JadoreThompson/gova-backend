from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from engine.actions.discord import (
    DiscordActionKick,
    DiscordActionReply,
    DiscordActionTimeout,
    DiscordActionType,
)
from engine.configs.discord import DiscordModeratorConfig
from enums import MessagePlatform

ACTION_CLASSES = {
    MessagePlatform.DISCORD: {
        DiscordActionType.KICK: DiscordActionKick,
        DiscordActionType.REPLY: DiscordActionReply,
        DiscordActionType.TIMEOUT: DiscordActionTimeout,
    }
}


def get_datetime():
    return datetime.now(UTC)


def build_config(platform: MessagePlatform, config: dict[str, Any]) -> BaseModel:
    """
    Builds the configuration object for a messaging platform.

    Args:
        platform (MessagePlatform): The type of the platform
        config (dict[str, Any]): The dictionary representation of the config

    Raises:
        NotImplementedError: Handler for `platform` not implemented

    Returns:
        BaseModel: Configuration object for `paltform`
    """
    config_copy = config.copy()

    actions = [
        ACTION_CLASSES[platform][action["type"]](**action)
        for action in config_copy.pop("actions")
    ]

    if platform == MessagePlatform.DISCORD:
        conf_cls = DiscordModeratorConfig
        return conf_cls(**config_copy, actions=actions)
    else:
        raise NotImplementedError(f"Configuration for {platform} not implemented.")
