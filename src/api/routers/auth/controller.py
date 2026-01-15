import random
import string
from typing import Any

from db_models import Users
from api.services import DiscordService, EncryptionService
from api.types import Identity 


def gen_verification_code(k: int = 6):
    """Generates a random verification code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=k))


async def handle_fetch_discord_identity(
    oauth_payload: dict[str, Any], user: Users
) -> Identity:
    refreshed = await DiscordService.refresh_token(oauth_payload)

    if refreshed != oauth_payload:
        user.discord_oauth = EncryptionService.encrypt(refreshed, aad=str(user.user_id))

    return await DiscordService.fetch_identity(refreshed["access_token"])
