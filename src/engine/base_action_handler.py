from abc import abstractmethod

from engine.base_action import BaseAction
from engine.models import BaseMessageContext


class BaseActionHandler:
    @abstractmethod
    async def handle(self, action: BaseAction, ctx: BaseMessageContext) -> bool: ...
