import asyncio
import logging
import time
from multiprocessing import Process

import uvicorn

from engine.discord.orchestrator import DiscordModeratorOrchestrator


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


@silence_keyboard_interrupt
def run_remote(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    pargs = (
        (run_orchestrator, (), {}, "Discord Orchestrator"),
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
