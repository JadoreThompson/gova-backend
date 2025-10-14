import asyncio
from uuid import uuid4
import uvicorn

from config import DISCORD_BOT_TOKEN


def main():
    uvicorn.run("server.app:app", host="localhost", port=8000, reload=True)


async def test():
    # from engine.discord.chat_stream import DiscordChatStream

    # stream = DiscordChatStream(DISCORD_BOT_TOKEN, 1334317047995432980)
    # async for msg in stream:
    #     print("Received context:", msg)
    from engine.discord.chat_moderator import DiscordChatModerator
    from engine.discord.chat_stream import DiscordChatStream

    stream = DiscordChatStream(DISCORD_BOT_TOKEN, 1334317047995432980)
    mod = DiscordChatModerator(uuid4(), stream)
    async with mod:
        await mod.moderate_chat()


if __name__ == "__main__":
    # main()
    asyncio.run(test())
