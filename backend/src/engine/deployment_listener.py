import asyncio
import threading
from json import JSONDecodeError, loads

from pydantic import ValidationError
from sqlalchemy import select

from db_models import ModeratorDeployments
from engine.base_moderator import BaseModerator
from engine.discord.config import DiscordConfig
from engine.discord.moderator import DiscordModerator
from kafka import KafkaConsumer

from config import (
    DISCORD_BOT_TOKEN,
    KAFKA_DEPLOYMENT_EVENTS_TOPIC,
    KAFKA_HOST,
    KAFKA_PORT,
)
from core.events import DeploymentEvent
from engine.discord.stream import DiscordStream
from utils.db import get_db_sess_sync


class DeploymentListener:
    def __init__(self):
        self._kafka_consumer = KafkaConsumer(
            KAFKA_DEPLOYMENT_EVENTS_TOPIC,
            bootstrap_servers=f"{KAFKA_HOST}:{KAFKA_PORT}",
            auto_offset_reset="latest",
        )
        self._th: threading.Thread | None = None
        self._ev: threading.Event | None = None

    def listen(self) -> None:
        for m in self._kafka_consumer:
            try:
                event = DeploymentEvent(**loads(m.value.decode()))
                if not self._ev:
                    self._handle_event(event)
            except (ValidationError, JSONDecodeError):
                pass

    def stop(self) -> None:
        if self._ev:
            self._ev.set()
            self._th.join()
            self._ev = None
            self._th = None

    def _handle_event(self, event: DeploymentEvent) -> None:
        with get_db_sess_sync() as db_sess:
            res = db_sess.execute(
                select(
                    ModeratorDeployments.moderator_id, ModeratorDeployments.conf
                ).where(ModeratorDeployments.deployment_id == event.deployment_id)
            )
            mid, conf = res.first()

        config = DiscordConfig(**conf)
        stream = DiscordStream(
            DISCORD_BOT_TOKEN, config.guild_id, config.allowed_channels.copy()
        )
        mod = DiscordModerator(mid, stream, config)
        self._ev = threading.Event()
        self._th = threading.Thread(
            target=self._target,
            args=(mod,),
            daemon=True,
            name="moderator-deployment-thread",
        )
        self._th.start()

    def _target(self, mod: DiscordModerator) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        th = threading.Thread(
            target=self._handle_ev, args=(loop,), daemon=True, name="ev-thread"
        )
        th.start()

        loop.run_until_complete(self._func(mod))
        th.join()
        loop.close()

    def _handle_ev(self, loop: asyncio.AbstractEventLoop) -> None:
        self._ev.wait()
        loop.stop()

    async def _func(self, moderator: BaseModerator) -> None:
        async with moderator:
            await moderator.moderate()

    def __del__(self) -> None:
        self.stop()
