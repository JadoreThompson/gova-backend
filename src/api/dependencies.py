from typing import AsyncGenerator, Type, TypeVar

from aiokafka import AIOKafkaProducer
from fastapi import Depends, Request

from config import COOKIE_ALIAS
from infra.db import smaker
from services.jwt import JWTService, JWTError
from services.kafka import KafkaProducerManager
from .types import JWTPayload


T = TypeVar("T")


async def depends_db_sess():
    async with smaker.begin() as s:
        try:
            yield s
        except:
            await s.rollback()
            raise


def depends_jwt(is_verified: bool = True):
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

        return await JWTService.validate_jwt(token, is_verified=is_verified)

    return func


async def depends_kafka_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    return KafkaProducerManager.get_producer()


def CSVQuery(name: str, Typ: Type[T]):
    def func(req: Request) -> list[T]:
        vals = req.query_params.get(name)
        if vals:
            return [Typ(val.strip()) for val in vals.strip().split(",")]

    return Depends(func)
