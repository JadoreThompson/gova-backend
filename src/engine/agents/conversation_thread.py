import uuid
from enum import Enum

from pydantic import BaseModel
from pydantic_ai import Agent, AgentRunResult

from engine.agents.base import BaseAgent


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


class ConversationThreadAgentOutput(BaseModel):
  message_id: uuid.UUID
  command: NewConversationCommand | AddToConversationCommand


class ConversationThreadGroup(BaseModel):
  indicies: list[int]
  command: NewConversationCommand | AddToConversationCommand


class ConversationThreadAgent(BaseAgent[list[ConversationThreadGroup]]):
  _EXAMPLES = """
Example 1 — All messages form one new conversation

Input:

MessageContexts:
0: alice: "Anyone used SQLAlchemy async?"
1: bob: "Yeah it's solid with FastAPI."
2: charlie: "Agreed, migrations are nice too."

ConversationThreads:
[]

Output:
[
  {
    "indicies": [0,1,2],
    "command": {
      "type": "NEW_CONVERSATION",
      "topic": "SQLAlchemy and Python ORM discussion"
    }
  }
]


Example 2 — Messages add to an existing conversation

Input:

MessageContexts:
0: alice: "Verstappen looks dominant this weekend."
1: bob: "Red Bull race pace is ridiculous."

ConversationThreads:
[
  {
    "conversation_id": "f1_thread_123",
    "topic": "Formula 1",
    "messages": [
      "Ferrari may struggle in qualifying"
    ]
  }
]

Output:
[
  {
    "indicies": [0,1],
    "command": {
      "type": "ADD_TO_CONVERSATION",
      "conversation_id": "f1_thread_123"
    }
  }
]


Example 3 — Existing conversations unrelated -> create new thread

Input:

MessageContexts:
0: alice: "Has anyone tried Rust for backend work?"
1: bob: "Ownership is painful at first."

ConversationThreads:
[
  {
    "conversation_id": "dogs_77",
    "topic": "Dogs",
    "messages": [
      "Golden retrievers are great"
    ]
  }
]

Output:
[
  {
    "indicies": [0,1],
    "command": {
      "type": "NEW_CONVERSATION",
      "topic": "Rust backend discussion"
    }
  }
]


Example 4 — Multiple simultaneous groups

Input:

MessageContexts:
0: alice: "Anyone use PostgreSQL logical replication?"
1: bob: "Yeah wal2json is useful."

2: mike: "Did you watch qualifying today?"
3: sara: "Verstappen pole again."

ConversationThreads:
[
  {
    "conversation_id":"f1_thread_456",
    "topic":"Formula 1",
    "messages":[
      "Who has the strongest midfield?"
    ]
  }
]

Output:
[
  {
    "indicies":[0,1],
    "command":{
      "type":"NEW_CONVERSATION",
      "topic":"PostgreSQL replication"
    }
  },
  {
    "indicies":[2,3],
    "command":{
      "type":"ADD_TO_CONVERSATION",
      "conversation_id":"f1_thread_456"
    }
  }
]


Example 5 — Unrelated messages should not be over-grouped

Input:

MessageContexts:
0: alice: "Anyone know a good monitor arm?"
1: bob: "Liverpool looked awful yesterday."

ConversationThreads:
[]

Output:
[
  {
    "indicies":[0],
    "command":{
      "type":"NEW_CONVERSATION",
      "topic":"Monitor arm recommendations"
    }
  },
  {
    "indicies":[1],
    "command":{
      "type":"NEW_CONVERSATION",
      "topic":"Football discussion"
    }
  }
]
"""

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

- indicies:
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

Return ONLY structured output matching the schema.
Do not return explanations or commentary.

Examples (follow these patterns exactly):
{examples}
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
          system_prompt=self._SYSYTEM_PROMPT.format(examples=self._EXAMPLES),
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
