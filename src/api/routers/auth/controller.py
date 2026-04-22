import random
import string
from datetime import timedelta
from typing import Any

import jwt
from fastapi import Response
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from api.types import Identity, JWTPayload
from config import COOKIE_ALIAS, IS_PRODUCTION, JWT_ALGO, JWT_EXPIRY_SECS, JWT_SECRET
from infra.db.models import Users
from services.discord import DiscordService
from services.encryption import EncryptionService
from utils import get_datetime


def gen_verification_code(k: int = 6):
    """Generates a random verification code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=k))


async def handle_fetch_discord_identity(
    oauth_payload: dict[str, Any], user: Users
) -> Identity:
    refreshed = await DiscordService.refresh_token(oauth_payload)

    if refreshed != oauth_payload:
        user.discord_oauth_payload = EncryptionService.encrypt(refreshed, aad=str(user.user_id))

    return await DiscordService.fetch_identity(refreshed["access_token"])


def generate_jwt(user: Users) -> tuple[str, JWTPayload]:
    """Generates a JWT token"""
    payload = JWTPayload(
        sub=user.user_id,
        em=user.email,
        exp=int((get_datetime() + timedelta(seconds=JWT_EXPIRY_SECS)).timestamp()),
        pricing_tier=user.pricing_tier,
        is_verified=user.verified_at is not None,
    )
    return (
        jwt.encode(payload.model_dump(mode="json"), JWT_SECRET, algorithm=JWT_ALGO),
        payload,
    )


async def set_cookie(user: Users, rsp: Response, db_sess: AsyncSession) -> Response:
    """Sets the JWT token in a secure, HttpOnly cookie."""
    jwt_token, payload = generate_jwt(user)

    await db_sess.execute(
        update(Users).values(jwt=jwt_token).where(Users.user_id == user.user_id)
    )

    rsp.set_cookie(
        COOKIE_ALIAS,
        jwt_token,
        httponly=True,
        secure=IS_PRODUCTION,
        expires=payload.exp,
    )
    return rsp


def remove_jwt(rsp: Response) -> Response:
    """Removes the JWT cookie."""
    rsp.delete_cookie(COOKIE_ALIAS)
    return rsp
