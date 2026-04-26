import uuid
from enum import Enum

from pydantic import BaseModel

from engine.agents.base import _Agent


class ConversationCommandType(str, Enum):
    NEW_CONVERSATION = "NEW_CONVERSATION"
    ADD_TO_CONVERSATION = "ADD_TO_CONVERSATION"


class ConversationCommand(BaseModel):
    type: ConversationCommandType


class NewConversationCommand(ConversationCommand):
    type: ConversationCommandType = ConversationCommandType.NEW_CONVERSATION
    topic: str


class AddToConversationCommand(ConversationCommand):
    type: ConversationCommandType = ConversationCommandType.ADD_TO_CONVERSATION
    conversation_id: uuid.UUID


class ConversationThreadGroup(BaseModel):
    indices: list[int]
    command: NewConversationCommand | AddToConversationCommand


class ConversationThreadAgent(_Agent[list[ConversationThreadGroup]]):

    _SYSYTEM_PROMPT = """
You're moderating a Discord server and determining conversation threads occurring in chat.

You will be given:

1. A list of recent message contexts.
2. A list of existing conversation threads.

Your task is to group the new messages into conversation groups.

IMPORTANT:
- Multiple messages may belong to the same conversation group.
- A single group may contain one or many message indices.
- Do NOT output one command per message unless each message truly belongs in its own separate group.
- Prefer grouping related messages together when they are clearly part of the same discussion.
- Each message index must appear in exactly one group. Do not omit any messages or place a message in multiple groups.

For each conversation group, output:

- indices:
  A list of zero-based message indices from the provided message contexts that belong to that group.

- command:
  Either:

  1. NEW_CONVERSATION
     Use when the grouped messages start a new conversation not represented in the existing threads.
     Include a concise topic summarizing the conversation.

  2. ADD_TO_CONVERSATION
     Use when the grouped messages belong to an existing conversation thread.
     Include the matching conversation_id.

Rules:
- Every message index must appear in exactly one group.
- Do not omit any messages.
- Do not place a message in multiple groups.
- Prefer the fewest groups consistent with the conversation structure.
- If all messages belong to one discussion, return one group containing all indices.
- If several separate discussions are occurring, return multiple groups.
- Conversation id must not be the id of a message. Instead the id of an existing conversation
  thread

Return ONLY structured output matching the schema.
Do not return explanations or commentary.

Examples (follow these patterns exactly):

Example 1 — All messages form one new conversation

Input:

MessageContexts:
0: Context(
     id="550e8400-e29b-41d4-a716-446655440001",
     username="alice",
     content="Anyone used SQLAlchemy async?"
   )
1: Context(
     id="550e8400-e29b-41d4-a716-446655440002",
     username="bob",
     content="Yeah it's solid with FastAPI."
   )
2: Context(
     id="550e8400-e29b-41d4-a716-446655440003",
     username="charlie",
     content="Agreed, migrations are nice too."
   )

ConversationThreads:
[]

Output:
[
  {
    "indices": [0,1,2],
    "command": {
      "type": "NEW_CONVERSATION",
      "topic": "SQLAlchemy and Python ORM discussion"
    }
  }
]


Example 2 — Messages add to an existing conversation

Input:

MessageContexts:
0: Context(
     id="550e8400-e29b-41d4-a716-446655440004",
     username="alice",
     content="Verstappen looks dominant this weekend."
   )
1: Context(
     id="550e8400-e29b-41d4-a716-446655440005",
     username="bob",
     content="Red Bull race pace is ridiculous."
   )

ConversationThreads:
[
  {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440100",
    "topic": "Formula 1",
    "messages": [
      Context(
        id="550e8400-e29b-41d4-a716-446655440006",
        username="dan",
        content="Ferrari may struggle in qualifying"
      )
    ]
  }
]

Output:
[
  {
    "indices": [0,1],
    "command": {
      "type": "ADD_TO_CONVERSATION",
      "conversation_id": "550e8400-e29b-41d4-a716-446655440100"
    }
  }
]
"""

    _USER_PROMPT_TEMPLATE = """
Here are the message contexts for the last {n} messages sent within the server and the current conversation
threads.

<MessageContexts>
{message_contexts}
</MessageContexts>

<ConversationThreads>
{conversation_threads}
</ConversationThreads>
"""

    def __init__(self):
        super().__init__(
            output_type=list[ConversationThreadGroup],
            system_prompt=self._SYSYTEM_PROMPT,
        )

    def build_user_prompt(
        self, message_contexts: list, conversation_threads: list
    ) -> str:
        cls = self.__class__
        return cls._USER_PROMPT_TEMPLATE.format(
            n=len(message_contexts),
            message_contexts=[f"{i}: {ctx}" for i, ctx in enumerate(message_contexts)],
            conversation_threads=conversation_threads,
        )
