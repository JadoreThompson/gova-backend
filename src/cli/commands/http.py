import logging
import click

from runners import RunnerConfig, APIRunner, run_runner


@click.group()
def http():
    return


@http.command(name="run")
def http_run():
    config = RunnerConfig(
        cls=APIRunner,
        name="Server",
        kwargs={"host": "localhost", "port": 8000, "reload": False},
    )

    run_runner(config)
