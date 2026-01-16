import asyncio
import json
import logging
import uuid

import discord
from pydantic import BaseModel

from config import DISCORD_BOT_TOKEN, KAFKA_MODERATOR_EVENTS_TOPIC
from db_models import Moderators
from engine.action_handlers.discord import DiscordActionHandler
from engine.configs.discord import DiscordModeratorConfig
from engine.enums import MessagePlatform
from engine.message_streams.discord import DiscordMessageStream
from engine.moderators.discord import DiscordModerator
from engine.orchestrators.discord import DiscordModeratorOrchestrator
from events.moderator import (
    AliveModeratorEvent,
    ConfigUpdatedModeratorEvent,
    DeadModeratorEvent,
    ModeratorEventType,
)
from infra.db import get_db_sess
from infra.kafka import AsyncKafkaConsumer, AsyncKafkaProducer
from .base_runner import BaseRunner


class ModeratorOrchestratorRunner(BaseRunner):
    """Runs the Discord Moderator Orchestrator."""

    def __init__(self, platform: MessagePlatform):
        super().__init__()
        self._platform = platform
        self._kafka_producer: AsyncKafkaProducer | None = None

        self._client: discord.Client | None = None
        self._client_task: asyncio.Task | None = None

        self._orchestrator: DiscordModeratorOrchestrator | None = None
        self._moderators: dict[uuid.UUID, DiscordModerator] = {}
        self._stream: DiscordMessageStream | None = None
        self._action_handler: DiscordActionHandler | None = None

        self._logger = logging.getLogger(type(self).__name__)

    def _setup(self):
        # Configuring discord client
        intents = discord.Intents.default()
        intents.message_content = True

        self._client = discord.Client(intents=intents)

        self._stream = DiscordMessageStream(self._client)
        self._stream.register_events()
        self._action_handler = DiscordActionHandler(self._client)
        self._orchestrator = DiscordModeratorOrchestrator(self._stream)

        self._client_task = asyncio.create_task(
            self._client.start(token=DISCORD_BOT_TOKEN)
        )

    def run(self):
        asyncio.run(self._run())

    async def _run(self):
        self._setup()
        consumer = AsyncKafkaConsumer(KAFKA_MODERATOR_EVENTS_TOPIC)
        self._kafka_producer = AsyncKafkaProducer()

        try:
            await consumer.start()
            await self._kafka_producer.start()
            self._orchestrator.start()

            async for msg in consumer:
                try:
                    event_data = json.loads(msg.value.decode())
                    event_type = event_data["type"]

                    if event_type == ModeratorEventType.START:
                        await self._handle_start_moderator(event_data["moderator_id"])
                    elif event_type == ModeratorEventType.STOP:
                        await self._handle_stop_moderator(event_data)
                    elif event_type == ModeratorEventType.UPDATE_CONFIG:
                        moderator_id = event_data["moderator_id"]
                        await self._handle_stop_moderator(event_data)
                        await self._handle_start_moderator(moderator_id)
                        event = ConfigUpdatedModeratorEvent(
                            moderator_id=moderator_id, config=event_data["config"]
                        )
                        await self._kafka_producer.send(
                            KAFKA_MODERATOR_EVENTS_TOPIC,
                            event.model_dump_json().encode(),
                        )

                except json.JSONDecodeError:
                    pass

        finally:
            await consumer.stop()
            await self._orchestrator.stop()

            for mod in list(self._moderators.values()):
                event = {"moderator_id": mod.moderator_id, "reason": "Service crashed"}
                await self._handle_stop_moderator(event)

            await self._kafka_producer.stop()

            if not self._client_task.done():
                self._client_task.cancel()
                try:
                    await self._client_task
                except asyncio.CancelledError:
                    pass

    async def _ensure_platform(self, moderator_id: uuid.UUID):
        async with get_db_sess() as db_sess:
            mod = await db_sess.get(Moderators, moderator_id)
            return mod is not None and mod.platform == self._platform

    async def _get_moderator(self, moderator_id: uuid.UUID) -> Moderators:
        async with get_db_sess() as db_sess:
            mod = await db_sess.get(Moderators, moderator_id)
            return mod

    async def _handle_start_moderator(self, moderator_id: uuid.UUID):
        db_mod = await self._get_moderator(moderator_id)
        if not db_mod:
            return

        mod = DiscordModerator(
            moderator_id,
            DiscordModeratorConfig(**db_mod.conf),
            self._action_handler,
            self._kafka_producer,
            max_channel_msgs=100,
        )
        success = self._orchestrator.add(mod)
        if success:
            self._moderators[moderator_id] = mod
        self._logger.info(f"Moderator id={moderator_id} added")

        event = AliveModeratorEvent(moderator_id=moderator_id)
        await self._emit_event(event)

    async def _handle_stop_moderator(self, event):
        moderator_id = event["moderator_id"]
        if moderator_id not in self._moderators:
            return

        mod = self._moderators.pop(moderator_id)
        self._orchestrator.remove(mod)
        await mod.close(event["reason"])
        event = DeadModeratorEvent(moderator_id=moderator_id, reason=event["reason"])
        await self._emit_event(event)

    async def _emit_event(self, event: BaseModel) -> None:
        await self._kafka_producer.send(
            KAFKA_MODERATOR_EVENTS_TOPIC, event.model_dump_json().encode()
        )
