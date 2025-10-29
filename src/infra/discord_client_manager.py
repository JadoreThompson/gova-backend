import asyncio
import logging
import discord

from config import DISCORD_BOT_TOKEN


logger = logging.getLogger("discord_client_manager")


class DiscordClientManager:
    client: discord.Client | None = None

    @classmethod
    async def start(cls) -> None:
        if not cls.client:
            intents = discord.Intents.default()
            cls.client = discord.Client(intents=intents)
            cls._register_events()
            cls._task = asyncio.create_task(cls.client.start(token=DISCORD_BOT_TOKEN))

    @classmethod
    async def stop(cls) -> None:
        if cls._task and not cls._task.done():
            cls._task.cancel()
            try:
                await cls._task
            except asyncio.CancelledError:
                pass
            cls._task = None

        cls._handler = None

    @classmethod
    def _register_events(cls) -> None:
        if cls.client:

            @cls.client.event
            async def on_ready():
                logger.info(f"Discord Manager logged in as {cls.client.user}.")
