from core.models import CustomBaseModel
from engine.base_action import BaseActionDefinition


class DiscordConfig(CustomBaseModel):
    guild_id: int
    allowed_channels: list[int]  # Channel IDs
    allowed_actions: list[BaseActionDefinition]
