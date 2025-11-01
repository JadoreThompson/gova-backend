from abc import ABC, abstractmethod

from engine.base.base_action import BaseAction
from engine.models import BaseMessageContext


class BaseActionHandler(ABC):
    @abstractmethod
    async def handle(self, action: BaseAction, ctx: BaseMessageContext) -> bool: ...
