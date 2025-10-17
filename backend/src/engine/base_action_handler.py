from abc import abstractmethod

from engine.base_action import BaseAction


class BaseActionHandler:
    @abstractmethod
    async def handle(self, action: BaseAction): ...