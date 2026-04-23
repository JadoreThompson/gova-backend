from engine.agents.conversation_thread import (
    ConversationCommandType,
    ConversationThreadAgent,
)
from engine.conversation.discord.conversation import DiscordConversation
from tests.engine.util import make_discord_message


def test_thread_creation():
    message_contexts = [
        make_discord_message("Hey, how are you doing?", user_id=123),
    ]

    agent = ConversationThreadAgent()

    user_prompt = agent.build_user_prompt(
        message_contexts=message_contexts,
        conversation_threads=[],
    )

    res = agent.run_sync(user_prompt)
    output = res.output

    assert isinstance(output, list)
    assert len(output) == 1
    assert output[0].command.type == ConversationCommandType.NEW_CONVERSATION


def test_thread_group_creation_all_messages_new_conversation():
    message_contexts = [
        make_discord_message("Anyone know a good Python ORM?", user_id=123),
        make_discord_message("I like SQLAlchemy personally.", user_id=456),
        make_discord_message("Same, especially with async support.", user_id=789),
    ]

    agent = ConversationThreadAgent()

    res = agent.run_sync(
        agent.build_user_prompt(
            message_contexts=message_contexts,
            conversation_threads=[],
        )
    )

    output = res.output

    assert len(output) == 1

    group = output[0]
    assert group.indicies == [0, 1, 2]
    assert group.command.type == ConversationCommandType.NEW_CONVERSATION
    assert group.command.topic


def test_thread_group_creates_new_conversation_when_existing_threads_are_unrelated():
    message_contexts = [
        make_discord_message(
            "Did you see the qualifying pace from Verstappen?", user_id=101
        ),
        make_discord_message(
            "Yeah, Red Bull looks dominant again this season.", user_id=102
        ),
        make_discord_message(
            "Ferrari strategy will probably ruin Sunday though.", user_id=103
        ),
    ]

    conversation_threads = [
        DiscordConversation(
            conversation_id="dogs_thread_123",
            channel_id=1,
            topic="Dogs",
            messages=[
                make_discord_message(
                    "What dog breed is easiest to train?", user_id=555
                ),
                make_discord_message("Border collies are brilliant.", user_id=556),
            ],
        ).to_dict(),
    ]

    agent = ConversationThreadAgent()

    res = agent.run_sync(
        agent.build_user_prompt(
            message_contexts=message_contexts,
            conversation_threads=conversation_threads,
        )
    )

    output = res.output
    group = output[0]

    assert len(output) == 1
    assert group.indicies == [0, 1, 2]
    assert group.command.type == ConversationCommandType.NEW_CONVERSATION
    assert group.command.topic


def test_thread_addition():
    message_contexts = [
        make_discord_message("Hey, how are you doing?", user_id=123),
    ]

    conversation_threads = [
        DiscordConversation(
            conversation_id="random_id_123_abcdef",
            channel_id=1,
            topic="Greeting",
            messages=[
                make_discord_message("Hey, how are you doing?", user_id=123),
            ],
        ).to_dict()
    ]

    agent = ConversationThreadAgent()

    res = agent.run_sync(
        agent.build_user_prompt(
            message_contexts=message_contexts,
            conversation_threads=conversation_threads,
        )
    )

    output = res.output

    assert len(output) == 1
    assert output[0].command.type == ConversationCommandType.ADD_TO_CONVERSATION
    assert output[0].command.conversation_id == "random_id_123_abcdef"


def test_thread_group_adds_messages_to_related_existing_conversation():
    message_contexts = [
        make_discord_message("Verstappen looked rapid in qualifying.", user_id=101),
        make_discord_message(
            "I think Red Bull takes the race tomorrow too.", user_id=102
        ),
    ]

    conversation_threads = [
        DiscordConversation(
            conversation_id="f1_thread_123",
            channel_id=1,
            topic="Formula 1 discussion",
            messages=[
                make_discord_message(
                    "Ferrari looked competitive in practice.", user_id=777
                ),
            ],
        ).to_dict()
    ]

    agent = ConversationThreadAgent()

    output = agent.run_sync(
        agent.build_user_prompt(
            message_contexts=message_contexts,
            conversation_threads=conversation_threads,
        )
    ).output

    group = output[0]

    assert len(output) == 1
    assert group.indicies == [0, 1]
    assert group.command.type == ConversationCommandType.ADD_TO_CONVERSATION
    assert group.command.conversation_id == "f1_thread_123"


def test_thread_group_adds_to_related_conversation_and_ignores_unrelated_conversation():
    message_contexts = [
        make_discord_message(
            "Mercedes upgrades might change the constructors battle.", user_id=201
        ),
        make_discord_message("Yeah McLaren has looked strong too.", user_id=202),
    ]

    conversation_threads = [
        DiscordConversation(
            conversation_id="dogs_thread_999",
            channel_id=1,
            topic="Dogs",
            messages=[
                make_discord_message(
                    "Golden retrievers are great family dogs.", user_id=555
                ),
            ],
        ).to_dict(),
        DiscordConversation(
            conversation_id="f1_thread_456",
            channel_id=1,
            topic="Formula 1",
            messages=[
                make_discord_message("Who has the best midfield package?", user_id=556),
            ],
        ).to_dict(),
    ]

    agent = ConversationThreadAgent()

    output = agent.run_sync(
        agent.build_user_prompt(
            message_contexts=message_contexts,
            conversation_threads=conversation_threads,
        )
    ).output

    group = output[0]

    assert len(output) == 1
    assert group.indicies == [0, 1]
    assert group.command.type == ConversationCommandType.ADD_TO_CONVERSATION
    assert group.command.conversation_id == "f1_thread_456"
