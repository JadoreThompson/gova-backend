import uuid
from engine.contexts.discord import DiscordMessageContext


class DiscordConversation:
    def __init__(
        self,
        topic: str,
        channel_id: str,
        messages: list[DiscordMessageContext] | None = None,
    ):
        self._conversation_id = uuid.uuid4()
        self._channel_id = channel_id
        self._topic = topic
        self.messages: list[DiscordMessageContext] = (
            messages if messages is not None else []
        )

    @property
    def conversation_id(self) -> uuid.UUID:
        return self._conversation_id

    @property
    def channel_id(self) -> str:
        return self._channel_id

    @property
    def topic(self) -> str:
        return self._topic

    def to_dict(self):
        return {
            "conversation_id": self.conversation_id,
            "channel_id": self.channel_id,
            "messages": self.messages,
        }
