import uuid
from engine.agents.conversation_thread import (
    ConversationThreadGroup,
    NewConversationCommand,
    AddToConversationCommand,
)
from engine.conversation.discord.conversation import DiscordConversation
from engine.conversation.discord.manager import DiscordConversationManager
from tests.engine.util import make_discord_message


def test_manager_creates_new_conversation():
    manager = DiscordConversationManager()

    messages = [
        make_discord_message("Hello world", user_id=123),
        make_discord_message("How are you?", user_id=456),
    ]

    groups = [
        ConversationThreadGroup(
            indices=[0, 1],
            command=NewConversationCommand(topic="Greeting chat"),
        )
    ]

    created = manager.apply_thread_groups(groups, messages)

    assert len(created) == 1
    assert len(manager.conversations) == 1

    conversation = list(manager.conversations.values())[0]

    assert conversation.topic == "Greeting chat"
    assert len(conversation.messages) == 2


def test_manager_adds_messages_to_existing_conversation():
    manager = DiscordConversationManager()

    existing = DiscordConversation(
        topic="F1 Chat",
        channel_id=1,
        messages=[make_discord_message("old message")],
    )

    manager.add_conversation(existing)

    messages = [
        make_discord_message("new message 1", user_id=123),
        make_discord_message("new message 2", user_id=123),
    ]

    groups = [
        ConversationThreadGroup(
            indices=[0, 1],
            command=AddToConversationCommand(conversation_id=existing.conversation_id),
        )
    ]

    manager.apply_thread_groups(groups, messages)

    conversation = manager.get_conversation(existing.conversation_id)

    assert conversation is not None
    assert len(conversation.messages) == 3


def test_manager_creates_multiple_new_conversations():
    manager = DiscordConversationManager()

    messages = [
        make_discord_message("topic A"),
        make_discord_message("topic B"),
        make_discord_message("topic C"),
    ]

    groups = [
        ConversationThreadGroup(
            indices=[0],
            command=NewConversationCommand(topic="Topic A"),
        ),
        ConversationThreadGroup(
            indices=[1],
            command=NewConversationCommand(topic="Topic B"),
        ),
        ConversationThreadGroup(
            indices=[2],
            command=NewConversationCommand(topic="Topic C"),
        ),
    ]

    created = manager.apply_thread_groups(groups, messages)

    assert len(created) == 3
    assert len(manager.conversations) == 3


def test_manager_handles_non_overlapping_indices_correctly():
    manager = DiscordConversationManager()

    messages = [
        make_discord_message("msg 0"),
        make_discord_message("msg 1"),
        make_discord_message("msg 2"),
    ]

    groups = [
        ConversationThreadGroup(
            indices=[0, 1],
            command=NewConversationCommand(topic="Group 1"),
        ),
        ConversationThreadGroup(
            indices=[2],
            command=NewConversationCommand(topic="Group 2"),
        ),
    ]

    manager.apply_thread_groups(groups, messages)

    assert len(manager.conversations) == 2

    all_messages = [
        msg for conv in manager.conversations.values() for msg in conv.messages
    ]

    assert len(all_messages) == 3


def test_manager_add_to_missing_conversation_is_safe():
    manager = DiscordConversationManager()

    messages = [make_discord_message("orphan message")]

    groups = [
        ConversationThreadGroup(
            indices=[0],
            command=AddToConversationCommand(conversation_id=uuid.uuid4()),
        )
    ]

    result = manager.apply_thread_groups(groups, messages)

    assert result == []
    assert len(manager.conversations) == 0


def test_manager_invalid_index_raises():
    manager = DiscordConversationManager()

    messages = [make_discord_message("only message")]

    groups = [
        ConversationThreadGroup(
            indices=[999],
            command=NewConversationCommand(topic="bad group"),
        )
    ]

    import pytest

    with pytest.raises(IndexError):
        manager.apply_thread_groups(groups, messages)


def test_manager_preserves_message_order():
    manager = DiscordConversationManager()

    messages = [
        make_discord_message("first"),
        make_discord_message("second"),
        make_discord_message("third"),
    ]

    groups = [
        ConversationThreadGroup(
            indices=[2, 0, 1],
            command=NewConversationCommand(topic="order test"),
        )
    ]

    manager.apply_thread_groups(groups, messages)

    conversation = list(manager.conversations.values())[0]

    contents = [m.content for m in conversation.messages]

    assert contents == ["third", "first", "second"]
