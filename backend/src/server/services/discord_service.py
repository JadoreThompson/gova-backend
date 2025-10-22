from aiohttp import BasicAuth, ClientError, ClientSession

from config import (
    DISCORD_BOT_TOKEN,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URI,
)
from server.typing import Guild, GuildChannel, Identity


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
    async def fetch_discord_access_token(cls, auth_code: str) -> None:
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
        data = await rsp.json()
        return data

    @classmethod
    async def fetch_identity(cls, data: dict) -> Identity:
        try:
            rsp = await cls._http_sess.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {data['access_token']}"},
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
                    icon=f"{cls._cdn_base_url}/icons/{g['id']}/{g['icon']}.png",
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
