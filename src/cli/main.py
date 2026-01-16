import click
from cli.commands import http, orchestrator, event_handler


@click.group()
def cli():
    pass


cli.add_command(http)
cli.add_command(orchestrator)
cli.add_command(event_handler)
