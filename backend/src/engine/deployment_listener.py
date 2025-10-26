import asyncio
import logging
from json import JSONDecodeError, loads
from multiprocessing import Event, Process
from multiprocessing.synchronize import Event as MPEventType
from uuid import UUID

from kafka import KafkaConsumer, KafkaProducer
from pydantic import ValidationError
from sqlalchemy import select

from db_models import ModeratorDeployments, Moderators, Users
from utils.db import get_db_sess_sync
from config import (
    DISCORD_BOT_TOKEN,
    KAFKA_BOOTSTRAP_SERVER,
    KAFKA_DEPLOYMENT_EVENTS_TOPIC,
)
from core.events import CreateDeploymentEvent, DeploymentEvent
from engine.discord.moderator import DiscordModerator
from server.services import EmailService


logger = logging.getLogger("deployment_listener")


class DeploymentEnvironment:
    def __init__(self, event: CreateDeploymentEvent, stop_event: MPEventType) -> None:
        self._event = event
        self.stop_event = stop_event

    def run(self) -> None:
        asyncio.run(self._handle_environment())

    async def _handle_environment(self) -> None:
        mod = DiscordModerator(
            self._event.deployment_id,
            self._event.moderator_id,
            logger=logging.getLogger(f"discord-moderator-{self._event.moderator_id}"),
            token=DISCORD_BOT_TOKEN,
            config=self._event.conf,
        )

        async with mod:
            task = asyncio.create_task(mod.run())

            try:
                while not task.done() and not self.stop_event.is_set():
                    await asyncio.sleep(0.1)
            finally:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        logger.info("Deployment stopped")


class DeploymentListener:
    def __init__(self):
        self._kafka_consumer = KafkaConsumer(
            KAFKA_DEPLOYMENT_EVENTS_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
            auto_offset_reset="latest",
        )
        self._kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVER)
        self._deployments: dict[UUID, tuple[Process, MPEventType]] = {}
        self._email_service = EmailService("No-Reply", "no-reply@gova.chat")

    def listen(self) -> None:
        for m in self._kafka_consumer:
            try:
                data = loads(m.value.decode())

                event_type = data.get("type")
                if event_type == "start":
                    event = CreateDeploymentEvent(**data)
                    self._handle_event(event)
            except (ValidationError, JSONDecodeError):
                pass

    def stop(self) -> None:
        for _, (ps, ev) in self._deployments.items():
            if ps.is_alive():
                ev.set()
                ps.join(timeout=10)

    def _handle_event(self, event: DeploymentEvent) -> None:
        if event.type == "start":
            return self._handle_start_deployment(event)

    def _handle_start_deployment(self, event: CreateDeploymentEvent) -> None:
        stop_ev = Event()
        env = DeploymentEnvironment(event, stop_ev)
        ps = Process(
            target=env.run,
            args=(),
            name=f"deployment-process-{event.deployment_id}",
        )
        self._deployments[event.deployment_id] = (ps, stop_ev)
        ps.start()
        self._send_email(event.deployment_id)

    def _send_email(self, deployment_id: UUID) -> None:
        with get_db_sess_sync() as db_sess:
            em = db_sess.scalar(
                select(Users.email)
                .select_from(ModeratorDeployments)
                .join(Moderators, Moderators.moderator_id == ModeratorDeployments.moderator_id)
                .join(Users, Users.user_id == Moderators.user_id)
                .where(ModeratorDeployments.deployment_id == deployment_id)
            )

        self._email_service.send_email_sync(em, "New Deployment", "A new deployment has been initiated.")

    def __del__(self) -> None:
        self.stop()
