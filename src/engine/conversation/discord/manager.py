from engine.contexts.discord import DiscordMessageContext
from .conversation import DiscordConversation
from engine.agents.conversation_thread import (
    ConversationThreadGroup,
    ConversationCommandType,
    NewConversationCommand,
    AddToConversationCommand,
)
import uuid


class DiscordConversationManager:
    def __init__(self):
        self.conversations: dict[str, DiscordConversation] = {}
        self.auto_prune = True

    def get_conversation(self, conversation_id: str) -> DiscordConversation | None:
        return self.conversations.get(conversation_id)

    def add_conversation(self, conversation: DiscordConversation) -> None:
        self.conversations[conversation.conversation_id] = conversation

    def remove_conversation(self, conversation_id: str) -> None:
        if conversation_id in self.conversations:
            self.conversations.pop(conversation_id)

    def apply_thread_groups(
        self,
        groups: list[ConversationThreadGroup],
        message_contexts: list[DiscordMessageContext],
    ) -> list[uuid.UUID]:
        """
        Applies agent output to conversation state.

        Returns:
            list[UUID]: list of created conversation_ids
        """
        conversation_ids: list[uuid.UUID] = []

        for group in groups:
            indices = group.indicies
            command = group.command
            messages = [message_contexts[i] for i in indices]

            if command.type == ConversationCommandType.NEW_CONVERSATION:
                cmd: NewConversationCommand = command
                conversation = DiscordConversation(
                    topic=cmd.topic,
                    channel_id=messages[0].channel_id,
                    messages=messages,
                )

                self.add_conversation(conversation)
                conversation_ids.append(conversation.conversation_id)
            elif command.type == ConversationCommandType.ADD_TO_CONVERSATION:
                cmd: AddToConversationCommand = command
                conversation = self.get_conversation(cmd.conversation_id)
                if conversation is not None:
                    conversation.messages.extend(messages)
            else:
                raise ValueError(f"Unknown command type: {command.type}")

        return conversation_ids
