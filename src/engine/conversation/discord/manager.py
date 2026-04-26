import uuid
from engine.contexts.discord import DiscordMessageContext
from engine.conversation.exception import ConversationDoesNotExistException
from .conversation import DiscordConversation
from engine.agents.conversation_thread import (
    ConversationThreadGroup,
    ConversationCommandType,
    NewConversationCommand,
    AddToConversationCommand,
)


class DiscordConversationManager:
    def __init__(self):
        self._conversations: dict[str, DiscordConversation] = {}
        self.auto_prune = True

    @property
    def conversations(self) -> dict[str, DiscordConversation]:
        return self._conversations

    def get_conversation(self, conversation_id: str) -> DiscordConversation | None:
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]
        raise ConversationDoesNotExistException(
            f"Conversation with id '{conversation_id}' does not exist."
        )

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
            list[UUID]: list of interacted conversation_ids
        """
        conversation_ids: list[uuid.UUID] = []

        for group in groups:
            indices = group.indices
            command = group.command
            messages = [message_contexts[i] for i in indices]

            if command.type == ConversationCommandType.NEW_CONVERSATION:
                cmd: NewConversationCommand = command
                conversation = DiscordConversation(
                    topic=cmd.topic, channel_id=messages[0].channel_id
                )
                conversation.messages.extend(messages)
                conversation_ids.append(conversation.conversation_id)
                self.add_conversation(conversation)
            elif command.type == ConversationCommandType.ADD_TO_CONVERSATION:
                cmd: AddToConversationCommand = command
                conversation = self.get_conversation(cmd.conversation_id)
                conversation.messages.extend(messages)
                conversation_ids.append(conversation.conversation_id)
            else:
                raise ValueError(f"Unknown command type: {command.type}")

        return conversation_ids
