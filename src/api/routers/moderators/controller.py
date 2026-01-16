from typing import Any

from pydantic import BaseModel

from engineV2.configs.discord import DiscordModeratorConfig
from enums import MessagePlatform


def validate_config(platform: MessagePlatform, config: dict[str, Any]) -> BaseModel:
    if platform == MessagePlatform.DISCORD:
        conf_cls = DiscordModeratorConfig
        return conf_cls(**config)
    else:
        raise ValueError(f"Configuration for {platform} not supported.")
