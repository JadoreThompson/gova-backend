import asyncio
import logging

from config import KAKFA_ACTION_EVENTS_TOPIC
from engineV2.actions.discord import BaseDiscordPerformedAction
from engineV2.message_streams.discord import DiscordMessageStream
from engineV2.moderators.discord import DiscordModerator
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
        self._moderators = set(moderators) if moderators else set()
        self._kafka_producer = kafka_producer

        self._guild_2_moderator = {mod.guild_id: mod for mod in self._moderators}

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
            mod = self._guild_2_moderator.get(msg.guild_id)
            if mod is None:
                continue

            await mod.process_message(msg)

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
            moderator.on_action_performed = self._on_action_performed
            self._moderators.add(moderator)
            return True
        return False

    def remove(self, moderator: DiscordModerator) -> None:
        if moderator in self._moderators:
            self._moderators.discard(moderator)
            self._guild_2_moderator.pop(moderator.guild_id)

    async def _on_action_performed(self, action: BaseDiscordPerformedAction) -> None:
        """Event hook for moderators"""
        if self._kafka_producer is not None:
            await self._kafka_producer.send(
                KAKFA_ACTION_EVENTS_TOPIC, action.model_dump_json().encode()
            )
