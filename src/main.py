import logging
import sys
import time
from multiprocessing import Process
from typing import Type, Any

from runners import BaseRunner, ServerRunner, OrchestratorRunner, EventLoggerRunner


logger = logging.getLogger("main")


def silence_keyboard_interrupt(func):
    def wrapper(*args, **kw):
        try:
            return func(*args, **kw)
        except KeyboardInterrupt:
            pass

    return wrapper


def launch_runner(runner_cls: Type[BaseRunner], *args: Any, **kwargs: Any):
    runner_instance = runner_cls(*args, **kwargs)
    runner_instance.run()


def run_remote(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    """
    Launches, runs, and monitors all services in separate processes.
    """
    p_configs: list[tuple[Type[BaseRunner], tuple, dict, str]] = [
        (OrchestratorRunner, (), {"batch_size": 1}, "Discord Orchestrator"),
        (ServerRunner, (), {"host": host, "port": port, "reload": reload}, "Server"),
        (EventLoggerRunner, (), {}, "Event Logger"),
    ]

    ps: list[Process] = []
    for runner_cls, c_args, c_kwargs, name in p_configs:
        proc = Process(
            target=launch_runner, name=name, args=(runner_cls, *c_args), kwargs=c_kwargs
        )
        ps.append(proc)

    for p in ps:
        p.start()
        logger.info(f"Started process '{p.name}' (PID: {p.pid}).")

    try:
        while True:
            for i, p in enumerate(ps):
                if not p.is_alive():
                    logger.critical(
                        f"Process '{p.name}' has died (exit code: {p.exitcode})."
                    )
                    p.join()

                    runner_cls, c_args, c_kwargs, name = p_configs[i]

                    logger.info(f"Relaunching '{name}'...")
                    new_process = Process(
                        target=launch_runner,
                        name=name,
                        args=(runner_cls, *c_args),
                        kwargs=c_kwargs,
                    )
                    ps[i] = new_process
                    new_process.start()
                    logger.critical(
                        f"Process '{new_process.name}' relaunched successfully (New PID: {new_process.pid})."
                    )
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — shutting down all processes.")
    finally:
        for p in ps:
            if p.is_alive():
                logger.info(f"Shutting down process '{p.name}'...")
                p.kill()
                p.join()
        logger.info("All processes shut down.")


if __name__ == "__main__":
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
        raise ValueError("Must provide --mode (e.g., --mode=local or --mode=remote)")

    if mode == "local":
        logger.info("Starting in local mode...")
        server = ServerRunner(host=host, port=port, reload=reload_flag)
        server.run()
    elif mode == "remote":
        logger.info("Starting in remote mode...")
        run_remote(host=host, port=port, reload=reload_flag)
    else:
        logger.error(f"Unknown mode: {mode}")
