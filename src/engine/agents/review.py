from enum import Enum
from typing import Generic, Type, TypeVar

from pydantic import field_validator

from engine.contexts.discord import DiscordMessageContext
from models import CustomBaseModel
from .base import BaseAgent


AT = TypeVar("AT", bound=Enum)


class ReviewAgentAction(CustomBaseModel, Generic[AT]):
    type: AT
    params: dict


class ReviewAgentOutput(CustomBaseModel):
    action: ReviewAgentAction | None = None
    severity_score: float
    reason: str

    @field_validator("severity_score", mode="after")
    def round_values(cls, v):
        return round(v, 2)


class ReviewAgent(BaseAgent):
    _SYSTEM_PROMPT = """
    You've got 5 years of experience moderating some of the largest discord
    servers where you've enforced guidelines and mtainied the quality
    of the chat.
    
    The server owners have provided you with a list of actions you can 
    wield and take advantage of only when necessary. Abuse of power will
    reuslt in your termination, leaving you with no food on the table.
    
    If you're granted the power to reply to messages you're only to 
    reply to messages when you're enforcing rules, not to answer stray 
    questions or take part in a conversation in any manner.

    Your task is to score the message on it's severity between 0 and 1.
    Where 0 signifies compliance with the guidelines and 1 is a strong
    violation of a guideline. Also the reasoning for your score and / or
    taking that action.
    """

    _USER_PROMPT_TEMPLATE = """
    Below is a summary of the discord server you're currently moderating.
    This'll help you understand type of conversations expected within the chat.

    <ServerSummary>
    {server_summary}
    </ServerSummary>

    Here are the guidelines for the server you're to enforce.

    <ServerGuidelines>
    {guidelines}
    </ServerGuidelines>

    Here is the most recent message sent alont with it's metadata. Your
    user_id is {user_id}.

    <Messages>
    {message}
    </Messages>

    Here's the current summary of the messages sent within the channel.
    
    <ChannelSummary>
    {channel_summary}
    </ChannelSummary>

    Below are the definitions of the actions you've granted power to use. Remember
    that it isn't compulsary to take an action but the action you choose to take must
    be the optimal action for that scenario. For example if the guidelines say no swearing
    and you've already warned the individual then it only makes sense to move to the next
    step which is timing out and progressively getting going higher and higher up the action
    chain.

    <ActionDefinitions>
    {action_params}
    </ActionDefinitions>
    """

    def __init__(self, *, output_type: Type[ReviewAgentOutput]):
        cls = self.__class__
        super().__init__(system_prompt=cls._SYSTEM_PROMPT, output_type=output_type)

    def build_user_prompt(
        self,
        user_id: str,
        server_summary: str,
        channel_summary: str,
        guidelines: str,
        message: DiscordMessageContext,
        action_params: list[dict],
    ):
        cls = self.__class__
        # print("\nAction Params:", action_params)
        return cls._USER_PROMPT_TEMPLATE.format(
            user_id=user_id,
            server_summary=server_summary,
            channel_summary=channel_summary,
            guidelines=guidelines,
            message=message.model_dump(mode="json"),
            action_params=action_params,
        )
