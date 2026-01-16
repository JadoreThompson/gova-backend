import asyncio

from services.event_handlers.moderator import ModeratorEventHandler
from .base_runner import BaseRunner


class EventHandlerRunner(BaseRunner):
    def run(self):
        handler = ModeratorEventHandler(batch_size=100)
        asyncio.run(handler.run())
