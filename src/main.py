import logging
import sys
import time
from multiprocessing import Process
from typing import Any

from runners import (
    APIRunner,
    OrchestratorRunner,
    EventLoggerRunner,
    run_runner,
)
from runners.runner_config import RunnerConfig


logger = logging.getLogger("main")


def run_remote(host: str = "0.0.0.0", port: int = 8000, reload: bool = True) -> None:
    """
    Launches, runs, and monitors all services in separate processes.
    Restarts any process that exits unexpectedly.
    """
    runner_configs: list[RunnerConfig] = [
        RunnerConfig(
            cls=OrchestratorRunner,
            name="Discord Orchestrator",
            kwargs={"batch_size": 1},
        ),
        RunnerConfig(
            cls=APIRunner,
            name="Server",
            kwargs={"host": host, "port": port, "reload": reload},
        ),
        RunnerConfig(
            cls=EventLoggerRunner,
            name="Event Logger",
        ),
    ]

    processes: list[Process] = []

    for rc in runner_configs:
        proc = Process(
            target=run_runner,
            name=rc.name,
            args=(rc,),
        )
        processes.append(proc)

    for p in processes:
        p.start()
        logger.info("Started process '%s' (PID: %s).", p.name, p.pid)

    try:
        while True:
            for i, p in enumerate(processes):
                if not p.is_alive():
                    logger.critical(
                        "Process '%s' died (exit code: %s).",
                        p.name,
                        p.exitcode,
                    )
                    p.join()

                    rc = runner_configs[i]
                    logger.info("Relaunching '%s'...", rc.name)

                    new_proc = Process(
                        target=run_runner,
                        name=rc.name,
                        args=(rc,),
                    )
                    processes[i] = new_proc
                    new_proc.start()

                    logger.critical(
                        "Process '%s' relaunched (PID: %s).",
                        new_proc.name,
                        new_proc.pid,
                    )
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — shutting down all processes.")
    finally:
        for p in processes:
            if p.is_alive():
                logger.info("Shutting down process '%s'...", p.name)
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
            mode = arg.split("=", 1)[1]
        elif arg.startswith("--host="):
            host = arg.split("=", 1)[1]
        elif arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
        elif arg.startswith("--reload="):
            reload_flag = arg.split("=", 1)[1].lower() == "true"

    if not mode:
        raise ValueError("Must provide --mode (e.g., --mode=local or --mode=remote)")

    if mode == "local":
        logger.info("Starting in local mode...")
        run_runner(
            RunnerConfig(
                cls=APIRunner,
                name="Server",
                kwargs={"host": host, "port": port, "reload": reload_flag},
            )
        )

    elif mode == "remote":
        logger.info("Starting in remote mode...")
        run_remote(host=host, port=port, reload=reload_flag)

    else:
        raise ValueError(f"Unknown mode: {mode}")
