from fastapi import HTTPException

from engine.action_handlers.discord import DiscordActionHandler
from services.discord import DiscordService


def get_discord_handler() -> DiscordActionHandler:
    """Get the Discord action handler."""
    client = DiscordService.client
    if client is None:
        raise HTTPException(status_code=503, detail="Discord client not available")
    return DiscordActionHandler(client)
