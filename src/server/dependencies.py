import logging
from typing import AsyncGenerator, Type

from aiokafka import AIOKafkaProducer
from fastapi import Request

from config import COOKIE_ALIAS
from core.enums import MessagePlatformType
from engine.base_action_handler import BaseActionHandler
from engine.discord.action_handler import DiscordActionHandler
from infra import DiscordClientManager, KafkaManager
from infra.discord_client_manager import DiscordClientManager
from infra.kafka_manager import KafkaManager
from utils.db import smaker
from server.exc import JWTError
from server.services import JWTService
from server.typing import JWTPayload


async def depends_db_sess():
    async with smaker.begin() as s:
        try:
            yield s
        except:
            await s.rollback()
            raise


def depends_jwt(is_authenticated: bool = True):
    """Verify the JWT token from the request cookies and validate it."""
    async def func(req: Request)-> JWTPayload:
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

        payload = JWTService.decode_jwt(token)
        return await JWTService.validate_payload(payload, is_authenticated=is_authenticated)

    return func

async def depends_kafka_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    return KafkaManager.get_producer()


def depends_action_handler(platform: MessagePlatformType):
    handler_cls: dict[MessagePlatformType, Type[BaseActionHandler]] = {
        MessagePlatformType.DISCORD: DiscordActionHandler
    }
    handlers: dict[MessagePlatformType, BaseActionHandler] = {}

    def wrapper() -> BaseActionHandler:
        nonlocal handlers, platform
        if platform not in handlers:
            handlers[platform] = handler_cls[platform](
                DiscordClientManager.client,
                logging.getLogger(f"global-{platform.value.lower()}-handler"),
            )
        return handlers[platform]

    return wrapper


depends_discord_action_handler = depends_action_handler(MessagePlatformType.DISCORD)
