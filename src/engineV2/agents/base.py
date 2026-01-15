from __future__ import annotations
from abc import abstractmethod

from pydantic_ai.agent import Agent

from config import MAX_RETRIES
from engineV2.agents.model import AGENT_MODEL


class BaseAgent(Agent):
    def __init__(self, *args, **kw) -> None:
        super().__init__(AGENT_MODEL, retries=MAX_RETRIES, *args, **kw)

    @abstractmethod
    def build_user_prompt(self, *args, **kw) -> str: ...
