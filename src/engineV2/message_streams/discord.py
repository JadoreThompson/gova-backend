import asyncio
import logging
from typing import AsyncGenerator

import discord

from engineV2.contexts.discord import DiscordMessageContext
from .exc import IterationInProgressException


class DiscordMessageStream:
    def __init__(self, client: discord.Client, max_size: int = 0):
        """
        Args:
            client (discord.Client): A discord client which hasn't been started.
            max_size (int, optional): Max size of the message queue. Defaults to 0 or
                no max size.
        """
        self._client = client
        self._alive = False
        self._queue: asyncio.Queue[discord.Message] = asyncio.Queue(max_size)
        self._sentinel = -1
        self._logger = logging.getLogger(type(self).__name__)

    @property
    def client(self) -> discord.Client:
        return self._client

    @property
    def alive(self) -> bool:
        return self._alive

    def start(self) -> None:
        self._register_events()

    def stop(self) -> None:
        self._queue.put_nowait(self._sentinel)

    def _register_events(self):
        @self._client.event
        async def on_ready():
            self._logger.info(f"Logged in as {self._client.user}")

        @self._client.event
        async def on_message(msg: discord.Message):
            await self._queue.put(msg)

    async def __aiter__(self) -> AsyncGenerator[DiscordMessageContext, None]:
        if self._alive:
            raise IterationInProgressException

        while True:
            msg = await self._queue.get()
            if msg == self._sentinel:
                self._logger.info("Sentinel received. Exiting loop")
                break

            reply_to = None
            if msg.reference is not None:
                ref = msg.reference.resolved
                if isinstance(ref, discord.Message):
                    reply_to = DiscordMessageContext(
                        guild_id=ref.guild.id,
                        channel_id=ref.channel.id,
                        user_id=ref.author.id,
                        content=msg.content,
                    )

            yield DiscordMessageContext(
                guild_id=msg.guild.id,
                channel_id=msg.channel.id,
                user_id=msg.author.id,
                content=msg.content,
                reply_to=reply_to,
            )

        self._logger.info("Exiting iteration")

    # async def __aiter__(self) -> AsyncGenerator[discord.Message, None]:
    #     if self._alive:
    #         raise IterationInProgressException

    #     while True:
    #         msg = await self._queue.get()
    #         if msg == self._sentinel:
    #             self._logger.info("Sentinel received. Exiting loop")
    #             break

    #         yield msg

    #     self._logger.info("Exiting iteration")
