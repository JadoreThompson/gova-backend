import asyncio
import logging
from typing import AsyncGenerator

import discord

from engine.contexts.discord import DiscordMessageContext
from .exceptions import IterationInProgressException


class DiscordMessageStream:
    def __init__(self, client: discord.Client, max_size: int = 0):
        """
        Args:
            client (discord.Client): A discord client which hasn't been started.
            max_size (int, optional): Max size of the message queue. Defaults to 0 or
                no max size.
        """
        self._client = client
        self._closed = False
        self._queue: asyncio.Queue[discord.Message] = asyncio.Queue(max_size)
        self._logger = logging.getLogger(type(self).__name__)

    @property
    def client(self) -> discord.Client:
        return self._client

    @property
    def alive(self) -> bool:
        return self._closed

    @property
    def closed(self):
        return self._closed

    def close(self) -> None:
        self._closed = True
        self._queue.shutdown(immediate=True)

    def register_events(self):
        @self._client.event
        async def on_ready():
            self._logger.info(f"Logged in as {self._client.user}")

        @self._client.event
        async def on_message(msg: discord.Message):
            # if msg.author.id == self._client.user.id:
            #     return
            await self._queue.put(msg)

    async def __aiter__(self) -> AsyncGenerator[DiscordMessageContext, None]:
        if self._closed:
            raise IterationInProgressException()

        while not self._closed:
            try:
                msg = await self._queue.get()
            except asyncio.QueueShutDown:
                break

            reply_to = None
            if msg.reference is not None:
                ref = msg.reference.resolved
                if isinstance(ref, discord.Message):
                    reply_to = DiscordMessageContext(
                        guild_id=ref.guild.id,
                        channel_id=ref.channel.id,
                        channel_name=ref.channel.name,
                        user_id=ref.author.id,
                        username=ref.author.name,
                        content=msg.content,
                        roles=[role.name for role in msg.author.roles]
                    )

            yield DiscordMessageContext(
                guild_id=msg.guild.id,
                channel_id=msg.channel.id,
                channel_name=msg.channel.name,
                user_id=msg.author.id,
                username=msg.author.name,
                content=msg.content,
                roles=[role.name for role in msg.author.roles],
                reply_to=reply_to,
            )

        self._logger.debug("Moderator closed, exiting iter")
