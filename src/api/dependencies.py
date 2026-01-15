from typing import AsyncGenerator, Type, TypeVar

from aiokafka import AIOKafkaProducer
from fastapi import Depends, Request

from config import COOKIE_ALIAS
from enums import MessagePlatform
from engine.base.base_action_handler import BaseActionHandler
from engine.discord.action_handler import DiscordActionHandler
from infra import DiscordClientManager, KafkaManager
from infra.db import smaker
from infra.discord_client_manager import DiscordClientManager
from infra.kafka_manager import KafkaManager
from server.exc import JWTError
from server.services import JWTService
from server.typing import JWTPayload


T = TypeVar("T")


async def depends_db_sess():
    async with smaker.begin() as s:
        try:
            yield s
        except:
            await s.rollback()
            raise


def depends_jwt(is_authenticated: bool = True):
    """Verify the JWT token from the request cookies and validate it."""

    async def func(req: Request) -> JWTPayload:
        """
        Args:
            req (Request)

        Raises:
            JWTError: If the JWT token is missing, expired, or invalid.

        Returns:
            JWTPayload: The decoded JWT payload if valid.
        """
        token = req.cookies.get(COOKIE_ALIAS)
        if not token:
            raise JWTError("Authentication token is missing")

        return await JWTService.validate_jwt(token, is_authenticated=is_authenticated)

    return func


async def depends_kafka_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    return KafkaManager.get_producer()


def depends_action_handler(platform: MessagePlatform):
    handler_cls: dict[MessagePlatform, Type[BaseActionHandler]] = {
        MessagePlatform.DISCORD: DiscordActionHandler
    }
    handlers: dict[MessagePlatform, BaseActionHandler] = {}

    def wrapper() -> BaseActionHandler:
        nonlocal handlers, platform
        if platform not in handlers:
            handlers[platform] = handler_cls[platform](DiscordClientManager.client)
        return handlers[platform]

    return wrapper


depends_discord_action_handler = depends_action_handler(MessagePlatform.DISCORD)


def CSVQuery(name: str, Typ: Type[T]):
    def func(req: Request) -> list[T]:
        vals = req.query_params.get(name)
        return [Typ(val.strip()) for val in vals.strip().split(",")]

    return Depends(func)
