import asyncio
import logging
import time
from multiprocessing import Process
from types import CoroutineType
from typing import Any, Callable

from sqlalchemy import select
import uvicorn

from db_models import ModeratorDeployments
from engine.deployment_listener import DeploymentListener
from utils.db import get_db_sess_sync

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


async def run_deployment_listener() -> None:
    """Run the Kafka deployment listener."""
    listener = DeploymentListener()
    listener.listen()


def asyncio_run(func: Callable[[], CoroutineType[Any, Any, Any]]) -> None:
    asyncio.run(func())


@silence_keyboard_interrupt
def run_remote(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    pargs = (
        (asyncio_run, (run_deployment_listener,), {}, "Deployment Listener"),
        (run_server, (host, port, reload), {}, "Server"),
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


@silence_keyboard_interrupt
def run_moderator(deployment_id: str):
    """Run a makeshift moderator function for testing."""
    from config import DISCORD_BOT_TOKEN
    from engine.discord.config import DiscordConfig
    from engine.discord.moderator import DiscordModerator

    async def runner(mod: DiscordModerator):
        async with mod:
            await mod.moderate()

    with get_db_sess_sync() as db_sess:
        dep = db_sess.scalar(
            select(ModeratorDeployments).where(
                ModeratorDeployments.deployment_id == deployment_id
            )
        )
        if dep is None:
            logger.info(f"Faild to find deployment '{deployment_id}'")
            return

        mod = DiscordModerator(
            deployment_id,
            dep.moderator_id,
            logger=logging.getLogger(f"moderator-{deployment_id}"),
            token=DISCORD_BOT_TOKEN,
            config=DiscordConfig(**dep.conf),
        )

    asyncio.run(runner(mod))


if __name__ == "__main__":
    import sys

    mode = ""
    host = "0.0.0.0"
    port = 8000
    reload_flag = True
    deployment_id = None

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
        elif arg.startswith("--deployment-id="):
            deployment_id = arg.split("=")[1]

    if not mode:
        raise ValueError("Must provide --mode")
    elif mode == "local":
        run_server(host=host, port=port, reload=reload_flag)
    elif mode == "remote":
        run_remote(host=host, port=port, reload=reload_flag)
    elif mode == "moderator":
        if not deployment_id:
            raise ValueError("Must provide --deployment-id for moderator mode")
        run_moderator(deployment_id)
