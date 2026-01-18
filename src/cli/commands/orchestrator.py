import click

from enums import MessagePlatform
from runners import RunnerConfig, run_runner, ModeratorOrchestratorRunner


@click.group()
def orchestrator():
    return


@orchestrator.command(name="run")
def orchestrator_run():
    config = RunnerConfig(
        cls=ModeratorOrchestratorRunner,
        kwargs={"platform": MessagePlatform.DISCORD},
    )

    run_runner(config)
