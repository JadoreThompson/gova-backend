import asyncio
import logging
from typing import AsyncIterator, Literal

import discord

from config import DISCORD_BOT_TOKEN
from engine.base.base_stream import BaseChatStream
from .context import DiscordMessageContext, DiscordContext


logger = logging.getLogger("discord-stream")


class DiscordStream(BaseChatStream):
    def __init__(
        self,
        guild_id: int,
        allowed_channels: list[int | Literal["*"]],
    ) -> None:
        super().__init__()
        self._guild_id = guild_id
        self._allowed_channels = set(allowed_channels)
        self._allowed_all_channels = allowed_channels[0] == "*"
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
            if msg.guild.id != self._guild_id:
                return

            if (
                not self._allowed_all_channels
                and msg.channel.id not in self._allowed_channels
            ):
                return

            self._msg_queue.put_nowait(msg)

            if msg.content.startswith("$hello"):
                await msg.channel.send("Hello!")

    async def _start_client(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        self._client = discord.Client(intents=intents)
        self.register_events()
        self._task = asyncio.create_task(self._client.start(token=DISCORD_BOT_TOKEN))

    async def __aiter__(self) -> AsyncIterator[DiscordMessageContext]:
        await self._start_client()

        try:
            while True:
                item = await self._msg_queue.get()
                ctx = DiscordMessageContext(
                    content=item.content,
                    platform_author_id=item.author.id,
                    platform_message_id=item.id,
                    discord=DiscordContext(
                        channel_id=item.channel.id,
                        guild_id=item.guild.id,
                    ),
                )
                yield ctx
        finally:
            if self._task and not self._task.done():
                self._task.cancel()
                await self._task
                await self._client.close()

            self._client = None
            self._msg_queue.shutdown()
