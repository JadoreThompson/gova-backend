from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from typing import AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker, Session

from config import DB_ENGINE, DB_ENGINE_SYNC


smaker = sessionmaker(DB_ENGINE, class_=AsyncSession, autocommit=False, autoflush=False)
smaker_sync = sessionmaker(DB_ENGINE_SYNC, class_=Session, autocommit=False, autoflush=False)


def get_datetime():
    return datetime.now(UTC)


@asynccontextmanager
async def get_db_sess() -> AsyncGenerator[AsyncSession, None]:
    async with smaker.begin() as s:
        try:
            yield s
        except:
            await s.rollback()
            raise


@contextmanager
def get_db_sess_sync() -> Generator[Session, None, None]:
    with smaker_sync.begin() as s:
        try:
            yield s
        except:
            s.rollback()
            raise
