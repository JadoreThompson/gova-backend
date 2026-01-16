from typing import Any
from aiohttp import BasicAuth, ClientError, ClientSession

from config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URI,
)
from utils import get_datetime
from .models import Identity, Guild, GuildChannel


class DiscordService:
    _http_sess: ClientSession | None = None
    _cdn_base_url: str = "https://cdn.discordapp.com"

    @classmethod
    def start(cls) -> None:
        cls._http_sess = ClientSession()

    @classmethod
    async def stop(cls):
        await cls._http_sess.close()

    @classmethod
    async def fetch_discord_oauth_payload(cls, auth_code: str) -> dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": DISCORD_REDIRECT_URI,
        }

        rsp = await cls._http_sess.post(
            "https://discord.com/api/oauth2/token",
            auth=BasicAuth(DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
        )
        rsp_data = await rsp.json()
        return rsp_data

    @classmethod
    async def fetch_identity(cls, access_token: str) -> Identity:
        try:
            rsp = await cls._http_sess.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            rsp.raise_for_status()
            rsp_body = await rsp.json()
            return Identity(
                username=rsp_body["username"],
                avatar=f"{cls._cdn_base_url}/avatars/{rsp_body['id']}/{rsp_body['avatar']}.png",
                success=True,
            )
        except ClientError:
            return Identity(username=None, avatar=None, success=False)

    @classmethod
    async def fetch_owned_guilds(cls, access_token: str) -> list[Guild]:
        try:
            rsp = await cls._http_sess.get(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            rsp.raise_for_status()
            guilds_data = await rsp.json()

            owned_guilds = [
                Guild(
                    id=g["id"],
                    name=g["name"],
                    icon=(
                        f"{cls._cdn_base_url}/icons/{g['id']}/{g['icon']}.png"
                        if g.get("icon")
                        else None
                    ),
                )
                for g in guilds_data
                if g.get("owner") is True
            ]
            return owned_guilds
        except ClientError:
            return []

    @classmethod
    async def fetch_guild_channels(cls, guild_id: str) -> list[GuildChannel]:
        if cls._http_sess is None:
            raise RuntimeError("HTTP session not started")

        try:
            rsp = await cls._http_sess.get(
                f"https://discord.com/api/v10/guilds/{guild_id}/channels",
                headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
            )
            rsp.raise_for_status()
            channels = await rsp.json()
            return [
                GuildChannel(id=ch["id"], name=ch["name"])
                for ch in channels
                if ch.get("type") == 0
            ]
        except ClientError:
            return []

    @classmethod
    async def refresh_token(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Refresh the Discord OAuth2 token if expired.

        payload: Dict containing 'access_token', 'refresh_token', 'expires_in', and 'created_at' (optional)

        Returns the updated payload if refreshed, or the original payload if still valid.
        """
        if (
            "expires_at" not in payload
            and "created_at" in payload
            and "expires_in" in payload
        ):
            payload["expires_at"] = payload["created_at"] + payload["expires_in"]

        if (
            "expires_at" in payload
            and get_datetime().timestamp() < payload["expires_at"]
        ):
            return payload

        data = {
            "grant_type": "refresh_token",
            "refresh_token": payload["refresh_token"],
            "redirect_uri": DISCORD_REDIRECT_URI,
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
        }

        try:
            created_at = get_datetime().timestamp()
            rsp = await cls._http_sess.post(
                "https://discord.com/api/v10/oauth2/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            rsp.raise_for_status()
            new_payload = await rsp.json()

            new_payload["created_at"] = created_at
            new_payload["expires_at"] = (
                new_payload["created_at"] + new_payload["expires_in"]
            )
            return new_payload
        except ClientError:
            return payload
