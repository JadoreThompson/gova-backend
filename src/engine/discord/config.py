from core.models import CustomBaseModel
from engine.base.base_action import BaseActionDefinition
from engine.discord.actions import DiscActionDefinitionUnion


class DiscordConfig(CustomBaseModel):
    guild_id: int
    # allowed_channels: tuple[Literal["*"]] | tuple[int, ...]
    # allowed_actions: tuple[Literal["*"]] | tuple[BaseActionDefinition, ...]
    allowed_channels: tuple[int, ...]
    allowed_actions: tuple[DiscActionDefinitionUnion, ...]
