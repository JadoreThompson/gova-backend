import asyncio
import logging
from typing import AsyncIterator

import discord

from engine.base_stream import BaseChatStream
from .context import DiscordMessageContext, DiscordServer


logger = logging.getLogger("discord-stream")


class DiscordStream(BaseChatStream):
    def __init__(self, token: str, guild_id: int, allowed_channels: list[int]) -> None:
        super().__init__()
        self._token = token
        self._guild_id = guild_id
        self._allowed_channels = set(allowed_channels)
        self._client: discord.Client | None = None
        self._msg_queue: asyncio.Queue[discord.Message] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    def _build_client(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        self._client = discord.Client(intents=intents)

        @self._client.event
        async def on_ready():
            logger.info(f"Logged in as {self._client.user}")

        @self._client.event
        async def on_message(msg: discord.Message):
            if (
                msg.guild.id != self._guild_id
                or msg.channel.id not in self._allowed_channels
            ):
                return

            self._msg_queue.put_nowait(msg)

            if msg.content.startswith("$hello"):
                await msg.channel.send("Hello!")

    async def __aiter__(self) -> AsyncIterator[DiscordMessageContext]:
        self._build_client()
        self._task = asyncio.create_task(self._client.start(self._token))

        while True:
            item = await self._msg_queue.get()
            ctx = DiscordMessageContext(
                content=item.content,
                server=DiscordServer(name=item.guild.name, id=item.guild.id),
                channel=item.channel.name,
                user_id=item.author.id,
            )
            yield ctx

    def __del__(self):
        if self._task:
            self._task.cancel()
