import uuid
from enum import Enum
from typing import Generic, TypeVar

from pydantic import field_validator

from engine.contexts.discord import DiscordMessageContext
from engine.conversation.conversation import Conversation
from models import CustomBaseModel
from .base import _Agent


AT = TypeVar("AT", bound=Enum)


class ReviewAgentAction(CustomBaseModel, Generic[AT]):
    type: str
    params: dict


class ReviewAgentOutput(CustomBaseModel):
    action: ReviewAgentAction | None = None
    severity_score: float
    reason: str

    @field_validator("severity_score", mode="after")
    def round_values(cls, v):
        return round(v, 2)


class ReviewAgentV2(_Agent[list[ReviewAgentOutput]]):
    
    _SYSTEM_PROMPT = """
# Task

Your task is to evalauate a set of messages from a Discord server against the community guidelines
and determine if any moderation action is warranted. You will be provided with the server summary,
the community guidelines, the conversation history for context, and a list of new messages that 
require your review. For each new message, you must assign a severity score indicating how much 
it violates the guidelines, and decide on the most appropriate action to take (if any). You must also
provide a clear reason for your decision, tied to the specific guideline(s) that were violated.

# Rules

- **CRITICAL**: You must ONLY moderate messages explicitly listed in the "Messages Under Review" section.
  Historical messages in conversations are provided for context only and have already been processed.
- **Proportionality**: Match your response to the severity of the violation. A first-time
  minor slip doesn't warrant the same response as repeated malicious behavior.
- **Context Awareness**: Consider the server and channel's purpose, ongoing conversation, and the
  member's history when making decisions.
- **Restraint**: Having power doesn't mean using it constantly. The best moderation is
  often invisible - communities thrive when members self-regulate.
- **Consistency**: Apply standards uniformly. Your credibility depends on predictable,
  fair enforcement.
- **CRITICICAL**: You're not to perform an evaluation based on a message sent within the conversation.
  These messages are for context only and have already been processed. You are only to evaluate the messages 
  explicitly listed in the "Messages Under Review" section.

# Boundaries

- You moderate; you do not participate. Never engage in casual conversation, answer
  questions unrelated to moderation, or insert yourself into discussions.
- If granted reply capabilities, use them exclusively for rule enforcement communications.
- When uncertain, err on the side of caution - a lower severity score with no action is
  better than over-moderation.

## Severity Scoring (0.0 - 1.0)

- **0.0 - 0.2**: Compliant or negligible concern. No action needed.
- **0.2 - 0.4**: Minor issue. May warrant a gentle reminder or note for tracking.
- **0.4 - 0.6**: Moderate violation. Warning or light action appropriate.
- **0.6 - 0.8**: Serious violation. Stronger action warranted (timeout, message removal).
- **0.8 - 1.0**: Severe violation. Immediate and firm action required.
"""

    _USER_PROMPT_TEMPLATE = """
# Server Summary
{server_summary}

# Community Guidelines
{guidelines}

# Conversation History (for context, already processed)
{conversations}

# Messages Under Review (NEW messages that require your evaluation)
{messages}

# Available Actions

The server owner has granted you the following moderation powers. You are not obligated
to use any action - only act when genuinely warranted. Choose the action that best fits
the situation, considering both the violation and the member's history.

# Action Parameter Definitions

{action_params}

## Previous Actions Record

Here's a record of your previous actions taken. Use this to apply progressive enforcement —
if a user has already been warned, escalate appropriately rather than repeating the same action.

{prev_actions}

# Community-Specific Instructions

{instructions}
"""

    _DEFAULT_INSTRUCTIONS = """
Use progressive enforcement when dealing with repeat offenders. If a member has already
been warned for a particular type of violation, escalate to the next appropriate action
rather than issuing another warning.

When in doubt about whether something violates guidelines, consider the intent and impact.
Genuine mistakes deserve more leniency than deliberate provocation.
"""

    def __init__(self, *args, **kw):
        cls = self.__class__
        kw["output_type"] = list[ReviewAgentOutput]
        kw["system_prompt"] = cls._SYSTEM_PROMPT
        super().__init__(*args, **kw)

    def build_user_prompt(
        self,
        server_summary: str,
        guidelines: str,
        conversations: list[Conversation],
        user_id: str,
        messages: list[
            tuple[uuid.UUID, DiscordMessageContext]
        ],  # (conversation_id, msg)
        action_params: list[dict],
        prev_actions: list[dict],
        instructions: str | None = None,
    ) -> str:
        cls = self.__class__
        formatted_messages = "\n".join(
            f"[conversation_id={conversation_id}] "
            f"user={msg.username} (id={msg.user_id}): {msg.content}"
            for conversation_id, msg in messages
        )
        formatted_conversations = "\n".join(str(c.to_dict()) for c in conversations)
        return cls._USER_PROMPT_TEMPLATE.format(
            user_id=user_id,
            server_summary=server_summary,
            guidelines=guidelines,
            conversations=formatted_conversations,
            messages=formatted_messages,
            action_params=action_params,
            prev_actions=prev_actions if prev_actions else "No previous actions.",
            instructions=instructions or cls._DEFAULT_INSTRUCTIONS,
        )
