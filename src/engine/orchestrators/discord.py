import asyncio
import functools
import logging
import uuid

from pydantic import BaseModel

from config import KAFKA_MODERATOR_EVENTS_TOPIC
from engine.actions.discord import BaseDiscordPerformedAction
from engine.contexts.discord import DiscordMessageContext
from engine.message_streams.discord import DiscordMessageStream
from engine.moderators.discord import DiscordModerator
from events.moderator import (
    DeadModeratorEvent,
    ActionPerformedModeratorEvent,
    EvaluationCreatedModeratorEvent,
)
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

        self._logger = logging.getLogger(type(self).__name__)

    def start(self) -> None:
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
                await mod.close(mod.moderator_id, error_msg)

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
            moderator not in self._moderators
            and len(self._moderators) < self.max_moderators
        ):
            moderator.on_action_performed = functools.partial(
                self._on_action_performed, moderator.moderator_id
            )
            moderator.on_closed = functools.partial(
                self._on_moderator_closed, moderator.moderator_id
            )
            self._moderators.add(moderator)
            return True
        return False

    def remove(self, moderator: DiscordModerator) -> None:
        if moderator in self._moderators:
            self._moderators.discard(moderator)
            self._guild_2_moderator.pop(moderator.guild_id)

    async def _on_action_performed(
        self,
        moderator_id: uuid.UUID,
        action: BaseDiscordPerformedAction,
        ctx: DiscordMessageContext,
    ) -> None:
        """Event hook for moderators"""
        if self._kafka_producer is not None:
            event = ActionPerformedModeratorEvent(
                moderator_id=moderator_id, action=action, ctx=ctx
            )
            await self._emit_event(event)

    async def _on_evaluation_created(
        self,
        moderator_id: uuid.UUID,
        user_id: int,
        severity_score: float,
        ctx: DiscordMessageContext,
    ) -> None:
        if self._kafka_producer is not None:
            event = EvaluationCreatedModeratorEvent(
                moderator_id=moderator_id,
                user_id=str(user_id),
                severity_score=severity_score,
                ctx=ctx,
            )
            await self._emit_event(event)

    async def _on_moderator_closed(self, moderator_id: uuid.UUID, reason: str) -> None:
        if self._kafka_producer is not None:
            event = DeadModeratorEvent(moderator_id=moderator_id, reason=reason)
            await self._emit_event(event)

    async def _emit_event(self, event: BaseModel) -> None:
        await self._kafka_producer.send(
            KAFKA_MODERATOR_EVENTS_TOPIC, event.model_dump_json().encode()
        )
