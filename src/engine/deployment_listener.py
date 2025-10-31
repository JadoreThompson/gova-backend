import asyncio
import json
import logging
from multiprocessing import Event, Process
from multiprocessing.synchronize import Event as MPEventType
from uuid import UUID

from hcloud import Client as HetznerClient
from hcloud.images import Image
from hcloud.ssh_keys import SSHKey
from hcloud.server_types import ServerType
from kafka import KafkaConsumer, KafkaProducer
from pydantic import ValidationError
from sentence_transformers import SentenceTransformer
from sqlalchemy import insert, select, update

from core.enums import ModeratorDeploymentEventType
from core.events import (
    ErrorModeratorDeploymentEvent,
    EvaluationModeratorDeploymentEvent,
    StartModeratorDeploymentEvent,
    ModeratorDeploymentEvent,
    StartedModeratorDeploymentEvent,
    StopModeratorDeploymentEvent,
)
from core.services import EmailService
from config import (
    DISCORD_BOT_TOKEN,
    HETZNER_API_KEY,
    HETZNER_SNAPSHOT_ID,
    KAFKA_BOOTSTRAP_SERVER,
    KAFKA_DEPLOYMENT_EVENTS_TOPIC,
)
from db_models import (
    Messages,
    MessagesEvaluations,
    ModeratorDeployments,
    Moderators,
    Users,
)
from engine.discord.moderator import DiscordModerator
from engine.event_logger import ModeratorDeploymentEventLogger
from utils.db import get_db_sess_sync, smaker_sync


logger = logging.getLogger("deployment_listener")


