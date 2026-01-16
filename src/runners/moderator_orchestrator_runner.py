import json
import uuid

from config import KAFKA_MODERATOR_EVENTS_TOPIC
from db_models import Moderators
from engineV2.configs.discord import DiscordModeratorConfig
from engineV2.enums import MessagePlatform
from engineV2.moderators.discord import DiscordModerator
from engineV2.orchestrators.discord import DiscordModeratorOrchestrator
from events.moderator import (
    AliveModeratorEvent,
    ConfigUpdatedModeratorEvent,
    ModeratorEventType,
)
from infra.db.utils import get_db_sess
from infra.kafka import AsyncKafkaConsumer, AsyncKafkaProducer
from .base_runner import BaseRunner


class ModeratorOrchestratorRunner(BaseRunner):
    """Runs the Discord Moderator Orchestrator."""

    def __init__(
        self, platform: MessagePlatform, orchestrator: DiscordModeratorOrchestrator
    ):
        super().__init__()
        self._platform = platform
        self._orchestrator = orchestrator
        self._moderators: dict[uuid.UUID, DiscordModerator] = {}
        self._producer: AsyncKafkaProducer = AsyncKafkaProducer()

    async def run(self):
        consumer = AsyncKafkaConsumer(KAFKA_MODERATOR_EVENTS_TOPIC)

        try:
            await consumer.start()

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
                        await self._producer.send(
                            KAFKA_MODERATOR_EVENTS_TOPIC,
                            event.model_dump_json().encode(),
                        )

                except json.JSONDecodeError:
                    pass

        finally:
            await consumer.stop()

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
            moderator_id, DiscordModeratorConfig(**db_mod.conf), max_channel_msgs=100
        )
        success = self._orchestrator.add(mod)
        if success:
            self._moderators[moderator_id] = mod

        event = AliveModeratorEvent(moderator_id=moderator_id)

        await self._producer.send(
            KAFKA_MODERATOR_EVENTS_TOPIC, event.model_dump_json().encode()
        )

    async def _handle_stop_moderator(self, event):
        moderator_id = event["moderator_id"]
        if moderator_id not in self._moderators:
            return

        mod = self._moderators.pop(moderator_id)
        self._orchestrator.remove(mod)
        await mod.close(event["reason"])
