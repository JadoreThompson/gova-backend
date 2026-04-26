import uuid
from engine.contexts.discord import DiscordMessageContext
from engine.conversation.conversation import Conversation


class DiscordConversation(Conversation):
    def __init__(self, topic: str, channel_id: int):
        super().__init__(topic)
        self._channel_id = channel_id
        self.messages: list[DiscordMessageContext] = []

    @property
    def channel_id(self) -> int:
        return self._channel_id
    
    def to_dict(self):
        return {
            "conversation_id": self.conversation_id,
            "channel_id": self.channel_id,
            "messages": self.messages,
        }
