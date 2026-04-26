from __future__ import annotations
from abc import abstractmethod
from typing import Generic, TypeVar

from pydantic_ai import AgentRunResult
from pydantic_ai.agent import Agent

from config import MAX_RETRIES
from engine.agents.settings import AGENT_MODEL

O = TypeVar("O")


class _Agent(Agent, Generic[O]):
    def __init__(self, *args, **kw) -> None:
        super().__init__(AGENT_MODEL, retries=MAX_RETRIES, *args, **kw)

    @abstractmethod
    def build_user_prompt(self, *args, **kw) -> str: ...

    async def run(self, *args, **kw) -> AgentRunResult[O]:
        return await super().run(*args, **kw)

    def run_sync(self, *args, **kw) -> AgentRunResult[O]:
        return super().run_sync(*args, **kw)
