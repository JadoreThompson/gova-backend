import uuid
from abc import ABC, abstractmethod


class Conversation(ABC):
    def __init__(self, topic: str):
        self._conversation_id: uuid.UUID = uuid.uuid4()
        self._topic = topic

    @property
    def conversation_id(self) -> uuid.UUID:
        return self._conversation_id

    @property
    def topic(self) -> str:
        return self._topic

    @abstractmethod
    def to_dict(self) -> dict: ...