class DeploymentEnvironment:
    def __init__(
        self,
        event: StartModeratorDeploymentEvent,
        stop_event: MPEventType,
        event_logger: ModeratorDeploymentEventLogger | None = None,
    ) -> None:
        self._event = event
        self.stop_event = stop_event
        self._event_logger = event_logger

    def run(self) -> None:
        asyncio.run(self._handle_environment())

    async def _handle_environment(self) -> None:
        mod = DiscordModerator(
            self._event.deployment_id,
            self._event.moderator_id,
            logger=logging.getLogger(f"discord-moderator-{self._event.moderator_id}"),
            token=DISCORD_BOT_TOKEN,
            config=self._event.moderator_conf,
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
    _class_map: dict[ModeratorDeploymentEventType, ModeratorDeploymentEvent] = {
        ModeratorDeploymentEventType.DEPLOYMENT_START: StartModeratorDeploymentEvent,
        ModeratorDeploymentEventType.DEPLOYMENT_ALIVE: StartedModeratorDeploymentEvent,
        ModeratorDeploymentEventType.DEPLOYMENT_STOP: StopModeratorDeploymentEvent,
        ModeratorDeploymentEventType.ERROR: ErrorModeratorDeploymentEvent,
    }

    def __init__(self):
        self._kafka_consumer = KafkaConsumer(
            KAFKA_DEPLOYMENT_EVENTS_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
            auto_offset_reset="latest",
        )
        self._kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVER)
        self._local_deployments: dict[UUID, tuple[Process, MPEventType]] = {}
        self._email_service = EmailService("No-Reply", "no-reply@gova.chat")
        self._event_handlers = {
            ModeratorDeploymentEventType.DEPLOYMENT_START: self._handle_start_deployment_remote,
            ModeratorDeploymentEventType.DEPLOYMENT_STOP: self._handle_stop_deployment,
            ModeratorDeploymentEventType.DEPLOYMENT_DEAD: self._handle_stopped_deployment_remote,
        }
        self._event_logger: ModeratorDeploymentEventLogger | None = None
        self._embedding_model: SentenceTransformer | None = None
        self._hetzner = HetznerClient(token=HETZNER_API_KEY)

    def listen(self) -> None:
        self._embedding_model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

        for m in self._kafka_consumer:
            try:
                data = json.loads(m.value.decode())
                event_data = data.get("data")
                event_type = event_data.get("type")
                print("Received event type", event_type)

                cls = self._class_map.get(event_type, ModeratorDeploymentEvent)
                event = cls(**event_data)
                if event is not None:
                    handler = self._event_handlers.get(event.type)
                    if handler is not None:
                        handler(event)
            except (ValidationError, json.JSONDecodeError):
                pass

    def stop(self) -> None:
        for _, (ps, ev) in self._local_deployments.items():
            if ps.is_alive():
                ev.set()
                ps.join(timeout=30)

    def _handle_start_deployment_local(
        self, event: StartModeratorDeploymentEvent
    ) -> None:
        stop_ev = Event()
        env = DeploymentEnvironment(event, stop_ev)
        ps = Process(
            target=env.run,
            args=(),
            name=f"deployment-process-{event.deployment_id}",
        )
        self._local_deployments[event.deployment_id] = (ps, stop_ev)
        ps.start()
        self._send_email(
            event.deployment_id,
            "New Deployment",
            "A new deployment has been initiated.",
        )

    def _handle_start_deployment_remote(
        self, event: StartedModeratorDeploymentEvent
    ) -> None:
        server_name = f"mod-deployment-{event.deployment_id}"
        logger.info(f"Creating Hetzner server '{server_name}'")

        rsp = self._hetzner.servers.create(
            name=server_name,
            server_type=ServerType(name="cx23"),
            image=Image(id=HETZNER_SNAPSHOT_ID),
            ssh_keys=[SSHKey("master")],
            user_data=f"""#cloud-config
    runcmd:
    - cd /backend
    - git pull
    - uv sync
    - uv run src/main.py --mode=moderator --deployment-id={event.deployment_id}
    """,
        )

        with get_db_sess_sync() as db_sess:
            db_sess.execute(
                update(ModeratorDeployments).values(server_id=str(rsp.server.id))
            )
            db_sess.commit()

        self._send_email(
            event.deployment_id,
            "New Deployment",
            f"Your moderator is being deployed.",
        )

    def _handle_stop_deployment(self, event: StopModeratorDeploymentEvent) -> None:
        self._send_email(
            event.deployment_id,
            "Stop deploment",
            "We've got your request. Stopping your deployment now.",
        )

    def _handle_stopped_deployment_local(self, event: ModeratorDeploymentEvent) -> None:
        self._send_email(
            event.deployment_id,
            "Deplyoment Stopped",
            "We've stopped your deployment.",
        )

    def _handle_stopped_deployment_remote(
        self, event: ModeratorDeploymentEvent
    ) -> None:
        with get_db_sess_sync() as db_sess:
            server_id = db_sess.scalar(
                select(ModeratorDeployments.server_id).where(
                    ModeratorDeployments.deployment_id == event.deployment_id
                )
            )

        if server_id is None:
            logger.warning(
                f"Server id for deployment '{event.deployment_id}' not found."
            )
            return

        server_id = int(server_id)

        try:
            server = self._hetzner.servers.get_by_id(server_id)
            if server is not None:
                logger.info(f"Deleting Hetzner server '{server.name}' (ID {server_id})")
                self._hetzner.servers.delete(server)
                self._send_email(
                    event.deployment_id,
                    "Deployment Stopped",
                    f"Hetzner server '{server.name}' has been fully deleted.",
                )
            else:
                logger.warning(f"Hetzner server with ID {server_id} not found.")
        except Exception as e:
            logger.error(f"Failed to delete Hetzner server {server_id}: {e}")

    def _handle_message_evaluation(
        self, event: EvaluationModeratorDeploymentEvent
    ) -> None:
        ctx = event.context
        embedding = self._embedding_model.encode([ctx.content])[0]

        with get_db_sess_sync() as db_sess:
            moderator_id = db_sess.scalar(
                select(ModeratorDeployments.moderator_id).where(
                    ModeratorDeployments.deployment_id == event.deployment_id
                )
            )
            message_id = db_sess.scalar(
                insert(Messages)
                .values(
                    moderator_id=moderator_id,
                    deployment_id=event.deployment_id,
                    content=ctx.content,
                    platform=ctx.platform.value,
                )
                .returning(Messages.message_id)
            )

            records = [
                {
                    "message_id": message_id,
                    "embedding": embedding,
                    "topic": teval.topic,
                    "topic_score": teval.topic_score,
                }
                for teval in event.evaluation.topic_evaluations
            ]

            db_sess.execute(insert(MessagesEvaluations), records)
            db_sess.commit()

    def _send_email(self, deployment_id: UUID, subject: str, body: str) -> None:
        with get_db_sess_sync() as db_sess:
            em = db_sess.scalar(
                select(Users.email)
                .select_from(ModeratorDeployments)
                .join(
                    Moderators,
                    Moderators.moderator_id == ModeratorDeployments.moderator_id,
                )
                .join(Users, Users.user_id == Moderators.user_id)
                .where(ModeratorDeployments.deployment_id == deployment_id)
            )

        self._email_service.send_email_sync(em, subject, body)

    def __del__(self) -> None:
        self.stop()
