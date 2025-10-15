import asyncio
from uuid import uuid4

import uvicorn

from config import DISCORD_BOT_TOKEN


def main():
    uvicorn.run("server.app:app", host="localhost", port=8000, reload=True)


async def test():
    from engine.discord.moderator import DiscordModerator
    from engine.discord.stream import DiscordStream

    stream = DiscordStream(DISCORD_BOT_TOKEN, 1334317047995432980)
    mod = DiscordModerator("51387d42-f73a-4fbf-b9bf-c633afc3345d", stream)
    async with mod:
        await mod.moderate()


if __name__ == "__main__":
    # main()
    asyncio.run(test())
