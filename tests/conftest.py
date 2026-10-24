import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import get_session
from app.integrations.fcm import get_push_notifier
from app.integrations.firebase import get_identity_provider
from app.integrations.redis import get_response_cache
from app.integrations.storage import get_object_storage
from app.integrations.stripe import get_payment_gateway
from app.main import app
from app.models import Base
from tests.fakes import FakeIdentityProvider, FakeIntegrations, FakeResponseCache

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/app_test"
)


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def identity() -> FakeIdentityProvider:
    return FakeIdentityProvider()


@pytest.fixture
def cache() -> FakeResponseCache:
    return FakeResponseCache()


@pytest.fixture
def integrations() -> FakeIntegrations:
    return FakeIntegrations()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    identity: FakeIdentityProvider,
    cache: FakeResponseCache,
    integrations: FakeIntegrations,
) -> AsyncIterator[AsyncClient]:
    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_identity_provider] = lambda: identity
    app.dependency_overrides[get_response_cache] = lambda: cache
    app.dependency_overrides[get_push_notifier] = lambda: integrations.push
    app.dependency_overrides[get_object_storage] = lambda: integrations.storage
    app.dependency_overrides[get_payment_gateway] = lambda: integrations.gateway
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
