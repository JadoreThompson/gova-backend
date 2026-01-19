from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import depends_db_sess, depends_jwt
from api.types import JWTPayload
from db_models import Users
from enums import MessagePlatform
from services.discord import DiscordService, Guild, GuildChannel, DiscordServiceException
from services.encryption import EncryptionService


router = APIRouter(prefix="/connections", tags=["Connections"])


@router.get("/discord/guilds", response_model=list[Guild])
async def get_owned_discord_guilds(
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.discord_oauth_payload is None:
        return []

    decrypted = EncryptionService.decrypt(
        user.discord_oauth_payload, expected_aad=str(user.user_id)
    )
    refreshed = await DiscordService.refresh_token(decrypted)
    if refreshed != decrypted:
        user.discord_oauth_payload = EncryptionService.encrypt(refreshed, aad=str(user.user_id))
        await db_sess.commit()

    owned_guilds = await DiscordService.fetch_owned_guilds(refreshed["access_token"])
    return [Guild(id=str(g.id), name=g.name, icon=g.icon) for g in owned_guilds]


@router.get("/discord/{guild_id}/channels", response_model=list[GuildChannel])
async def get_discord_channels(
    guild_id: str,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    decrypted = EncryptionService.decrypt(
        user.discord_oauth_payload, expected_aad=str(user.user_id)
    )
    refreshed = await DiscordService.refresh_token(decrypted)
    if refreshed != decrypted:
        user.discord_oauth_payload = EncryptionService.encrypt(
            refreshed, aad=str(user.user_id)
        )
        await db_sess.commit()

    try:
        parsed_id = int(guild_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid guild id.")

    try:
        channels = await DiscordService.fetch_guild_channels(parsed_id)
        return [GuildChannel(id=str(ch.id), name=ch.name) for ch in channels]
    except DiscordServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{platform}")
async def delete_connection(
    platform: MessagePlatform,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    query = update(Users).where(Users.user_id == jwt.sub)
    if platform == MessagePlatform.DISCORD:
        query = query.values(discord_oauth_payload=None)

    await db_sess.execute(query)
    await db_sess.commit()
