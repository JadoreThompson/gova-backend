from abc import abstractmethod
from typing import AsyncIterator

from engine.models import BaseMessageContext


class BaseChatStream:
    @abstractmethod
    async def __aiter__(self) -> AsyncIterator[BaseMessageContext]: ...
