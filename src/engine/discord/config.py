from typing import Literal

from core.models import CustomBaseModel
from engine.base.base_action import BaseActionDefinition


class DiscordConfig(CustomBaseModel):
    guild_id: int
    allowed_channels: tuple[Literal["*"]] | tuple[int, ...]
    allowed_actions: tuple[Literal["*"]] | tuple[BaseActionDefinition, ...]
