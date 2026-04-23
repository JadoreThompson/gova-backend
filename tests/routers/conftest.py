

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from infra.db.models import Users, Moderators, EvaluationEvents, ActionEvents
from infra.db.utils import get_db_sess


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:password@localhost:5132/gova"
    )

    async def delete_all():
        async with engine.begin() as conn:
            await conn.execute(delete(Users))
            await conn.execute(delete(Moderators))
            await conn.execute(delete(EvaluationEvents))
            await conn.execute(delete(ActionEvents))
            await conn.commit()

    await delete_all()
    yield
    await delete_all()
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with get_db_sess() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client():
    from httpx import AsyncClient, ASGITransport
    from api.app import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()