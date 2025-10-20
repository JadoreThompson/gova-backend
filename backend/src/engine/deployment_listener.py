import asyncio
import logging
import threading
from json import JSONDecodeError, loads

from kafka import KafkaConsumer, KafkaProducer
from pydantic import ValidationError

from config import (
    DISCORD_BOT_TOKEN,
    KAFKA_BOOTSTRAP_SERVER,
    KAFKA_DEPLOYMENT_EVENTS_TOPIC,
)
from core.events import CreateDeploymentEvent, DeploymentEvent
from engine.base_moderator import BaseModerator
from engine.discord.moderator import DiscordModerator


logger = logging.getLogger("deployment_listener")


class DeploymentListener:
    def __init__(self):
        self._kafka_consumer = KafkaConsumer(
            KAFKA_DEPLOYMENT_EVENTS_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
            auto_offset_reset="latest",
        )
        self._kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVER)
        self._th: threading.Thread | None = None
        self._ev: threading.Event | None = None

    def listen(self) -> None:
        for m in self._kafka_consumer:
            try:
                data = loads(m.value.decode())
                
                event_type = data.get("type")
                print(self._th, self._ev)
                if event_type == "start" and self._ev is None:
                    event = CreateDeploymentEvent(**data)
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
        if event.type == "start":
            return self._handle_start_deployment(event)
        

    def _handle_start_deployment(self, event: CreateDeploymentEvent) -> None:
        mod = DiscordModerator(
            event.deployment_id, event.moderator_id, DISCORD_BOT_TOKEN, event.conf
        )
        self._ev = threading.Event()
        self._th = threading.Thread(
            target=self._target,
            args=(mod,),
            daemon=True,
            name=f"moderator-deployment-thread-{event.deployment_id}",
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
        self._ev.set()
        th.join()
        loop.close()
        
        self._th = None
        self._ev = None

    def _handle_ev(self, loop: asyncio.AbstractEventLoop) -> None:
        self._ev.wait()
        
        loop.stop()

    async def _func(self, moderator: BaseModerator) -> None:
        async with moderator:
            await moderator.run()

    def __del__(self) -> None:
        self.stop()
