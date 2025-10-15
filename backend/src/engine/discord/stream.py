import asyncio
from typing import AsyncIterator

import discord

from backend.src.engine.base_stream import BaseChatStream
from .context import DiscordMessageContext, DiscordServer


class DiscordStream(BaseChatStream):
    def __init__(self, token: str, guild_id: int) -> None:
        self._token = token
        self._guild_id = guild_id
        self._client: discord.Client | None = None
        self._msg_queue: asyncio.Queue[discord.Message] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        super().__init__()

    def _build_client(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        self._client = discord.Client(intents=intents)

        @self._client.event
        async def on_ready():
            print(f"We have logged in as {self._client.user}")

        @self._client.event
        async def on_message(msg: discord.Message):
            if msg.guild.id != self._guild_id:
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
