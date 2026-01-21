import asyncio
import logging

from engine.actions.registry import PerformedActionRegistry
from engine.message_streams.discord import DiscordMessageStream
from engine.moderators.discord import DiscordModerator
from infra.kafka import AsyncKafkaProducer


class DiscordModeratorOrchestrator:
    def __init__(
        self,
        msg_stream: DiscordMessageStream,
        moderators: list[DiscordModerator] | None = None,
        kafka_producer: AsyncKafkaProducer | None = None,
        max_moderators: int = 5,
        batch_size: int = 20,
        flush_interval: int = 5,
    ):
        self._msg_stream = msg_stream
        self._moderators = {}
        if moderators:
            self._moderators = {
                moderator.moderator_id: moderator for moderator in moderators
            }
        self._kafka_producer = kafka_producer

        self._guild_2_moderator = {
            mod.guild_id: mod for mod in self._moderators.values()
        }

        self.max_moderators = max_moderators
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._logger = logging.getLogger(type(self).__name__)

    def start(self) -> None:
        PerformedActionRegistry.register_discord()
        self._run_task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        async for msg in self._msg_stream:
            mod = self._guild_2_moderator.get(msg.guild_id)
            if mod is None:
                continue

            try:
                await mod.process_message(msg)
            except Exception:
                error_msg = (
                    "An error occured whilst processing message "
                    f"for moderator '{mod.moderator_id}'"
                )
                self._logger.error(error_msg, exc_info=True)
                await mod.close(error_msg)

    async def stop(self) -> None:
        if self._run_task is not None and not self._run_task.done():
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
            self._run_task = None

    def add(self, moderator: DiscordModerator) -> bool:
        if (
            moderator.moderator_id not in self._moderators
            and len(self._moderators) < self.max_moderators
        ):
            self._moderators[moderator.moderator_id] = moderator
            self._guild_2_moderator[moderator.guild_id] = moderator
            return True
        return False

    def remove(self, moderator: DiscordModerator) -> None:
        if moderator.moderator_id in self._moderators:
            self._moderators.pop(moderator.moderator_id)
            self._guild_2_moderator.pop(moderator.guild_id)
