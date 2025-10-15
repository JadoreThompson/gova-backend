from abc import abstractmethod
from typing import AsyncIterator

from engine.models import MessageContext


class BaseChatStream:
    @abstractmethod
    async def __aiter__(self) -> AsyncIterator[MessageContext]: ...
