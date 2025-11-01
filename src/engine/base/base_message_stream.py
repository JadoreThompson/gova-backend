from abc import ABC, abstractmethod
from typing import AsyncIterator, Generic, TypeVar

T = TypeVar("T")


class BaseMessageStream(Generic[T], ABC):
    @abstractmethod
    async def __aiter__(self) -> AsyncIterator[T]: ...
