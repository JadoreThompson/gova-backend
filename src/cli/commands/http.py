import logging
import click

from config import IS_PRODUCTION
from runners import RunnerConfig, APIRunner, run_runner


@click.group()
def http():
    return


@http.command(name="run")
def http_run():
    config = RunnerConfig(
        cls=APIRunner,
        name="Server",
        kwargs={
            "host": "0.0.0.0" if IS_PRODUCTION else "localhost",
            "port": 8000,
            "reload": False,
        },
    )

    run_runner(config)
