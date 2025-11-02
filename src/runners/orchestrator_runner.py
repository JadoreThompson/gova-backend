import asyncio
from .base_runner import BaseRunner
from engine.discord.orchestrator import DiscordModeratorOrchestrator

class OrchestratorRunner(BaseRunner):
    """Runs the Discord Moderator Orchestrator."""

    def __init__(self, batch_size: int = 1, batch_interval_seconds: int = 5):
        super().__init__("Discord Orchestrator")
        self.batch_size = batch_size
        self.batch_interval_seconds = batch_interval_seconds

    def run(self) -> None:
        """Initializes and starts the orchestrator's main loop."""
        orch = DiscordModeratorOrchestrator(
            batch_size=self.batch_size,
            batch_interval_seconds=self.batch_interval_seconds
        )
        asyncio.run(orch.run())