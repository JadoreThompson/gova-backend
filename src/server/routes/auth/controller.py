import random
import string
from typing import Any
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import MessagePlatformType
from db_models import Users
from server.services.discord_service import DiscordService
from server.services.encryption_service import EncryptionService


def gen_verification_code(k: int = 6):
    """Generates a random verification code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=k))


async def handle_fetch_discord_identity(oauth_payload: dict[str, Any], db_sess: AsyncSession, user: Users):
    refreshed = await DiscordService.refresh_token(oauth_payload)
    to_commit = False
    
    # Save updated token if it changed
    if refreshed != oauth_payload:
        conns = user.connections or {}
        conns[MessagePlatformType.DISCORD] = EncryptionService.encrypt(refreshed, aad=str(user.user_id))
        to_commit = True

    return DiscordService.fetch_identity(refreshed['access_token']), to_commit