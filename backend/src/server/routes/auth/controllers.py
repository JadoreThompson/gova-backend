from aiohttp import BasicAuth, ClientSession
from fastapi import Response

from config import (
    COOKIE_ALIAS,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URI,
)
from server.services import JWTService


def set_cookie(rsp: Response | None = None, **kw) -> Response:
    if rsp is None:
        rsp = Response()

    rsp.set_cookie(COOKIE_ALIAS, JWTService.generate_jwt(**kw))
    return rsp


async def fetch_discord_access_token(auth_code: str):
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": DISCORD_REDIRECT_URI,
    }

    async with ClientSession() as sess:
        rsp = await sess.post(
            "https://discord.com/api/oauth2/token",
            auth=BasicAuth(DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
        )
        data = await rsp.json()
        return data
