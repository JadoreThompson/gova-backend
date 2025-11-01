import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import ValidationError

from config import KAFKA_BOOTSTRAP_SERVER, KAFKA_MODERATOR_EVENTS_TOPIC
from core.enums import CoreEventType, MessagePlatformType, ModeratorEventType, ModeratorStatus
from core.events import (
    CoreEvent,
    DeadModeratorEvent,
    HeartbeatModeratorEvent,
    KillModeratorEvent,
    ModeratorEvent,
    StartModeratorEvent,
)
from engine.discord.action_handler import DiscordActionHandler
from engine.discord.context import DiscordContext, DiscordMessageContext
from engine.discord.message_stream import DiscordMessageStream
from engine.discord.moderator import DiscordModerator
from engine.models import BaseMessageContext
from engine.task_pool import TaskPool
from utils.db import get_datetime
from utils.kafka import dump_model


logger = logging.getLogger("discord_moderator_orchestrator")


class DiscordModeratorOrchestrator:
    def __init__(
        self,
        batch_size: int = 1,
    ):
        self._stream = DiscordMessageStream()
        self._batch_size = batch_size
        self._guild_moderators: dict[
            int, tuple[DiscordModerator, list[BaseMessageContext]]
        ] = {}
        self._moderators: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._task_pool = TaskPool()
        self._kafka_consumer: AIOKafkaConsumer | None = None
        self._kafka_producer: AIOKafkaProducer | None = None
        self._listen_task: asyncio.Task | None = None

    async def run(self):
        """Starts the orchestrator loop.

        Continuously reads messages from the Discord stream and routes them
        to the corresponding moderator. Messages are batched based on
        `batch_size` before moderation is triggered.

        Raises:
            asyncio.CancelledError: If the orchestrator is stopped externally.
        """
        self._task_pool.start()
        self._listen_task = asyncio.create_task(self._listen())
        self._kafka_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVER)
        await self._kafka_producer.start()
        logger.info("Orchestrator alive")

        try:
            async for msg in self._stream:
                guild_id = msg.guild.id
                print(msg)
                if guild_id not in self._guild_moderators:
                    continue

                ctx = DiscordMessageContext(
                    platform=MessagePlatformType.DISCORD,
                    platform_author_id=msg.author.id,
                    platform_message_id=msg.id,
                    content=msg.content,
                    metadata=DiscordContext(
                        channel_id=msg.channel.id, guild_id=msg.guild.id
                    ),
                )
                print(ctx)

                async with self._lock:
                    moderator, batch = self._guild_moderators[guild_id]
                    batch.append(ctx)
                    if len(batch) >= self._batch_size:
                        await self._task_pool.submit(
                            moderator.moderate(batch[0])
                        )  # single for now
                        self._guild_moderators[guild_id] = (moderator, [])
        except Exception as e:
            logger.error(f"{type(e)} - {str(e)}")
        finally:
            await self._task_pool.stop()
            if self._listen_task is not None and not self._listen_task.done():
                self._listen_task.cancel()
                await self._listen_task
            
            await self._kafka_producer.stop()
            logger.info("Orchestrator dead")

    async def _listen(self):
        """
        Continuously listens for moderator lifecycle events on Kafka.
        """
    
        self._kafka_consumer = AIOKafkaConsumer(KAFKA_MODERATOR_EVENTS_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP_SERVER)
        await self._kafka_consumer.start()
        
        try:
            async for msg in self._kafka_consumer:
                try:
                    data = json.loads(msg.value.decode())
                    ev = CoreEvent(**data)
                    ev_type = ev.data.get("type")
                    logger.info(f"Received event type '{ev_type}'")

                    if ev_type == ModeratorEventType.START:
                        await self._handle_start_event(StartModeratorEvent(**ev.data))
                    if ev_type == ModeratorEventType.HEARTBEAT:
                        await self._handle_heartbeat_event(HeartbeatModeratorEvent(**ev.data))
                    elif ev_type == ModeratorEventType.KILL:
                        await self._handle_kill_event(KillModeratorEvent(**ev.data))

                except (ValidationError, json.JSONDecodeError):
                    pass
                except Exception as e:
                    logger.error(f"{type(e)} - {str(e)}")
        finally:
            await self._kafka_consumer.stop()

    async def _handle_start_event(self, event: StartModeratorEvent) -> None:
        async with self._lock:
            if event.moderator_id in self._moderators:
                logger.warning(f"Moderator {event.moderator_id} already exists")
                return
            print(1)
            moderator = DiscordModerator(
                moderator_id=event.moderator_id,
                action_handler=DiscordActionHandler(self._stream.client),
                kafka_producer=self._kafka_producer,
                task_pool=self._task_pool,
                config=event.conf,
            )
            print(2)

            guild_id = event.conf.guild_id
            self._guild_moderators[guild_id] = (moderator, [])
            self._moderators[event.moderator_id] = guild_id

            print(3)
            await moderator.start()
            print(4)

        logger.info(f"Moderator {event.moderator_id} launched with config")

    async def _handle_heartbeat_event(self, event: HeartbeatModeratorEvent) -> None:
        """Handles incoming heartbeat events from moderators or servers.

        This method ensures that moderators remain active and synchronized with
        the orchestrator. When a heartbeat is received from a `server` role, the
        orchestrator validates the moderator's state and, if healthy, echoes a
        moderator-level heartbeat event back to Kafka. Otherwise, the moderator
        is removed from active tracking.

        Args:
            event (HeartbeatModeratorEvent): The heartbeat event received
                from Kafka, emitted by a moderator or its managing server.
        """
        if event.role != "server":
            return

        async with self._lock:
            if event.moderator_id not in self._moderators:
                return

            guild_id = self._moderators[event.moderator_id]
            moderator, _ = self._guild_moderators[guild_id]

        if moderator.status == ModeratorStatus.ONLINE:
            hb = HeartbeatModeratorEvent(
                moderator_id=event.moderator_id,
                role="moderator",
                timestamp=get_datetime().timestamp(),
            )
            await self._kafka_producer.send(
                KAFKA_MODERATOR_EVENTS_TOPIC,
                dump_model(CoreEvent(type=CoreEventType.MODERATOR_EVENT, data=hb)),
            )
            logger.debug(f"Heartbeat acknowledged for moderator {event.moderator_id}")

        else:
            async with self._lock:
                if event.moderator_id not in self._moderators:
                    return

                guild_id = self._moderators[event.moderator_id]
                del self._moderators[event.moderator_id]
                del self._guild_moderators[guild_id]

                logger.warning(
                    f"Removed dead moderator {event.moderator_id} (guild {guild_id}) "
                    "after failed heartbeat check."
                )

    async def _handle_kill_event(self, event: KillModeratorEvent) -> None:
        """Handles a moderator kill event.

        Stops the corresponding moderator and removes it from the active pool.
        Publishes a `DeadModeratorEvent` to Kafka.

        Args:
            event (KillModeratorEvent): The kill event to process.
        """
        logger.info(f"Handling '{event.type}'")

        async with self._lock:
            if event.moderator_id not in self._moderators:
                return

            guild_id = self._moderators[event.moderator_id]

            moderator, _ = self._guild_moderators[guild_id]
            asyncio.create_task(moderator.stop())

            del self._moderators[event.moderator_id]
            del self._guild_moderators[guild_id]

        event = DeadModeratorEvent(
            moderator_id=moderator.moderator_id, reason=event.reason
        )
        logger.info(f"Emitting '{event.type}'")
        await self._kafka_producer.send(
            KAFKA_MODERATOR_EVENTS_TOPIC,
            dump_model(CoreEvent(type=CoreEventType.MODERATOR_EVENT, data=event)),
        )
        logger.info(f"'{event.type}' emitted.")
