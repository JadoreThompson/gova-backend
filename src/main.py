import asyncio
import json
import logging
import time
from multiprocessing import Process

import uvicorn
from kafka import KafkaConsumer

from config import KAFKA_BOOTSTRAP_SERVER, KAFKA_MODERATOR_EVENTS_TOPIC
from core.enums import ModeratorEventType
from core.events import (
    DeadModeratorEvent,
    EvaluationCreatedModeratorEvent,
    CoreEvent,
    ActionPerformedModeratorEvent,
    KillModeratorEvent,
    ModeratorEvent,
    StartModeratorEvent,
)
from engine.discord.context import DiscordMessageContext
from engine.discord.models import DiscordAction
from engine.discord.orchestrator import DiscordModeratorOrchestrator
from engine.moderator_event_logger import ModeratorEventLogger
from utils.db import smaker_sync


logger = logging.getLogger("main")


def silence_keyboard_interrupt(func):
    def wrapper(*args, **kw):
        try:
            res = func(*args, **kw)
            return res
        except KeyboardInterrupt:
            pass

    return wrapper


# Base runners


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    """Run only the FastAPI server."""
    uvicorn.run("server.app:app", host=host, port=port, reload=reload)


def run_orchestrator(batch_size: int = 1):
    orch = DiscordModeratorOrchestrator(batch_size)
    asyncio.run(orch.run())


def run_event_logger():
    db = smaker_sync()
    moderator_logger = ModeratorEventLogger(db)
    consumer = KafkaConsumer(
        KAFKA_MODERATOR_EVENTS_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP_SERVER
    )

    event_class_map = {
        ModeratorEventType.START: StartModeratorEvent,
        ModeratorEventType.ALIVE: ModeratorEvent,
        ModeratorEventType.KILL: KillModeratorEvent,
        ModeratorEventType.DEAD: DeadModeratorEvent,
        ModeratorEventType.ACTION_PERFORMED: ActionPerformedModeratorEvent[
            DiscordAction
        ],
        ModeratorEventType.EVALUATION_CREATED: EvaluationCreatedModeratorEvent[
            DiscordAction, DiscordMessageContext
        ],
    }

    for msg in consumer:
        try:
            data = json.loads(msg.value.decode())
            ev = CoreEvent(**data)
            ev_type = ev.data.get("type")

            event_cls = event_class_map.get(ev_type)
            if event_cls:
                parsed_ev = event_cls(**ev.data)
                moderator_logger.log_event(parsed_ev)
            else:
                logger.warning(f"Unhandled event type: {ev_type}")

        except Exception as e:
            logger.exception(f"Error processing event: {e}")


@silence_keyboard_interrupt
def run_remote(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    pargs = (
        (run_orchestrator, (), {}, "Discord Orchestrator"),
        (run_server, (host, port, reload), {}, "Server"),
        (run_event_logger, (), {}, "Event Logger"),
    )

    ps = [
        Process(target=target, args=args, kwargs=kw, name=name)
        for target, args, kw, name in pargs
    ]

    for p in ps:
        p.start()

    try:
        while True:
            for idx, p in enumerate(ps):
                if not p.is_alive():
                    logger.critical(f"Process '{p.name}' has died.")
                    p.kill()
                    p.join()
                    target, args, kw, name = pargs[idx]
                    ps[idx] = Process(target=target, args=args, kwargs=kw, name=name)
                    ps[idx].start()
                    logger.critical(f"Process '{p.name}' relaunched successfully.")
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — shutting down all processes.")
    finally:
        for p in ps:
            logger.info(f"Shutting down process '{p.name}'...")
            p.kill()
            p.join()
        logger.info("All processes shut down.")


if __name__ == "__main__":
    import sys

    mode = ""
    host = "0.0.0.0"
    port = 8000
    reload_flag = True

    args = sys.argv[1:]
    for arg in args:
        if arg.startswith("--mode="):
            mode = arg.split("=")[1]
        elif arg.startswith("--host="):
            host = arg.split("=")[1]
        elif arg.startswith("--port="):
            port = int(arg.split("=")[1])
        elif arg.startswith("--reload="):
            reload_flag = arg.split("=")[1].lower() == "true"

    if not mode:
        raise ValueError("Must provide --mode")
    elif mode == "local":
        run_server(host=host, port=port, reload=reload_flag)
    elif mode == "remote":
        run_remote(host=host, port=port, reload=reload_flag)
