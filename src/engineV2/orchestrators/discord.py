import asyncio
import logging

from engineV2.contexts.discord import DiscordMessageContext
from engineV2.message_streams.discord import DiscordMessageStream
from engineV2.moderators.discord import DiscordModerator
from engineV2.orchestrators.moderator_context_group import ModeratorContextGroup


class DiscordModeratorOrchestrator:
    def __init__(
        self,
        msg_stream: DiscordMessageStream,
        moderators: list[DiscordModerator] | None = None,
        max_moderators: int = 5,
        batch_size: int = 20,
        flush_interval: int = 5,
    ):
        self._msg_stream = msg_stream
        self._moderators = set(moderators) if moderators else set()
        self._guild_2_moderator = {
            mod.guild_id: ModeratorContextGroup[
                DiscordModerator, DiscordMessageContext
            ](moderator=mod)
            for mod in self._moderators
        }

        self.max_moderators = max_moderators
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._flush_task: asyncio.Task | None = None
        
        self._logger = logging.getLogger(type(self).__name__)

    def start(self) -> None:
        self._run_task = asyncio.create_task(self._run())
        self._flush_task = asyncio.create_task(self._flush())

    async def _run(self) -> None:
        async for msg in self._msg_stream:
            mod_ctx = self._guild_2_moderator.get(msg.guild_id)
            if mod_ctx is None:
                continue

            async with mod_ctx.lock:
                mod_ctx.messages.append(msg)
                if len(mod_ctx.messages) >= self.batch_size:
                    await mod_ctx.moderator.process_messages(mod_ctx.messages)
                    mod_ctx.messages = []

    async def _flush(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.flush_interval)

                for mod_ctx in self._guild_2_moderator.values():
                    async with mod_ctx.lock:
                        if mod_ctx.messages:
                            await mod_ctx.moderator.process_messages(mod_ctx.messages)
                            mod_ctx.messages = []

        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        if self._run_task is not None and not self._run_task.done():
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
            self._run_task = None

        if self._flush_task is not None and not self._flush_task.done():
            self._flush_task.cancel()
            await self._flush_task

    def add(self, moderator: DiscordModerator) -> bool:
        if (
            moderator not in self._moderators
            and len(self._moderators) < self.max_moderators
        ):
            self._moderators.add(moderator)
            return True
        return False

    def remove(self, moderator: DiscordModerator) -> None:
        if moderator in self._moderators:
            self._moderators.discard(moderator)
            self._guild_2_moderator.pop(moderator.guild_id)
