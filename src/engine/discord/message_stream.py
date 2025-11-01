import asyncio
import logging
from typing import AsyncIterator

import discord

from config import DISCORD_BOT_TOKEN
from engine.base.base_message_stream import BaseMessageStream


logger = logging.getLogger("discord-stream")


class DiscordMessageStream(BaseMessageStream[discord.Message]):
    def __init__(
        self,
    ) -> None:
        super().__init__()
        self._msg_queue: asyncio.Queue[discord.Message] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    @property
    def client(self) -> discord.Client | None:
        return self._client

    def register_events(self) -> None:
        @self._client.event
        async def on_ready():
            logger.info(f"Logged in as {self._client.user}")

        @self._client.event
        async def on_message(msg: discord.Message):
            self._msg_queue.put_nowait(msg)

    def _start_client(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        self._client = discord.Client(intents=intents)
        self.register_events()
        self._task = asyncio.create_task(self._client.start(token=DISCORD_BOT_TOKEN))

    async def __aiter__(self) -> AsyncIterator[discord.Message]:
        self._start_client()

        try:
            while True:
                item = await self._msg_queue.get()
                yield item
        finally:
            if self._task and not self._task.done():
                self._task.cancel()
                await self._task
                await self._client.close()

            self._client = None
            self._msg_queue.shutdown()
