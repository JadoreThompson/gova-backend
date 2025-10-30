import asyncio
import logging
import time
from multiprocessing import Process
from types import CoroutineType
from typing import Any, Callable

import uvicorn

from engine.deployment_listener import DeploymentListener


logger = logging.getLogger("main")


def run_sever():
    uvicorn.run("server.app:app", host="localhost", port=8000)


async def run_deployment_listener() -> None:
    listener = DeploymentListener()
    listener.listen()


def asyncio_run(func: Callable[[], CoroutineType[Any, Any, Any]]) -> None:
    asyncio.run(func())


def main() -> None:
    pargs = (
        (asyncio_run, (run_deployment_listener,), {}, "Deployment Listener"),
        (run_sever, (), {}, "Server"),
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

                    logger.critical(
                        f"Process '{p.name}' has been relaunced successfully."
                    )

            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutting down all processes.")

        for p in ps:
            logger.info(f"Process '{p.name}' is shutting down.")
            p.kill()
            p.join()
            logger.info(f"Process '{p.name}' shut down successfully.")

        logger.info("All processes shut down.")


async def test():
    from config import DISCORD_BOT_TOKEN
    from engine.discord.actions import (
        BanActionDefinition,
        MuteActionDefinition,
        KickActionDefinition,
    )
    from engine.discord.config import DiscordConfig
    from engine.discord.moderator import DiscordModerator

    mod = DiscordModerator(
        "f22de979-2ca4-4163-b974-b018359ba4b4",
        "0e55d78b-ec79-400a-8df9-1d077ebfafc2",
        logger=logging.getLogger("test-discord-moderator"),
        token=DISCORD_BOT_TOKEN,
        config=DiscordConfig(
            guild_id=1334317047995432980,
            allowed_channels=[1334317050629460114],
            allowed_actions=[
                MuteActionDefinition(requires_approval=False),
                KickActionDefinition(requires_approval=True),
            ],
        ),
    )
    async with mod:
        await mod.moderate()


if __name__ == "__main__":
    import sys

    args = sys.argv

    if len(args) == 1 or args[1] == "0":
        uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=True)
    elif args[1] == "1":
        main()
    elif args[1] == "2":
        asyncio.run(test())
