import asyncio
import heapq
from typing import Generic, TypeVar

from engineV2.contexts.discord import DiscordMessageContext
from engineV2.moderators.discord import DiscordModerator

M = TypeVar("M", bound=DiscordModerator)
C = TypeVar("C", bound=DiscordMessageContext)


class ModeratorContextGroup(Generic[M, C]):
    """
    Holds a DiscordModerator, a list of message contexts, and a lock to synchronize access.
    """

    def __init__(
        self,
        moderator: M | None = None,
        messages: list[C] | None = None,
        lock: asyncio.Lock | None = None,
    ):
        self.moderator = moderator
        self.messages = messages or []
        self.lock = lock or asyncio.Lock()
        self._heap: list[tuple[int, list[C]]] = []
