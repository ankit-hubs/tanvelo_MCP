"""
Pytest configuration and test fixtures for Tanvelo
"""

import asyncio
import os
import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from app.config import settings

# Force testing environment for fast, isolated, deterministic unit testing
settings.TANVELO_ENV = "testing"
settings.RATE_LIMIT_ENABLED = False

from app.database import Base, get_db
from app.main import app
from app.services.auth_service import create_user_and_api_key

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True
)

test_async_session = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Create fresh database tables for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        yield session


@pytest.fixture
async def user_a(db_session: AsyncSession):
    user, key_model, raw_key = await create_user_and_api_key(
        db=db_session,
        email="user_a@tanvelo.ai",
        key_name="User A Key"
    )
    return {"user": user, "key_model": key_model, "raw_key": raw_key}


@pytest.fixture
async def user_b(db_session: AsyncSession):
    user, key_model, raw_key = await create_user_and_api_key(
        db=db_session,
        email="user_b@tanvelo.ai",
        key_name="User B Key"
    )
    return {"user": user, "key_model": key_model, "raw_key": raw_key}


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
