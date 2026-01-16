import click

from runners import RunnerConfig, run_runner, EventHandlerRunner


@click.group()
def event_handler():
    return


@event_handler.command(name="run")
def event_handler_run():
    config = RunnerConfig(cls=EventHandlerRunner)
    run_runner(config)
