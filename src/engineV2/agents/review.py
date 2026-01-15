from enum import Enum
from typing import Generic, Type, TypeVar

from pydantic import BaseModel, field_validator

from engineV2.actions.base import BaseAction, BasePerformedAction
from engineV2.contexts.discord import DiscordMessageContext
from models import CustomBaseModel
from .base import BaseAgent


AP = TypeVar("P", bound=BaseAction)
AT = TypeVar("T", bound=Enum)
RA = TypeVar("")

# class ReviewAgentOutput(CustomBaseModel, Generic[A]):
# action: A | None = None


class ReviewAgentAction(CustomBaseModel, Generic[AT]):
    type: AT
    params: dict


class ReviewAgentOutput(CustomBaseModel):
    action: ReviewAgentAction | None = None
    severity_score: float

    @field_validator("severity_score", mode="after")
    def round_values(cls, v):
        return round(v, 2)


class ReviewAgent(BaseAgent):
    _instance = None
    _SYSTEM_PROMPT = """
    You're a senior moderator with 5+ years of experience moderating discord
    communities.
    """

    _USER_PROMPT_TMPL = """
    Below is a summary of the server you're currently overseeing.

    <ServerSummary>
    {server_summary}
    </ServerSummary>

    Here are the guidelines for the server that the owner has given you

    <ServerGuidelines>
    {guidelines}
    </ServerGuidelines>

    A message has come through and your task is to decide whether or not this
    message violates the guidelines in anyway and score the severity from 0 to 1
    where 1 is a complete violation and 0 is no violation of any of the guidelines
    rounded to 2dp. If you score it low, it's assumed you won't return an action.
    However if you score it high then it's assumed you will return an action. Below
    are definitions for the actions availabe to you. If you've chosen an action you're
    to fill in the necessary values for the params object.

    <Message>
    {message}
    </Message>

    <ActionDefinitions>
    {action_definitions}
    </ActionDefinitions>

    Your output should follow the described
    """

    def __new__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, *, output_type: Type[ReviewAgentOutput]):
        cls = self.__class__
        super().__init__(system_prompt=cls._SYSTEM_PROMPT, output_type=output_type)

    def build_user_prompt(
        self,
        server_summary: str,
        guidelines: str,
        message: DiscordMessageContext,
        action_definitions: list[dict],
    ):
        cls = self.__class__
        return cls._USER_PROMPT_TMPL.format(
            server_summary=server_summary,
            guidelines=guidelines,
            message=message.model_dump(mode="json"),
            action_definitions=action_definitions,
        )
